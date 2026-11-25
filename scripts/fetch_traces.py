#!/usr/bin/env python3
"""Fetch the fresh relay run's conversation traces (input/output turns) from
Meko, so the token comparison measures the exact texts as stored in the
datapack. Writes runs/relay-traces-2026-11-25.json.

Reads the conversation ids from runs/relay-2026-11-25.jsonl.
No context_search is used here (conversation_get only).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meko_client import MCP, load_key  # noqa: E402

PROJECT_ROOT = os.path.expanduser("~/workspace/makefun/contextcon")


def main():
    jsonl = f"{PROJECT_ROOT}/runs/relay-2026-11-25.jsonl"
    lines = open(jsonl, encoding="utf-8").read().strip().splitlines()
    agents = [json.loads(l) for l in lines[1:] if l.strip()]

    m = MCP(load_key())
    info = m.initialize()
    print(f"traces: connected to {info.get('name')} {info.get('version')}")

    conv = json.loads(m.call("conversation_create",
                             {"title": "token comparison — trace fetch — 2026-11-25"}))["id"]

    out = {}
    for a in agents:
        cid = a["conversation_id"]
        got = json.loads(m.call("conversation_get", {
            "conversation_id": cid, "include_messages": True}))
        out[a["agent"]] = {
            "conversation_id": cid,
            "title": got.get("title", ""),
            "raw": got,
        }
        print(f"traces: {a['agent']} {cid[:8]}… title={got.get('title', '')!r}")
        print(f"  raw keys: {sorted(got.keys())}")

    with open(f"{PROJECT_ROOT}/runs/relay-traces-2026-11-25.json", "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("traces: wrote runs/relay-traces-2026-11-25.json")


if __name__ == "__main__":
    main()
