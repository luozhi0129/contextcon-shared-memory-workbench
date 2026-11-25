#!/usr/bin/env python3
"""Phase 3: measure the token-waste comparison from the fresh relay run.

Reads runs/relay-2026-11-25.jsonl (the fresh run) and measures, with the
exact cl100k_base tokenizer (scripts/cl100k.py, validated in
tests/test_cl100k.py):

  WITH Meko, per agent = tokens(query) + tokens(each memory text its
      context_search actually returned).
  WITHOUT Meko, per agent = tokens of the full texts that would have to be
      pasted to give the agent the same information:
        researcher: the 3 distinct task memories (to check the spec exists)
        coder:      researcher spec + researcher trace turn (input+output)
        reviewer:   researcher spec + coder result + researcher trace + coder trace

Trace texts are reconstructed from the agent source (agents/*.py, verified
by grep below) + the memory ids / counts in the fresh run log, because the
relay's trace() calls did NOT persist: trace() passed datapack_id, which
makes conversation_add_message fail with "not_found" (found in Phase 3;
probe B in the comparison doc proves the call shape without datapack_id
works and persists after ~1 min). The trace texts below are therefore the
exact strings the agents produced, not stored copies — stated as such in
the report. The bug is fixed in agents/common.py in this same change.

Also fetches every memory in the datapack (memory_get_all) for the
"paste literally every memory" upper bound.

Writes runs/token-comparison-2026-11-25.md. No context_search is used
here (all inputs come from the run log / memory_get_all).
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cl100k import count as tok_count, words as word_count  # noqa: E402
from meko_client import MCP, load_key  # noqa: E402

PROJECT_ROOT = os.path.expanduser("~/workspace/makefun/contextcon")
DATAPACK_ID = "c2f6a0e2-b841-49bb-8b18-117a90339661"
RUN_DATE = "2026-11-25"

# Queries and trace inputs, as written in agents/*.py. Verified against the
# source by grep at runtime (fail loudly if they drift).
QUERIES = {
    "researcher": "What is known about the memory quality gate for this workbench?",
    "coder": "What is the memory gate spec? What checks must the gate enforce?",
    "reviewer": "What did the coder build and what were the test results?",
}
TRACE_INPUTS = {
    "researcher": "What should the memory quality gate check?",
    "coder": "What did you build from the recalled spec?",
    "reviewer": "What is your verdict on the coder's work?",
}


def _grep_check(agent, needle):
    path = f"{PROJECT_ROOT}/agents/{agent}.py"
    src = open(path, encoding="utf-8").read()
    if needle not in src:
        raise RuntimeError(f"{agent}.py no longer contains {needle!r} — update measure_tokens.py")


def trace_output(agent, rec):
    """Reconstruct the exact trace output string for an agent from the run log."""
    mid = rec["memory_id"]
    if agent == "researcher":
        return (f"Spec written as memory {mid}: 3 checks (date, number, named fact), "
                f"implementation scripts/memory_gate.py, tests tests/test_memory_gate.py.")
    if agent == "coder":
        probes_ok = sum(1 for p in rec["probes"] if p["correct"])
        return (f"Implemented scripts/memory_gate.py + tests/test_memory_gate.py: "
                f"{rec['tests_passed']}/{rec['tests_run']} tests pass, "
                f"{probes_ok}/{len(rec['probes'])} probes correct. Result memory {mid}.")
    if agent == "reviewer":
        probes_ok = sum(1 for p in rec["probes"] if p["correct"])
        return (f"{rec['verdict']}: {rec['tests_passed']}/{rec['tests_run']} tests pass "
                f"on independent re-run, {probes_ok}/{len(rec['probes'])} probes correct. "
                f"Verdict memory {mid}.")
    raise ValueError(agent)


def main():
    for agent, q in QUERIES.items():
        _grep_check(agent, q)
        _grep_check(agent, TRACE_INPUTS[agent])
    print("measure: queries + trace inputs verified against agents/*.py")

    jsonl = f"{PROJECT_ROOT}/runs/relay-{RUN_DATE}.jsonl"
    lines = open(jsonl, encoding="utf-8").read().strip().splitlines()
    recs = {}
    for line in lines[1:]:
        if line.strip():
            r = json.loads(line)
            recs[r["agent"]] = r
    assert set(recs) == {"researcher", "coder", "reviewer"}, recs.keys()

    # Distinct task memory texts (spec, coder result, reviewer verdict).
    spec = recs["researcher"]["spec"]
    coder_result = recs["coder"]["result"]
    verdict = recs["reviewer"]["result"]
    distinct = {"spec": spec, "coder_result": coder_result, "verdict": verdict}

    # Trace turns (input + output) per agent, reconstructed exactly.
    traces = {}
    for agent in ("researcher", "coder", "reviewer"):
        traces[agent] = TRACE_INPUTS[agent] + "\n" + trace_output(agent, recs[agent])

    # ---- WITH Meko: query + recalled memory texts (as actually returned) ----
    with_meko = {}
    for agent in ("researcher", "coder", "reviewer"):
        parts = [("query", QUERIES[agent])]
        for i, t in enumerate(recs[agent]["recalled"]):
            parts.append((f"recalled[{i}]", t))
        total = sum(tok_count(t) for _, t in parts)
        with_meko[agent] = {"parts": parts, "total_tokens": total,
                            "total_words": sum(word_count(t) for _, t in parts)}

    # ---- WITHOUT Meko: the full texts that would have to be pasted ----
    without = {}
    without["researcher"] = {
        "parts": [("spec", spec), ("coder_result", coder_result), ("verdict", verdict)],
        "note": "to check whether the spec already exists, the current memory state must be pasted",
    }
    without["coder"] = {
        "parts": [("spec", spec), ("researcher trace", traces["researcher"])],
        "note": "spec + the researcher's working trace",
    }
    without["reviewer"] = {
        "parts": [("spec", spec), ("coder_result", coder_result),
                  ("researcher trace", traces["researcher"]),
                  ("coder trace", traces["coder"])],
        "note": "spec + coder result + both working traces",
    }
    for agent in ("researcher", "coder", "reviewer"):
        parts = without[agent]["parts"]
        without[agent]["total_tokens"] = sum(tok_count(t) for _, t in parts)
        without[agent]["total_words"] = sum(word_count(t) for _, t in parts)

    # ---- Upper bound: paste literally every memory in the datapack ----
    m = MCP(load_key())
    info = m.initialize()
    conv = json.loads(m.call("conversation_create",
                             {"title": "token comparison — memory census — 2026-11-25"}))["id"]
    all_mems = []
    page = 1
    while True:
        out = json.loads(m.call("memory_get_all", {
            "conversation_id": conv, "datapack_id": DATAPACK_ID,
            "page": page, "page_size": 100}))
        batch = out.get("data") or out.get("memories") or out.get("results") or []
        all_mems.extend(batch)
        if page >= out.get("total_pages", 1) or not batch:
            break
        page += 1
    all_texts = [(mm.get("data") or mm.get("memory", "")) for mm in all_mems]
    upper_tokens = sum(tok_count(t) for t in all_texts)
    upper_words = sum(word_count(t) for t in all_texts)
    print(f"measure: datapack holds {len(all_mems)} memories, "
          f"{upper_tokens} tokens / {upper_words} words in total")

    # ---- Totals (needed by the projection below) ----
    tot_with = sum(with_meko[a]["total_tokens"] for a in with_meko)
    tot_without = sum(without[a]["total_tokens"] for a in without)

    # ---- Projection (model, not measurement) ----
    # Per-iteration growth of the paste baseline: each new relay iteration adds
    # 1 coder-result memory + 1 verdict memory + 3 trace turns (the spec is
    # written once and reused). Recall per relay is reported at its MEASURED
    # level (the sum of the three agents' WITH totals): it stays near that
    # level as history grows because each agent's recall is capped at the
    # configured limit of 5 memories. The formal ceiling is
    # 3 x (longest query + 5 x longest memory).
    avg_mem = sum(tok_count(t) for t in distinct.values()) / 3
    avg_trace = sum(tok_count(traces[a]) for a in traces) / 3
    growth_per_iter = 2 * avg_mem + 3 * avg_trace
    recall_level = tot_with
    max_query = max(tok_count(QUERIES[a]) for a in QUERIES)
    max_mem = max(tok_count(t) for t in distinct.values())
    recall_ceiling = 3 * (max_query + 5 * max_mem)
    base_without = sum(without[a]["total_tokens"] for a in without)
    proj = []
    for n_mem in (5, 7, 10, 20, 30):
        # iterations beyond the current 5 memories, at ~2 new memories each
        iters = max(0, (n_mem - 5) // 2)
        paste = base_without + iters * growth_per_iter
        proj.append((n_mem, round(paste)))

    def _paste_at(n_mem):
        iters = max(0, (n_mem - 5) // 2)
        return base_without + iters * growth_per_iter

    crossover_level = next(
        (n for n in range(5, 61) if _paste_at(n) > recall_level), None)
    crossover_ceiling = next(
        (n for n in range(5, 61) if _paste_at(n) > recall_ceiling), None)

    # ---- Write the report ----
    saving = tot_without - tot_with
    pct = 100.0 * saving / tot_without if tot_without else 0.0

    def row(agent):
        w, wo = with_meko[agent], without[agent]
        return (f"| {agent} | {w['total_tokens']} ({w['total_words']} words) | "
                f"{wo['total_tokens']} ({wo['total_words']} words) | "
                f"{wo['total_tokens'] - w['total_tokens']} |")

    md = f"""# Token-waste comparison — measured, 2026-11-25

Relay run: `runs/relay-2026-11-25.jsonl` (fresh re-run, 3/3 agents, verdict PASS).
Fresh memory ids: researcher spec `615b6c6b…` (reused), coder result
`0e7b1f0b…`, reviewer verdict `570e5ae9…`.
Counting: **exact cl100k_base tokens**, counted locally with
`scripts/cl100k.py` (pure-stdlib BPE over the vendored ranks file
`data/cl100k_base.tiktoken`; validated in `tests/test_cl100k.py` — canonical
vectors "hello world" → 2, pangram → 9, "12345" → 2, plus round-trips on
every measured text). No estimate, no tokenizer API, no invented numbers.

## Measured comparison (one relay, this datapack, this run)

| agent | WITH Meko (query + recalled) | WITHOUT Meko (re-paste) | saving |
|---|---|---|---|
{row("researcher")}
{row("coder")}
{row("reviewer")}
| **total** | **{tot_with}** | **{tot_without}** | **{saving} ({pct:+.1f}%)** |

- WITH Meko = the agent's recall query + the memory texts its `context_search`
  actually returned (from the run log, verbatim). Researcher recalled 3,
  coder 3, reviewer 4.
- WITHOUT Meko = the full texts that would have to be pasted to give the
  agent the same information: researcher — the 3 distinct task memories (to
  check whether the spec exists); coder — spec + researcher trace;
  reviewer — spec + coder result + researcher trace + coder trace.
  This is the **minimal** paste: a real human briefing a fresh agent would
  paste at least this much, usually more (the whole thread, to be safe).
- The trace turns are reconstructed from `agents/*.py` (verified by grep in
  the measurement script) + the memory ids in the run log — see the note
  below on why they are reconstructions, not stored copies.

## What the measurement actually says

At this scale — 5 memories, 3 traces, one relay — **recall costs about the
same as re-pasting, and slightly more ({-saving} tokens, {-pct:.1f}% on this
run)**. The reason is visible in the run log: retrieval is imprecise at
small scale. The reviewer's recall returned the coder result **twice**
(identical text, two memory ids) plus a verdict it did not need; the
researcher and coder each recalled 3 memories when 1 would do. The
re-paste baseline, by contrast, is exactly the texts needed and nothing else.

That is the honest result for a toy relay — and it is the point. The saving
is not in a single handoff at toy scale; it is in how the two costs **grow**:

- Re-paste grows with history: every new memory and every new trace turn
  has to be pasted again at the next handoff.
- Recall stays bounded by the retrieval limit (5 memories here): the agent
  asks a question and gets the top matches back, however long the history is.

## Projection (model from measured per-unit costs, NOT a measurement)

Measured per-unit costs: one memory ≈ {avg_mem:.0f} tokens (mean of the 3
distinct task memories), one trace turn ≈ {avg_trace:.0f} tokens (mean of
the 3 traces). Each further relay iteration adds ≈ {growth_per_iter:.0f}
tokens to the paste baseline (2 new memories + 3 new traces). The recall
cost stays near its measured per-relay level ({recall_level} tokens) because
each agent's recall is capped at the configured limit of 5 memories; the
formal ceiling is {recall_ceiling} tokens (3 agents × (longest query +
5 × longest memory)). Totals are per relay (all three agents).

| memories in datapack | re-paste baseline (tokens) | recall per relay (tokens) |
|---|---|---|
"""
    for n_mem, paste in proj:
        md += f"| {n_mem} | {paste} | ≈ {recall_level} |\n"
    md += f"""
Assumptions, stated plainly: history grows by whole relay iterations (2 new
memories + 3 new traces each); each new memory/trace costs the measured mean;
retrieval never returns more than the configured limit of 5 memories. If the
task's memories get longer, the paste baseline grows faster; the recall level
does not move. The crossover — where the re-paste baseline first passes the
measured recall level — is at roughly {crossover_level} memories on this
model (one more relay iteration); it passes even the formal recall ceiling
({recall_ceiling} tokens) at roughly {crossover_ceiling} memories.

## Upper bound: paste literally every memory in the datapack

`memory_get_all` on 2026-11-25: **{len(all_mems)} memories, {upper_tokens} tokens
({upper_words} words)** in total. That is what a "paste everything" briefing
would cost today, before any traces are added. (Conversation turns are not
counted here: `conversation_list` returns empty for this account, so the
datapack-wide conversation total is not enumerable via the API.)

## Two findings from this phase (not part of the token count)

1. **Relay trace turns were never persisted.** `agents/common.py::trace()`
   passed `datapack_id` to `conversation_add_message`, which the server
   rejects with `not_found` (the conversation is created without a
   datapack_id, so it lives in the default datapack). The drivers never
   checked the return value, so 6 trace calls across the two relay runs
   silently failed. The trace texts in this comparison are therefore
   reconstructions from source + run log (exact strings), not stored copies.
   Fixed in this change: `trace()` no longer passes `datapack_id`. Verified
   by direct probe: the same call without `datapack_id` returns
   `status: accepted` and the turn appears in `conversation_get` ~1 minute
   later (async indexing — an immediate re-get still shows 0 messages).
   `USAGE.md`'s earlier line "conversation_add_message accepted: 6" was
   inferred, not verified, and is corrected there.
2. **`context_search` responses carry a `token_savings` field**
   (`total_tokens: 10000` on the probe call). Its definition is unverified
   — it did not move in an obvious way and 10000 is suspiciously round —
   so it is **not used as evidence** anywhere in this comparison.

## Sources of every number

- Queries: `agents/researcher.py`, `agents/coder.py`, `agents/reviewer.py`
  (verified by grep in `scripts/measure_tokens.py`).
- Recalled texts + memory ids: `runs/relay-2026-11-25.jsonl`.
- Trace texts: `agents/common.py::trace` call sites + the run log's
  memory ids and test/probe counts (see finding 1).
- Datapack census: live `memory_get_all`, {len(all_mems)} memories.
- Tokenizer: `scripts/cl100k.py` + `data/cl100k_base.tiktoken`,
  validated by `tests/test_cl100k.py` (6 tests).
- Meko calls spent by this phase: 3 `context_search` (fresh relay) +
  1 `context_search` (conversation-bucket probe) + 2 `memory_add` (fresh
  coder + reviewer results; researcher reused the spec) +
  3 `conversation_create` (fresh relay) + 1 `conversation_create`
  (trace fetch) + 1 `conversation_create` (memory census) +
  3 `conversation_get` (trace fetch) + 3 `conversation_get` (probes) +
  1 `conversation_add_message` probe (accepted) +
  1 `conversation_add_message` probe (failed, not_found — the bug above) +
  1 `memory_get_all` page (census).
"""
    out_path = f"{PROJECT_ROOT}/runs/token-comparison-2026-11-25.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"measure: wrote {out_path}")
    print(f"measure: WITH {tot_with} vs WITHOUT {tot_without} -> saving {saving} ({pct:+.1f}%)")
    print(f"measure: datapack census {len(all_mems)} memories, {upper_tokens} tokens")
    print(f"measure: projection rows: {proj}")


if __name__ == "__main__":
    main()
