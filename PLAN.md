# ContextCon build plan

## Phase 0 — Foundations (2026-11-25, in progress)

- [x] Requirements verified (HackerEarth FAQ + Meko docs, live reads)
- [x] Concept fixed: multi-agent shared-memory workbench
- [x] Meko tool surface + free-tier quotas recorded (see README)
- [x] Meko account created (browser task running) + API key saved to
      `~/workspace/makefun/contextcon/.meko-api-key.json` (0600)
- [x] Project scaffold (this file, README, USAGE log)

## Phase 1 — Meko smoke test (DONE 2026-11-25 10:31)

A minimal MCP client script (`scripts/meko-client.py`, stdlib + plain HTTP):
- MCP endpoint is https://mcp.mekodata.ai/mcp (the cloud.mekodata.ai/mcp URL
  serves the web app HTML, not MCP). Server: Meko MCP 3.2.4, protocol 2025-03-26.
- The server requires `Accept: application/json, text/event-stream` and keeps
  the SSE stream open after answering — the client reads line by line and stops
  after the message with the matching id, then closes the connection.
- The VM's egress goes through an authenticated HTTP proxy (env `https_proxy`);
  the client does CONNECT tunneling via `http.client.set_tunnel`.
- Every tool call needs a `conversation_id` (create one first).
- Tool schemas are strict per tool — read them from `tools/list` before
  calling (e.g. `datapack_list`/`datapack_create` reject `agent_id`).
- memory_add returns `{"results": [{"id": ...}]}` — the id is nested, not top-level.

Smoke test (`scripts/meko-smoke.py`) PASSED 2026-11-25 10:31:
datapack `contextcon-workbench` created (id c2f6a0e2-b841-49bb-8b18-117a90339661);
3 dated facts written (researcher/coder/reviewer); a FRESH agent with zero
briefing recalled all three via `context_search`; one conversation turn saved;
the 3 smoke memories were deleted afterwards (verified `memory_get_all` total 0).
Usage: 1 datapack, 3 memory adds, 1 context search, 1 turn. Datapacks on the
account: 2/10 (default + project).

Meko account notes: luozhi0129@gmail.com, Free plan, workspace
"Super Hakimi's Workspace", account id <redacted-account-id>.
Profile NAME shows "智 罗" (from the Google identity) and is NOT editable in
Meko Settings — leave it; the workspace name and the project identity are
Super Hakimi, and the Meko profile field is not public-facing.

## Phase 2 — The three-agent relay (DONE 2026-11-25 10:40)

- [x] `agents/researcher.py`, `agents/coder.py`, `agents/reviewer.py` — thin
  drivers that all speak to the same datapack through the MCP client
  (`agents/common.py` holds the shared plumbing).
- [x] Each agent's loop: `context_search` → do its step → `memory_add` (dated,
  facts/numbers/dates) → `conversation_add_message` (trace).
- [x] The relay task: the memory quality gate itself — research (spec) +
  implement (`scripts/memory_gate.py` + `tests/test_memory_gate.py`, 11 cases)
  + review (independent re-run + 4 adversarial probes), fixed scope in code.
- [x] Memory quality gate (`scripts/memory_gate.py`): every summary must contain
  at least one date, one number, and one named fact, or it is rejected before
  writing. Enforced in code (coder + reviewer gate their own memories).
- [x] Memory audit view (`web/audit.html`): who wrote what, when, based on what —
  rendered from `memory_get_all` + `conversation_get` by `scripts/render_audit.py`.

Relay run 2026-11-25 (runs/relay-2026-11-25.jsonl): 3/3 agents complete.
Coder recalled the researcher's spec with zero briefing (1 memory, contains
"date", "number", "named fact"); reviewer recalled coder result + spec with
zero briefing (2 memories). Tests 11/11 pass twice (coder run + reviewer
independent re-run). Probes 4/4 correct twice. Verdict: PASS.
Memories in datapack: 3 (spec 615b6c6b…, coder result 13b7803a…,
reviewer verdict e29e7489…). Quota used in Phase 2: 8 more context searches
(9 total incl. smoke), 4 more memory adds (7 total). See USAGE.md.

Lessons recorded in code (do not re-learn):
- `memory_add` metadata must be a JSON-encoded STRING, not a dict.
- `conversation_create` / `conversation_add_message` must NOT pass agent_id
  (server owns them as meko_agent; a mismatch errors agent_id_mismatch).
- `memory_get_all` returns text under `data` (not `memory`), conversation
  under `conversation_id` (not `run_id`), and no score.
- `conversation_list` returns an empty list for this account — fetch titles
  via `conversation_get` per id instead.
- Loading a dataclass module via importlib requires registering it in
  sys.modules BEFORE exec_module.

## Phase 3 — Token-waste comparison (DONE 2026-11-25)

- [x] Fresh relay re-run (`runs/relay-2026-11-25.jsonl`, 3/3, PASS; Phase 2
  run archived as `runs/relay-2026-11-25-phase2.*`).
- [x] Exact token counting: `scripts/cl100k.py` — pure-stdlib cl100k_base BPE
  over the vendored ranks file `data/cl100k_base.tiktoken` (copied from the
  open-code-review repo's vendored copy; no tiktoken/transformers on the VM).
  Validated by `tests/test_cl100k.py` (6 tests: canonical vectors + round-trips).
- [x] Measurement (`scripts/measure_tokens.py`): WITH Meko 1,000 tokens vs
  WITHOUT (minimal re-paste) 830 → saving −170 (−20.5%) at this scale.
  Per agent: researcher 307 vs 294, coder 308 vs 195, reviewer 385 vs 341.
  Projection from measured per-unit costs (memory ≈98, trace ≈62 tokens;
  +381/iteration): re-paste passes the measured recall level at ~7 memories,
  the formal recall ceiling (2,037) at ~13. Report:
  `runs/token-comparison-2026-11-25.md`.
- [x] Upper bound: `memory_get_all` census — 5 memories, 455 tokens in the
  datapack. (Datapack-wide conversation total not enumerable:
  `conversation_list` returns empty for this account.)
- [x] Quota recorded in `USAGE.md`: context_search 13 total (budget ~30),
  memory_add 9 total. Datapacks still 2/10.

Findings (recorded in the comparison doc + `USAGE.md`):
- Relay trace turns were never persisted: `trace()` passed `datapack_id` to
  `conversation_add_message` → server `not_found`; drivers never checked the
  return value, so 6 trace calls failed silently across both relay runs.
  Fixed: `trace()` no longer passes `datapack_id` (probe-verified: accepted,
  visible in `conversation_get` after ~1 min async indexing). Trace texts in
  the comparison are reconstructions from source + run log (exact strings).
- `context_search` responses carry a `token_savings` field (`total_tokens:
  10000` on the probe) — definition unverified, NOT used as evidence.

## Phase 4 — Demo link + presentation + video (PART 1 DONE, repo + demo LIVE 2026-11-25 11:23)

- [x] Presentation: `presentation.md` (+ rendered `docs/presentation.html`):
  problem → Meko usage → relay → measured comparison (honest headline) →
  audit view → gate. Every number traces to `runs/`.
- [x] Video script: `video-script.md` (~680 words, ~4:30 read aloud, token
  counter visible from 2:30). Script only — no recording in this phase.
- [x] Static demo site in `docs/` (`scripts/render_site.py`): landing
  (`index.html`), audit view, comparison, presentation, run logs + `.nojekyll`.
  Verified locally (tables render, 1000/830 present).
- [x] Public repo `contextcon-shared-memory-workbench` — **LIVE 2026-11-25
  11:19:** the connector's `create_repository` → 403 (GitHub App token
  cannot create user repos), so the empty public repo was created in the
  browser, then the 41-file snapshot was pushed via the connector's
  `push-files` (commit `bb7af0d1ea4eda978812ff4b87bc09c2fe238b50` on `main`,
  after `list_commits` 409 confirmed the repo was empty; sync record
  `contextcon.muse-github-snapshot-sync.json` written). Repo:
  https://github.com/luozhi0129/contextcon-shared-memory-workbench
- [x] Demo link — **LIVE 2026-11-25 11:23:** Pages enabled in the browser
  (source `main` / `docs`); verified with curl — home/audit/comparison all
  HTTP 200, key numbers (1,000 / 830) present. URL:
  https://luozhi0129.github.io/contextcon-shared-memory-workbench/
- [ ] Demo video ≤ 5 min — record only after the repo + demo link are live.

Notes: Meko account UUID redacted from published run artifacts
(`<redacted-account-id>` in PLAN.md, smoke-report.json,
runs/relay-traces-2026-11-25.json). The API key exists only in
`.meko-api-key.json` (gitignored, never in the repo). No Meko quota used
in this phase (0 calls).

## Phase 5 — Submit (by 2027-01-18 01:30 Beijing)

- HackerEarth Submit Now → fill fields → Publish. Editable until deadline;
  re-publish after any fix.
- Before submitting: re-check the official page for the exact deadline,
  the prize split, and the full rules (still unverified).

## Rules for this build

- Free tier only. No card, no paid plan, no second Meko account.
- One datapack, ever. No throwaway datapacks in tests.
- Context searches are a lifetime budget of 1,000 — keep a running count in
  `USAGE.md`; stop and report if the build would burn more than ~100.
- Every number in the presentation/video traces to a run log in this repo.
- Submission goes in the user's name — show him the final package before
  publishing (his call, per the delegation rule).
