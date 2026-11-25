#!/usr/bin/env python3
"""Minimal MCP client (Streamable HTTP, stdlib only) for Meko.

The server requires Accept: application/json, text/event-stream and keeps the
SSE stream open after answering, so this client reads the stream line by line
and stops after the first JSON-RPC message with the matching id, then closes
the connection. Plain read-to-EOF would hang until timeout.

Usage: python3 meko-client.py <tool> '<json-args>'
Reads the API key from ../.meko-api-key.json (0600).
Endpoint: https://mcp.mekodata.ai/mcp (the cloud.mekodata.ai/mcp URL serves
the web app HTML, not MCP — do not use it).
"""
import base64
import http.client
import json
import os
import ssl
import sys
import urllib.parse

ENDPOINT = "https://mcp.mekodata.ai/mcp"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
READ_TIMEOUT = 30


def _proxy_tunnel():
    """The VM's egress goes through an authenticated HTTP proxy (env).
    Return (proxy_host, proxy_port, proxy_auth_header) or None for direct."""
    raw = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    if not raw:
        return None
    u = urllib.parse.urlparse(raw)
    auth = None
    if u.username:
        auth = "Basic " + base64.b64encode(
            f"{urllib.parse.unquote(u.username)}:{urllib.parse.unquote(u.password or '')}".encode()
        ).decode()
    return (u.hostname, u.port or 3128, auth)


def _connect(target_host):
    """HTTPS connection to target_host, via the egress proxy when set."""
    t = _proxy_tunnel()
    ctx = ssl.create_default_context()
    if t is None:
        return http.client.HTTPSConnection(target_host, 443, timeout=READ_TIMEOUT, context=ctx)
    ph, pp, auth = t
    conn = http.client.HTTPSConnection(ph, pp, timeout=READ_TIMEOUT, context=ctx)
    headers = {"Proxy-Authorization": auth} if auth else {}
    conn.set_tunnel(target_host, 443, headers=headers)
    return conn


def load_key():
    p = os.path.expanduser("~/workspace/makefun/contextcon/.meko-api-key.json")
    return json.load(open(p))["api_key"]


class MCP:
    def __init__(self, key):
        self.key = key
        self.session = None
        self.n = 0

    def _post(self, payload):
        """Send one JSON-RPC message; return its response dict (or None for
        a notification the server answers with 202 and no body)."""
        self.n += 1
        u = urllib.parse.urlparse(ENDPOINT)
        conn = _connect(u.hostname)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer " + self.key,
            "User-Agent": UA,
        }
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        try:
            conn.request("POST", u.path, body=json.dumps(payload), headers=headers)
            resp = conn.getresponse()
            sid = resp.getheader("mcp-session-id") or resp.getheader("Mcp-Session-Id")
            if sid and not self.session:
                self.session = sid
            if resp.status == 202:
                return None
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}: {resp.read(600)!r}")
            want_id = payload.get("id")
            # Read SSE lines until the message with our id arrives.
            buf = b""
            while True:
                line = resp.readline()
                if not line:
                    raise RuntimeError("stream closed before a response arrived")
                if line.startswith(b"data:"):
                    try:
                        msg = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if want_id is None or msg.get("id") == want_id:
                        return msg
                buf += line
                if len(buf) > 2_000_000:
                    raise RuntimeError("response too large")
        finally:
            conn.close()

    def initialize(self):
        res = self._post({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "contextcon-build", "version": "0.1"},
            },
        })
        if res is None or "error" in res:
            raise RuntimeError(f"initialize error: {res}")
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return res["result"].get("serverInfo", {})

    def call(self, name, args):
        res = self._post({
            "jsonrpc": "2.0", "id": 100 + self.n,
            "method": "tools/call",
            "params": {"name": name, "arguments": args},
        })
        if res is None:
            raise RuntimeError(f"tool {name}: no response")
        if "error" in res:
            raise RuntimeError(f"tool {name} error: {res['error']}")
        out = []
        for c in res["result"].get("content", []):
            if c.get("type") == "text":
                out.append(c["text"])
        return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("usage: meko-client.py <tool> '<json-args>'")
        sys.exit(2)
    tool, args = sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    m = MCP(load_key())
    info = m.initialize()
    print("server:", json.dumps(info), file=sys.stderr)
    print(m.call(tool, args))


if __name__ == "__main__":
    main()
