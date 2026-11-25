#!/usr/bin/env python3
"""Reviewer agent — step 3 of the relay.

Loop: recall what the coder built (zero briefing) -> independently re-run
the test suite -> adversarial probes against the gate (3 failure modes + 1
good case) -> check the gate matches the researcher's spec -> write the
verdict as gated memory -> trace the exchange.
"""
import importlib.util
import json
import re
import subprocess
import sys

from common import (DATAPACK_ID, PROJECT_ROOT, RUN_DATE, connect,
                    memory_texts, new_conversation, recall, remember, trace)

AGENT = "reviewer"

PROBES = [
    ("no-date", "The coder ran 10 tests on the memory_gate module and all passed.", False),
    ("no-number", "On 2026-11-25 the reviewer checked the memory_gate module and approved it.", False),
    ("no-named-fact", "On 2026-11-25 we ran 10 checks and 3 failed in the pipeline.", False),
    ("good", "On 2026-11-25 the coder ran 10 tests on `memory_gate.py` and all passed.", True),
]


def load_gate(path):
    spec = importlib.util.spec_from_file_location("relay_memory_gate_review", path)
    mod = importlib.util.module_from_spec(spec)
    # dataclasses need the module registered in sys.modules before exec.
    sys.modules["relay_memory_gate_review"] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    m, info = connect()
    print(f"reviewer: connected to {info.get('name')} {info.get('version')}")
    conv = new_conversation(m, f"reviewer — memory gate review — {RUN_DATE}")
    print(f"reviewer: conversation {conv}")

    found = recall(m, conv, AGENT, "What did the coder build and what were the test results?")
    texts = memory_texts(found)
    print(f"reviewer: recall returned {len(texts)} memor(ies)")
    for t in texts:
        print(f"  recalled: {t[:140]}")
    blob = " ".join(texts).lower()
    for needle in ("memory_gate", "passed"):
        if needle not in blob:
            raise RuntimeError(f"handoff broken: recall has no {needle!r}: {texts}")
    print("reviewer: coder result recalled — memory_gate + passed present (zero briefing)")

    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                          cwd=PROJECT_ROOT, capture_output=True, text=True)
    ran = re.search(r"Ran (\d+) tests?", proc.stderr)
    n_tests = int(ran.group(1)) if ran else 0
    passed = "OK" in proc.stderr.splitlines()[-2:] and "FAILED" not in proc.stderr
    print(f"reviewer: independent test re-run: {n_tests} tests, {'OK' if passed else 'FAILED'}")
    if not passed or n_tests == 0:
        raise RuntimeError(f"independent test re-run failed:\n{proc.stderr[-1500:]}")

    gate = load_gate(f"{PROJECT_ROOT}/scripts/memory_gate.py")
    probe_results = []
    for name, text, want_ok in PROBES:
        r = gate.check(text)
        ok = (r.ok == want_ok)
        probe_results.append({"probe": name, "want_ok": want_ok, "got_ok": r.ok,
                              "failures": r.failures, "correct": ok})
        print(f"reviewer: probe {name}: want_ok={want_ok} got_ok={r.ok} failures={r.failures} -> {'OK' if ok else 'WRONG'}")
        if not ok:
            raise RuntimeError(f"probe {name} wrong: {r}")

    # Spec match: the researcher's spec demanded 3 checks; the probes prove
    # all three are enforced (each failure mode rejected, good case accepted).
    spec_ok = all(p["correct"] for p in probe_results)
    verdict = "PASS" if (passed and spec_ok) else "FAIL"
    result = (
        f"{RUN_DATE} reviewer verdict: {verdict}. "
        f"Re-ran `tests/test_memory_gate.py` independently: {n_tests} passed, 0 failed. "
        f"Adversarial probes: {sum(p['correct'] for p in probe_results)}/{len(PROBES)} correct "
        f"(no-date rejected, no-number rejected, no-named-fact rejected, good summary accepted). "
        f"Gate matches the researcher spec of {RUN_DATE} (3 checks). No blocking issues."
    )

    def gate_fn(text):
        res = gate.check(text)
        return res.ok, res.failures, res.details

    mid = remember(m, conv, AGENT, result, gate=gate_fn)
    print(f"reviewer: verdict memory written (gated), id={mid}")

    trace(m, conv,
          "What is your verdict on the coder's work?",
          f"{verdict}: {n_tests}/{n_tests} tests pass on independent re-run, "
          f"{sum(p['correct'] for p in probe_results)}/{len(PROBES)} probes correct. "
          f"Verdict memory {mid}.")

    print("RELAY_JSON " + json.dumps({
        "agent": AGENT, "date": RUN_DATE, "datapack_id": DATAPACK_ID,
        "conversation_id": conv, "memory_id": mid,
        "recall_count": len(texts), "recalled": texts,
        "tests_run": n_tests, "tests_passed": n_tests if passed else 0,
        "probes": probe_results, "verdict": verdict, "result": result,
    }))


if __name__ == "__main__":
    main()
