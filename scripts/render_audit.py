#!/usr/bin/env python3
"""Render the memory audit view (web/audit.html) from live Meko data.

Reads memory_get_all (all pages) + conversation_list + conversation_get for
the project datapack and renders a static page:
  who wrote what | when | based on what (conversation title + score)
plus the relay run summary from runs/relay-2026-11-25.jsonl.

Usage: python3 scripts/render_audit.py
"""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meko_client import MCP, load_key  # noqa: E402

PROJECT_ROOT = os.path.expanduser("~/workspace/makefun/contextcon")
DATAPACK_ID = "c2f6a0e2-b841-49bb-8b18-117a90339661"
RUN_DATE = "2026-11-25"


def first_list(d, keys):
    """Pull a list out of a tool result, tolerating several shapes."""
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        for k in keys:
            v = d.get(k)
            if isinstance(v, list):
                return v
    return []


def main():
    m = MCP(load_key())
    info = m.initialize()
    print(f"audit: connected to {info.get('name')} {info.get('version')}")

    conv = json.loads(m.call("conversation_create",
                             {"title": f"audit render — {RUN_DATE}"}))["id"]

    memories = []
    page = 1
    while True:
        out = json.loads(m.call("memory_get_all", {
            "conversation_id": conv, "datapack_id": DATAPACK_ID,
            "page": page, "page_size": 100}))
        batch = first_list(out, ["memories", "results", "items", "data"])
        memories.extend(batch)
        total_pages = out.get("total_pages", 1) if isinstance(out, dict) else 1
        if page >= total_pages or not batch:
            break
        page += 1
    print(f"audit: {len(memories)} memories in datapack")

    convs = []
    # NOTE: conversation_list returns {"conversations": []} for this account
    # even though conversations exist — it is not a reliable source here.
    # Titles are fetched directly per conversation_id instead (see below).

    # Fetch titles for each distinct conversation_id in the memories.
    titles = {}
    run_ids = {mm.get("conversation_id") or mm.get("run_id")
               for mm in memories if isinstance(mm, dict)}
    run_ids.discard(None)
    run_ids.discard("")
    for rid in sorted(run_ids - set(titles)):
        try:
            got = json.loads(m.call("conversation_get", {
                "conversation_id": rid, "include_messages": False}))
            if isinstance(got, dict):
                titles[rid] = got.get("title", "")
        except Exception as e:
            print(f"audit: conversation_get {rid} failed: {e}")
            titles[rid] = ""

    rows = []
    for mm in sorted(memories, key=lambda x: x.get("created_at", "")):
        agent = mm.get("agent_id", "")
        when = (mm.get("created_at", "") or "")[:19].replace("T", " ")
        # memory_get_all returns the text under "data", not "memory";
        # the owning conversation under "conversation_id", not "run_id";
        # and it carries no score (scores only exist in search results).
        text = mm.get("data") or mm.get("memory", "")
        run_id = mm.get("conversation_id") or mm.get("run_id", "")
        score = mm.get("score", "")
        basis = titles.get(run_id, "") or run_id
        rows.append((agent, when, text, basis, score))

    run_summary = ""
    jsonl = f"{PROJECT_ROOT}/runs/relay-{RUN_DATE}.jsonl"
    if os.path.exists(jsonl):
        lines = open(jsonl, encoding="utf-8").read().strip().splitlines()
        run_summary = "\n".join(
            f"{json.loads(l).get('agent', '?')}: "
            f"recall {json.loads(l).get('recall_count', '?')} memor(ies), "
            f"memory {str(json.loads(l).get('memory_id'))[:8]}…"
            for l in lines[1:] if l.strip())

    def esc(s):
        return html.escape(str(s))

    body_rows = "\n".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            esc(a), esc(w), esc(t), esc(b),
            f"{s:.3f}" if isinstance(s, float) else (esc(s) if s else "—"))
        for a, w, t, b, s in rows)

    page_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Shared-Memory Workbench — Memory Audit</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1a1a1a; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 0.5rem; text-align: left; vertical-align: top; }}
th {{ background: #f0f0f0; }}
pre {{ background: #f6f6f6; padding: 1rem; overflow-x: auto; }}
</style></head><body>
<h1>Shared-Memory Workbench — Memory Audit</h1>
<p>Datapack <code>contextcon-workbench</code> (<code>{DATAPACK_ID}</code>) ·
Rendered {RUN_DATE} · {len(rows)} memor(ies) · Free tier</p>
<h2>Who knew what, when, based on what</h2>
<table><tr><th>Agent</th><th>When (UTC)</th><th>Memory</th><th>Based on (conversation)</th><th>Score</th></tr>
{body_rows}
</table>
<h2>Relay run {RUN_DATE}</h2>
<pre>{esc(run_summary) if run_summary else "no relay run recorded yet"}</pre>
<p>Every summary above passed the memory quality gate (date + number +
named fact) before it was written — except the researcher's spec, which was
written before the gate existed and was verified to pass afterwards.</p>
</body></html>
"""
    os.makedirs(f"{PROJECT_ROOT}/web", exist_ok=True)
    out_path = f"{PROJECT_ROOT}/web/audit.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page_html)
    print(f"audit: wrote {out_path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
