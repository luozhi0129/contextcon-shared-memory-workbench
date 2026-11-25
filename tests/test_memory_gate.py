#!/usr/bin/env python3
"""Unit tests for the memory gate (scripts/memory_gate.py). Stdlib only."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from memory_gate import check, expires_on


class TestGate(unittest.TestCase):
    def test_good_iso_summary_passes(self):
        r = check("On 2026-11-25 the coder ran 10 tests on `memory_gate.py` and all passed.")
        self.assertTrue(r.ok, r)

    def test_month_name_date_passes(self):
        r = check("On November 25, 2026 we shipped 3 features in the `workbench` repo.")
        self.assertTrue(r.ok, r)

    def test_no_date_fails(self):
        r = check("The coder ran 10 tests on the memory_gate module and all passed.")
        self.assertFalse(r.ok)
        self.assertIn("date", r.failures)
        self.assertNotIn("number", r.failures)
        self.assertNotIn("named_fact", r.failures)

    def test_no_number_fails(self):
        r = check("On 2026-11-25 the reviewer checked the memory_gate module and approved it.")
        self.assertFalse(r.ok)
        self.assertIn("number", r.failures)

    def test_no_named_fact_fails(self):
        r = check("On 2026-11-25 we ran 10 checks and 3 failed in the pipeline.")
        self.assertFalse(r.ok)
        self.assertIn("named_fact", r.failures)

    def test_empty_fails_all_three(self):
        r = check("   ")
        self.assertFalse(r.ok)
        self.assertEqual(sorted(r.failures), ["date", "named_fact", "number"])

    def test_money_and_percent_numbers_pass(self):
        r = check("On 2026-11-25 the bounty paid $10 and views rose 30% on `square-post`.")
        self.assertTrue(r.ok, r)

    def test_slug_counts_as_named_fact(self):
        r = check("On 2026-11-25 the team shipped 2 fixes to contextcon-workbench.")
        self.assertTrue(r.ok, r)

    def test_quoted_token_counts_as_named_fact(self):
        r = check('On 2026-11-25 the reviewer approved 1 change to "memory gate v1.0".')
        self.assertTrue(r.ok, r)

    def test_word_count_reported_and_long_warns(self):
        r = check("On 2026-11-25 the `gate` passed 1 check. " + "filler " * 1300)
        self.assertTrue(r.ok, r)
        self.assertIn("warning", r.details)
        self.assertGreater(r.details["words"], 1200)

    def test_expires_on_30_days(self):
        self.assertEqual(expires_on("2026-11-25"), "2026-12-25")
        self.assertEqual(expires_on("2026-11-25", 7), "2026-12-02")


if __name__ == "__main__":
    unittest.main()
