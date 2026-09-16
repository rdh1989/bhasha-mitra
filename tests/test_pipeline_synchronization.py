import unittest

import numpy as np

from app.pipeline import (
    _normalize_timed_units,
    _split_tts_text,
    _subdivide_tts_segment,
    _synthesize_at_natural_rate,
)


class FakeTTS:
    def __init__(self, duration_seconds):
        self.duration_seconds = duration_seconds
        self.calls = []

    def sampling_rate_for(self, _language):
        return 1000

    def synthesize(self, text, _language, voice_index=0, length_scale=None):
        self.calls.append((text, voice_index, length_scale))
        return np.ones(int(self.duration_seconds * 1000), dtype=np.float32)


def waveform_with_pauses(pauses, duration=8.0, sample_rate=1000):
    audio = np.ones(int(duration * sample_rate), dtype=np.float32)
    for start, end in pauses:
        audio[int(start * sample_rate):int(end * sample_rate)] = 0.0
    return audio


class PipelineSynchronizationTests(unittest.TestCase):
    def setUp(self):
        self.two_clauses = (
            "This is a sufficiently long first clause, "
            "this is a sufficiently long second clause."
        )
        self.three_clauses = (
            "This is a sufficiently long first clause, "
            "this is a sufficiently long second clause; "
            "this is a sufficiently long final clause."
        )

    def test_event_without_internal_pause_remains_one_unit(self):
        units = _subdivide_tts_segment(
            0.0, 4.0, self.two_clauses, waveform_with_pauses([] , duration=4.0), 1000
        )
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0][2], self.two_clauses)

    def test_one_internal_pause_creates_two_absolute_units(self):
        units = _subdivide_tts_segment(
            0.0,
            4.0,
            self.two_clauses,
            waveform_with_pauses([(1.4, 2.4)], duration=4.0),
            1000,
        )
        self.assertEqual(len(units), 2)
        self.assertLessEqual(units[0][1], units[1][0])
        self.assertGreater(units[0][3], 0.8)
        self.assertEqual(" ".join(unit[2] for unit in units), self.two_clauses)

    def test_multiple_internal_pauses_create_multiple_units(self):
        units = _subdivide_tts_segment(
            0.0,
            8.0,
            self.three_clauses,
            waveform_with_pauses([(1.8, 2.6), (4.6, 5.5)], duration=8.0),
            1000,
        )
        self.assertEqual(len(units), 3)
        self.assertEqual(" ".join(unit[2] for unit in units), self.three_clauses)
        self.assertTrue(all(a[1] <= b[0] for a, b in zip(units, units[1:])))

    def test_short_pause_is_not_promoted_to_linguistic_boundary(self):
        units = _subdivide_tts_segment(
            0.0,
            4.0,
            self.two_clauses,
            waveform_with_pauses([(1.8, 2.0)], duration=4.0),
            1000,
        )
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0][2], self.two_clauses)

    def test_safe_split_preserves_target_content_and_order(self):
        parts = _split_tts_text(self.three_clauses)
        self.assertEqual(" ".join(parts), self.three_clauses)
        self.assertEqual(parts[0][-1], ",")
        self.assertEqual(parts[1][-1], ";")
        self.assertEqual(parts[2][-1], ".")

    def test_natural_shorter_target_is_not_stretched(self):
        tts = FakeTTS(duration_seconds=1.0)
        audio, length_scale = _synthesize_at_natural_rate(
            tts, "complete target text", object(), 2.0, True
        )
        self.assertEqual(len(audio), 1000)
        self.assertIsNone(length_scale)
        self.assertEqual(len(tts.calls), 1)

    def test_moderately_long_target_uses_bounded_rate_adjustment(self):
        tts = FakeTTS(duration_seconds=3.0)
        _audio, length_scale = _synthesize_at_natural_rate(
            tts, "complete target text", object(), 2.0, True
        )
        self.assertEqual(length_scale, 0.9)
        self.assertEqual(len(tts.calls), 2)
        self.assertEqual(tts.calls[0][0], tts.calls[1][0])

    def test_short_segment_is_kept_inside_its_source_window(self):
        units = _normalize_timed_units([(2.0, 2.5, "short", 0.0)], 10.0)
        self.assertEqual(units, [(2.0, 2.5, "short", 0.0)])
        self.assertLessEqual(units[0][1], 2.5)

    def test_long_segment_and_gap_keep_absolute_timestamps(self):
        units = _normalize_timed_units(
            [(1.2, 5.8, "first", 0.0), (7.1, 14.65, "second", 0.0)],
            20.0,
        )
        self.assertEqual((units[0][0], units[0][1]), (1.2, 5.8))
        self.assertEqual((units[1][0], units[1][1]), (7.1, 14.65))
        self.assertEqual(units[0][1], 5.8)
        self.assertEqual(units[1][0], 7.1)

    def test_overlapping_segments_are_resolved_without_overwriting(self):
        units = _normalize_timed_units(
            [(1.0, 3.0, "first", 0.0), (2.5, 4.0, "second", 0.0)],
            10.0,
        )
        self.assertEqual(units[0][0:2], (1.0, 3.0))
        self.assertEqual(units[1][0:2], (3.0, 4.0))
        self.assertTrue(all(left[1] <= right[0] for left, right in zip(units, units[1:])))


if __name__ == "__main__":
    unittest.main()
