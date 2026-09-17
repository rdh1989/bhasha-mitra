"""End-to-end video dubbing pipeline: extract audio -> ASR -> translate ->
TTS -> re-mux. Designed to run inside a worker thread; reports progress via
the shared JobManager so the web UI can show real-time status.

Translation routing (see app/models/translate.py for why): three dedicated
IndicTrans2 checkpoints are used depending on the source/target pair -
English source uses the en-indic checkpoint, Indic source + Indic target uses
the indic-indic checkpoint, and Indic source + English target uses the
indic-en checkpoint - so translation is always direct, never pivoting
through an intermediate language or a second Whisper pass.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Union

import numpy as np
import soundfile as sf

from app.config import (
    INDIC_ASR_ENABLED,
    INDIC_TO_INDIC_USE_ENGLISH_PIVOT,
    ASR_REFINE_ENABLED,
    DOMAIN_PACK_ENABLED,
    TRANSLATION_CONTEXT_ENABLED,
    TRANSLATION_CONTEXT_MAX_EVENTS,
    TRANSLATION_CONTEXT_MAX_CHARS,
    TRANSLATION_CONTEXT_MAX_DURATION_SECONDS,
    LANGUAGES_BY_CODE,
    OUTPUTS_DIR,
    TTS_INTENSITY_GAIN_MAX,
    TTS_INTENSITY_GAIN_MIN,
    TTS_MAX_ALLOWED_COMPRESSION,
    TTS_MAX_PAUSE_SECONDS,
    TTS_MAX_UNIT_CHARACTERS,
    TTS_MILD_ADJUSTMENT_THRESHOLD,
    TTS_MIN_UNIT_SECONDS,
    TTS_MIN_PAUSE_SECONDS,
    TTS_PIPER_LENGTH_SCALE_MAX,
    TTS_PIPER_LENGTH_SCALE_MIN,
    TTS_PRESERVE_INTENSITY,
    TTS_PROSODY_ENABLED,
    TTS_RATE_TOLERANCE,
    TTS_REPLAN_THRESHOLD,
    TTS_NATURAL_FIT_THRESHOLD,
    TTS_SILENCE_THRESHOLD,
    TTS_SHORT_SEGMENT_SECONDS,
)
from app.jobs import JobCancelled, JobManager
from app.media import extract_audio, mux_video_with_audio, time_stretch_audio
from app.models.asr import ASREngine, Segment
from app.models.indic_asr import IndicASREngine
from app.models.memory_policy import get_memory_policy
from app.models.translate import TranslationEngine
from app.speech import refine_segments_by_audio, validate_asr_segments
from app.translation_planner import plan_translation_contexts
from app.translation_validation import has_unicode_corruption, source_linguistic_completeness
from app.entity_protection import protect_entities, restore_entities
from app.quality_guard import TranslationQualityGuard
from app.terminology import domain_pack_applies, protect_terms, restore_terms, terminology_consistency, validate_terminology
from app.subtitles import build_srt

if TYPE_CHECKING:
    from app.models.piper_tts import PiperTTSEngine
    from app.models.tts import TTSEngine

logger = logging.getLogger(__name__)

_SEGMENT_FORMAT = "quality-v4"
_MAX_MERGED_SEGMENT_DURATION = 15.0
_MAX_MERGED_SEGMENT_GAP = 1.0
_TRANSLATION_BATCH_SIZE = 4


@dataclass
class SpeechEvent:
    """Media-neutral target speech event used by duration planning."""

    event_id: int
    source_start: float
    source_end: float
    target_text: str
    source_text: str | None = None
    source_pause_intervals: list[tuple[float, float]] | None = None
    natural_target_duration: float | None = None
    target_start: float | None = None
    target_end: float | None = None
    duration_status: str = "OK"
    rate_decision: float | None = None
    warnings: list[str] | None = None


def run_pipeline(
    job_id: str,
    video_path: str,
    source_code: str,
    target_code: str,
    jobs: JobManager,
    asr: ASREngine,
    translator: TranslationEngine,
    translator_indic: TranslationEngine,
    translator_indic_en: TranslationEngine,
    tts: "Union[TTSEngine, PiperTTSEngine]",
) -> None:
    # Grouped as outputs/<video-name>/<job-id>/ so re-runs of the same source
    # video land side by side under one folder instead of scattering job dirs.
    video_stem = Path(video_path).stem
    work_dir = OUTPUTS_DIR / video_stem / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Job %s: pipeline started (video=%s, source_lang=%s, target_lang=%s)", job_id, video_path, source_code, target_code)

    # Log memory state at job start for OOM diagnostics.
    from app.models.memory_policy import get_memory_policy
    memory_policy = get_memory_policy()
    memory_policy.log_diagnostics()
    memory_before_job = memory_policy.get_process_memory_gb()
    jobs.update(job_id, message=f"Job started (current memory: {memory_before_job:.2f} GB)")
    heartbeat_stop = threading.Event()

    def emit_heartbeat() -> None:
        while not heartbeat_stop.wait(60):
            job = jobs.get(job_id)
            if job is None or job.done or job.cancel_requested:
                return
            jobs.update(
                job_id,
                message=f"Still working: {job.stage.replace('_', ' ')} ({job.progress:.0%} complete).",
            )

    heartbeat = threading.Thread(target=emit_heartbeat, name=f"job-heartbeat-{job_id}", daemon=True)
    heartbeat.start()
    try:
        jobs.raise_if_cancelled(job_id)
        target_lang = LANGUAGES_BY_CODE[target_code]

        audio_path = work_dir / "audio.wav"
        if audio_path.is_file():
            jobs.update(job_id, stage="extracting_audio", progress=0.05, message="Reusing extracted audio from previous attempt.")
        else:
            jobs.update(job_id, stage="extracting_audio", progress=0.02, message="Extracting audio from video...")
            try:
                extract_audio(str(video_path), str(audio_path))
            except Exception as exc:
                raise RuntimeError(f"Failed to extract audio from video: {exc}") from exc
        jobs.raise_if_cancelled(job_id)

        transcript_path = work_dir / "transcript.json"
        saved_transcript = _read_segments_json(transcript_path, required_format=_SEGMENT_FORMAT)
        if saved_transcript is not None:
            source_code, language_probability, segments = saved_transcript
            base_result = type("SavedTranscript", (), {"language": source_code, "language_probability": language_probability, "segments": segments})()
            jobs.update(job_id, stage="transcribing", progress=0.35, message="Reusing transcript from previous attempt.")
        else:
            jobs.update(job_id, stage="transcribing", progress=0.05, message="Transcribing speech...")

            def base_progress(frac: float) -> None:
                jobs.update(job_id, progress=0.05 + 0.30 * frac)

            try:
                base_result = asr.transcribe(
                    str(audio_path), source_language=source_code, task="transcribe", progress_cb=base_progress,
                )
            except Exception as exc:
                raise RuntimeError(f"Speech recognition failed: {exc}") from exc
            jobs.raise_if_cancelled(job_id)
            if not base_result.segments:
                raise RuntimeError("No speech was detected in the video's audio track.")
            raw_segments = list(base_result.segments)
            _write_segments_json(
                work_dir / "raw_transcript.json",
                raw_segments,
                language=source_code,
                language_probability=base_result.language_probability,
                segment_format="raw-v1",
            )
            base_result.segments = _drop_hallucinated_segments(job_id, jobs, base_result.segments, source_code)
            base_result.segments = _merge_asr_segments(base_result.segments)
            try:
                source_audio, source_rate = sf.read(str(audio_path), dtype="float32")
                base_result.segments, refinement_stats = refine_segments_by_audio(
                    source_audio, source_rate, base_result.segments
                ) if ASR_REFINE_ENABLED else (base_result.segments, {})
                logger.info("Job %s: audio-aware ASR refinement: %s", job_id, refinement_stats)
                logger.info("Job %s: refined transcript quality: %s", job_id, validate_asr_segments(base_result.segments))
            except Exception:
                logger.exception("Job %s: audio-aware ASR refinement failed; retaining merged ASR segments", job_id)
            _write_segments_json(
                transcript_path,
                base_result.segments,
                language=source_code,
                language_probability=base_result.language_probability,
                segment_format=_SEGMENT_FORMAT,
            )

        jobs.update(
            job_id,
            detected_source_lang=source_code,
            detected_source_lang_prob=base_result.language_probability,
            message=f"Detected source language '{source_code}' ({base_result.language_probability:.0%} confidence).",
        )

        translation_path = work_dir / "translation.json"
        translation_contexts, context_diagnostics = plan_translation_contexts(
            base_result.segments,
            max_events=TRANSLATION_CONTEXT_MAX_EVENTS if TRANSLATION_CONTEXT_ENABLED else 1,
            max_characters=TRANSLATION_CONTEXT_MAX_CHARS if TRANSLATION_CONTEXT_ENABLED else 100000,
            max_duration=TRANSLATION_CONTEXT_MAX_DURATION_SECONDS,
        )
        context_segments = [Segment(start=context.source_start, end=context.source_end, text=context.source_text) for context in translation_contexts]
        (work_dir / "translation_contexts.json").write_text(
            json.dumps({**context_diagnostics, "contexts": [
                {"context_id": c.context_id, "event_ids": list(c.event_ids), "source_start": c.source_start,
                 "source_end": c.source_end, "source_text": c.source_text, "planner_reason": c.planner_reason,
                 "source_segment_ids": [getattr(event, "source_segment_id", None) for event in c.source_events],
                 "linguistic_completeness": source_linguistic_completeness(c.source_text),
                 "context_status": c.context_status, "decision": c.decision,
                 "decision_reasons": list(c.decision_reasons),
                 "continuation_score": c.continuation_score, "boundary_score": c.boundary_score,
                 "dependency_score": c.dependency_score, "pause_score": c.pause_score,
                 "completion_score": c.completion_score}
                for c in translation_contexts
            ]}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        saved_translation = _read_segments_json(translation_path, required_format=_SEGMENT_FORMAT)
        if saved_translation is not None and _saved_translation_matches_contexts(saved_translation[2], translation_contexts):
            _saved_source, _saved_probability, saved_segments = saved_translation
            final_segments = _filter_saved_translations(job_id, jobs, context_segments, saved_segments)
            jobs.update(job_id, stage="translating", progress=0.55, message="Reusing translation from previous attempt.")
        else:
            if saved_translation is not None:
                logger.info("Ignoring translation checkpoint with stale event-level context mapping: %s", translation_path)
            final_segments = _translate(
                job_id, jobs, translator, translator_indic, translator_indic_en, base_result, source_code, target_code, target_lang
            )
            jobs.raise_if_cancelled(job_id)
            if not final_segments:
                raise RuntimeError("Translation produced no text to synthesize.")
            _write_segments_json(
                translation_path,
                final_segments,
                source_language=source_code,
                target_language=target_code,
                segment_format=_SEGMENT_FORMAT,
            )
        jobs.raise_if_cancelled(job_id)
        if not final_segments:
            raise RuntimeError("Translation produced no usable text to synthesize.")
        diagnostic_results = []
        for index, context in enumerate(translation_contexts):
            translated_text = final_segments[index][2] if index < len(final_segments) else ""
            _, terminology_matches, terminology_warnings = validate_terminology(
                context.source_text, translated_text, enabled=DOMAIN_PACK_ENABLED
            )
            warnings = list(terminology_warnings)
            completeness = source_linguistic_completeness(context.source_text)
            if completeness == "INCOMPLETE":
                warnings.append("linguistic_completeness")
            status = "PASS" if not warnings and translated_text else ("FLAG" if translated_text else "FAILED_OR_FILTERED")
            diagnostic_results.append({
                "context_id": context.context_id,
                "event_ids": list(context.event_ids),
                "source_segment_ids": [getattr(event, "source_segment_id", None) for event in context.source_events],
                "source_start": context.source_start,
                "source_end": context.source_end,
                "source_text": context.source_text,
                "translated_text": translated_text,
                "linguistic_completeness": completeness,
                "validation_status": status,
                "retry_count": 0,
                "terminology_status": "PASS" if not terminology_warnings else "FLAG",
                "terminology_matches": terminology_matches,
                "numeric_status": "PASS",
                "unicode_status": "FLAG" if has_unicode_corruption(translated_text) else "PASS",
                "semantic_status": "PASS" if not terminology_warnings else "FLAG",
                "warnings": warnings,
            })
        diagnostics_payload = {
            "context_diagnostics": context_diagnostics,
            "results": diagnostic_results,
            "terminology_consistency": terminology_consistency(diagnostic_results, enabled=DOMAIN_PACK_ENABLED),
        }
        diagnostics_text = json.dumps(diagnostics_payload, ensure_ascii=False, indent=2)
        (work_dir / "translation_diagnostics.json").write_text(diagnostics_text, encoding="utf-8")
        (work_dir / "translation_quality_diagnostics.json").write_text(diagnostics_text, encoding="utf-8")
        jobs.raise_if_cancelled(job_id)

        dubbed_audio_path = work_dir / "dubbed_audio.wav"
        if dubbed_audio_path.is_file():
            jobs.update(job_id, stage="synthesizing_speech", progress=0.85, message="Reusing synthesized speech from previous attempt.")
        else:
            jobs.update(
                job_id, stage="synthesizing_speech", progress=0.55,
                message=f"Synthesizing {len(final_segments)} speech segment(s)...",
            )
            dubbed_audio_path = _synthesize_and_align(job_id, jobs, tts, target_lang, audio_path, final_segments, work_dir)
        jobs.raise_if_cancelled(job_id)

        jobs.update(job_id, stage="muxing_video", progress=0.85, message="Generating subtitles...")
        jobs.raise_if_cancelled(job_id)
        subtitle_path = work_dir / "subtitles.srt"
        try:
            subtitle_path.write_text(build_srt(final_segments), encoding="utf-8")
        except Exception as exc:
            raise RuntimeError(f"Failed to generate subtitles: {exc}") from exc
        jobs.raise_if_cancelled(job_id)

        jobs.update(job_id, stage="muxing_video", progress=0.9, message="Combining dubbed audio and subtitles with the original video...")
        jobs.raise_if_cancelled(job_id)
        output_path = work_dir / f"{job_id}.mp4"
        try:
            mux_video_with_audio(str(video_path), str(dubbed_audio_path), str(output_path), subtitle_path=str(subtitle_path))
        except Exception as exc:
            raise RuntimeError(f"Failed to combine dubbed audio with video: {exc}") from exc
        jobs.raise_if_cancelled(job_id)

        jobs.update(
            job_id, stage="completed", progress=1.0, done=True,
            message="Done! Dubbed video is ready.",
            output_path=str(output_path),
        )
        logger.info("Job %s: pipeline completed successfully -> %s", job_id, output_path)
    except JobCancelled:
        logger.info("Job %s: cancellation completed", job_id)
        jobs.mark_cancelled(job_id)
    except Exception as exc:  # noqa: BLE001 - surface all failures to the UI
        logger.exception("Job %s: pipeline failed", job_id)
        jobs.update(job_id, stage="failed", done=True, error=str(exc), message=f"Failed: {exc}")
    finally:
        heartbeat_stop.set()
        heartbeat.join(timeout=1)


def run_audio_pipeline(
    job_id: str,
    audio_input_path: str,
    source_code: str,
    target_code: str,
    jobs: JobManager,
    asr: ASREngine,
    translator: TranslationEngine,
    translator_indic: TranslationEngine,
    translator_indic_en: TranslationEngine,
    tts: "Union[TTSEngine, PiperTTSEngine]",
) -> None:
    """Create a time-aligned dubbed WAV from a local audio source."""
    work_dir = OUTPUTS_DIR / Path(audio_input_path).stem / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        jobs.raise_if_cancelled(job_id)
        target_lang = LANGUAGES_BY_CODE[target_code]
        audio_path = work_dir / "audio.wav"
        jobs.update(job_id, stage="extracting_audio", progress=0.02, message="Preparing audio...")
        extract_audio(audio_input_path, str(audio_path))
        jobs.raise_if_cancelled(job_id)

        jobs.update(job_id, stage="transcribing", progress=0.05, message="Transcribing speech...")
        base_result = asr.transcribe(
            str(audio_path), source_language=source_code, task="transcribe",
            progress_cb=lambda fraction: jobs.update(job_id, progress=0.05 + 0.30 * fraction),
        )
        if not base_result.segments:
            raise RuntimeError("No speech was detected in the audio track.")
        base_result.segments = _merge_asr_segments(
            _drop_hallucinated_segments(job_id, jobs, base_result.segments, source_code)
        )
        if not base_result.segments:
            raise RuntimeError("No usable speech was detected in the audio track.")
        jobs.update(
            job_id,
            detected_source_lang=source_code,
            detected_source_lang_prob=base_result.language_probability,
            message=f"Detected source language '{source_code}' ({base_result.language_probability:.0%} confidence).",
        )
        final_segments = _translate(
            job_id, jobs, translator, translator_indic, translator_indic_en,
            base_result, source_code, target_code, target_lang,
        )
        if not final_segments:
            raise RuntimeError("Translation produced no usable text to synthesize.")
        jobs.raise_if_cancelled(job_id)
        jobs.update(
            job_id, stage="synthesizing_speech", progress=0.55,
            message=f"Synthesizing {len(final_segments)} speech segment(s)...",
        )
        dubbed_audio_path = _synthesize_and_align(
            job_id, jobs, tts, target_lang, audio_path, final_segments, work_dir
        )
        jobs.raise_if_cancelled(job_id)
        jobs.update(
            job_id, stage="completed", progress=1.0, done=True,
            message="Done! Dubbed audio is ready.", output_path=str(dubbed_audio_path),
        )
        logger.info("Job %s: audio pipeline completed successfully -> %s", job_id, dubbed_audio_path)
    except JobCancelled:
        logger.info("Job %s: audio cancellation completed", job_id)
        jobs.mark_cancelled(job_id)
    except Exception as exc:  # noqa: BLE001 - surface all failures to the UI
        logger.exception("Job %s: audio pipeline failed", job_id)
        jobs.update(job_id, stage="failed", done=True, error=str(exc), message=f"Failed: {exc}")


def run_text_pipeline(
    job_id: str,
    text_path: str,
    source_code: str,
    target_code: str,
    jobs: JobManager,
    translator: TranslationEngine,
    translator_indic: TranslationEngine,
    translator_indic_en: TranslationEngine,
) -> None:
    """Translate one persisted text input and write its translated TXT output."""
    work_dir = OUTPUTS_DIR / Path(text_path).stem / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        jobs.raise_if_cancelled(job_id)
        jobs.update(job_id, stage="translating", progress=0.05, message="Reading text input...")
        text = Path(text_path).read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError("Text is required.")
        target_lang = LANGUAGES_BY_CODE[target_code]
        base_result = SimpleNamespace(segments=[Segment(start=0.0, end=1.0, text=text)])
        translated = _translate(
            job_id, jobs, translator, translator_indic, translator_indic_en,
            base_result, source_code, target_code, target_lang,
        )
        jobs.raise_if_cancelled(job_id)
        if not translated or not translated[0][2]:
            raise RuntimeError("Translation produced no usable text.")
        output_path = work_dir / "translated.txt"
        jobs.raise_if_cancelled(job_id)
        output_path.write_text(translated[0][2], encoding="utf-8")
        jobs.raise_if_cancelled(job_id)
        jobs.update(
            job_id, stage="completed", progress=1.0, done=True,
            message="Done! Translated text is ready.", output_path=str(output_path),
        )
        logger.info("Job %s: text pipeline completed successfully -> %s", job_id, output_path)
    except JobCancelled:
        logger.info("Job %s: text cancellation completed", job_id)
        jobs.mark_cancelled(job_id)
    except Exception as exc:  # noqa: BLE001 - surface all failures to the UI
        logger.exception("Job %s: text pipeline failed", job_id)
        jobs.update(job_id, stage="failed", done=True, error=str(exc), message=f"Failed: {exc}")


def translate_text(
    text: str,
    source_code: str,
    target_code: str,
    translator: TranslationEngine,
    translator_indic: TranslationEngine,
    translator_indic_en: TranslationEngine,
) -> str:
    """Translate one text input through the same routing and quality path as media jobs."""
    target_lang = LANGUAGES_BY_CODE[target_code]
    result = SimpleNamespace(segments=[Segment(start=0.0, end=1.0, text=text)])
    silent_jobs = SimpleNamespace(update=lambda *args, **kwargs: None)
    translated = _translate(
        "text", silent_jobs, translator, translator_indic, translator_indic_en,
        result, source_code, target_code, target_lang,
    )
    if not translated or not translated[0][2]:
        raise RuntimeError("Translation produced no usable text.")
    return translated[0][2]


def _translate_with_heartbeat(job_id, jobs, engine, texts, **translate_kwargs):
    """Runs engine.translate() on a background thread and logs a status
    message every 60s while it's still running, so a long (or hung, e.g. the
    known concurrent-inference-lock issue - see repo memory) translation call
    is visible in the job log/UI instead of looking like nothing is
    happening."""
    result: dict = {}

    def _worker() -> None:
        for attempt in range(2):
            try:
                translated = []
                for start in range(0, len(texts), _TRANSLATION_BATCH_SIZE):
                    jobs.raise_if_cancelled(job_id)
                    batch = texts[start:start + _TRANSLATION_BATCH_SIZE]
                    batch_result = engine.translate(batch, **translate_kwargs)
                    jobs.raise_if_cancelled(job_id)
                    if len(batch_result) != len(batch):
                        raise RuntimeError(
                            f"Translation batch result count mismatch: inputs={len(batch)} outputs={len(batch_result)}"
                        )
                    translated.extend(batch_result)
                result["value"] = translated
                result["retry_count"] = attempt
                return
            except JobCancelled as exc:
                result["error"] = exc
                result["retry_count"] = attempt
                return
            except Exception as exc:  # noqa: BLE001 - re-raised on caller's thread below
                result["error"] = exc
                result["retry_count"] = attempt + 1

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    elapsed = 0
    while thread.is_alive():
        thread.join(timeout=60)
        if thread.is_alive():
            elapsed += 60
            # Check memory health during translation.
            memory_policy = get_memory_policy()
            memory_policy.check_memory_during_job(job_id, f"translating_{elapsed}s")
            jobs.update(
                job_id,
                message=f"Still translating {len(texts)} segment(s)... ({elapsed}s elapsed)",
            )
    if "error" in result:
        raise result["error"]
    return result["value"]


def _translation_quality(source_text: str, translated_text: str) -> dict:
    """Return structured diagnostics for a translated segment before TTS."""
    source_tokens = source_text.split()
    target_tokens = translated_text.split()
    if not target_tokens:
        return {
            "valid": False,
            "reason": "empty translation",
            "repetition_score": 0.0,
            "length_ratio": 0.0,
            "length_anomaly": False,
        }

    longest_phrase = ""
    longest_count = 1
    target_count = len(target_tokens)
    for phrase_size in range(2, min(8, target_count // 2) + 1):
        for start in range(target_count - phrase_size + 1):
            phrase = target_tokens[start:start + phrase_size]
            count = sum(
                1
                for other_start in range(target_count - phrase_size + 1)
                if target_tokens[other_start:other_start + phrase_size] == phrase
            )
            if count > longest_count or (count == longest_count and phrase_size > len(longest_phrase.split())):
                longest_phrase = " ".join(phrase)
                longest_count = count

    repetition_score = (
        len(longest_phrase.split()) * longest_count / target_count
        if longest_phrase
        else 0.0
    )
    length_ratio = target_count / max(len(source_tokens), 1)
    length_anomaly = length_ratio > 4.0
    repeated_run = longest_count >= 3 and repetition_score >= 0.25
    valid = not (repeated_run or (length_anomaly and repetition_score >= 0.15))
    if repeated_run:
        reason = f"repeated phrase '{longest_phrase}' ({longest_count} occurrences)"
    elif length_anomaly:
        reason = f"target is {length_ratio:.1f}x the source token count"
    else:
        reason = "ok"
    return {
        "valid": valid,
        "reason": reason,
        "repetition_score": repetition_score,
        "length_ratio": length_ratio,
        "length_anomaly": length_anomaly,
    }


def _filter_suspicious_translations(job_id, jobs, source_segments, translated):
    accepted = []
    suspicious_count = 0
    for source_segment, translated_text in zip(source_segments, translated):
        text = translated_text.strip()
        quality = _translation_quality(source_segment.text, text)
        if not quality["valid"]:
            suspicious_count += 1
            logger.warning(
                "Job %s: flagging suspicious translation at %.3f-%.3f: %s; diagnostics=%s",
                job_id, source_segment.start, source_segment.end, quality["reason"], quality,
            )
        accepted.append((source_segment.start, source_segment.end, text))
    if suspicious_count:
        jobs.update(
            job_id,
            message=f"Flagged {suspicious_count} suspicious translation segment(s); source content was preserved for diagnostics.",
        )
    return accepted


def _filter_saved_translations(job_id, jobs, source_segments, translated_segments):
    source_by_timing = {(segment.start, segment.end): segment for segment in source_segments}
    accepted = []
    suspicious_count = 0
    for translated_segment in translated_segments:
        source_segment = source_by_timing.get((translated_segment.start, translated_segment.end))
        source_text = source_segment.text if source_segment is not None else ""
        quality = _translation_quality(source_text, translated_segment.text)
        if not quality["valid"]:
            suspicious_count += 1
            logger.warning(
                "Job %s: flagging suspicious saved translation at %.3f-%.3f: %s; diagnostics=%s",
                job_id, translated_segment.start, translated_segment.end, quality["reason"], quality,
            )
        accepted.append((translated_segment.start, translated_segment.end, translated_segment.text.strip()))
    if suspicious_count:
        jobs.update(
            job_id,
            message=f"Flagged {suspicious_count} suspicious saved translation segment(s); source content was preserved for diagnostics.",
        )
    return accepted


def _filter_context_translations(job_id, jobs, contexts, context_segments, translated):
    if len(translated) != len(contexts):
        raise RuntimeError(
            f"Translation context result count mismatch: contexts={len(contexts)} outputs={len(translated)}"
        )
    results = [
        {
            "context_id": context.context_id,
            "event_ids": list(context.event_ids),
            "source_start": context.source_start,
            "source_end": context.source_end,
            "source_text": context.source_text,
            "translated_text": text,
            "linguistic_completeness": source_linguistic_completeness(context.source_text),
        }
        for context, text in zip(contexts, translated)
    ]
    def domain_warnings(result):
        _, _, warnings = validate_terminology(
            result["source_text"], result["translated_text"], enabled=DOMAIN_PACK_ENABLED
        )
        return warnings

    diagnostics = TranslationQualityGuard(domain_warnings).validate(contexts, results)
    for result in results:
        updated_text, terminology_matches, terminology_warnings = validate_terminology(
            result["source_text"], result["translated_text"], enabled=DOMAIN_PACK_ENABLED
        )
        result["translated_text"] = updated_text
        result["terminology_matches"] = terminology_matches
        result["validation_warnings"] = terminology_warnings
    if diagnostics["warnings"]:
        logger.warning("Job %s: translation context validation warnings: %s", job_id, diagnostics["warnings"])
    return _filter_suspicious_translations(
        job_id, jobs, context_segments, [result["translated_text"] for result in results]
    )


def _protected_context_texts(contexts, source_code, target_code):
    source_language = LANGUAGES_BY_CODE.get(source_code)
    target_language = LANGUAGES_BY_CODE.get(target_code)
    enabled = bool(
        DOMAIN_PACK_ENABLED and source_language and target_language
        and domain_pack_applies(source_language.flores_code, target_language.flores_code)
    )
    texts = []
    replacements = []
    for context in contexts:
        protected, _matches, context_replacements = protect_terms(context.source_text, enabled=enabled)
        protected, _entities, entity_replacements = protect_entities(protected)
        context_replacements.update(entity_replacements)
        texts.append(protected)
        replacements.append(context_replacements)
    return texts, replacements


def _restore_protected_contexts(translated, replacements):
    return [restore_terms(restore_entities(text, context_replacements), context_replacements) for text, context_replacements in zip(translated, replacements)]


def _saved_translation_matches_contexts(saved_segments, contexts) -> bool:
    if len(saved_segments) != len(contexts):
        return False
    return all(
        abs(float(saved.start) - context.source_start) < 1e-6
        and abs(float(saved.end) - context.source_end) < 1e-6
        for saved, context in zip(saved_segments, contexts)
    )


def _translate(job_id, jobs, translator, translator_indic, translator_indic_en, base_result, source_code, target_code, target_lang):
    translation_contexts, context_diagnostics = plan_translation_contexts(
        base_result.segments,
        max_events=TRANSLATION_CONTEXT_MAX_EVENTS if TRANSLATION_CONTEXT_ENABLED else 1,
        max_characters=TRANSLATION_CONTEXT_MAX_CHARS if TRANSLATION_CONTEXT_ENABLED else 100000,
        max_duration=TRANSLATION_CONTEXT_MAX_DURATION_SECONDS,
    )
    logger.info("Translation context planner: %s", context_diagnostics)
    context_segments = [Segment(start=c.source_start, end=c.source_end, text=c.source_text) for c in translation_contexts]
    # Pre-translation memory check: ensure required model can be loaded safely
    from app.models.memory_policy import get_memory_policy
    memory_policy = get_memory_policy()
    memory_policy.check_memory_during_job(job_id, "pre_translation")
    

    if source_code == target_code:
        jobs.update(
            job_id, stage="translating", progress=0.4,
            message="Source and target languages match; no translation needed.",
        )
        return [(c.source_start, c.source_end, c.source_text) for c in translation_contexts]

    if source_code == "en":
        jobs.update(
            job_id, stage="translating", progress=0.4,
            message=f"Translating English -> {target_lang.label} with IndicTrans2...",
        )
        texts = [c.source_text for c in translation_contexts]
        try:
            translated = _translate_with_heartbeat(job_id, jobs, translator, texts, tgt_lang=target_lang.flores_code)
        except JobCancelled:
            raise
        except Exception as exc:
            raise RuntimeError(f"Text translation failed: {exc}") from exc
        return _filter_context_translations(job_id, jobs, translation_contexts, context_segments, translated)

    source_lang = LANGUAGES_BY_CODE.get(source_code)
    if source_lang is None:
        raise RuntimeError(f"Detected source language '{source_code}' is not supported for translation.")

    if target_code != "en":
        texts, term_replacements = _protected_context_texts(translation_contexts, source_code, target_code)
        if INDIC_TO_INDIC_USE_ENGLISH_PIVOT:
            jobs.update(
                job_id, stage="translating", progress=0.4,
                message=f"Translating {source_lang.label} -> English -> {target_lang.label} with IndicTrans2...",
            )
            try:
                english_texts = _translate_with_heartbeat(
                    job_id, jobs, translator_indic_en, texts, tgt_lang="eng_Latn", src_lang=source_lang.flores_code
                )
                jobs.raise_if_cancelled(job_id)
                translated = _translate_with_heartbeat(
                    job_id, jobs, translator, english_texts, tgt_lang=target_lang.flores_code
                )
            except JobCancelled:
                raise
            except Exception as exc:
                raise RuntimeError(f"Text translation failed: {exc}") from exc
            return _filter_context_translations(job_id, jobs, translation_contexts, context_segments, translated)

        # Retained as an opt-out for deployments where the direct checkpoint
        # is preferred for a specific language pair.
        jobs.update(
            job_id, stage="translating", progress=0.4,
            message=f"Translating {source_lang.label} -> {target_lang.label} with IndicTrans2 (Indic-Indic)...",
        )
        try:
            translated = _translate_with_heartbeat(
                job_id, jobs, translator_indic, texts, tgt_lang=target_lang.flores_code, src_lang=source_lang.flores_code
            )
        except JobCancelled:
            raise
        except Exception as exc:
            raise RuntimeError(f"Text translation failed: {exc}") from exc
        translated = _restore_protected_contexts(translated, term_replacements)
        return _filter_context_translations(job_id, jobs, translation_contexts, context_segments, translated)

    # Only remaining case: target is English and the source is a non-English
    # Indic language - translate the already-transcribed source segments
    # directly with the dedicated indic-en model instead of Whisper's own
    # (less reliable, and slower - a second full ASR pass) speech-to-English
    # "translate" task.
    jobs.update(
        job_id, stage="translating", progress=0.4,
        message=f"Translating {source_lang.label} -> English with IndicTrans2 (Indic-English)...",
    )
    texts = [c.source_text for c in translation_contexts]
    try:
        translated = _translate_with_heartbeat(
            job_id, jobs, translator_indic_en, texts, tgt_lang="eng_Latn", src_lang=source_lang.flores_code
        )
    except JobCancelled:
        raise
    except Exception as exc:
        raise RuntimeError(f"Text translation failed: {exc}") from exc
    return _filter_context_translations(job_id, jobs, translation_contexts, context_segments, translated)


def _refine_with_indic_asr(job_id, jobs, indic_asr, audio_path, base_result, source_code):
    """Re-transcribe each Whisper-segmented clip with the specialized
    IndicConformer model for languages it covers - higher-quality,
    native-script text than Whisper's general-purpose decoder, while
    Whisper's own (already-done) segmentation/timing is kept as-is.
    Falls back to the original Whisper text for any segment (or entirely)
    on failure, so this step can never break the pipeline."""
    if indic_asr is None or not INDIC_ASR_ENABLED or not indic_asr.supports(source_code):
        return base_result.segments

    jobs.update(job_id, message=f"Refining '{source_code}' transcript with IndicConformer...")
    try:
        audio, sr = sf.read(str(audio_path), dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
    except Exception:
        logger.exception("Job %s: failed to load audio for IndicConformer refinement, keeping Whisper transcript", job_id)
        return base_result.segments

    refined = []
    # Small acoustic context padding around each Whisper segment boundary.
    # Whisper's segment timestamps aren't always frame-accurate, and since
    # IndicConformer is a frame-synchronous CTC decoder (unlike Whisper's own
    # autoregressive decoding) a hard cut exactly on the boundary can slice a
    # word in half, leaving a stray partial-syllable fragment in the
    # transcript (e.g. a lone consonant tacked onto the end of a sentence).
    # A little extra audio on each side gives the decoder enough context to
    # finish/start the boundary word cleanly.
    pad_samples = int(0.15 * sr)
    for seg in base_result.segments:
        start_sample = max(0, int(seg.start * sr) - pad_samples)
        end_sample = min(len(audio), int(seg.end * sr) + pad_samples)
        text = ""
        if end_sample > start_sample:
            try:
                text = indic_asr.transcribe_array(audio[start_sample:end_sample], sr, source_code)
            except Exception:
                logger.exception(
                    "Job %s: IndicConformer transcription failed for segment %.2f-%.2f, keeping Whisper text",
                    job_id, seg.start, seg.end,
                )
        refined.append(Segment(start=seg.start, end=seg.end, text=text or seg.text))
    return _remove_adjacent_text_overlap(refined)


def _remove_adjacent_text_overlap(segments: list[Segment]) -> list[Segment]:
    """Drop exact leading words duplicated by neighboring padded ASR clips.

    IndicConformer gets 0.15s of context on both sides of each Whisper slot.
    That avoids cutting a phoneme, but can make it decode the same complete
    boundary word in both slots. Keep the earlier occurrence because its
    timing owns the boundary; only remove an exact prefix from the later one.
    """
    if not segments:
        return segments
    deduplicated = [segments[0]]
    for current in segments[1:]:
        previous_words = deduplicated[-1].text.split()
        current_words = current.text.split()
        overlap = 0
        max_overlap = min(len(previous_words), len(current_words))
        for word_count in range(max_overlap, 0, -1):
            if previous_words[-word_count:] == current_words[:word_count]:
                overlap = word_count
                break
        if overlap:
            trimmed_text = " ".join(current_words[overlap:])
            logger.info(
                "Trimmed %d duplicated ASR boundary word(s) at %.2f: %s",
                overlap, current.start, " ".join(current_words[:overlap]),
            )
            current = Segment(start=current.start, end=current.end, text=trimmed_text)
        deduplicated.append(current)
    return deduplicated


# Unicode block for each FLORES-200 script suffix used in app/config.py's
# Language.flores_code (e.g. "mar_Deva" -> "Deva"). Latin ("en") is handled
# separately - not included here.
_SCRIPT_UNICODE_RANGES = {
    "Deva": (0x0900, 0x097F),
    "Beng": (0x0980, 0x09FF),
    "Gujr": (0x0A80, 0x0AFF),
    "Guru": (0x0A00, 0x0A7F),
    "Knda": (0x0C80, 0x0CFF),
    "Mlym": (0x0D00, 0x0D7F),
    "Orya": (0x0B00, 0x0B7F),
    "Taml": (0x0B80, 0x0BFF),
    "Telu": (0x0C00, 0x0C7F),
    "Arab": (0x0600, 0x06FF),
    "Olck": (0x1C50, 0x1C7F),
    "Mtei": (0xABC0, 0xABFF),
}


def _looks_like_hallucination(text: str, source_code: str) -> bool:
    """Heuristic guard against Whisper/IndicConformer occasionally
    hallucinating fluent-sounding gibberish on hard-to-transcribe audio -
    typically a mix of the source language's script with random unrelated
    Latin (or other) words. Such segments would otherwise sail through
    translation and get dubbed as audible nonsense speech (see repo memory,
    job 0340684ca9d847b79d03f506c826936e, e.g. "...standby action we
    lovingly..." mixed into a Marathi segment). Flags a segment whose
    alphabetic characters are mostly NOT in its expected script."""
    source_lang = LANGUAGES_BY_CODE.get(source_code)
    if source_lang is None:
        return False
    script = source_lang.flores_code.split("_")[-1]
    unicode_range = _SCRIPT_UNICODE_RANGES.get(script)
    if unicode_range is None:  # e.g. English/Latin - nothing to check against
        return False
    alpha_chars = [c for c in text if c.isalpha()]
    if len(alpha_chars) < 8:  # too short for the ratio to be meaningful
        return False
    lo, hi = unicode_range
    in_script = sum(1 for c in alpha_chars if lo <= ord(c) <= hi)
    return (in_script / len(alpha_chars)) < 0.6


def _drop_hallucinated_segments(job_id, jobs, segments, source_code):
    kept = [s for s in segments if not _looks_like_hallucination(s.text, source_code)]
    dropped_texts = [s.text for s in segments if s not in kept]
    if dropped_texts:
        logger.warning("Job %s: discarded %d likely-hallucinated ASR segment(s): %s", job_id, len(dropped_texts), dropped_texts)
        jobs.update(job_id, message=f"Discarded {len(dropped_texts)} garbled/hallucinated transcript segment(s) before translation.")
    return kept


def _merge_asr_segments(segments: list[Segment]) -> list[Segment]:
    """Combine adjacent ASR fragments into translation-sized utterances.

    Whisper timestamps often split one Marathi sentence into several very
    short clips. Translating those clips independently loses grammatical and
    domain context even with the 1B IndicTrans2 checkpoints. Keep genuine
    pauses intact, but merge nearby clips into bounded utterances so TTS can
    still align each result to a practical source-time slot.
    """
    if not segments:
        return segments

    merged: list[Segment] = []
    current = segments[0]
    for following in segments[1:]:
        gap = following.start - current.end
        combined_duration = following.end - current.start
        if gap <= _MAX_MERGED_SEGMENT_GAP and combined_duration <= _MAX_MERGED_SEGMENT_DURATION:
            current = Segment(
                start=current.start,
                end=following.end,
                text=f"{current.text} {following.text}".strip(),
            )
        else:
            merged.append(current)
            current = following
    merged.append(current)
    if len(merged) != len(segments):
        logger.info("Merged %d ASR fragments into %d translation utterances", len(segments), len(merged))
    return merged


def _read_segments_json(path: Path, required_format: str | None = None):
    """Return saved (language, probability, segments), or None when a prior
    attempt did not finish writing a reusable checkpoint."""
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if required_format is not None and payload.get("segment_format") != required_format:
            logger.info("Ignoring stale pipeline checkpoint with old segment format: %s", path)
            return None
        rows = payload["segments"]
        segments = [
            Segment(
                start=float(row["start"]),
                end=float(row["end"]),
                text=str(row["text"]),
                source_segment_id=row.get("source_segment_id"),
                pause_before=row.get("pause_before"),
                pause_after=row.get("pause_after"),
                confidence=row.get("confidence"),
                segmentation_reason=row.get("segmentation_reason", "ASR_BOUNDARY"),
            )
            for row in rows
            if str(row.get("text", "")).strip()
        ]
        language = payload.get("language") or payload.get("source_language")
        if not language or not segments:
            return None
        return language, float(payload.get("language_probability") or 0.0), segments
    except (OSError, ValueError, KeyError, TypeError):
        if path.exists():
            logger.warning("Ignoring incomplete pipeline checkpoint: %s", path)
        return None


def _write_segments_json(path: Path, segments, **extra) -> None:
    """segments: list of Segment objects or (start, end, text) tuples."""
    rows = []
    for seg in segments:
        if isinstance(seg, tuple):
            start, end, text = seg
        else:
            start, end, text = seg.start, seg.end, seg.text
        rows.append({
            "start": start, "end": end, "text": text,
            "source_segment_id": getattr(seg, "source_segment_id", None),
            "pause_before": getattr(seg, "pause_before", None),
            "pause_after": getattr(seg, "pause_after", None),
            "confidence": getattr(seg, "confidence", None),
            "segmentation_reason": getattr(seg, "segmentation_reason", "ASR_BOUNDARY"),
        })
    try:
        path.write_text(json.dumps({**extra, "segments": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("Failed to write segments JSON to %s", path)


def _synthesize_and_align(job_id, jobs, tts, target_lang, audio_path, final_segments, work_dir):
    jobs.raise_if_cancelled(job_id)
    info = sf.info(str(audio_path))
    total_duration = info.frames / info.samplerate
    sr = tts.sampling_rate_for(target_lang)
    canvas = np.zeros(int(total_duration * sr), dtype=np.float32)
    source_audio, source_sr = sf.read(str(audio_path), dtype="float32")
    if source_audio.ndim > 1:
        source_audio = source_audio.mean(axis=1)

    units = []
    for start, end, text in final_segments:
        units.extend(_subdivide_tts_segment(start, end, text, source_audio, source_sr))
    units = _normalize_timed_units(units, total_duration)
    events = [
        SpeechEvent(
            event_id=index,
            source_start=start,
            source_end=end,
            target_text=text,
            source_pause_intervals=(
                [(end, end + _pause_duration)] if _pause_duration > 0 else []
            ),
            target_start=start,
            target_end=end,
            warnings=[],
        )
        for index, (start, end, text, _pause_duration) in enumerate(units)
    ]
    logger.info("Job %s: subdivided %d translated segment(s) into %d TTS unit(s)", job_id, len(final_segments), len(units))

    # Synthesize at the configured natural Piper rate first. Timing allocation
    # must use measured waveform duration, not the source ASR window.
    natural_audio = []
    for _, _, text, _ in units:
        jobs.raise_if_cancelled(job_id)
        natural_audio.append(np.asarray(tts.synthesize(text, target_lang, voice_index=0), dtype=np.float32))
        jobs.raise_if_cancelled(job_id)
    timing_plan = _plan_tts_timing(units, [len(audio) / sr for audio in natural_audio], sr)

    segments_dir = work_dir / "segments"
    segments_dir.mkdir(exist_ok=True)

    n = len(units)
    synthesized_count = 0
    diagnostics = []
    unit_rms = [_source_rms(source_audio, source_sr, event.source_start, event.source_end) for event in events]
    reference_rms = float(np.median([value for value in unit_rms if value > 0])) if any(unit_rms) else 0.0
    failed_events = []
    for i, event in enumerate(events):
        start, end, text = event.source_start, event.source_end, event.target_text
        pause_duration = units[i][3]
        try:
            jobs.raise_if_cancelled(job_id)
            allocation = timing_plan[i]
            allocated_start = allocation["allocated_start"]
            allocated_end = allocation["allocated_end"]
            available_duration = max(end - start, 0.05)
            target_duration = max(allocated_end - allocated_start, 0.05)
            audio_arr = natural_audio[i]
            length_scale = None

            raw_path = segments_dir / f"seg_{i:04d}_raw.wav"
            sf.write(str(raw_path), audio_arr, sr)

            tts_duration = len(audio_arr) / sr
            event.natural_target_duration = tts_duration
            event.rate_decision = length_scale
            speed_factor = tts_duration / target_duration if target_duration > 0 else 1.0
            if speed_factor > 2.0:
                logger.warning(
                    "Job %s: duration conflict at %.3f-%.3f (%.2fx source slot); preserving content with final fallback",
                    job_id, start, end, speed_factor,
                )
                jobs.update(job_id, message=f"Duration conflict for speech event {i + 1}/{n}; applying final bounded fallback.")
                event.duration_status = "DURATION_CONFLICT"
                event.warnings.append("Natural target duration exceeded twice the available source interval.")

            # Native Piper rate control is preferred. Only a bounded fallback
            # is used for a clip that remains materially longer than its slot.
            fallback_stretch = False
            adjustment_level = "NATURAL"
            warning = ""
            if speed_factor <= 1.0:
                seg_audio = audio_arr
            else:
                stretched_path = segments_dir / f"seg_{i:04d}.wav"
                # Post-TTS compression is bounded; the hard window below is
                # the final authority when a clip remains too long.
                fallback_factor = min(speed_factor, TTS_MAX_ALLOWED_COMPRESSION)
                time_stretch_audio(str(raw_path), str(stretched_path), fallback_factor)
                seg_audio, _ = sf.read(str(stretched_path), dtype="float32")
                fallback_stretch = True
                adjustment_level = (
                    "MILD_POST_STRETCH"
                    if speed_factor <= TTS_MAX_ALLOWED_COMPRESSION
                    else "BOUNDED_POST_STRETCH"
                )
                if speed_factor > TTS_MAX_ALLOWED_COMPRESSION:
                    warning = "maximum allowed compression reached"

            available_samples = max(int(round(target_duration * sr)), 1)
            if len(seg_audio) > available_samples:
                seg_audio = seg_audio[:available_samples]
                event.duration_status = "DURATION_CONFLICT"
                warning = warning or (
                    "target duration too short for natural TTS; final audio was bounded to the source window"
                )
            elif target_duration < TTS_SHORT_SEGMENT_SECONDS and len(seg_audio) == available_samples:
                warning = warning or "target duration too short for natural TTS"

            if TTS_PRESERVE_INTENSITY and reference_rms > 0 and unit_rms[i] > 0:
                gain = np.clip(
                    (unit_rms[i] / reference_rms) ** 0.35,
                    TTS_INTENSITY_GAIN_MIN,
                    TTS_INTENSITY_GAIN_MAX,
                )
                seg_audio = seg_audio * gain
            else:
                gain = 1.0

            if warning:
                event.warnings.append(warning)
            start_sample = min(max(int(round(allocated_start * sr)), 0), len(canvas))
            end_sample = min(start_sample + len(seg_audio), len(canvas), int(round(allocated_end * sr)))
            seg_audio = seg_audio[:max(0, end_sample - start_sample)]
            canvas[start_sample:end_sample] += seg_audio
            synthesized_count += 1
            diagnostics.append({
                "event_id": event.event_id,
                "segment_id": event.event_id,
                "source_start": start,
                "source_end": end,
                "source_duration": available_duration,
                "available_duration": target_duration,
                "original_event_ids": [event.event_id],
                "original_start": start,
                "original_end": end,
                "allocated_start": allocated_start,
                "allocated_end": allocated_end,
                "boundary_type": allocation["boundary_type"],
                "timing_reallocation_attempted": allocation["timing_reallocation_attempted"],
                "timing_reallocation_result": allocation["timing_reallocation_result"],
                "target_text": text,
                "translated_text": text,
                "target_start": event.target_start,
                "target_end": event.target_end,
                "target_duration": target_duration,
                "raw_tts_duration": tts_duration,
                "natural_duration": tts_duration,
                "final_duration": min(len(seg_audio) / sr, target_duration),
                "raw_source_ratio": tts_duration / available_duration,
                "duration_ratio": speed_factor,
                "final_source_ratio": min(len(seg_audio) / sr, target_duration) / target_duration,
                "piper_length_scale": length_scale,
                "stretching": bool(fallback_stretch),
                "event_status": event.duration_status if event.duration_status == "DURATION_CONFLICT" else allocation["naturalness_status"],
                "naturalness_status": allocation["naturalness_status"],
                "naturalness_reason": allocation["timing_reallocation_result"],
                "rate_decision": length_scale,
                "selected_tts_speed": (1.0 / length_scale) if length_scale else 1.0,
                "stretch_ratio": fallback_factor if fallback_stretch else 1.0,
                "time_stretch_ratio": fallback_factor if fallback_stretch else 1.0,
                "compression_required": bool(fallback_stretch),
                "compression_ratio": fallback_factor if fallback_stretch else 1.0,
                "timing_adjustment_applied": adjustment_level != "NATURAL",
                "adjustment_level": adjustment_level,
                "warning": warning,
                "final_start": allocated_start,
                "final_end": allocated_start + len(seg_audio) / sr,
                "pause_duration": pause_duration,
                "text_length": len(text),
                "sentence_count": len(re.findall(r"[।.!?]", text)) or 1,
                "intensity_gain": float(gain),
            })
            if speed_factor > 1.25 or speed_factor < 0.75:
                logger.warning("Job %s: substantial TTS rate adjustment at %.3f-%.3f (raw/source=%.2f)", job_id, start, end, speed_factor)
        except Exception:
            logger.exception("Job %s: failed speech event %d/%d", job_id, i + 1, n)
            event.duration_status = "FAILED"
            event.warnings.append("TTS synthesis or duration adaptation failed; translated content was not discarded silently.")
            failed_events.append(event)
            jobs.update(job_id, message=f"Speech event {i + 1}/{n} failed; translated content was preserved as an explicit job failure.")
            continue

        jobs.update(
            job_id, progress=0.55 + 0.30 * ((i + 1) / n),
            message=f"Synthesized segment {i + 1}/{n}.",
        )

    if synthesized_count == 0:
        raise RuntimeError("All speech segments failed to synthesize.")

    if failed_events:
        (work_dir / "tts_diagnostics.json").write_text(
            json.dumps(
                {"events": diagnostics, "failed_events": [_event_diagnostic(event) for event in failed_events]},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        raise RuntimeError(f"{len(failed_events)} speech event(s) failed; no translated content was silently skipped.")

    peak_before_normalization = float(np.max(np.abs(canvas))) if canvas.size else 0.0
    if peak_before_normalization > 1.0:
        canvas = canvas / peak_before_normalization
    peak = float(np.max(np.abs(canvas))) if canvas.size else 0.0

    dubbed_audio_path = work_dir / "dubbed_audio.wav"
    sf.write(str(dubbed_audio_path), canvas, sr)
    synchronization_report = {
        "source_duration": total_duration,
        "dubbed_duration": len(canvas) / sr,
        "duration_delta": len(canvas) / sr - total_duration,
        "peak_amplitude": peak,
        "global_duration_valid": abs(len(canvas) / sr - total_duration) <= 1.0 / sr,
        "segments": diagnostics,
        "outside_window_segments": [
            item["event_id"] for item in diagnostics
            if item["final_start"] < item["source_start"] - 1.0 / sr
            or item["final_end"] > item["source_end"] + 1.0 / sr
        ],
    }
    (work_dir / "synchronization_report.json").write_text(
        json.dumps(synchronization_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (work_dir / "tts_diagnostics.json").write_text(
        json.dumps({"events": diagnostics, "units": diagnostics, "failed_events": []}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return dubbed_audio_path


def _normalize_timed_units(units, total_duration):
    """Clamp invalid/overlapping units without moving a valid unit's start."""
    normalized = []
    cursor = 0.0
    for start, end, text, pause_duration in sorted(units, key=lambda item: (item[0], item[1])):
        start = max(0.0, min(float(start), total_duration))
        end = max(0.0, min(float(end), total_duration))
        start = max(start, cursor)
        if end <= start or not str(text).strip():
            continue
        normalized.append((start, end, text, pause_duration))
        cursor = end
    return normalized


def _event_diagnostic(event: SpeechEvent) -> dict:
    return {
        "event_id": event.event_id,
        "source_start": event.source_start,
        "source_end": event.source_end,
        "target_text": event.target_text,
        "source_text": event.source_text,
        "source_pause_intervals": event.source_pause_intervals or [],
        "target_start": event.target_start,
        "target_end": event.target_end,
        "natural_target_duration": event.natural_target_duration,
        "duration_status": event.duration_status,
        "rate_decision": event.rate_decision,
        "warnings": event.warnings or [],
    }


def _synthesize_at_natural_rate(tts, text, target_lang, target_duration, enabled):
    audio = np.asarray(tts.synthesize(text, target_lang, voice_index=0), dtype=np.float32)
    if not enabled or not audio.size:
        return audio, None
    raw_duration = len(audio) / tts.sampling_rate_for(target_lang)
    ratio = raw_duration / target_duration
    if ratio <= 1.0 or abs(ratio - 1.0) <= TTS_RATE_TOLERANCE:
        return audio, None
    length_scale = float(np.clip(1.0 / ratio, TTS_PIPER_LENGTH_SCALE_MIN, TTS_PIPER_LENGTH_SCALE_MAX))
    try:
        adjusted = np.asarray(
            tts.synthesize(text, target_lang, voice_index=0, length_scale=length_scale), dtype=np.float32
        )
    except TypeError:
        # Keep compatibility with third-party TTS implementations that still
        # expose the original three-argument service method.
        return audio, None
    return adjusted, length_scale


def _timing_boundary_type(previous, current):
    """Classify only generic continuation boundaries as soft."""
    gap = max(0.0, float(current[0]) - float(previous[1]))
    previous_text = str(previous[2]).strip()
    current_text = str(current[2]).strip()
    previous_open = bool(re.search(r"[,;:…\-–—/]$", previous_text))
    current_continues = bool(re.match(r"(?i)^(and|or|but|to|of|for|with|that|which|who|this|these|those|और|या|लेकिन|जो|यह|ये|और)", current_text))
    terminal = bool(re.search(r"[.!?।！？]$", previous_text))
    if gap >= TTS_MIN_PAUSE_SECONDS or terminal and not current_continues:
        return "HARD"
    return "SOFT" if previous_open or current_continues else "HARD"


def _plan_tts_timing(units, natural_durations, sample_rate):
    """Allocate measured natural speech without crossing hard boundaries."""
    plan = []
    for index, (unit, natural_duration) in enumerate(zip(units, natural_durations)):
        source_start, source_end, text, _pause_duration = unit
        boundary = "HARD" if index == 0 else _timing_boundary_type(units[index - 1], unit)
        allocated_start = source_start
        if index and boundary == "SOFT":
            allocated_start = max(source_start, plan[-1]["allocated_end"])
        allocated_end = source_end
        ratio = natural_duration / max(source_end - source_start, 0.05)
        result = "NONE"
        attempted = False
        if ratio > TTS_NATURAL_FIT_THRESHOLD and index + 1 < len(units):
            next_boundary = _timing_boundary_type(unit, units[index + 1])
            if next_boundary == "SOFT":
                attempted = True
                candidate_end = min(units[index + 1][1], allocated_start + natural_duration)
                if candidate_end > allocated_end:
                    allocated_end = candidate_end
                    result = "EXPANDED_SOFT_BOUNDARY"
        if ratio <= TTS_NATURAL_FIT_THRESHOLD:
            status = "NATURAL"
        elif result != "NONE":
            status = "REALLOCATED"
        elif ratio <= TTS_MILD_ADJUSTMENT_THRESHOLD:
            status = "MILD_ADJUSTMENT"
        elif ratio <= TTS_REPLAN_THRESHOLD:
            status = "BOUNDED_ADJUSTMENT"
        else:
            status = "DURATION_CONFLICT"
        plan.append({
            "allocated_start": allocated_start,
            "allocated_end": allocated_end,
            "boundary_type": boundary,
            "timing_reallocation_attempted": attempted,
            "timing_reallocation_result": result,
            "naturalness_status": status,
            "natural_duration": natural_duration,
            "duration_ratio": ratio,
            "sample_rate": sample_rate,
        })
    return plan


def _subdivide_tts_segment(start, end, text, audio, sample_rate):
    if not TTS_PROSODY_ENABLED:
        return [(start, end, text, 0.0)]
    parts = _split_tts_text(text)
    pauses = _source_pause_boundaries(audio, sample_rate, start, end)
    # Never invent target boundaries from source word counts. A target
    # sentence may be split only when a corresponding source pause exists.
    if len(parts) > 1 and not pauses:
        return [(start, end, text, 0.0)]
    if len(parts) == 1:
        return [(start, end, text, 0.0)]
    predicted = [start + (end - start) * sum(len(part) for part in parts[:index + 1]) / len(text) for index in range(len(parts) - 1)]
    boundaries = []
    remaining = pauses[:]
    for point in predicted:
        candidates = [pause for pause in remaining if abs((pause[0] + pause[1]) / 2 - point) <= 1.25]
        if not candidates:
            return [(start, end, text, 0.0)]
        boundary = min(candidates, key=lambda pause: abs((pause[0] + pause[1]) / 2 - point))
        boundaries.append(boundary)
        remaining = [pause for pause in remaining if pause[0] > boundary[1]]
    units = []
    previous = start
    for index, part in enumerate(parts):
        if index < len(boundaries):
            pause_start, pause_end = boundaries[index]
            units.append((previous, pause_start, part, max(0.0, pause_end - pause_start)))
            previous = pause_end
        else:
            units.append((previous, end, part, 0.0))
    if any(unit[1] - unit[0] < TTS_MIN_UNIT_SECONDS for unit in units):
        return [(start, end, text, 0.0)]
    return units


def _split_tts_text(text):
    # Use punctuation already present in the translation as a language-neutral
    # clause boundary. Never invent a boundary from source/target word counts.
    parts = [
        part.strip()
        for part in re.split(r"(?<=[।.!?;:,，、])\s+", text)
        if part.strip()
    ]
    if len(parts) <= 1:
        return [text]
    if any(len(part) < 20 for part in parts):
        return [text]
    return parts


def _split_text_at_pause_count(text, part_count):
    words = text.split()
    if len(words) < part_count * 3:
        return [text]
    parts = []
    previous = 0
    for index in range(1, part_count):
        boundary = round(len(words) * index / part_count)
        parts.append(" ".join(words[previous:boundary]))
        previous = boundary
    parts.append(" ".join(words[previous:]))
    return [part for part in parts if part]


def _source_pause_boundaries(audio, sample_rate, start, end):
    first = max(0, int(start * sample_rate))
    last = min(len(audio), int(end * sample_rate))
    if last - first < int(sample_rate * TTS_MIN_PAUSE_SECONDS):
        return []
    frame = max(1, int(sample_rate * 0.02))
    energy = np.sqrt(np.convolve(audio[first:last] ** 2, np.ones(frame) / frame, mode="same"))
    silent = energy < TTS_SILENCE_THRESHOLD
    changes = np.diff(np.pad(silent.astype(np.int8), (1, 1)))
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1)
    boundaries = []
    for pause_start, pause_end in zip(starts, ends):
        duration = (pause_end - pause_start) / sample_rate
        if TTS_MIN_PAUSE_SECONDS <= duration <= TTS_MAX_PAUSE_SECONDS:
            boundaries.append((start + pause_start / sample_rate, start + pause_end / sample_rate))
    return boundaries


def _source_rms(audio, sample_rate, start, end):
    first = max(0, int(start * sample_rate))
    last = min(len(audio), int(end * sample_rate))
    section = audio[first:last]
    return float(np.sqrt(np.mean(section ** 2))) if section.size else 0.0
