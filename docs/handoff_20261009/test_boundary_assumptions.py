"""Synthetic boundary counterexamples; no private data or B code."""
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location("boundary_audit",Path(__file__).with_name("audit_boundary_assumptions.py"))
a=importlib.util.module_from_spec(spec); spec.loader.exec_module(a)

class BoundaryTests(unittest.TestCase):
    def test_single_month(self):
        self.assertEqual(a.last_segment([10]),(10,10))
    def test_consecutive_months(self):
        self.assertEqual(a.last_segment([10,11]),(10,11))
    def test_gap_selects_latest_segment(self):
        self.assertEqual(a.last_segment([1,2,6,7]),(6,7))
    def test_unsorted_months(self):
        self.assertEqual(a.last_segment([7,1,6]),(6,7))
    def test_no_event_blocks(self):
        with self.assertRaises(ValueError): a.last_segment([])
    def test_calendar_year_rollover(self):
        self.assertEqual(a.month_number("2025-12-1")+1,a.month_number("2026-1-1"))
    def test_invalid_month_blocks(self):
        with self.assertRaises(ValueError): a.month_number("2025-13-1")
    def test_duplicate_normalized_month_blocks(self):
        with self.assertRaises(ValueError): a.unique_month_map([{"NY":"2025-1-1"},{"NY":"2025-01-15"}],"NY")
    def test_observational_equivalence(self):
        for months in ([1],[1,2],[1,2,6,7],[3,4,5]):
            with self.subTest(months=months):
                self.assertEqual(a.target_months(months,"latest_segment_end"),a.target_months(months,"latest_independent_record"))
    def test_start_rule_distinguishable_for_multiple_months(self):
        self.assertNotEqual(a.target_months([3,4],"latest_segment_start"),a.target_months([3,4],"latest_segment_end"))
    def test_single_month_does_not_distinguish_start_end(self):
        self.assertEqual(a.target_months([3],"latest_segment_start"),a.target_months([3],"latest_segment_end"))
    def test_exactly_twelve_consecutive_target_months(self):
        self.assertEqual(a.target_months([3,4],"latest_segment_end"),tuple(range(5,17)))
    def test_unknown_interpretation_blocks(self):
        with self.assertRaises(ValueError): a.target_months([3,4],"score_selected_rule")
    def test_start_cutoff_excludes_operation_months(self):
        rows=[(2,10),(3,20),(4,30),(5,40)]
        self.assertEqual(a.before_month(rows,3),((2,10),))
        self.assertEqual(a.before_month(rows,4),((2,10),(3,20)))
    def test_future_mutation_preserves_selected_history(self):
        self.assertEqual(a.before_month([(2,10),(3,20),(4,30)],3),a.before_month([(2,10),(3,99999),(4,-99999)],3))
    def test_zero_valid_missing_nonfinite_invalid(self):
        self.assertTrue(a.finite_nonnegative("0"))
        for value in ("","nan","inf","-1",None):
            with self.subTest(value=value): self.assertFalse(a.finite_nonnegative(value))
if __name__=="__main__":
    unittest.main(verbosity=2)
