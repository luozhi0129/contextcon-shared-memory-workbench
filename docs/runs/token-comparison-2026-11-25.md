# Token-waste comparison — measured, 2026-11-25

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
| researcher | 307 (143 words) | 294 (132 words) | -13 |
| coder | 308 (144 words) | 195 (84 words) | -113 |
| reviewer | 385 (177 words) | 341 (139 words) | -44 |
| **total** | **1000** | **830** | **-170 (-20.5%)** |

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
same as re-pasting, and slightly more (170 tokens, 20.5% on this
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

Measured per-unit costs: one memory ≈ 98 tokens (mean of the 3
distinct task memories), one trace turn ≈ 62 tokens (mean of
the 3 traces). Each further relay iteration adds ≈ 381
tokens to the paste baseline (2 new memories + 3 new traces). The recall
cost stays near its measured per-relay level (1000 tokens) because
each agent's recall is capped at the configured limit of 5 memories; the
formal ceiling is 2037 tokens (3 agents × (longest query +
5 × longest memory)). Totals are per relay (all three agents).

| memories in datapack | re-paste baseline (tokens) | recall per relay (tokens) |
|---|---|---|
| 5 | 830 | ≈ 1000 |
| 7 | 1211 | ≈ 1000 |
| 10 | 1592 | ≈ 1000 |
| 20 | 3497 | ≈ 1000 |
| 30 | 5402 | ≈ 1000 |

Assumptions, stated plainly: history grows by whole relay iterations (2 new
memories + 3 new traces each); each new memory/trace costs the measured mean;
retrieval never returns more than the configured limit of 5 memories. If the
task's memories get longer, the paste baseline grows faster; the recall level
does not move. The crossover — where the re-paste baseline first passes the
measured recall level — is at roughly 7 memories on this
model (one more relay iteration); it passes even the formal recall ceiling
(2037 tokens) at roughly 13 memories.

## Upper bound: paste literally every memory in the datapack

`memory_get_all` on 2026-11-25: **5 memories, 455 tokens
(202 words)** in total. That is what a "paste everything" briefing
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
- Datapack census: live `memory_get_all`, 5 memories.
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
