"""End-to-end video dubbing pipeline: extract audio -> ASR -> translate ->
TTS -> re-mux. Designed to run inside a worker thread; reports progress via
the shared JobManager so the web UI can show real-time status.

Translation routing (see app/models/translate.py for why): the bundled
IndicTrans2 checkpoint only translates English -> Indic, so when the source
speech is not English we pivot through Whisper's own X -> English "translate"
task before (optionally) handing the English text to IndicTrans2.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import soundfile as sf

from app.config import LANGUAGES_BY_CODE, OUTPUTS_DIR, WHISPER_SUPPORTED_SOURCE_CODES
from app.jobs import JobManager
from app.media import extract_audio, mux_video_with_audio, time_stretch_audio
from app.models.asr import ASREngine
from app.models.translate import TranslationEngine
from app.models.tts import TTSEngine
from app.tts_style import build_description

logger = logging.getLogger(__name__)


def run_pipeline(
    job_id: str,
    video_path: str,
    target_code: str,
    jobs: JobManager,
    asr: ASREngine,
    translator: TranslationEngine,
    tts: TTSEngine,
) -> None:
    work_dir = Path(video_path).parent
    logger.info("Job %s: pipeline started (video=%s, target_lang=%s)", job_id, video_path, target_code)
    try:
        target_lang = LANGUAGES_BY_CODE[target_code]

        jobs.update(job_id, stage="extracting_audio", progress=0.02, message="Extracting audio from video...")
        audio_path = work_dir / "audio.wav"
        try:
            extract_audio(str(video_path), str(audio_path))
        except Exception as exc:
            raise RuntimeError(f"Failed to extract audio from video: {exc}") from exc

        jobs.update(
            job_id, stage="transcribing", progress=0.05,
            message="Transcribing speech...",
        )

        def base_progress(frac: float) -> None:
            jobs.update(job_id, progress=0.05 + 0.30 * frac)

        try:
            base_result = asr.transcribe(str(audio_path), task="transcribe", progress_cb=base_progress)
        except Exception as exc:
            raise RuntimeError(f"Speech recognition failed: {exc}") from exc
        source_code = base_result.language

        if not base_result.segments:
            raise RuntimeError("No speech was detected in the video's audio track.")

        jobs.update(
            job_id,
            detected_source_lang=source_code,
            detected_source_lang_prob=base_result.language_probability,
            message=(
                f"Detected source language '{source_code}' "
                f"({base_result.language_probability:.0%} confidence)."
            ),
        )

        final_segments = _translate(
            job_id, jobs, asr, translator, audio_path, base_result, source_code, target_code, target_lang
        )

        if not final_segments:
            raise RuntimeError("Translation produced no text to synthesize.")

        jobs.update(
            job_id, stage="synthesizing_speech", progress=0.55,
            message=f"Synthesizing {len(final_segments)} speech segment(s)...",
        )

        dubbed_audio_path = _synthesize_and_align(job_id, jobs, tts, target_lang, audio_path, final_segments, work_dir)

        jobs.update(job_id, stage="muxing_video", progress=0.9, message="Combining dubbed audio with the original video...")
        output_path = OUTPUTS_DIR / f"{job_id}.mp4"
        try:
            mux_video_with_audio(str(video_path), str(dubbed_audio_path), str(output_path))
        except Exception as exc:
            raise RuntimeError(f"Failed to combine dubbed audio with video: {exc}") from exc

        jobs.update(
            job_id, stage="completed", progress=1.0, done=True,
            message="Done! Dubbed video is ready.",
            output_path=str(output_path),
        )
        logger.info("Job %s: pipeline completed successfully -> %s", job_id, output_path)
    except Exception as exc:  # noqa: BLE001 - surface all failures to the UI
        logger.exception("Job %s: pipeline failed", job_id)
        jobs.update(job_id, stage="failed", done=True, error=str(exc), message=f"Failed: {exc}")


def _translate(job_id, jobs, asr, translator, audio_path, base_result, source_code, target_code, target_lang):
    if source_code == target_code:
        jobs.update(
            job_id, stage="translating", progress=0.4,
            message="Source and target languages match; no translation needed.",
        )
        return [(s.start, s.end, s.text) for s in base_result.segments]

    if source_code == "en":
        jobs.update(
            job_id, stage="translating", progress=0.4,
            message=f"Translating English -> {target_lang.label} with IndicTrans2...",
        )
        texts = [s.text for s in base_result.segments]
        try:
            translated = translator.translate(texts, tgt_lang=target_lang.flores_code)
        except Exception as exc:
            raise RuntimeError(f"Text translation failed: {exc}") from exc
        return [(s.start, s.end, t) for s, t in zip(base_result.segments, translated) if t.strip()]

    if source_code not in WHISPER_SUPPORTED_SOURCE_CODES:
        raise RuntimeError(
            f"Source language '{source_code}' is not supported for speech translation by the ASR model."
        )

    jobs.update(
        job_id, stage="transcribing", progress=0.35,
        message=f"Re-running ASR to translate '{source_code}' speech directly to English...",
    )
    try:
        en_result = asr.transcribe(
            str(audio_path), task="translate",
            progress_cb=lambda f: jobs.update(job_id, progress=0.35 + 0.1 * f),
        )
    except Exception as exc:
        raise RuntimeError(f"Speech-to-English translation failed: {exc}") from exc

    if target_code == "en":
        return [(s.start, s.end, s.text) for s in en_result.segments]

    jobs.update(
        job_id, stage="translating", progress=0.45,
        message=f"Translating English -> {target_lang.label} with IndicTrans2 (pivot)...",
    )
    texts = [s.text for s in en_result.segments]
    try:
        translated = translator.translate(texts, tgt_lang=target_lang.flores_code)
    except Exception as exc:
        raise RuntimeError(f"Text translation failed: {exc}") from exc
    return [(s.start, s.end, t) for s, t in zip(en_result.segments, translated) if t.strip()]


def _synthesize_and_align(job_id, jobs, tts, target_lang, audio_path, final_segments, work_dir):
    info = sf.info(str(audio_path))
    total_duration = info.frames / info.samplerate
    sr = tts.sampling_rate
    canvas = np.zeros(int(total_duration * sr) + sr, dtype=np.float32)

    segments_dir = work_dir / "segments"
    segments_dir.mkdir(exist_ok=True)

    n = len(final_segments)
    synthesized_count = 0
    for i, (start, end, text) in enumerate(final_segments):
        try:
            description = build_description(target_lang, voice_index=i % 2)
            audio_arr = np.asarray(tts.synthesize(text, description), dtype=np.float32)

            raw_path = segments_dir / f"seg_{i:04d}_raw.wav"
            sf.write(str(raw_path), audio_arr, sr)

            target_duration = max(end - start, 0.05)
            tts_duration = len(audio_arr) / sr
            speed_factor = tts_duration / target_duration if target_duration > 0 else 1.0

            if 0.9 <= speed_factor <= 1.1:
                seg_audio = audio_arr
            else:
                stretched_path = segments_dir / f"seg_{i:04d}.wav"
                time_stretch_audio(str(raw_path), str(stretched_path), speed_factor)
                seg_audio, _ = sf.read(str(stretched_path), dtype="float32")

            start_sample = int(start * sr)
            end_sample = start_sample + len(seg_audio)
            if end_sample > len(canvas):
                canvas = np.pad(canvas, (0, end_sample - len(canvas)))
            canvas[start_sample:end_sample] += seg_audio
            synthesized_count += 1
        except Exception:
            # Don't let one bad segment (e.g. an unusual string or a
            # transient generation error) abort the whole dubbed video.
            logger.exception("Job %s: failed to synthesize segment %d/%d, skipping it", job_id, i + 1, n)
            jobs.update(job_id, message=f"Warning: could not synthesize segment {i + 1}/{n}, skipping it.")
            continue

        jobs.update(
            job_id, progress=0.55 + 0.30 * ((i + 1) / n),
            message=f"Synthesized segment {i + 1}/{n}.",
        )

    if synthesized_count == 0:
        raise RuntimeError("All speech segments failed to synthesize.")

    peak = float(np.max(np.abs(canvas))) if canvas.size else 0.0
    if peak > 1.0:
        canvas = canvas / peak

    dubbed_audio_path = work_dir / "dubbed_audio.wav"
    sf.write(str(dubbed_audio_path), canvas, sr)
    return dubbed_audio_path
