# ContextCon: Shared-Memory Workbench

Multi-agent shared-memory workbench — several agents and a user collaborate on one
long task across days with **zero re-briefing**, on Meko as the context layer.

## The idea in one line

Every agent writes dated, compressed memory (facts / numbers / dates, auto-expiring)
into one shared Meko datapack and runs `context_search` before starting work, so
"where did we get to last time" is answered by the datapack, not by re-pasting context.

## Why it wins (judging weights)

- **Use of Meko 30%** — one datapack per project; conversations + memory + knowledge
  base + decision traces all in Meko; `context_search` is the working loop, not a demo prop.
- **Impact & usefulness 25%** — the token-waste comparison is measured, not claimed:
  re-pasting context vs recalling it, in real tokens.
- **Technical execution 20%** — three agents relaying one real bounty over days.
- **Innovation 15%** — a memory quality gate: every summary must carry verifiable
  facts / numbers / dates, plus a "memory audit" view (who knew what, when, based on what).
- **Presentation 10%** — ≤5 min video showing one zero-briefing handoff end to end.

## Demo scenario

Researcher, coder, and reviewer agents relay one bounty across days:

1. **Researcher** (day 1): investigates, writes findings as dated memory
   (facts, numbers, dates, sources) into the shared datapack.
2. **Coder** (day 2): starts with `context_search` only — zero briefing — and
   picks up exactly where the researcher stopped.
3. **Reviewer** (day 3): verifies against the same decision traces, writes the
   verdict as memory.
4. Side-by-side: the same relay done by re-pasting full context, with the token
   count shown. The saving is the number, not a slogan.

## Memory rules (from the QQ bridge, verified in production)

- 20-turn live window + ~1,200-word compressed summaries.
- A summary must state concrete facts / numbers / dates — no vague prose.
- Memories expire; stale facts don't silently linger.
- Fast-path memory and main memory stay isolated (per-conversation), same as the bridge.

## Meko integration

- MCP endpoint: `https://mcp.mekodata.ai/mcp`, API key from Settings > API Keys.
- Tools used: `datapack_create`, `memory_add`, `memory_search`, `context_search`,
  `conversation_create`, `conversation_add_message`, `knowledgebase_upload_document`,
  `artifact_put`, `track_token_usage`, `memory_promote`.
- **Exactly one datapack** for the whole project (`contextcon-workbench`).
  Free tier allows 10 datapacks for the life of the account and deleting one does
  NOT free a slot — no throwaway datapacks in tests.
- Quota budget (Free, lifetime, no reset): 1,000 context searches — budget ~100
  for build + demo + tests; 10,000 memory adds; 1,000 memory searches;
  2,000 searchable conversation turns. Track usage in `USAGE.md`.

## Deliverables (HackerEarth)

- [x] Working demo link (hosted workbench) — **LIVE:** https://luozhi0129.github.io/contextcon-shared-memory-workbench/ (GitHub Pages, `main` / `docs`; verified HTTP 200 on home/audit/comparison).
- [x] Repo URL (public, open source) — **LIVE:** https://github.com/luozhi0129/contextcon-shared-memory-workbench (41 files, commit `bb7af0d1`).
- [ ] Demo video ≤ 5 minutes (script drafted: `video-script.md`)
- [x] Project presentation — `presentation.md` (+ rendered on the demo site)
- [x] Setup / run instructions — see below
- [x] Optional: architecture doc, Meko-usage doc, token / relevance metrics doc — `runs/token-comparison-2026-11-25.md` (token metrics, measured), Meko usage in `presentation.md` §2

## Setup / run instructions

```bash
git clone https://github.com/luozhi0129/contextcon-shared-memory-workbench
cd contextcon-shared-memory-workbench
# A Meko API key is needed for the live parts (free Meko account:
# Settings > API Keys). Save it as .meko-api-key.json (0600):
#   {"label": "your-label", "api_key": "mko_tkn_..."}
python3 scripts/meko-smoke.py        # Phase 1: datapack + recall check
python3 scripts/run_relay.py         # Phase 2: three-agent relay
python3 -m unittest discover -s tests  # 17 tests, stdlib only
python3 scripts/render_site.py       # rebuild the demo site in docs/
```

## Key facts (verified 2026-11-25)

- Competition: ContextCon: Remember Everything (YugabyteDB × HackerEarth),
  online, 2026-11-07 → 2027-01-17. Solo OK, teams 1–4.
- **Submit by the earlier deadline: 2027-01-18 01:30 Beijing**
  (2027-01-17 17:30 UTC; another source says 23:59 PT — plan by the earlier one,
  re-check on the official page before submitting).
- Total pool $10,000 (FAQ confirmed). Prize split NOT re-verified — do not quote it.
- No China/Singapore exclusion found in the FAQ; full rules page not read
  (partial verification). No KYC mentioned in the FAQ.
- Free Meko account suffices: 10 datapacks, 100 MB knowledge, no credit card.
- Meko MCP docs: https://docs.mekodata.ai/reference/mcp-server/

## Status

- 2026-11-25: requirements verified; Meko account + API key requested (browser);
  project scaffolded. Build next.
- 2026-11-25 10:31: Phase 1 smoke test passed (fresh agent recalled 3 facts
  with zero briefing; datapack `contextcon-workbench` created).
- 2026-11-25 10:40: Phase 2 relay complete — 3/3 agents, verdict PASS.
  Gate (`scripts/memory_gate.py`, 11 tests) + audit view (`web/audit.html`)
  live in the repo.
- 2026-11-25 ~11:00: Phase 3 token comparison done — exact cl100k_base
  counts (`scripts/cl100k.py`, validated): WITH Meko 1,000 tokens vs
  WITHOUT (minimal re-paste) 830 → −170 (−20.5%) at this scale; the
  re-paste baseline passes the recall level at ~7 memories (projection
  from measured per-unit costs). Also found + fixed: relay trace turns
  were never persisted (`trace()` passed a wrong `datapack_id`). Report:
  `runs/token-comparison-2026-11-25.md`. Next: Phase 4 demo + video.
- 2026-11-25 ~11:10: Phase 4 (part 1) — presentation (`presentation.md`) +
  video script (`video-script.md`) written, static demo site built in `docs/`
  (audit view, comparison, presentation, run logs). Meko account UUID redacted
  from published run artifacts. Repo creation was blocked at first
  (connector `create_repository` → 403, GitHub App token cannot create user
  repos) — fixed the same day: empty public repo created in the browser,
  snapshot pushed via the connector (`bb7af0d1`, 41 files), Pages enabled
  (`main` / `docs`). **Repo + demo link are LIVE** (see Deliverables).
  Remaining: the ≤5 min demo video (script drafted).
