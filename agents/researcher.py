#!/usr/bin/env python3
"""Researcher agent — step 1 of the relay.

Loop: recall (what is already known about the memory gate?) -> write the
gate spec as dated memory -> trace the exchange.

The researcher runs BEFORE the gate exists, so its memory is written
ungated. The spec text is written to pass the gate anyway (date + number +
named fact), so the reviewer can later verify it would pass.

Fixed scope (in code, repeatable): the memory quality gate, version 1.0.
"""
import json
import sys

from common import (DATAPACK_ID, RUN_DATE, connect, memory_texts,
                    new_conversation, recall, recall_hits, remember, trace)

AGENT = "researcher"

SPEC = (
    f"{RUN_DATE} researcher spec: memory gate v1.0 enforces 3 checks — "
    "(1) DATE: ISO YYYY-MM-DD or Month D, YYYY; "
    "(2) NUMBER: digits outside the date, e.g. $10, 30%, 1000 tokens; "
    "(3) NAMED FACT: backticked/quoted token, hyphenated slug, "
    "'Label: value', or capitalised proper noun. "
    "Implementation: `scripts/memory_gate.py` (stdlib only, importable + CLI), "
    "tests in `tests/test_memory_gate.py`, gate version 1.0. "
    "Summaries expire 30 days after their date."
)


def main():
    m, info = connect()
    print(f"researcher: connected to {info.get('name')} {info.get('version')}")
    conv = new_conversation(m, f"researcher — memory gate spec — {RUN_DATE}")
    print(f"researcher: conversation {conv}")

    found = recall(m, conv, AGENT, "What is known about the memory quality gate for this workbench?")
    texts = memory_texts(found)
    print(f"researcher: recall returned {len(texts)} memor(ies)")
    for t in texts:
        print(f"  recalled: {t[:140]}")

    # Idempotent re-run: if the spec is already in the datapack, reuse it
    # instead of writing a duplicate.
    mid = None
    for hit in recall_hits(found):
        if (hit.get("memory", "") or "").startswith(f"{RUN_DATE} researcher spec:"):
            mid = hit.get("id")
            print(f"researcher: spec already present, reusing memory {mid}")
            break
    if mid is None:
        mid = remember(m, conv, AGENT, SPEC, gate=None)
        print(f"researcher: spec memory written, id={mid}")

    trace(m, conv,
          "What should the memory quality gate check?",
          f"Spec written as memory {mid}: 3 checks (date, number, named fact), "
          f"implementation scripts/memory_gate.py, tests tests/test_memory_gate.py.")

    print("RELAY_JSON " + json.dumps({
        "agent": AGENT, "date": RUN_DATE, "datapack_id": DATAPACK_ID,
        "conversation_id": conv, "memory_id": mid,
        "recall_count": len(texts), "recalled": texts,
        "spec": SPEC,
    }))


if __name__ == "__main__":
    main()
