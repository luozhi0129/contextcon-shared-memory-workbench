
## Smoke test 2026-11-25

- datapack_create: 1 (contextcon-workbench, id c2f6a0e2-b841-49bb-8b18-117a90339661)
- memory_add: 3 (deleted after verification)
- context_search: 1, memory_search: 0, conversation turns: 1
- Datapacks used on the account: 2/10 (default + project)
## Relay run 2026-11-25 (Phase 2, runs/relay-2026-11-25.jsonl)

Counts reconstructed from the run logs + probe calls (4 relay attempts:
1 failed on memory_add metadata, 1 on a missing import, 1 on a
dataclass load, 1 complete):
- context_search: 9 total (smoke 1 + relay attempts 8) — budget for this
  build was ~30; lifetime allowance is 1,000.
- memory_add: 7 (smoke 3 + probe 1 + spec 1 + coder result 1 + reviewer
  verdict 1). memory_delete: 4 (smoke 3 + probe 1).
- memory_search: 1 (probe). conversation_add_message: 6 calls, outcome
  NOT verified at the time — see the Phase 3 correction below (the relay's
  trace calls actually failed with not_found; the "accepted: 6" claim in
  the original note was inferred, not checked).
- conversation_create: 16 (smoke 1 + probes 4 + relay attempts 8 + audit 3).
- memory_get_all: 4 (audit renders + probes). conversation_list: 2
  (returns empty for this account — do not rely on it).
  conversation_get: 8 (audit renders + probes).
- Datapacks on the account: 2/10 (default + contextcon-workbench).
  No new datapack was created in Phase 2.
- Relay outcome: 3/3 agents; coder recalled the researcher's spec with
  zero briefing; reviewer recalled coder result + spec with zero briefing;
  11/11 tests pass twice (coder + independent reviewer re-run); 4/4
  adversarial probes correct twice; verdict PASS.
## Token comparison 2026-11-25 (Phase 3, runs/token-comparison-2026-11-25.md)

Fresh relay re-run + measurement. Result: WITH Meko 1,000 tokens vs
WITHOUT (minimal re-paste) 830 tokens — saving −170 (−20.5%) at this scale
(5 memories, 3 traces). Projection from measured per-unit costs: the
re-paste baseline passes the measured recall level at ~7 memories and the
formal recall ceiling (2,037 tokens) at ~13 memories. Full table + method
in the comparison doc; every number traces to runs/relay-2026-11-25.jsonl.
- context_search: 4 (3 fresh relay + 1 conversation-bucket probe).
  Total now 13 — budget for the build was ~30; lifetime allowance 1,000.
- memory_add: 2 (fresh coder result + reviewer verdict; researcher reused
  the spec). Total now 9. memory_delete: 0 in this phase.
- conversation_create: 10 (3 relay + 1 trace fetch + 1 probe + 2 probe
  A/B + 1 search probe + 2 memory census). Total now 26.
- conversation_add_message: 6 calls — 3 relay + 1 probe failed with
  not_found (the datapack_id bug, see below), 1 probe outcome not recorded
  (output truncated), 1 probe accepted (without datapack_id).
- conversation_get: 7 (3 trace fetch + 4 probes/re-gets). Total now 15.
- memory_get_all: 2 pages (datapack census, 5 memories, 455 tokens).
  Total now 6.
- CORRECTION (found in Phase 3): the relay's trace() calls never persisted
  — common.py::trace() passed datapack_id to conversation_add_message,
  which the server rejects with not_found, and the drivers never checked
  the return value. 6 trace calls across the two relay runs failed silently.
  Fixed in this phase: trace() no longer passes datapack_id (verified by
  direct probe: accepted, turn visible in conversation_get after ~1 min
  of async indexing). The Phase 2 note "conversation_add_message
  accepted: 6" above is corrected to "6 calls, outcome not verified".
- Datapacks on the account: still 2/10 (default + contextcon-workbench).
  No new datapack was created in Phase 3.

## Phase 4 part 1 — 2026-11-25 (repo + demo site + presentation)
- Meko calls: 0. No quota used in this phase.
- Repo creation blocked: connector create_repository -> 403 POST /user/repos
  (GitHub App token cannot create user repos). Next step is the parent/browser
  creating the empty public repo, then push-files snapshot + Pages enable.
- Local snapshot ready: git commit 01e646d, 41 files, no secrets
  (API key gitignored; Meko account UUID redacted from published artifacts).
