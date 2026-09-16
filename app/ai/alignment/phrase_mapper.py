"""Diagnostic source-phrase grouping for existing IndicConformer word timings.

This module consumes alignment sidecar data; it does not run ASR, alter a
transcript, regenerate translation, or connect to TTS. Marathi-to-Hindi phrase
allocation is deliberately marked heuristic because translated word indexes
are not semantically equivalent.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

DEFAULT_MIN_PAUSE_SECONDS = 0.35
DEFAULT_MAX_PHRASE_WORDS = 18
DEFAULT_MAX_PHRASE_SECONDS = 8.0


def map_phrases(
    alignment_segments: Iterable[dict[str, Any]],
    translation_segments: Iterable[dict[str, Any]],
    *,
    pauses: Iterable[dict[str, float]] | None = None,
    min_pause_seconds: float = DEFAULT_MIN_PAUSE_SECONDS,
    max_phrase_words: int = DEFAULT_MAX_PHRASE_WORDS,
    max_phrase_seconds: float = DEFAULT_MAX_PHRASE_SECONDS,
) -> dict[str, Any]:
    """Build diagnostic source phrases and heuristic Hindi phrase allocation."""
    alignment_segments = list(alignment_segments)
    translations = list(translation_segments)
    translation_by_timing = {
        (float(item["start"]), float(item["end"])): item for item in translations
    }
    pause_list = [
        (float(item["start"]), float(item["end"])) for item in (pauses or [])
        if float(item["end"]) > float(item["start"])
    ]
    output_segments = []
    source_words_lost = 0
    target_words_lost = 0
    missing_translations = 0
    for segment in alignment_segments:
        source_start = float(segment["source_start"])
        source_end = float(segment["source_end"])
        words = list(segment.get("words", []))
        translation = translation_by_timing.get((source_start, source_end))
        if translation is None:
            missing_translations += 1
            output_segments.append(_missing_segment(segment, "no translation segment has matching source timing"))
            continue
        target_text = str(translation.get("text", "")).strip()
        groups = _group_source_words(
            words,
            pause_list,
            min_pause_seconds=min_pause_seconds,
            max_phrase_words=max_phrase_words,
            max_phrase_seconds=max_phrase_seconds,
        )
        target_parts = _allocate_target_text(target_text, groups)
        phrases = []
        for phrase_id, (group, target_part) in enumerate(zip(groups, target_parts), 1):
            phrases.append({
                "phrase_id": phrase_id,
                "source_segment_id": segment.get("segment_id"),
                "start": group["start"],
                "end": group["end"],
                "source_text": group["text"],
                "boundary_reason": group["boundary_reason"],
                "target_text": target_part,
                "target_word_count": len(target_part.split()),
                "target_duration": max(0.0, group["end"] - group["start"]),
                "mapping_method": "proportional_phrase_allocation",
                "warnings": (["Hindi phrase boundary is heuristic; no semantic word alignment was performed"]),
            })
        source_words_lost += max(0, len(words) - sum(len(group["words"]) for group in groups))
        target_words_lost += max(0, len(target_text.split()) - sum(len(part.split()) for part in target_parts))
        output_segments.append({
            "source_segment_id": segment.get("segment_id"),
            "source_start": source_start,
            "source_end": source_end,
            "source_text": segment.get("source_text", ""),
            "translation_missing": False,
            "target_text": target_text,
            "target_text_preserved": " ".join(target_text.split()) == " ".join(" ".join(target_parts).split()),
            "phrases": phrases,
            "warnings": [],
        })
    phrases = [phrase for segment in output_segments for phrase in segment.get("phrases", [])]
    durations = [phrase["target_duration"] for phrase in phrases]
    return {
        "version": "1.0",
        "alignment_method": "indicconformer_word_timestamps_phrase_mapping",
        "mapping_method": "source_word_gaps_plus_optional_pauses_and_proportional_target_allocation",
        "segments": output_segments,
        "statistics": {
            "source_segments": len(alignment_segments),
            "source_phrases": len(phrases),
            "average_phrase_duration": sum(durations) / len(durations) if durations else 0.0,
            "minimum_phrase_duration": min(durations) if durations else 0.0,
            "maximum_phrase_duration": max(durations) if durations else 0.0,
            "natural_pause_boundaries": sum(p["boundary_reason"] == "natural_pause" for p in phrases),
            "punctuation_boundaries": sum(p["boundary_reason"] == "punctuation" for p in phrases),
            "safety_boundaries": sum(p["boundary_reason"] == "safety_word_limit" for p in phrases),
            "source_words_lost": source_words_lost,
            "target_words_lost": target_words_lost,
            "missing_translations": missing_translations,
        },
        "limitations": [
            "Hindi phrases are allocated proportionally, not semantically aligned word-for-word.",
            "Source timing resolution is inherited from the approximately 80 ms CTC word timestamps.",
            "No TTS or production pipeline integration is performed.",
        ],
    }


def load_and_map(alignment_path: str | Path, translation_path: str | Path, output_path: str | Path, **kwargs) -> dict[str, Any]:
    alignment = json.loads(Path(alignment_path).read_text(encoding="utf-8"))
    translation = json.loads(Path(translation_path).read_text(encoding="utf-8"))
    pauses = kwargs.pop("pauses", None)
    if pauses is None:
        pauses = derive_pause_intervals(alignment["segments"])
    report = map_phrases(alignment["segments"], translation["segments"], pauses=pauses, **kwargs)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def derive_pause_intervals(alignment_segments, *, min_pause_seconds=DEFAULT_MIN_PAUSE_SECONDS):
    """Return gaps already represented by adjacent aligned word timestamps."""
    pauses = []
    for segment in alignment_segments:
        words = segment.get("words", [])
        for previous, current in zip(words, words[1:]):
            start = float(previous["end"])
            end = float(current["start"])
            if end - start >= min_pause_seconds:
                pauses.append({"start": start, "end": end})
    return pauses


def _group_source_words(words, pauses, *, min_pause_seconds, max_phrase_words, max_phrase_seconds):
    if not words:
        return []
    groups = []
    current = [words[0]]
    for word in words[1:]:
        previous = current[-1]
        gap_start, gap_end = float(previous["end"]), float(word["start"])
        gap = max(0.0, gap_end - gap_start)
        has_pause = any(start <= gap_start + 0.04 and end >= gap_end - 0.04 for start, end in pauses)
        punctuation = bool(re.search(r"[।.!?]$", str(previous.get("text", ""))))
        reason = "natural_pause" if has_pause and gap >= min_pause_seconds else ("punctuation" if punctuation else None)
        long_phrase = word["end"] - current[0]["start"] >= max_phrase_seconds
        too_many_words = len(current) >= max_phrase_words
        if reason or long_phrase or too_many_words:
            groups.append(_make_group(current, reason or ("safety_word_limit" if too_many_words else "punctuation")))
            current = [word]
        else:
            current.append(word)
    groups.append(_make_group(current, "segment_end"))
    return groups


def _make_group(words, reason):
    return {
        "words": words,
        "start": float(words[0]["start"]),
        "end": float(words[-1]["end"]),
        "text": " ".join(word["text"] for word in words),
        "boundary_reason": reason,
    }


def _allocate_target_text(text, groups):
    target_words = text.split()
    if not groups:
        return []
    if len(groups) == 1:
        return [text]
    total_source_words = sum(len(group["words"]) for group in groups)
    parts = []
    position = 0
    for index, group in enumerate(groups):
        if index == len(groups) - 1:
            end = len(target_words)
        else:
            end = position + max(1, round(len(target_words) * len(group["words"]) / max(total_source_words, 1)))
            remaining_groups = len(groups) - index - 1
            end = min(end, len(target_words) - remaining_groups)
        parts.append(" ".join(target_words[position:end]))
        position = end
    return parts


def _missing_segment(segment, warning):
    return {
        "source_segment_id": segment.get("segment_id"),
        "source_start": float(segment["source_start"]),
        "source_end": float(segment["source_end"]),
        "source_text": segment.get("source_text", ""),
        "translation_missing": True,
        "target_text": "",
        "target_text_preserved": False,
        "phrases": [],
        "warnings": [warning],
    }
