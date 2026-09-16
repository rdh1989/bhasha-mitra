import unittest

from app.entity_protection import protect_entities, restore_entities, validate_entities
from app.quality_guard import TranslationQualityGuard


class QualityGuardTests(unittest.TestCase):
    def test_numeric_entity_round_trip(self):
        protected, entities, replacements = protect_entities("X × Y ÷ 2 at 10%")
        self.assertEqual(entities, ["X × Y", "2", "10%"])
        self.assertEqual(restore_entities(protected, replacements), "X × Y ÷ 2 at 10%")

    def test_entity_integrity_is_generic(self):
        self.assertEqual(validate_entities("value 12%", "मूल्य 13%"), ["entity_integrity"])

    def test_guard_returns_retry_for_numeric_failure(self):
        class Context:
            event_ids = (0,)
            source_text = "value 12"

        result = {"context_id": 0, "event_ids": [0], "source_start": 0, "source_end": 1, "source_text": "value 12", "translated_text": "मूल्य 13"}
        diagnostics = TranslationQualityGuard().validate([Context()], [result])
        self.assertEqual(diagnostics["status"], "RETRY")


if __name__ == "__main__":
    unittest.main()