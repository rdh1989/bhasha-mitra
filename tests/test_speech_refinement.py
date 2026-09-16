import unittest

import numpy as np

from app.models.asr import Segment
from app.speech import refine_segments_by_audio, validate_asr_segments


class SpeechRefinementTests(unittest.TestCase):
    sample_rate = 1000

    def audio(self, pauses, duration=12.0):
        signal = np.ones(int(duration * self.sample_rate), dtype=np.float32)
        for start, end in pauses:
            signal[int(start * self.sample_rate):int(end * self.sample_rate)] = 0.0
        return signal

    def refine(self, text, pauses, duration=12.0, **kwargs):
        return refine_segments_by_audio(
            self.audio(pauses, duration),
            self.sample_rate,
            [Segment(0.0, duration, text)],
            min_pause_seconds=kwargs.pop("min_pause_seconds", 0.5),
            min_event_duration_seconds=kwargs.pop("min_event_duration_seconds", 0.8),
            min_fragment_words=kwargs.pop("min_fragment_words", 2),
            **kwargs,
        )

    def test_one_internal_pause(self):
        refined, stats = self.refine("one two three four five six", [(4.0, 5.5)])
        self.assertEqual(len(refined), 2)
        self.assertEqual(stats["boundaries_created"], 1)

    def test_multiple_internal_pauses(self):
        refined, stats = self.refine(
            "one two three four five six seven eight nine", [(2.0, 3.0), (7.0, 8.2)]
        )
        self.assertEqual(len(refined), 3)
        self.assertEqual(stats["boundaries_created"], 2)

    def test_long_pause_is_preserved(self):
        refined, _ = self.refine("one two three four five six", [(4.0, 7.0)], duration=10.0)
        self.assertEqual(len(refined), 2)
        self.assertAlmostEqual(refined[1].start - refined[0].end, 3.0, places=2)

    def test_pause_without_punctuation(self):
        refined, _ = self.refine("one two three four five six", [(4.0, 5.5)])
        self.assertEqual(" ".join(item.text for item in refined), "one two three four five six")

    def test_pause_near_punctuation_boundary(self):
        refined, _ = self.refine("one two, three four five six", [(4.0, 5.5)])
        self.assertEqual(len(refined), 2)
        self.assertTrue(refined[0].text.endswith(","))

    def test_pause_too_close_to_word_boundary_is_rejected(self):
        refined, stats = self.refine(
            "one two three four five six", [(0.2, 0.8)], min_fragment_words=2
        )
        self.assertEqual(len(refined), 1)
        self.assertEqual(stats["unsafe_pauses"], 1)

    def test_short_silence_does_not_split(self):
        refined, stats = self.refine("one two three four five six", [(4.0, 4.3)])
        self.assertEqual(len(refined), 1)
        self.assertEqual(stats["internal_pauses_detected"], 0)

    def test_no_pause_and_continuous_speech(self):
        refined, stats = self.refine("one two three four five six", [])
        self.assertEqual(len(refined), 1)
        self.assertEqual(stats["internal_pauses_detected"], 0)

    def test_no_words_or_invalid_event_is_reported(self):
        result = validate_asr_segments([Segment(4.0, 3.0, "")])
        self.assertEqual(result["empty_or_invalid_events"], 1)

    def test_order_absolute_timestamps_and_content(self):
        text = "one two three four five six seven eight"
        refined, _ = self.refine(text, [(3.0, 4.5)])
        self.assertEqual(" ".join(item.text for item in refined), text)
        self.assertTrue(all(a.end <= b.start for a, b in zip(refined, refined[1:])))
        self.assertEqual(refined[0].start, 0.0)
        self.assertEqual(refined[-1].end, 12.0)

    def test_overlapping_timestamp_quality_warning(self):
        result = validate_asr_segments([Segment(0, 2, "one"), Segment(1, 3, "two")])
        self.assertEqual(result["timestamp_violations"], 1)

    def test_english_and_indic_paths_are_language_neutral(self):
        english, _ = self.refine("one two three four five six", [(4.0, 5.5)])
        indic, _ = self.refine("एक दोन तीन चार पाच सहा", [(4.0, 5.5)])
        self.assertEqual(len(english), 2)
        self.assertEqual(len(indic), 2)


if __name__ == "__main__":
    unittest.main()
