import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.ai.alignment.phrase_mapper import derive_pause_intervals, map_phrases


class PhraseMapperTests(unittest.TestCase):
    def setUp(self):
        self.alignment = [{
            "segment_id": 4,
            "source_start": 10.0,
            "source_end": 16.0,
            "source_text": "एक दोन तीन चार पाच सहा",
            "words": [
                {"text": "एक", "start": 10.0, "end": 10.5},
                {"text": "दोन", "start": 10.6, "end": 11.1},
                {"text": "तीन", "start": 11.6, "end": 12.1},
                {"text": "चार", "start": 12.2, "end": 12.7},
                {"text": "पाच", "start": 12.8, "end": 13.3},
                {"text": "सहा", "start": 13.4, "end": 13.9},
            ],
        }]
        self.translation = [{"start": 10.0, "end": 16.0, "text": "एक दो तीन चार पांच छह"}]

    def test_meaningful_pause_creates_boundary(self):
        result = map_phrases(
            self.alignment,
            self.translation,
            pauses=[{"start": 11.1, "end": 11.6}],
            min_pause_seconds=0.35,
        )
        self.assertGreaterEqual(result["statistics"]["source_phrases"], 2)

    def test_existing_word_gap_can_supply_pause_evidence(self):
        pauses = derive_pause_intervals(self.alignment)
        self.assertEqual(pauses, [{"start": 11.1, "end": 11.6}])

    def test_punctuation_creates_boundary(self):
        alignment = json.loads(json.dumps(self.alignment))
        alignment[0]["words"][2]["text"] = "तीन।"
        result = map_phrases(alignment, self.translation)
        self.assertEqual(result["statistics"]["punctuation_boundaries"], 1)

    def test_tiny_pause_does_not_create_boundary(self):
        alignment = json.loads(json.dumps(self.alignment))
        alignment[0]["words"][2]["start"] = 11.2
        result = map_phrases(alignment, self.translation, min_pause_seconds=0.35)
        self.assertEqual(result["statistics"]["source_phrases"], 1)

    def test_source_and_target_text_are_preserved(self):
        result = map_phrases(self.alignment, self.translation)
        segment = result["segments"][0]
        self.assertEqual(" ".join(segment["target_text"].split()), " ".join(" ".join(p["target_text"] for p in segment["phrases"]).split()))
        self.assertEqual(result["statistics"]["source_words_lost"], 0)
        self.assertEqual(result["statistics"]["target_words_lost"], 0)

    def test_phrases_are_monotonic_and_missing_translation_is_reported(self):
        missing = map_phrases(self.alignment, [])
        self.assertTrue(missing["segments"][0]["translation_missing"])
        result = map_phrases(self.alignment, self.translation)
        phrases = result["segments"][0]["phrases"]
        self.assertTrue(all(a["end"] <= b["start"] for a, b in zip(phrases, phrases[1:])))

    def test_long_phrase_uses_safety_boundary_without_losing_words(self):
        result = map_phrases(
            self.alignment,
            self.translation,
            max_phrase_words=2,
            max_phrase_seconds=99,
        )
        self.assertGreater(result["statistics"]["safety_boundaries"], 0)
        self.assertEqual(result["statistics"]["source_words_lost"], 0)

    def test_absolute_timestamps_are_preserved(self):
        result = map_phrases(self.alignment, self.translation)
        segment = result["segments"][0]
        self.assertEqual(segment["source_start"], 10.0)
        self.assertEqual(segment["source_end"], 16.0)
        self.assertEqual(segment["phrases"][0]["start"], 10.0)

    def test_artifact_hashes_are_not_changed_by_mapper(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "transcript.json"
            target = Path(directory) / "translation.json"
            source.write_text(json.dumps(self.alignment), encoding="utf-8")
            target.write_text(json.dumps(self.translation), encoding="utf-8")
            before = (hashlib.sha256(source.read_bytes()).hexdigest(), hashlib.sha256(target.read_bytes()).hexdigest())
            map_phrases(self.alignment, self.translation)
            after = (hashlib.sha256(source.read_bytes()).hexdigest(), hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertEqual(before, after)

    def test_real_artifact_hashes_remain_unchanged(self):
        root = Path(__file__).resolve().parents[1] / "outputs" / "401.5"
        transcript = root / "b50deb736f774e8491d28aee7b3a8e70" / "transcript.json"
        translation = root / "b50deb736f774e8491d28aee7b3a8e70" / "translation.json"
        alignment = root / "ctc_alignment_20260905" / "word_alignment.json"
        if not transcript.exists() or not translation.exists() or not alignment.exists():
            self.skipTest("real diagnostic artifacts are not present")
        before = (hashlib.sha256(transcript.read_bytes()).digest(), hashlib.sha256(translation.read_bytes()).digest())
        map_phrases(json.loads(alignment.read_text(encoding="utf-8"))["segments"], json.loads(translation.read_text(encoding="utf-8"))["segments"])
        after = (hashlib.sha256(transcript.read_bytes()).digest(), hashlib.sha256(translation.read_bytes()).digest())
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
