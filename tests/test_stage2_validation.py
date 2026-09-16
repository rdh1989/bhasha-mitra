import unittest

from app.models.asr import Segment
from app.translation_validation import validate_context_results
from app.terminology import validate_terminology


class Stage2ValidationTests(unittest.TestCase):
    def context(self, text="source"):
        class Context:
            event_ids = (0,)
            source_text = text
        return Context()

    def test_numeric_integrity_warning(self):
        result = {"context_id": 0, "event_ids": [0], "source_start": 0, "source_end": 1, "source_text": "10 meter", "translated_text": "20 meter"}
        diagnostics = validate_context_results([self.context("10 meter")], [result])
        self.assertIn("numeric_integrity:0", diagnostics["warnings"])

    def test_formula_operator_warning(self):
        result = {"context_id": 0, "event_ids": [0], "source_start": 0, "source_end": 1, "source_text": "10 गुणिले 2", "translated_text": "दस"}
        diagnostics = validate_context_results([self.context("10 गुणिले 2")], [result])
        self.assertIn("formula_operator_integrity:0", diagnostics["warnings"])

    def test_unicode_warning(self):
        result = {"context_id": 0, "event_ids": [0], "source_start": 0, "source_end": 1, "source_text": "source", "translated_text": "U093C"}
        self.assertIn("malformed_unicode:0", validate_context_results([self.context()], [result])["warnings"])

    def test_unicode_escape_and_mixed_script_warnings(self):
        for text in ("u093Cs", "ü093C", "शेळी®", "बकरीabc"):
            result = {"context_id": 0, "event_ids": [0], "source_start": 0, "source_end": 1, "source_text": "source", "translated_text": text}
            diagnostics = validate_context_results([self.context()], [result])
            self.assertIn("malformed_unicode:0", diagnostics["warnings"])

    def test_approved_terminology_protection_and_contradiction(self):
        from app.terminology import protect_terms, restore_terms

        protected, matches, replacements = protect_terms("शेळीपालन आणि शेळी", enabled=True)
        self.assertNotIn("शेळी", protected)
        self.assertEqual(len(matches), 2)
        self.assertEqual(restore_terms(protected, replacements), "बकरी पालन आणि बकरी")
        _, _, warnings = validate_terminology("शेळी", "भेड़", enabled=True)
        self.assertTrue(any("domain_category_contradiction" in warning for warning in warnings))

    def test_terminology_disabled_is_identity(self):
        text, matches, warnings = validate_terminology("शेळी", "बकरी", enabled=False)
        self.assertEqual(text, "बकरी")
        self.assertEqual(matches, [])
        self.assertEqual(warnings, [])

    def test_empty_output_is_invalid(self):
        result = {"context_id": 0, "event_ids": [0], "source_start": 0, "source_end": 1, "source_text": "source", "translated_text": ""}
        self.assertFalse(validate_context_results([self.context()], [result])["valid"])


if __name__ == "__main__":
    unittest.main()
