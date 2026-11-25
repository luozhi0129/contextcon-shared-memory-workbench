#!/usr/bin/env python3
"""Coder agent — step 2 of the relay.

Loop: recall the researcher's spec (zero briefing — this is the proof the
handoff worked) -> implement scripts/memory_gate.py + tests/test_memory_gate.py
-> run the test suite -> gate its own result memory with the freshly written
gate -> trace the exchange.

The gate implementation and its tests are embedded below as templates; the
coder step materialises them as real files, runs them, and records the result.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

from common import (DATAPACK_ID, PROJECT_ROOT, RUN_DATE, connect,
                    memory_texts, new_conversation, recall, remember, trace)

AGENT = "coder"

GATE_SOURCE = '''#!/usr/bin/env python3
"""Memory quality gate for the Shared-Memory Workbench.

Written by the coder step of the ContextCon relay, 2026-11-25.
Every summary written to the shared datapack must carry:
  1. a DATE   - ISO YYYY-MM-DD, or "Month D, YYYY" / "D Month YYYY"
  2. a NUMBER - digits outside the date(s), e.g. $10, 30%, 1,000 tokens
  3. a NAMED FACT - a backticked/quoted token, a hyphenated slug,
     a "Label: value" pair, or a capitalised proper-noun phrase.

check(text) -> GateResult(ok, failures, details)
The checks are heuristics, not a language model: they catch vague prose
("we made good progress recently") and let concrete summaries through.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta

__version__ = "1.0"

MONTHS = ("January|February|March|April|May|June|July|August|September|"
          "October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|"
          "Sept|Oct|Nov|Dec")

DATE_PATTERNS = [
    re.compile(r"\\b\\d{4}-\\d{2}-\\d{2}\\b"),
    re.compile(rf"\\b(?:{MONTHS})\\.?\\s+\\d{{1,2}},?\\s+\\d{{4}}\\b"),
    re.compile(rf"\\b\\d{{1,2}}\\s+(?:{MONTHS})\\.?\\s+\\d{{4}}\\b"),
]
NUMBER_RE = re.compile(r"\\d[\\d,]*(?:\\.\\d+)?")
BACKTICK_RE = re.compile(r"`[^`]{2,}`")
QUOTE_RE = re.compile(r'"[^"]{2,}"')
SLUG_RE = re.compile(r"\\b[a-z0-9]+(?:[-_][a-z0-9]+)+\\b")
LABEL_RE = re.compile(r"\\b[A-Z][A-Za-z]{1,30}:\\s+\\S")
CAPITAL_RE = re.compile(r"\\b[A-Z][a-z]{2,}\\b")
SENTENCE_START = re.compile(r"(^|[.!?]\\s+)([A-Z][a-z]{2,})")
STOP_WORDS = {
    "The", "This", "That", "These", "Those", "With", "From", "Each",
    "Every", "When", "Then", "Also", "And", "But", "For", "Our",
    "Your", "Their", "There", "Here", "What", "Which", "While",
}
WORD_LIMIT = 1200


@dataclass
class GateResult:
    ok: bool
    failures: list
    details: dict = field(default_factory=dict)


def find_named_fact(text):
    """Return one named-fact witness, or None.

    Dates are stripped first: an ISO date like 2026-11-25 would otherwise
    match the slug pattern and count as its own named fact.
    """
    rest = text
    for p in DATE_PATTERNS:
        rest = p.sub(" ", rest)
    for rx in (BACKTICK_RE, QUOTE_RE, SLUG_RE, LABEL_RE):
        m = rx.search(rest)
        if m:
            return m.group(0)
    initials = {m.group(2) for m in SENTENCE_START.finditer(rest)}
    for m in CAPITAL_RE.finditer(rest):
        w = m.group(0)
        if w in initials or w in STOP_WORDS:
            continue
        return w
    return None


def check(text):
    """Check a summary against the three rules."""
    if not text or not text.strip():
        return GateResult(False, ["date", "number", "named_fact"], {"words": 0})
    dates = [m.group(0) for p in DATE_PATTERNS for m in p.finditer(text)]
    details = {"dates": dates}
    failures = []
    if not dates:
        failures.append("date")
    rest = text
    for d in dates:
        rest = rest.replace(d, " ", 1)
    numbers = NUMBER_RE.findall(rest)
    details["numbers"] = numbers
    if not numbers:
        failures.append("number")
    named = find_named_fact(text)
    details["named_fact"] = named
    if not named:
        failures.append("named_fact")
    words = len(text.split())
    details["words"] = words
    if words > WORD_LIMIT:
        details["warning"] = f"over {WORD_LIMIT} words ({words})"
    return GateResult(not failures, failures, details)


def expires_on(date_str, days=30):
    """Expiry date for a memory dated date_str (ISO), default 30 days."""
    return (date.fromisoformat(date_str) + timedelta(days=days)).isoformat()


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Memory quality gate: date + number + named fact.")
    p.add_argument("text", nargs="?", help="summary text to check")
    p.add_argument("--file", help="read the summary from a file")
    args = p.parse_args(argv)
    text = open(args.file, encoding="utf-8").read() if args.file else (args.text or "")
    r = check(text)
    print("PASS" if r.ok else "FAIL", r.failures if not r.ok else "", r.details)
    return 0 if r.ok else 1


if __name__ == "__main__":
    sys.exit(main())
'''

TESTS_SOURCE = '''#!/usr/bin/env python3
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
'''

# Adversarial probes the coder runs on its own work (reviewer repeats them).
PROBES = [
    ("no-date", "The coder ran 10 tests on the memory_gate module and all passed.", False),
    ("no-number", "On 2026-11-25 the reviewer checked the memory_gate module and approved it.", False),
    ("no-named-fact", "On 2026-11-25 we ran 10 checks and 3 failed in the pipeline.", False),
    ("good", "On 2026-11-25 the coder ran 10 tests on `memory_gate.py` and all passed.", True),
]


def load_gate(path):
    spec = importlib.util.spec_from_file_location("relay_memory_gate", path)
    mod = importlib.util.module_from_spec(spec)
    # dataclasses need the module registered in sys.modules before exec.
    sys.modules["relay_memory_gate"] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    m, info = connect()
    print(f"coder: connected to {info.get('name')} {info.get('version')}")
    conv = new_conversation(m, f"coder — memory gate implementation — {RUN_DATE}")
    print(f"coder: conversation {conv}")

    # Zero briefing: the coder only knows what the datapack tells it.
    found = recall(m, conv, AGENT, "What is the memory gate spec? What checks must the gate enforce?")
    texts = memory_texts(found)
    print(f"coder: recall returned {len(texts)} memor(ies)")
    for t in texts:
        print(f"  recalled: {t[:140]}")
    blob = " ".join(texts).lower()
    for needle in ("date", "number", "named fact"):
        if needle not in blob:
            raise RuntimeError(f"handoff broken: recall has no {needle!r}: {texts}")
    print("coder: spec recalled — date + number + named fact all present (zero briefing)")

    gate_path = f"{PROJECT_ROOT}/scripts/memory_gate.py"
    test_path = f"{PROJECT_ROOT}/tests/test_memory_gate.py"
    os.makedirs(f"{PROJECT_ROOT}/tests", exist_ok=True)
    with open(gate_path, "w", encoding="utf-8") as f:
        f.write(GATE_SOURCE)
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(TESTS_SOURCE)
    print(f"coder: wrote {gate_path} and {test_path}")

    gate = load_gate(gate_path)
    probe_results = []
    for name, text, want_ok in PROBES:
        r = gate.check(text)
        ok = (r.ok == want_ok)
        probe_results.append({"probe": name, "want_ok": want_ok, "got_ok": r.ok,
                              "failures": r.failures, "correct": ok})
        print(f"coder: probe {name}: want_ok={want_ok} got_ok={r.ok} failures={r.failures} -> {'OK' if ok else 'WRONG'}")
        if not ok:
            raise RuntimeError(f"probe {name} wrong: {r}")

    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                          cwd=PROJECT_ROOT, capture_output=True, text=True)
    ran = re.search(r"Ran (\d+) tests?", proc.stderr)
    n_tests = int(ran.group(1)) if ran else 0
    passed = "OK" in proc.stderr.splitlines()[-2:] and "FAILED" not in proc.stderr
    print(f"coder: test suite: {n_tests} tests, {'OK' if passed else 'FAILED'}")
    print(proc.stderr.strip().splitlines()[-3:])
    if not passed or n_tests == 0:
        raise RuntimeError(f"test suite failed:\n{proc.stderr[-1500:]}")

    result = (
        f"{RUN_DATE} coder result: wrote `scripts/memory_gate.py` (gate v1.0, 3 checks) "
        f"and `tests/test_memory_gate.py` ({n_tests} cases). "
        f"Test run: {n_tests} passed, 0 failed, 0 errors. "
        f"Gate self-check: {len(PROBES)} failure modes probed, {len(PROBES)} correct. "
        f"Files: 2 created, 0 modified."
    )
    r = gate.check(result)
    assert r.ok, f"own result memory failed the gate: {r}"

    def gate_fn(text):
        res = gate.check(text)
        return res.ok, res.failures, res.details

    mid = remember(m, conv, AGENT, result, gate=gate_fn)
    print(f"coder: result memory written (gated), id={mid}")

    trace(m, conv,
          "What did you build from the recalled spec?",
          f"Implemented scripts/memory_gate.py + tests/test_memory_gate.py: "
          f"{n_tests}/{n_tests} tests pass, {len(PROBES)}/{len(PROBES)} probes correct. "
          f"Result memory {mid}.")

    print("RELAY_JSON " + json.dumps({
        "agent": AGENT, "date": RUN_DATE, "datapack_id": DATAPACK_ID,
        "conversation_id": conv, "memory_id": mid,
        "recall_count": len(texts), "recalled": texts,
        "tests_run": n_tests, "tests_passed": n_tests if passed else 0,
        "probes": probe_results, "result": result,
    }))


if __name__ == "__main__":
    main()
