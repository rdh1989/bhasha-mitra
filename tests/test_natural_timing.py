import unittest

from app.pipeline import _plan_tts_timing


class NaturalTimingPlannerTests(unittest.TestCase):
    def test_natural_duration_fits_without_adjustment(self):
        units = [(0.0, 2.0, "complete sentence.", 0.0)]
        plan = _plan_tts_timing(units, [1.9], 1000)
        self.assertEqual(plan[0]["naturalness_status"], "NATURAL")
        self.assertEqual(plan[0]["allocated_start"], 0.0)
        self.assertEqual(plan[0]["allocated_end"], 2.0)

    def test_soft_boundary_reallocates_measured_duration(self):
        units = [
            (0.0, 1.0, "the first clause,", 0.0),
            (1.05, 2.0, "and the continuation.", 0.0),
        ]
        plan = _plan_tts_timing(units, [1.4, 0.8], 1000)
        self.assertEqual(plan[0]["boundary_type"], "HARD")
        self.assertEqual(plan[0]["naturalness_status"], "REALLOCATED")
        self.assertGreaterEqual(plan[0]["allocated_end"], 1.4)
        self.assertGreaterEqual(plan[1]["allocated_start"], plan[0]["allocated_end"])

    def test_hard_boundary_is_not_crossed(self):
        units = [
            (0.0, 1.0, "complete sentence.", 0.0),
            (1.1, 2.0, "Independent sentence.", 0.0),
        ]
        plan = _plan_tts_timing(units, [1.8, 0.8], 1000)
        self.assertEqual(plan[0]["naturalness_status"], "DURATION_CONFLICT")
        self.assertEqual(plan[0]["allocated_end"], 1.0)

    def test_original_timestamps_are_preserved(self):
        units = [(2.5, 3.5, "a continuation,", 0.0), (3.55, 4.5, "and more.", 0.0)]
        plan = _plan_tts_timing(units, [1.3, 0.8], 1000)
        self.assertEqual((units[0][0], units[0][1]), (2.5, 3.5))
        self.assertEqual((units[1][0], units[1][1]), (3.55, 4.5))
        self.assertIn("allocated_start", plan[0])
        self.assertIn("allocated_end", plan[0])

    def test_unrelated_neighbor_is_not_merged(self):
        units = [
            (0.0, 1.0, "A complete thought.", 0.0),
            (1.05, 2.0, "A separate thought.", 0.0),
        ]
        plan = _plan_tts_timing(units, [1.4, 0.8], 1000)
        self.assertEqual(plan[0]["boundary_type"], "HARD")
        self.assertEqual(plan[0]["allocated_end"], 1.0)

    def test_short_window_does_not_raise_compression_limit(self):
        units = [(0.0, 0.8, "very long translated speech", 0.0)]
        plan = _plan_tts_timing(units, [2.5], 1000)
        self.assertEqual(plan[0]["naturalness_status"], "DURATION_CONFLICT")
        self.assertEqual(plan[0]["allocated_end"], 0.8)


if __name__ == "__main__":
    unittest.main()