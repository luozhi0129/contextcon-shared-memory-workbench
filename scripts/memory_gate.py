#!/usr/bin/env python3
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
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(rf"\b(?:{MONTHS})\.?\s+\d{{1,2}},?\s+\d{{4}}\b"),
    re.compile(rf"\b\d{{1,2}}\s+(?:{MONTHS})\.?\s+\d{{4}}\b"),
]
NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
BACKTICK_RE = re.compile(r"`[^`]{2,}`")
QUOTE_RE = re.compile(r'"[^"]{2,}"')
SLUG_RE = re.compile(r"\b[a-z0-9]+(?:[-_][a-z0-9]+)+\b")
LABEL_RE = re.compile(r"\b[A-Z][A-Za-z]{1,30}:\s+\S")
CAPITAL_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")
SENTENCE_START = re.compile(r"(^|[.!?]\s+)([A-Z][a-z]{2,})")
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
