import unittest

from app.models.asr import Segment
from app.translation_planner import plan_translation_contexts


class TranslationPlannerTests(unittest.TestCase):
    def test_complete_event_stays_standalone(self):
        contexts, _ = plan_translation_contexts([Segment(0, 1, "Complete sentence.", source_segment_id=1)])
        self.assertEqual(contexts[0].event_ids, (0,))

    def test_weak_event_can_merge_across_provenance(self):
        contexts, _ = plan_translation_contexts([
            Segment(0, 1, "complete preceding thought,", source_segment_id=1),
            Segment(2, 2.5, "short fragment", source_segment_id=2),
            Segment(3, 4, "continuing context words", source_segment_id=3),
        ])
        self.assertEqual(contexts[0].event_ids, (0, 1))

    def test_sentence_boundary_stops_expansion(self):
        contexts, _ = plan_translation_contexts([
            Segment(0, 1, "Complete sentence.", source_segment_id=1),
            Segment(2, 3, "Next thought", source_segment_id=2),
        ])
        self.assertEqual(len(contexts), 2)

    def test_pause_does_not_automatically_end_context(self):
        contexts, _ = plan_translation_contexts([
            Segment(0, 1, "first complete phrase.", source_segment_id=1, pause_after=2.0),
            Segment(3, 4, "short fragment", source_segment_id=2, pause_before=2.0),
            Segment(5, 6, "continuation words follow", source_segment_id=3, pause_before=2.0),
        ])
        self.assertEqual(len(contexts), 3)

    def test_event_and_duration_limits_are_bounded(self):
        events = [Segment(i, i + 20, f"word {i}", source_segment_id=1) for i in range(4)]
        contexts, diagnostics = plan_translation_contexts(events, max_events=3, max_duration=30)
        self.assertTrue(all(len(context.event_ids) <= 3 for context in contexts))
        self.assertEqual(diagnostics["source_events"], 4)

    def test_every_event_is_traceable_once(self):
        events = [Segment(i, i + 1, f"word {i}", source_segment_id=i) for i in range(5)]
        contexts, _ = plan_translation_contexts(events)
        ids = [event_id for context in contexts for event_id in context.event_ids]
        self.assertEqual(ids, list(range(5)))

    def test_numeric_phrase_continuation_merges_minimum_events(self):
        contexts, _ = plan_translation_contexts([
            Segment(0, 1, "first 8"),
            Segment(2, 3, "items completed"),
            Segment(4, 5, "A complete independent sentence."),
        ])
        self.assertEqual(contexts[0].event_ids, (0, 1))
        self.assertEqual(contexts[1].event_ids, (2,))

    def test_case_phrase_continuation_merges(self):
        contexts, _ = plan_translation_contexts([
            Segment(0, 1, "the first measured value of,"),
            Segment(2, 3, "the ratio is equal"),
        ])
        self.assertEqual(contexts[0].event_ids, (0, 1))

    def test_auxiliary_continuation_merges(self):
        contexts, _ = plan_translation_contexts([
            Segment(0, 1, "completion is required,"),
            Segment(2, 3, "now"),
        ])
        self.assertEqual(contexts[0].event_ids, (0, 1))

    def test_ambiguous_fragment_stays_standalone(self):
        contexts, _ = plan_translation_contexts([
            Segment(0, 1, "surrounding text"),
            Segment(2, 3, "unknown"),
            Segment(4, 5, "following text"),
        ])
        ambiguous = next(context for context in contexts if context.source_text == "unknown")
        self.assertEqual(ambiguous.event_ids, (1,))
        self.assertEqual(ambiguous.context_status, "AMBIGUOUS_CONTEXT")

    def test_dangling_function_word_merges_next(self):
        contexts, _ = plan_translation_contexts([
            Segment(0, 1, "The end result was always the"),
            Segment(1, 2, "same."),
        ])
        self.assertEqual(contexts[0].event_ids, (0, 1))
        self.assertIn("DANGLING_FUNCTION_WORD", contexts[0].decision_reasons)

    def test_home_phrase_merges_with_to_continuation(self):
        contexts, _ = plan_translation_contexts([
            Segment(0, 1, "This region is home"),
            Segment(1, 2, "to millions of pastoralists."),
        ])
        self.assertEqual(contexts[0].event_ids, (0, 1))

    def test_three_part_sentence_preserves_words_and_timestamps(self):
        events = [
            Segment(10, 12, "Unhealthy herds can cause disease"),
            Segment(12, 14.5, "outbreaks that endanger livestock and"),
            Segment(14.5, 16, "humans."),
        ]
        contexts, _ = plan_translation_contexts(events)
        self.assertEqual(contexts[0].event_ids, (0, 1, 2))
        self.assertEqual((contexts[0].source_start, contexts[0].source_end), (10.0, 16.0))
        self.assertEqual(contexts[0].source_text, " ".join(event.text for event in events))

    def test_short_complete_sentence_does_not_merge(self):
        contexts, _ = plan_translation_contexts([
            Segment(0, 1, "Stop."),
            Segment(1, 2, "Continue."),
        ])
        self.assertEqual([context.event_ids for context in contexts], [(0,), (1,)])

    def test_continuation_start_can_merge_previous_context(self):
        contexts, _ = plan_translation_contexts([
            Segment(0, 1, "The project supports rural communities."),
            Segment(1, 2, "and strengthens local schools."),
        ])
        self.assertEqual(contexts[0].event_ids, (0, 1))
        self.assertEqual(contexts[0].decision, "MERGE_PREVIOUS")


if __name__ == "__main__":
    unittest.main()
