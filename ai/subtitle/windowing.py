"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : windowing.py
Purpose     : Rolling Subtitle Window Generation

Description:
    Builds readable, time-accurate rolling subtitle groups from a
    word-timed SubtitleSegment, so a subtitle no longer stays on screen for
    an entire ASR/translation segment.

    Groups are formed by greedily packing consecutive words until adding
    another word would exceed the configured max characters-per-line /
    max lines-per-subtitle, keeping this readable (never one word per
    subtitle, never a giant multi-sentence block).

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.subtitle.config import SubtitleConfig
from ai.subtitle.models import SubtitleSegment, SubtitleWord


def _sanitize_words(
    words: list[SubtitleWord],
    segment_start: float,
    segment_end: float,
) -> list[SubtitleWord]:
    """
    Defensively clean word timing: finite, ordered, clamped to the segment
    window and strictly non-overlapping.
    """

    cleaned: list[tuple[str, float, float]] = []

    for word in words:

        text = (word.word or "").strip()

        if not text:
            continue

        start, end = word.start, word.end

        if (
            start != start  # NaN
            or end != end  # NaN
            or not isinstance(start, (int, float))
            or not isinstance(end, (int, float))
        ):
            continue

        if end < start:
            start, end = end, start

        start = min(max(start, segment_start), segment_end)
        end = min(max(end, segment_start), segment_end)

        if end <= start:
            continue

        cleaned.append((text, start, end))

    cleaned.sort(key=lambda item: item[1])

    normalized: list[SubtitleWord] = []
    previous_end = segment_start

    for text, start, end in cleaned:

        start = max(start, previous_end)

        if end <= start:
            continue

        normalized.append(SubtitleWord(word=text, start=start, end=end))
        previous_end = end

    return normalized


def _wrap_text(text: str, max_characters_per_line: int) -> list[str]:
    """
    Wrap text into lines without splitting words. A single word longer than
    the limit is kept whole on its own line rather than being cut.
    """

    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:

        candidate = f"{current} {word}".strip()

        if len(candidate) <= max_characters_per_line or not current:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def _fits(text: str, max_characters_per_line: int, max_lines: int) -> bool:
    return len(_wrap_text(text, max_characters_per_line)) <= max_lines


def build_rolling_groups(
    segment: SubtitleSegment,
    config: SubtitleConfig,
) -> list[SubtitleSegment]:
    """
    Expand one (typically long) word-timed segment into several smaller,
    contiguous, non-overlapping subtitle groups sized to the configured
    line/character limits.

    Falls back to returning the original segment unchanged whenever word
    timing is unavailable or unusable, rather than raising.
    """

    if not segment.words:
        return [segment]

    max_characters_per_line = max(1, config.max_characters_per_line)
    max_lines = max(1, config.max_lines_per_subtitle)

    words = _sanitize_words(segment.words, segment.start, segment.end)

    if not words:
        return [segment]

    groups: list[list[SubtitleWord]] = []
    current: list[SubtitleWord] = []

    for word in words:

        candidate_text = " ".join(
            w.word for w in (current + [word])
        )

        if current and not _fits(
            candidate_text, max_characters_per_line, max_lines
        ):
            groups.append(current)
            current = [word]
        else:
            current.append(word)

    if current:
        groups.append(current)

    if not groups:
        return [segment]

    results: list[SubtitleSegment] = []

    for group in groups:

        text = "\n".join(
            _wrap_text(
                " ".join(w.word for w in group),
                max_characters_per_line,
            )
        )

        results.append(
            SubtitleSegment(
                start=group[0].start,
                end=group[-1].end,
                text=text,
            )
        )

    # Guarantee full, gap-free, non-overlapping coverage of the source
    # segment window: the subtitle currently on screen stays up until the
    # next one is ready to replace it.
    results[0].start = segment.start

    for index in range(len(results) - 1):
        results[index].end = results[index + 1].start

    results[-1].end = segment.end

    return results
