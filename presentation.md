# Shared-Memory Workbench — ContextCon presentation

**Team:** Super Hakimi (solo) · **Context layer:** Meko (free tier)
**Repo:** https://github.com/luozhi0129/contextcon-shared-memory-workbench
**Demo:** https://luozhi0129.github.io/contextcon-shared-memory-workbench/

Every number below traces to a run log in the repo (`runs/`). Nothing is estimated
without being labelled as a model.

---

## 1. The problem

When several agents — or one agent over several days — work on the same long
task, each handoff starts from zero. The usual fix is to re-paste the whole
context: the spec, the previous results, the conversation history. That works
until the history gets long, and then it costs tokens on every single handoff,
forever.

The alternative is a shared memory: every agent writes what it learned into
one place, and the next agent recalls it instead of being re-briefed. That is
what we built — and we measured whether it actually saves anything, instead
of assuming it does.

## 2. How we use Meko (30% of the judging)

One datapack, `contextcon-workbench`, holds everything for the project:

| Meko surface | How the workbench uses it |
|---|---|
| `context_search` | The working loop. Every agent recalls before it starts — zero briefing, by construction. |
| `memory_add` | Dated, compressed facts (facts / numbers / dates). 9 memories written so far. |
| `conversation_create` / `conversation_add_message` | Decision traces: every agent's step is saved as a turn. |
| `memory_get_all` | The audit view and the datapack census (5 memories, 455 tokens). |
| `knowledgebase_*`, `artifact_*`, `memory_promote` | Available for shared documents and promoting private memory to shared knowledge; wired into the client, used as the project grows. |

Free tier only. Usage so far: **13 context searches** of the 1,000 lifetime
allowance, **2 of 10 datapacks** (the default one plus the project datapack).
No card, no paid plan.

## 3. The relay — three agents, zero briefing

One fixed-scope task, run end to end: research, implement, and review the
memory quality gate itself.

| Agent | What it did | What it recalled (zero briefing) |
|---|---|---|
| Researcher | Wrote the gate spec (3 checks) | 0 memories — fresh start |
| Coder | Implemented `scripts/memory_gate.py` + 11 tests, 11/11 pass, 4/4 adversarial probes correct | 1 memory — the spec, verbatim |
| Reviewer | Independently re-ran the suite: 11/11 pass, 4/4 probes correct. Verdict: **PASS** | 2 memories — coder result + spec |

Run log: `runs/relay-2026-11-25.jsonl`. The coder picked up exactly where the
researcher stopped, with no briefing pasted. The reviewer verified against the
same decision traces.

## 4. The measured comparison — the honest result

Same relay, two ways. Tokens counted exactly (cl100k_base, counted locally
with `scripts/cl100k.py`, validated against canonical vectors).

| Agent | WITH Meko (query + recalled) | WITHOUT Meko (minimal re-paste) |
|---|---|---|
| Researcher | 307 | 294 |
| Coder | 308 | 195 |
| Reviewer | 385 | 341 |
| **Total** | **1,000** | **830** |

**At this scale — 5 memories, 3 traces — recall costs slightly MORE:
−170 tokens (−20.5%).** We report that, not a saving we did not measure.

Why: retrieval is imprecise at small scale. The reviewer recalled the coder
result twice (identical text, two memory ids) plus a verdict it did not need;
the researcher and coder each recalled 3 memories when 1 would do. The
re-paste baseline is exactly the texts needed and nothing else.

But the two costs grow differently, and that is the point:

- Re-paste grows with history: every new memory and every new trace has to be
  pasted again at the next handoff.
- Recall stays bounded by the retrieval limit (5 memories here): the agent
  asks a question and gets the top matches back, however long the history is.

**Projection — a model from measured per-unit costs, NOT a measurement:**
one memory ≈ 98 tokens, one trace ≈ 62 tokens, so each further relay
iteration adds ≈ 381 tokens to the paste baseline while recall stays near
its measured 1,000-token level. The re-paste baseline passes the recall level
at **~7 memories** (one more iteration) and the formal recall ceiling
(2,037 tokens) at **~13 memories**.

| Memories in datapack | Re-paste baseline | Recall per relay |
|---|---|---|
| 5 (measured) | 830 | 1,000 |
| 7 | 1,211 | ≈ 1,000 |
| 10 | 1,592 | ≈ 1,000 |
| 20 | 3,497 | ≈ 1,000 |
| 30 | 5,402 | ≈ 1,000 |

Upper bound: pasting literally every memory in the datapack today costs
455 tokens (5 memories, `memory_get_all` census). Full method, assumptions,
and sources of every number: `runs/token-comparison-2026-11-25.md`.

## 5. The memory audit — who knew what, when, based on what

The audit view (`web/audit.html`, live on the demo site) renders the
datapack's memories with their writer, timestamp, and the conversation each
one is based on. Every summary above passed the memory quality gate before
it was written.

## 6. The memory quality gate — the differentiator

A summary is not a memory until it can be checked. The gate
(`scripts/memory_gate.py`) rejects any summary that lacks any of:

1. **A date** — ISO `YYYY-MM-DD` or `Month D, YYYY`;
2. **A number** — digits outside the date (`$10`, `30%`, `1000 tokens`);
3. **A named fact** — a backticked/quoted token, a hyphenated slug,
   `Label: value`, or a capitalised proper noun.

Enforced in code, not in prose: coder and reviewer both gate their own
memories before writing. 11 unit tests pass; 4 adversarial probes (no-date,
no-number, no-named-fact, good) all behave correctly — verified twice
(coder run + reviewer independent re-run).

Summaries expire 30 days after their date, so stale facts do not linger.
This is the mechanism we run in production on our own QQ bridge, where
memory is a 20-turn live window plus ~1,200-word compressed summaries that
must state concrete facts, numbers, and dates.

## 7. What we learned (and fixed) by measuring

- **A real bug, found by the measurement:** the relay's trace turns were
  never persisted — `trace()` passed a `datapack_id` the server rejects
  with `not_found`, and the drivers never checked the return value. Six
  trace calls failed silently across two relay runs. Fixed in Phase 3;
  the comparison's trace texts are reconstructions from source + run log,
  labelled as such.
- **`context_search` returns a `token_savings` field** (`total_tokens:
  10000` on a probe). Its definition is unverified and the value looks
  like a placeholder, so it is **not used as evidence** anywhere.

## 8. Run it yourself

```bash
git clone https://github.com/luozhi0129/contextcon-shared-memory-workbench
cd contextcon-shared-memory-workbench
python3 scripts/meko-smoke.py        # needs a Meko API key (free account)
python3 scripts/run_relay.py         # the three-agent relay
python3 -m unittest discover -s tests  # 17 tests, stdlib only
```

Setup / run instructions: `README.md`. The demo site hosts the audit view,
the full comparison, and the run logs.
