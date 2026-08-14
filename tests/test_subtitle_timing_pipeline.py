"""
===============================================================================
Bhasha Mitra - Subtitle Timing Pipeline Tests
-------------------------------------------------------------------------------
Covers the rolling-subtitle-window behavior end to end:

    ASR word timestamps -> translated word timing alignment ->
    rolling subtitle window generation -> SRT output.

Author:
    Bhasha Mitra AI Team
===============================================================================
"""

from __future__ import annotations

import re

from ai.subtitle.adapter import SubtitleAdapter
from ai.subtitle.config import SubtitleConfig, SubtitleFormatConfig
from ai.subtitle.models import SubtitleRequest, SubtitleSegment, SubtitleWord
from ai.subtitle.service import SubtitleService
from ai.subtitle.windowing import build_rolling_groups
from ai.translation.timing import align_translation_words


def _make_service(max_characters_per_line=42, max_lines_per_subtitle=2):
    config = SubtitleConfig(
        default_format="srt",
        formats={
            "srt": SubtitleFormatConfig(
                enabled=True,
                implementation="ai.subtitle.formats.srt:SRTFormatter",
            )
        },
        max_characters_per_line=max_characters_per_line,
        max_lines_per_subtitle=max_lines_per_subtitle,
    )
    return SubtitleService(adapter=SubtitleAdapter(), config=config)


def _srt_intervals(srt_text: str) -> list[tuple[float, float]]:
    pattern = re.compile(
        r"(\d\d):(\d\d):(\d\d),(\d\d\d) --> (\d\d):(\d\d):(\d\d),(\d\d\d)"
    )

    def to_seconds(h, m, s, ms):
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    intervals = []
    for match in pattern.finditer(srt_text):
        h1, m1, s1, ms1, h2, m2, s2, ms2 = match.groups()
        intervals.append(
            (to_seconds(h1, m1, s1, ms1), to_seconds(h2, m2, s2, ms2))
        )
    return intervals


# ---------------------------------------------------------------------------
# Test 2: Long sentence -> multiple readable rolling groups
# ---------------------------------------------------------------------------

def test_long_sentence_produces_multiple_rolling_groups(tmp_path):
    words = [
        SubtitleWord(word=w, start=i * 0.4, end=(i + 1) * 0.4)
        for i, w in enumerate(
            "आज आपण या विषयाबद्दल सविस्तर माहिती जाणून घेणार आहोत".split()
        )
    ]
    segment = SubtitleSegment(start=0.0, end=len(words) * 0.4, text=" ".join(w.word for w in words), words=words)

    service = _make_service(max_characters_per_line=20, max_lines_per_subtitle=1)
    output_path = tmp_path / "subtitle.srt"

    result = service.generate(
        SubtitleRequest(segments=[segment], output_path=output_path)
    )

    assert result.segment_count > 1
    content = output_path.read_text(encoding="utf-8")
    intervals = _srt_intervals(content)
    assert len(intervals) == result.segment_count
    # Full coverage of the source window.
    assert intervals[0][0] == 0.0
    assert intervals[-1][1] == segment.end


# ---------------------------------------------------------------------------
# Test 3: Translated sentence with different word count from source
# ---------------------------------------------------------------------------

def test_translation_alignment_handles_word_count_mismatch():
    source_words = [
        {"word": "the", "start": 0.0, "end": 0.2},
        {"word": "quick", "start": 0.2, "end": 0.5},
        {"word": "brown", "start": 0.5, "end": 0.9},
        {"word": "fox", "start": 0.9, "end": 1.2},
    ]

    # Translated text merges/reorders into fewer, longer words.
    translated_words = align_translation_words(
        translated_text="वेगवान तपकिरी कोल्हा",
        unit_start=0.0,
        unit_end=1.2,
        source_words=source_words,
    )

    assert len(translated_words) == 3
    assert translated_words[0].start == 0.0
    assert translated_words[-1].end == 1.2

    for word in translated_words:
        assert 0.0 <= word.start <= 1.2
        assert 0.0 <= word.end <= 1.2
        assert word.end >= word.start

    for previous, current in zip(translated_words, translated_words[1:]):
        assert current.start >= previous.end


def test_translation_alignment_falls_back_without_source_words():
    translated_words = align_translation_words(
        translated_text="hello there friend",
        unit_start=10.0,
        unit_end=13.0,
        source_words=None,
    )

    assert len(translated_words) == 3
    assert translated_words[0].start == 10.0
    assert translated_words[-1].end == 13.0


def test_translation_alignment_handles_degenerate_window():
    translated_words = align_translation_words(
        translated_text="hello world",
        unit_start=5.0,
        unit_end=5.0,
    )

    assert all(word.start == 5.0 and word.end == 5.0 for word in translated_words)


def test_translation_alignment_handles_empty_text():
    assert align_translation_words("", 0.0, 1.0, source_words=[]) == []


# ---------------------------------------------------------------------------
# Test 4: Missing word timestamps -> segment-level fallback
# ---------------------------------------------------------------------------

def test_subtitle_generation_falls_back_without_word_timing(tmp_path):
    segment = SubtitleSegment(start=30.0, end=35.0, text="आज आपण या विषयाबद्दल सविस्तर माहिती जाणून घेणार आहोत.")

    service = _make_service()
    output_path = tmp_path / "subtitle.srt"

    result = service.generate(
        SubtitleRequest(segments=[segment], output_path=output_path)
    )

    assert result.segment_count == 1
    content = output_path.read_text(encoding="utf-8")
    intervals = _srt_intervals(content)
    assert intervals == [(30.0, 35.0)]


# ---------------------------------------------------------------------------
# Test 5: Two-line subtitle limit
# ---------------------------------------------------------------------------

def test_rolling_groups_respect_two_line_limit():
    words = [
        SubtitleWord(word=w, start=i * 0.3, end=(i + 1) * 0.3)
        for i, w in enumerate(("word" * 8 + " " + "another" * 8 + " short text here more words").split())
    ]
    segment = SubtitleSegment(start=0.0, end=len(words) * 0.3, text=" ".join(w.word for w in words), words=words)

    config = SubtitleConfig(
        default_format="srt",
        formats={"srt": SubtitleFormatConfig(enabled=True, implementation="ai.subtitle.formats.srt:SRTFormatter")},
        max_characters_per_line=15,
        max_lines_per_subtitle=2,
    )

    groups = build_rolling_groups(segment, config)

    for group in groups:
        assert group.text.count("\n") <= 1  # at most 2 lines


# ---------------------------------------------------------------------------
# Test 6: Long words / punctuation
# ---------------------------------------------------------------------------

def test_rolling_groups_handle_long_words_and_punctuation():
    words = [
        SubtitleWord(word="Supercalifragilisticexpialidocious,", start=0.0, end=1.0),
        SubtitleWord(word="wow!", start=1.0, end=1.5),
        SubtitleWord(word="really?", start=1.5, end=2.0),
    ]
    segment = SubtitleSegment(start=0.0, end=2.0, text="Supercalifragilisticexpialidocious, wow! really?", words=words)

    config = SubtitleConfig(
        default_format="srt",
        formats={"srt": SubtitleFormatConfig(enabled=True, implementation="ai.subtitle.formats.srt:SRTFormatter")},
        max_characters_per_line=10,
        max_lines_per_subtitle=2,
    )

    groups = build_rolling_groups(segment, config)

    assert groups  # no crash, produced output
    assert groups[0].start == 0.0
    assert groups[-1].end == 2.0


# ---------------------------------------------------------------------------
# Test 7: Multiple ASR segments
# ---------------------------------------------------------------------------

def test_multiple_segments_generate_independent_rolling_groups(tmp_path):
    words_a = [
        SubtitleWord(word=w, start=i * 0.5, end=(i + 1) * 0.5)
        for i, w in enumerate("hello there friend how are you".split())
    ]
    segment_a = SubtitleSegment(start=0.0, end=3.0, text=" ".join(w.word for w in words_a), words=words_a)

    words_b = [
        SubtitleWord(word=w, start=5.0 + i * 0.5, end=5.0 + (i + 1) * 0.5)
        for i, w in enumerate("this is segment two now".split())
    ]
    segment_b = SubtitleSegment(start=5.0, end=7.0, text=" ".join(w.word for w in words_b), words=words_b)

    service = _make_service(max_characters_per_line=15, max_lines_per_subtitle=1)
    output_path = tmp_path / "subtitle.srt"

    result = service.generate(
        SubtitleRequest(segments=[segment_a, segment_b], output_path=output_path)
    )

    assert result.segment_count > 2
    intervals = _srt_intervals(output_path.read_text(encoding="utf-8"))
    # Groups belonging to segment_a stay within [0, 3], segment_b within [5, 7].
    assert all(end <= 3.0 for start, end in intervals if start < 5.0)
    assert all(start >= 5.0 for start, end in intervals if start >= 5.0)


# ---------------------------------------------------------------------------
# Test 8: Subtitle timestamps never exceed source segment boundaries
# ---------------------------------------------------------------------------

def test_rolling_groups_never_exceed_segment_boundaries():
    words = [
        SubtitleWord(word=w, start=-1.0 + i * 0.3, end=-1.0 + (i + 1) * 0.3)
        for i, w in enumerate("one two three four five six seven".split())
    ]
    # Deliberately out-of-range word timestamps (before segment start).
    segment = SubtitleSegment(start=0.0, end=2.0, text=" ".join(w.word for w in words), words=words)

    config = SubtitleConfig(
        default_format="srt",
        formats={"srt": SubtitleFormatConfig(enabled=True, implementation="ai.subtitle.formats.srt:SRTFormatter")},
        max_characters_per_line=42,
        max_lines_per_subtitle=2,
    )

    groups = build_rolling_groups(segment, config)

    for group in groups:
        assert group.start >= segment.start - 1e-9
        assert group.end <= segment.end + 1e-9


# ---------------------------------------------------------------------------
# Test 9: No overlapping subtitle intervals
# ---------------------------------------------------------------------------

def test_rolling_groups_never_overlap():
    words = [
        SubtitleWord(word=w, start=i * 0.25, end=(i + 1) * 0.25)
        for i, w in enumerate("a b c d e f g h i j k l".split())
    ]
    segment = SubtitleSegment(start=0.0, end=3.0, text=" ".join(w.word for w in words), words=words)

    config = SubtitleConfig(
        default_format="srt",
        formats={"srt": SubtitleFormatConfig(enabled=True, implementation="ai.subtitle.formats.srt:SRTFormatter")},
        max_characters_per_line=5,
        max_lines_per_subtitle=1,
    )

    groups = build_rolling_groups(segment, config)

    for previous, current in zip(groups, groups[1:]):
        assert current.start >= previous.end


# ---------------------------------------------------------------------------
# Test 10: Full simulated ASR -> translation -> subtitle chain still works
# ---------------------------------------------------------------------------

def test_full_asr_translation_subtitle_chain_still_works(tmp_path):
    source_words = [
        {"word": "आज", "start": 30.0, "end": 30.4},
        {"word": "आपण", "start": 30.4, "end": 30.8},
        {"word": "या", "start": 30.8, "end": 31.1},
        {"word": "विषयाबद्दल", "start": 31.1, "end": 32.1},
        {"word": "सविस्तर", "start": 32.1, "end": 32.8},
        {"word": "माहिती", "start": 32.8, "end": 33.5},
        {"word": "जाणून", "start": 33.5, "end": 34.2},
        {"word": "घेणार", "start": 34.2, "end": 34.7},
        {"word": "आहोत", "start": 34.7, "end": 35.0},
    ]

    translated_text = "आज आपण या विषयाबद्दल सविस्तर माहिती जाणून घेणार आहोत"

    translated_words = align_translation_words(
        translated_text=translated_text,
        unit_start=30.0,
        unit_end=35.0,
        source_words=source_words,
    )

    subtitle_words = [
        SubtitleWord(word=w.word, start=w.start, end=w.end) for w in translated_words
    ]

    segment = SubtitleSegment(start=30.0, end=35.0, text=translated_text, words=subtitle_words)

    service = _make_service(max_characters_per_line=20, max_lines_per_subtitle=2)
    output_path = tmp_path / "subtitle.srt"

    result = service.generate(
        SubtitleRequest(segments=[segment], output_path=output_path)
    )

    assert output_path.exists()
    assert result.segment_count >= 1

    intervals = _srt_intervals(output_path.read_text(encoding="utf-8"))
    assert intervals[0][0] == 30.0
    assert intervals[-1][1] == 35.0
    for previous, current in zip(intervals, intervals[1:]):
        assert current[0] >= previous[1]
