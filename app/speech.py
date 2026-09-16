"""Audio-driven speech regions and bounded ASR inference chunk planning."""
from __future__ import annotations

from dataclasses import dataclass
import re

import numpy as np

from app.config import (
    ASR_REFINE_MAX_INSIGNIFICANT_SILENCE_SECONDS,
    ASR_REFINE_MIN_EVENT_DURATION_SECONDS,
    ASR_REFINE_MIN_FRAGMENT_WORDS,
    ASR_REFINE_MIN_PAUSE_SECONDS,
    ASR_REFINE_SAFE_BOUNDARY_WINDOW_SECONDS,
    ASR_REFINE_SILENCE_THRESHOLD,
)


@dataclass(frozen=True)
class SpeechRegion:
    start: float
    end: float


@dataclass(frozen=True)
class ASRChunk:
    start: float
    end: float
    reason: str


def refine_segments_by_audio(
    audio: np.ndarray,
    sample_rate: int,
    segments,
    *,
    silence_threshold: float = ASR_REFINE_SILENCE_THRESHOLD,
    min_pause_seconds: float = ASR_REFINE_MIN_PAUSE_SECONDS,
    max_insignificant_silence_seconds: float = ASR_REFINE_MAX_INSIGNIFICANT_SILENCE_SECONDS,
    min_event_duration_seconds: float = ASR_REFINE_MIN_EVENT_DURATION_SECONDS,
    min_fragment_words: int = ASR_REFINE_MIN_FRAGMENT_WORDS,
    safe_boundary_window_seconds: float = ASR_REFINE_SAFE_BOUNDARY_WINDOW_SECONDS,
):
    """Split raw ASR segments only at meaningful waveform pauses.

    Text is partitioned at complete word boundaries selected near the audio
    pause. No text is inferred, corrected, or aligned by token semantics.
    """
    if not segments or sample_rate <= 0:
        return [], {"internal_pauses_detected": 0, "boundaries_created": 0, "unsafe_pauses": 0}
    mono = np.mean(audio, axis=1) if getattr(audio, "ndim", 1) > 1 else audio
    frame = max(1, int(sample_rate * 0.02))
    refined = []
    detected = created = unsafe = 0
    for segment_id, segment in enumerate(segments):
        words = segment.text.split()
        if not words or segment.end <= segment.start:
            continue
        first = max(0, int(segment.start * sample_rate))
        last = min(len(mono), int(segment.end * sample_rate))
        frame_count = (last - first) // frame
        if frame_count <= 0:
            refined.append(_refined_segment(segment, segment_id, segment.start, segment.end, segment.text, "ASR_BOUNDARY"))
            continue
        section = mono[first:first + frame_count * frame]
        energy = np.sqrt(np.mean(section.reshape(frame_count, frame) ** 2, axis=1) + 1e-12)
        silent = energy < silence_threshold
        pauses = _pause_runs(silent, frame, sample_rate, segment.start, min_pause_seconds)
        detected += len(pauses)
        boundaries = []
        previous = segment.start
        for pause_start, pause_end in pauses:
            relative = (pause_start + pause_end) / 2 - segment.start
            ratio = relative / max(segment.end - segment.start, 1e-6)
            desired_index = min(len(words) - 1, max(0, round(ratio * len(words)) - 1))
            candidates = []
            for index in range(1, len(words)):
                boundary_time = segment.start + (segment.end - segment.start) * index / len(words)
                distance = abs(boundary_time - (pause_start + pause_end) / 2)
                punctuation = bool(re.search(r"[।.!?;:,，、]$", words[index - 1]))
                candidates.append((distance, 0 if punctuation else 1, abs(index - desired_index), index, boundary_time))
            candidates.sort()
            chosen = next((item for item in candidates if item[0] <= safe_boundary_window_seconds), None)
            if chosen is None:
                unsafe += 1
                continue
            _, _, _, index, boundary_time = chosen
            left_duration = boundary_time - previous
            right_duration = segment.end - boundary_time
            if index < min_fragment_words or len(words) - index < min_fragment_words:
                unsafe += 1
                continue
            if left_duration < min_event_duration_seconds or right_duration < min_event_duration_seconds:
                unsafe += 1
                continue
            boundaries.append((index, pause_start, pause_end))
            previous = pause_end
        if not boundaries:
            refined.append(_refined_segment(segment, segment_id, segment.start, segment.end, segment.text, "ASR_BOUNDARY"))
            continue
        word_start = 0
        event_start = segment.start
        for index, pause_start, pause_end in boundaries:
            text = " ".join(words[word_start:index]).strip()
            refined.append(_refined_segment(segment, segment_id, event_start, pause_start, text, "NATURAL_PAUSE", pause_after=pause_end - pause_start))
            word_start = index
            event_start = pause_end
            created += 1
        text = " ".join(words[word_start:]).strip()
        refined.append(_refined_segment(segment, segment_id, event_start, segment.end, text, "NATURAL_PAUSE"))
    for index, segment in enumerate(refined):
        if index:
            segment.pause_before = max(0.0, segment.start - refined[index - 1].end)
    return refined, {"internal_pauses_detected": detected, "boundaries_created": created, "unsafe_pauses": unsafe}


def _pause_runs(silent, frame, sample_rate, segment_start, min_pause_seconds):
    pauses = []
    index = 0
    while index < len(silent):
        if not silent[index]:
            index += 1
            continue
        end = index + 1
        while end < len(silent) and silent[end]:
            end += 1
        duration = (end - index) * frame / sample_rate
        if duration >= min_pause_seconds:
            pauses.append((segment_start + index * frame / sample_rate, segment_start + end * frame / sample_rate))
        index = end
    return pauses


def _refined_segment(segment, source_segment_id, start, end, text, reason, pause_after=None):
    return type(segment)(
        start=float(start), end=float(end), text=text,
        source_segment_id=source_segment_id,
        pause_after=pause_after,
        confidence=getattr(segment, "confidence", None),
        segmentation_reason=reason,
    )


def validate_asr_segments(segments) -> dict:
    """Report transcript risks without modifying recognized text."""
    warnings = []
    previous_end = None
    seen_words = set()
    word_count = 0
    for index, segment in enumerate(segments):
        text = str(segment.text or "").strip()
        words = text.split()
        word_count += len(words)
        if not text or segment.end <= segment.start:
            warnings.append({"index": index, "reason": "EMPTY_OR_INVALID_EVENT"})
        if previous_end is not None and segment.start < previous_end:
            warnings.append({"index": index, "reason": "OVERLAPPING_OR_NON_MONOTONIC_TIMESTAMP"})
        if len(words) >= 4 and len(words) % 2 == 0 and words[: len(words) // 2] == words[len(words) // 2:]:
            warnings.append({"index": index, "reason": "DUPLICATED_WORD_SEQUENCE"})
        for word in words:
            normal = word.casefold()
            if normal in seen_words and len(normal) > 2:
                continue
            seen_words.add(normal)
        previous_end = max(previous_end or segment.end, segment.end)
    return {
        "segment_count": len(segments),
        "word_count": word_count,
        "warnings": warnings,
        "timestamp_violations": sum(item["reason"] == "OVERLAPPING_OR_NON_MONOTONIC_TIMESTAMP" for item in warnings),
        "empty_or_invalid_events": sum(item["reason"] == "EMPTY_OR_INVALID_EVENT" for item in warnings),
    }


def detect_speech_regions(
    audio: np.ndarray,
    sample_rate: int,
    *,
    threshold: float,
    min_silence_ms: int,
    speech_padding_ms: int,
) -> list[SpeechRegion]:
    """Return absolute speech regions from the source audio timeline."""
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    options = VadOptions(
        threshold=threshold,
        min_speech_duration_ms=250,
        min_silence_duration_ms=min_silence_ms,
        speech_pad_ms=speech_padding_ms,
    )
    return [
        SpeechRegion(item["start"] / sample_rate, item["end"] / sample_rate)
        for item in get_speech_timestamps(audio, vad_options=options, sampling_rate=sample_rate)
        if item["end"] > item["start"]
    ]


def plan_asr_chunks(
    regions: list[SpeechRegion],
    *,
    max_duration: float,
    overlap_duration: float,
) -> list[ASRChunk]:
    """Prefer VAD pause boundaries; use model limits only when necessary."""
    chunks: list[ASRChunk] = []
    current: list[SpeechRegion] = []

    def emit_current(reason: str) -> None:
        if current:
            chunks.append(ASRChunk(current[0].start, current[-1].end, reason))
            current.clear()

    for region in regions:
        if region.end - region.start > max_duration:
            emit_current("NATURAL_PAUSE")
            split_start = region.start
            while split_start < region.end:
                split_end = min(split_start + max_duration, region.end)
                chunks.append(ASRChunk(split_start, split_end, "MODEL_SAFETY_LIMIT"))
                if split_end == region.end:
                    break
                split_start = split_end - overlap_duration
            continue
        if not current:
            current.append(region)
        elif region.end - current[0].start <= max_duration:
            current.append(region)
        else:
            emit_current("NATURAL_PAUSE")
            current.append(region)
    emit_current("AUDIO_BOUNDARY")
    return chunks