#!/usr/bin/env python3
"""Validation vectors for the pure-stdlib cl100k encoder (scripts/cl100k.py).

Canonical vectors are the well-known cl100k_base counts; the round-trip
check proves the BPE is a proper partition of every measured text.
Run: python3 -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from cl100k import count, decode, encode  # noqa: E402


class TestCl100k(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(count(""), 0)

    def test_hello_world(self):
        self.assertEqual(count("hello world"), 2)

    def test_hello_world_punct(self):
        self.assertEqual(count("Hello, world!"), 4)

    def test_pangram(self):
        self.assertEqual(count("The quick brown fox jumps over the lazy dog"), 9)

    def test_digits_chunked_1_to_3(self):
        self.assertEqual(count("12345"), 2)  # "123" + "45"

    def test_round_trip_measured_texts(self):
        texts = [
            "What is known about the memory quality gate for this workbench?",
            "What is the memory gate spec? What checks must the gate enforce?",
            "What did the coder build and what were the test results?",
            "2026-11-25 researcher spec: memory gate v1.0 enforces 3 checks — "
            "(1) DATE: ISO YYYY-MM-DD or Month D, YYYY; "
            "(2) NUMBER: digits outside the date, e.g. $10, 30%, 1000 tokens; "
            "(3) NAMED FACT: backticked/quoted token, hyphenated slug, "
            "'Label: value', or capitalised proper noun. "
            "Implementation: `scripts/memory_gate.py` (stdlib only, importable + CLI), "
            "tests in `tests/test_memory_gate.py`, gate version 1.0. "
            "Summaries expire 30 days after their date.",
            "2026-11-25 coder result: wrote `scripts/memory_gate.py` (gate v1.0, 3 checks) "
            "and `tests/test_memory_gate.py` (11 cases). Test run: 11 passed, 0 failed, "
            "0 errors. Gate self-check: 4 failure modes probed, 4 correct. "
            "Files: 2 created, 0 modified.",
            "2026-11-25 reviewer verdict: PASS. Re-ran `tests/test_memory_gate.py` "
            "independently: 11 passed, 0 failed. Adversarial probes: 4/4 correct "
            "(no-date rejected, no-number rejected, no-named-fact rejected, good summary "
            "accepted). Gate matches the researcher spec of 2026-11-25 (3 checks). "
            "No blocking issues.",
        ]
        for t in texts:
            with self.subTest(text=t[:40]):
                self.assertEqual(decode(encode(t)), t)
                self.assertGreater(count(t), 0)


if __name__ == "__main__":
    unittest.main()
