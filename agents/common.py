#!/usr/bin/env python3
"""Shared relay plumbing for the ContextCon workbench agents.

Every agent driver (researcher / coder / reviewer) uses these helpers so the
relay loop is identical for all three:
  connect -> new conversation -> recall (context_search) -> work ->
  remember (gated memory_add) -> trace (conversation_add_message)

Rules learned from the Phase 1 smoke test (do not re-learn them):
- MCP endpoint is https://mcp.mekodata.ai/mcp; see scripts/meko_client.py.
- Every tool call needs a conversation_id.
- conversation_create / conversation_add_message must NOT pass agent_id:
  the server owns those conversations as 'meko_agent' and rejects a
  mismatched agent_id with agent_id_mismatch. Create without agent_id,
  trace without agent_id.
- memory_add DOES take agent_id (that is how a memory is attributed to a
  role) and returns {"results": [{"id": ...}]} — the id is nested.
- Tool schemas are strict per tool; read them from tools/list first.
"""
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from meko_client import MCP, load_key  # noqa: E402

PROJECT_ROOT = os.path.expanduser("~/workspace/makefun/contextcon")
DATAPACK_ID = "c2f6a0e2-b841-49bb-8b18-117a90339661"
DATAPACK_NAME = "contextcon-workbench"
RUN_DATE = "2026-11-25"  # relay run date, fixed in code for repeatability
GATE_VERSION = "memory-gate/1.0"


def connect():
    m = MCP(load_key())
    info = m.initialize()
    return m, info


def new_conversation(m, title):
    """Create a conversation owned by the server (no agent_id)."""
    out = json.loads(m.call("conversation_create", {"title": title}))
    return out["id"]


def recall(m, conv_id, agent_id, query, limit=5):
    """Zero-briefing recall: what does the datapack know about query?"""
    out = json.loads(m.call("context_search", {
        "query": query, "conversation_id": conv_id,
        "agent_id": agent_id, "datapack_id": DATAPACK_ID, "limit": limit,
    }))
    return out


def remember(m, conv_id, agent_id, text, gate=None):
    """Gate-check then write a dated memory. Returns the memory id.

    gate: optional callable(text) -> (ok, failures, details). The researcher
    runs before the gate exists, so it passes gate=None; the coder and
    reviewer pass the gate they built/verified.
    """
    if gate is not None:
        ok, failures, _details = gate(text)
        if not ok:
            raise RuntimeError(f"memory gate rejected this summary: {failures}: {text[:120]}")
    expires = (date.fromisoformat(RUN_DATE) + timedelta(days=30)).isoformat()
    # metadata must be a STRING (the server rejects a dict); JSON-encode it.
    meta = json.dumps({"gate": GATE_VERSION, "expires_on": expires})
    out = json.loads(m.call("memory_add", {
        "text": text, "conversation_id": conv_id, "agent_id": agent_id,
        "datapack_id": DATAPACK_ID,
        "metadata": meta,
    }))
    results = out.get("results") or []
    return results[0].get("id") if results else None


def trace(m, conv_id, user_turn, agent_reply):
    """Save one exchange to the conversation trace (no agent_id).

    Do NOT pass datapack_id: the conversation is created without one (so it
    lives in the default datapack) and conversation_add_message with a
    datapack_id fails with "not_found". Found in Phase 3 (2026-11-25): the
    relay's trace() calls silently failed this way across both relay runs
    because the drivers never checked the return value. Without datapack_id
    the call returns status "accepted" and the turn appears in
    conversation_get after ~1 min (async indexing).
    """
    return json.loads(m.call("conversation_add_message", {
        "conversation_id": conv_id, "input": user_turn, "output": agent_reply,
    }))


def memory_texts(recall_out):
    """Flatten the memory bucket of a context_search result to plain texts."""
    return [h.get("memory", "") for h in recall_hits(recall_out)]


def recall_hits(recall_out):
    """The memory bucket of a context_search result, as raw hit dicts."""
    res = recall_out.get("results", {}) if isinstance(recall_out, dict) else {}
    hits = res.get("memory", [])
    return [h for h in hits if isinstance(h, dict)]
