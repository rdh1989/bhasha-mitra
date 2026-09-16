"""Optional transcript-constrained CTC alignment for IndicConformer.

This is a sidecar capability. It never performs normal ASR and never writes
transcript.json. The supplied transcript is the forced target sequence.

IndicConformer emits one CTC frame approximately every 80 ms. The resulting
word spans are therefore approximate model-frame timings, not millisecond
precision or human-annotated ground truth.
"""
from __future__ import annotations

import json
import logging
import math
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "mr"
DEFAULT_FRAME_DURATION_SECONDS = 0.08
DEFAULT_MAX_CHUNK_SECONDS = 15.0


def align(
    audio_path: str | Path,
    transcript_segments: Iterable[dict[str, Any]],
    model,
    output_path: str | Path,
    *,
    language: str = DEFAULT_LANGUAGE,
    max_chunk_seconds: float = DEFAULT_MAX_CHUNK_SECONDS,
) -> dict[str, Any]:
    """Force-align known transcript text against IndicConformer CTC output.

    ``model`` should be an already-loaded ``IndicASREngine``. A compatible
    model-like object exposing ``ensure_loaded()`` and ``_model`` is accepted
    to keep this module independent from ModelManager and production ASR.
    """
    started = time.monotonic()
    segments = [_normalise_segment(item, index) for index, item in enumerate(transcript_segments)]
    audio, sample_rate = sf.read(str(audio_path), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    duration = len(audio) / sample_rate if sample_rate else 0.0
    _validate_chunk_limit(segments, max_chunk_seconds)

    model.ensure_loaded()
    core = getattr(model, "_model", None)
    if core is None:
        raise ValueError("model must expose an already-loaded IndicConformer instance as _model")
    frame_duration = float(getattr(core.config, "FRAME_DURATION_MS", DEFAULT_FRAME_DURATION_SECONDS))
    if frame_duration > 1.0:
        frame_duration /= 1000.0
    blank_id = int(core.config.BLANK_ID)
    vocab = list(core.vocab[language])
    token_ids = {token: index for index, token in enumerate(vocab)}

    output_segments = []
    failed = 0
    low_quality = 0
    total_words = 0
    for segment in segments:
        result = _align_segment(
            audio, sample_rate, segment, core, language, token_ids, vocab,
            blank_id, frame_duration, max_chunk_seconds,
        )
        output_segments.append(result)
        quality = result["quality"]
        failed += quality == "failed"
        low_quality += quality in ("low", "warning")
        total_words += len(result["words"])

    report = {
        "version": "1.0",
        "alignment_method": "indicconformer_ctc_forced",
        "language": language,
        "duration": duration,
        "timestamp_resolution_seconds": frame_duration,
        "segments": output_segments,
        "statistics": {
            "transcript_segments": len(segments),
            "aligned_segments": sum(item["quality"] != "failed" for item in output_segments),
            "aligned_words": total_words,
            "failed_segments": failed,
            "low_quality_segments": low_quality,
            "words_not_aligned": sum(item["words_not_aligned"] for item in output_segments),
            "chunk_boundaries": sum(item["chunk_count"] - 1 for item in output_segments),
            "overlap_duplicates_removed": 0,
            "average_word_duration_seconds": _average_word_duration(output_segments),
            "minimum_word_duration_seconds": _word_duration_stat(output_segments, min),
            "maximum_word_duration_seconds": _word_duration_stat(output_segments, max),
            "processing_time_seconds": time.monotonic() - started,
            "model_reused": True,
        },
        "limitations": [
            "CTC frame timing resolution is approximately %.3f seconds." % frame_duration,
            "Spans are greedy-frame/forced-path estimates, not annotated ground truth.",
            "Confidence is intentionally null because no calibrated confidence is computed.",
        ],
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _normalise_segment(item: dict[str, Any], index: int) -> dict[str, Any]:
    start = float(item.get("start", item.get("source_start")))
    end = float(item.get("end", item.get("source_end")))
    text = str(item.get("text", item.get("source_text", ""))).strip()
    if end <= start or not text:
        raise ValueError(f"Invalid transcript segment {index}: expected positive interval and text")
    return {"segment_id": item.get("segment_id", index), "start": start, "end": end, "text": text}


def _validate_chunk_limit(segments: list[dict[str, Any]], max_chunk_seconds: float) -> None:
    for segment in segments:
        if segment["end"] - segment["start"] > max_chunk_seconds + 1e-6:
            raise ValueError(
                f"Segment {segment['segment_id']} exceeds the {max_chunk_seconds:.2f}s alignment chunk limit"
            )


def _align_segment(audio, sample_rate, segment, core, language, token_ids, vocab, blank_id, frame_duration, max_chunk_seconds):
    start_sample = round(segment["start"] * sample_rate)
    end_sample = round(segment["end"] * sample_rate)
    warnings: list[str] = []
    labels, unknown = _tokenize_text(segment["text"], token_ids, vocab, blank_id)
    if unknown:
        warnings.append("Transcript contains text not representable by the model vocabulary: " + " ".join(unknown[:8]))
        return _failed_segment(segment, warnings, len(unknown))
    try:
        logprobs, encoded_length = _ctc_logprobs(
            core, audio[start_sample:end_sample], sample_rate, language
        )
        if encoded_length < len(labels):
            return _failed_segment(segment, ["CTC frame count is shorter than the forced token sequence"], 0)
        token_spans, score = _viterbi_spans(logprobs[:encoded_length], labels, blank_id)
        words = _group_words(token_spans, labels, vocab, segment["start"], segment["end"], frame_duration)
        words_not_aligned = len(labels) - len(token_spans)
        quality = "good"
        if not words or words_not_aligned:
            quality = "low"
            warnings.append("One or more forced tokens did not receive a non-blank frame")
        elif score / max(encoded_length, 1) < -8.0:
            quality = "warning"
            warnings.append("Low mean forced-path log score; timing may be unreliable")
        _validate_words(words, segment["start"], segment["end"])
        return {
            "segment_id": segment["segment_id"],
            "source_start": segment["start"],
            "source_end": segment["end"],
            "source_text": segment["text"],
            "quality": quality,
            "warnings": warnings,
            "words": words,
            "words_not_aligned": words_not_aligned,
            "chunk_count": 1,
            "forced_path_mean_log_score": score / max(encoded_length, 1),
        }
    except Exception as exc:  # alignment is an optional sidecar
        logger.exception("CTC alignment failed for segment %s", segment["segment_id"])
        return _failed_segment(segment, [f"Alignment error: {exc}"], 0)


def _ctc_logprobs(core, audio, sample_rate, language):
    import torch
    import torchaudio

    wav = torch.from_numpy(np.asarray(audio, dtype=np.float32)).unsqueeze(0)
    if sample_rate != 16000:
        wav = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)(wav)
    with torch.no_grad():
        encoder_outputs, encoded_lengths = core.encode(wav)
    raw = core.models["ctc_decoder"].run(["logprobs"], {"encoder_output": encoder_outputs})[0]
    mask = np.asarray(core.language_masks[language], dtype=bool)
    selected = torch.from_numpy(raw[:, :, mask]).log_softmax(dim=-1)[0]
    return selected.numpy(), int(encoded_lengths[0].item())


def _tokenize_text(text: str, token_ids: dict[str, int], vocab: list[str], blank_id: int):
    normalised = "▁" + text.strip().replace(" ", "▁")
    usable = [token for index, token in enumerate(vocab) if index not in (0, blank_id) and token]
    usable.sort(key=len, reverse=True)
    labels = []
    unknown = []
    position = 0
    while position < len(normalised):
        match = next((token for token in usable if normalised.startswith(token, position)), None)
        if match is None:
            unknown.append(normalised[position])
            position += 1
        else:
            labels.append(token_ids[match])
            position += len(match)
    return labels, unknown


def _viterbi_spans(logprobs: np.ndarray, labels: list[int], blank_id: int):
    extended = [blank_id]
    for label in labels:
        extended.extend((label, blank_id))
    states = len(extended)
    frames = logprobs.shape[0]
    scores = np.full(states, -np.inf, dtype=np.float64)
    back = np.full((frames, states), -1, dtype=np.int32)
    scores[0] = float(logprobs[0, blank_id])
    if states > 1:
        scores[1] = float(logprobs[0, extended[1]])
    for frame in range(1, frames):
        next_scores = np.full(states, -np.inf, dtype=np.float64)
        for state, label in enumerate(extended):
            candidates = [(scores[state], state)]
            if state > 0:
                candidates.append((scores[state - 1], state - 1))
            if state > 1 and label != blank_id and label != extended[state - 2]:
                candidates.append((scores[state - 2], state - 2))
            previous_score, previous_state = max(candidates, key=lambda item: item[0])
            next_scores[state] = previous_score + float(logprobs[frame, label])
            back[frame, state] = previous_state
        scores = next_scores
    end_state = states - 1 if scores[states - 1] >= scores[max(states - 2, 0)] else states - 2
    path = [end_state]
    for frame in range(frames - 1, 0, -1):
        path.append(int(back[frame, path[-1]]))
    path.reverse()
    spans = []
    for label_index, label in enumerate(labels):
        state = 2 * label_index + 1
        indexes = [frame for frame, path_state in enumerate(path) if path_state == state]
        if indexes:
            spans.append((label_index, label, min(indexes), max(indexes) + 1))
    return spans, float(scores[end_state])


def _group_words(token_spans, labels, vocab, source_start, source_end, frame_duration):
    words = []
    current = None
    for label_index, label, start_frame, end_frame in token_spans:
        token = vocab[label]
        starts_word = token.startswith("▁")
        token_text = token.replace("▁", "")
        if starts_word and current is not None:
            words.append(current)
            current = None
        if current is None:
            current = {"text": token_text, "start": min(source_end, source_start + start_frame * frame_duration), "end": min(source_end, source_start + end_frame * frame_duration)}
        else:
            current["text"] += token_text
            current["end"] = min(source_end, source_start + end_frame * frame_duration)
    if current is not None:
        words.append(current)
    for word in words:
        word["confidence"] = None
    return words


def _validate_words(words, segment_start, segment_end):
    previous_end = segment_start
    for word in words:
        if not segment_start <= word["start"] < word["end"] <= segment_end:
            raise ValueError("word span lies outside its source segment")
        if word["start"] < previous_end:
            raise ValueError("word spans are not monotonic")
        previous_end = word["end"]


def _failed_segment(segment, warnings, words_not_aligned):
    return {
        "segment_id": segment["segment_id"],
        "source_start": segment["start"],
        "source_end": segment["end"],
        "source_text": segment["text"],
        "quality": "failed",
        "warnings": warnings,
        "words": [],
        "words_not_aligned": words_not_aligned,
        "chunk_count": 1,
        "forced_path_mean_log_score": None,
    }


def _word_duration_stat(segments, function):
    durations = [word["end"] - word["start"] for segment in segments for word in segment["words"]]
    return function(durations) if durations else None


def _average_word_duration(segments):
    durations = [word["end"] - word["start"] for segment in segments for word in segment["words"]]
    return sum(durations) / len(durations) if durations else None


if __name__ == "__main__":
    raise SystemExit("Import align() from this sidecar module; it does not alter production ASR.")
