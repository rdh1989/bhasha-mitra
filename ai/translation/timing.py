"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : timing.py
Purpose     : Translation Word Timing Alignment

Description:
    Translation can reorder, merge, split, or otherwise change the number of
    words compared to the source text, so translated words can NEVER be
    assigned the source words' timestamps directly.

    This module distributes translated words across the source segment's
    speaking timeline (derived from ASR word timestamps) so that rolling
    subtitle windows can be generated for the translated text while staying
    strictly within the original source segment's [start, end] boundaries.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TranslationWord:
    """
    A translated word with a derived (approximate) timestamp.
    """

    word: str

    start: float

    end: float


def _sanitize_source_words(
    source_words: list[dict],
    unit_start: float,
    unit_end: float,
) -> list[tuple[str, float, float]]:
    """
    Defensively clean source ASR word timing so it can be used to build a
    speaking-time envelope: finite, ordered, clamped to the unit window and
    non-overlapping.
    """

    cleaned: list[tuple[str, float, float]] = []

    for raw_word in source_words:

        if not isinstance(raw_word, dict):
            continue

        try:
            start = float(raw_word.get("start"))
            end = float(raw_word.get("end"))
        except (TypeError, ValueError):
            continue

        if start != start or end != end:  # NaN guard
            continue

        if end < start:
            start, end = end, start

        start = min(max(start, unit_start), unit_end)
        end = min(max(end, unit_start), unit_end)

        if end <= start:
            continue

        text = str(raw_word.get("word", "")).strip()

        if not text:
            continue

        cleaned.append((text, start, end))

    cleaned.sort(key=lambda item: item[1])

    normalized: list[tuple[str, float, float]] = []
    previous_end = unit_start

    for text, start, end in cleaned:

        start = max(start, previous_end)

        if end <= start:
            continue

        normalized.append((text, start, end))
        previous_end = end

    return normalized


def _map_active_to_real(
    active_position: float,
    active_bounds: list[tuple[float, float, float, float]],
) -> float:
    """
    Map a position in the concatenated "active speaking time" domain back to
    real time using the source word intervals it was built from.
    """

    for active_start, active_end, real_start, real_end in active_bounds:

        if active_position <= active_end + 1e-9:

            span = active_end - active_start

            if span <= 1e-9:
                return real_start

            fraction = (active_position - active_start) / span
            fraction = min(max(fraction, 0.0), 1.0)

            return real_start + fraction * (real_end - real_start)

    return active_bounds[-1][3]


def align_translation_words(
    translated_text: str,
    unit_start: float,
    unit_end: float,
    source_words: list[dict] | None = None,
) -> list[TranslationWord]:
    """
    Distribute the words of `translated_text` across [unit_start, unit_end].

    Strategy
    --------
    • Each translated word is weighted by its character length (longer
      words are shown longer).
    • When source ASR word timestamps are available, the weighted
      distribution is mapped through the source words' speaking-time
      envelope (silence between source words is skipped) so pacing follows
      the original audio rather than a flat linear spread.
    • When source word timing is unavailable (or there are too few points
      to build an envelope), fall back to a flat proportional distribution
      across the unit window.

    The result is always monotonic, non-overlapping, and clamped to
    [unit_start, unit_end] regardless of translation reordering/merging.
    """

    tokens = translated_text.split()

    if not tokens:
        return []

    if not (unit_end > unit_start):
        # Degenerate/invalid window: collapse safely instead of crashing.
        return [
            TranslationWord(word=token, start=unit_start, end=unit_start)
            for token in tokens
        ]

    total_duration = unit_end - unit_start
    weights = [max(len(token), 1) for token in tokens]
    total_weight = sum(weights)

    cleaned_source = _sanitize_source_words(
        source_words or [],
        unit_start,
        unit_end,
    )

    if len(cleaned_source) >= 2:

        active_bounds: list[tuple[float, float, float, float]] = []
        cursor = 0.0

        for _, real_start, real_end in cleaned_source:
            span = real_end - real_start
            active_bounds.append((cursor, cursor + span, real_start, real_end))
            cursor += span

        total_active = cursor

        if total_active <= 1e-9:
            active_bounds = [(0.0, total_duration, unit_start, unit_end)]
            total_active = total_duration

    else:
        active_bounds = [(0.0, total_duration, unit_start, unit_end)]
        total_active = total_duration

    cumulative = 0.0
    active_boundaries = [0.0]

    for weight in weights:
        cumulative += weight
        active_boundaries.append(cumulative / total_weight * total_active)

    words: list[TranslationWord] = []

    for index, token in enumerate(tokens):

        start = _map_active_to_real(active_boundaries[index], active_bounds)
        end = _map_active_to_real(active_boundaries[index + 1], active_bounds)

        start = min(max(start, unit_start), unit_end)
        end = min(max(end, unit_start), unit_end)

        if end < start:
            end = start

        words.append(TranslationWord(word=token, start=start, end=end))

    # Enforce strict monotonic, non-overlapping timing.
    for index in range(1, len(words)):
        if words[index].start < words[index - 1].end:
            words[index].start = words[index - 1].end
            if words[index].end < words[index].start:
                words[index].end = words[index].start

    words[-1].end = unit_end

    return words
