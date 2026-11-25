#!/usr/bin/env python3
"""Phase 1 smoke test for the ContextCon build (Meko).

Flow:
  1. conversation_create (Meko tools require a conversation_id)
  2. datapack_list -> find the default datapack id
  3. datapack_create "contextcon-workbench" (ONE project datapack, ever)
  4. memory_add x3 (one dated fact per agent role, marked SMOKE TEST)
  5. context_search as a FRESH agent (no briefing) -> the facts must come back
  6. conversation_add_message -> one saved exchange
  7. delete the 3 smoke memories (memory_delete_by_id) so the datapack starts clean

Writes a JSON report to ../smoke-report.json and appends quota use to ../USAGE.md.
Stops on the first failure with a clear error — no workarounds.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meko_client import MCP, load_key  # noqa: E402

BASE = os.path.expanduser("~/workspace/makefun/contextcon")
AGENT = "smoke-test"
DATE = "2026-11-25"
report = {"steps": [], "ok": False}


def step(name, fn):
    try:
        out = fn()
        report["steps"].append({"name": name, "ok": True, "out": out})
        print(f"[ok] {name}")
        return out
    except Exception as e:
        report["steps"].append({"name": name, "ok": False, "error": str(e)[:500]})
        print(f"[FAIL] {name}: {e}")
        raise


def main():
    m = MCP(load_key())
    info = m.initialize()
    print("server:", info.get("name"), info.get("version"))
    report["server"] = {"name": info.get("name"), "version": info.get("version")}

    conv = step("conversation_create", lambda: json.loads(m.call(
        "conversation_create",
        {"agent_id": AGENT, "title": "contextcon smoke test " + DATE})))
    conv_id = conv.get("conversation_id") or conv.get("id")
    if not conv_id:
        raise RuntimeError(f"no conversation_id in {conv}")
    report["conversation_id"] = conv_id
    print("conversation_id:", conv_id)

    packs = step("datapack_list", lambda: json.loads(m.call(
        "datapack_list", {"conversation_id": conv_id})))
    report["datapacks"] = packs

    # Find or create the project datapack.
    existing = []
    for key in ("datapacks", "items", "results", "data"):
        if isinstance(packs, dict) and isinstance(packs.get(key), list):
            existing = packs[key]
            break
    names = [d.get("name") for d in existing if isinstance(d, dict)]
    if "contextcon-workbench" in names:
        dp = next(d for d in existing if d.get("name") == "contextcon-workbench")
        print("project datapack already exists, reusing it")
    else:
        dp = step("datapack_create", lambda: json.loads(m.call(
            "datapack_create",
            {"name": "contextcon-workbench", "conversation_id": conv_id})))
    dp_id = dp.get("datapack_id") or dp.get("id") or dp.get("datapack", {}).get("id")
    if not dp_id:
        raise RuntimeError(f"no datapack_id in {dp}")
    report["datapack_id"] = dp_id
    print("datapack_id:", dp_id)

    facts = [
        ("researcher", f"SMOKE TEST {DATE}: researcher found that the bounty pays $10, source is the task page."),
        ("coder", f"SMOKE TEST {DATE}: coder chose Python stdlib only, no new dependencies."),
        ("reviewer", f"SMOKE TEST {DATE}: reviewer requires every number to trace to a run log."),
    ]
    mem_ids = []
    for role, text in facts:
        r = step(f"memory_add[{role}]", lambda t=text: json.loads(m.call(
            "memory_add", {"text": t, "conversation_id": conv_id,
                           "agent_id": role, "datapack_id": dp_id})))
        # memory_add returns {"results": [{"id": ..., "memory": ..., ...}]}
        mid = (r.get("results") or [{}])[0].get("id")
        mem_ids.append(mid)
        print(f"  {role} memory id: {mid}")
    report["memory_ids"] = mem_ids

    # Fresh agent, zero briefing: recall must return the researcher's fact.
    recall = step("context_search[fresh agent]", lambda: json.loads(m.call(
        "context_search",
        {"query": "what did the researcher find about the bounty?",
         "conversation_id": conv_id, "agent_id": "fresh-agent",
         "datapack_id": dp_id, "limit": 5})))
    report["recall"] = recall
    recall_text = json.dumps(recall)
    for needle in ("$10", "stdlib", "run log"):
        assert needle in recall_text, f"recall missing {needle!r}: {recall_text[:400]}"
    print("recall: all three facts found by the fresh agent")

    step("conversation_add_message", lambda: json.loads(m.call(
        "conversation_add_message",
        {"conversation_id": conv_id, "agent_id": AGENT, "datapack_id": dp_id,
         "input": "smoke test exchange, user turn",
         "output": "smoke test exchange, agent reply"})))

    # Clean up: delete the smoke memories so the datapack starts clean.
    for mid in mem_ids:
        if mid:
            step(f"memory_delete[{mid}]", lambda m_id=mid: json.loads(m.call(
                "memory_delete_by_id",
                {"memory_id": m_id, "conversation_id": conv_id,
                 "agent_id": AGENT, "datapack_id": dp_id})))

    report["ok"] = True
    json.dump(report, open(os.path.join(BASE, "smoke-report.json"), "w"), indent=2)
    with open(os.path.join(BASE, "USAGE.md"), "a") as f:
        f.write(f"\n## Smoke test {DATE}\n\n"
                f"- datapack_create: 1 (contextcon-workbench, id {dp_id})\n"
                f"- memory_add: 3 (deleted after verification)\n"
                f"- context_search: 1, memory_search: 0, conversation turns: 1\n"
                f"- Datapacks used on the account: 2/10 (default + project)\n")
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
