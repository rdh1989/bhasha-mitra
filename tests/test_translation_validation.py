import unittest

from app.translation_validation import validate_context_results


class TranslationValidationTests(unittest.TestCase):
    def test_valid_result(self):
        class Context:
            event_ids = (0,)
        result = {"context_id": 0, "event_ids": [0], "source_start": 0, "source_end": 1, "translated_text": "valid"}
        self.assertTrue(validate_context_results([Context()], [result])["valid"])

    def test_empty_and_unicode_are_warnings(self):
        class Context:
            event_ids = (0,)
        result = {"context_id": 0, "event_ids": [0], "source_start": 0, "source_end": 1, "translated_text": "U093C"}
        diagnostics = validate_context_results([Context()], [result])
        self.assertIn("malformed_unicode:0", diagnostics["warnings"])

    def test_traceability_mismatch_is_invalid(self):
        class Context:
            event_ids = (0,)
        result = {"context_id": 0, "event_ids": [], "source_start": 0, "source_end": 1, "translated_text": "valid"}
        self.assertFalse(validate_context_results([Context()], [result])["valid"])

    def test_incomplete_source_is_reported(self):
        class Context:
            event_ids = (0,)
        result = {
            "context_id": 0, "event_ids": [0], "source_start": 0, "source_end": 1,
            "source_text": "the end result was always the", "translated_text": "result",
        }
        diagnostics = validate_context_results([Context()], [result])
        self.assertIn("linguistic_completeness:0", diagnostics["warnings"])
        self.assertEqual(result["linguistic_completeness"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
