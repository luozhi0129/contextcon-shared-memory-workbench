#!/usr/bin/env python3
"""Run the three-agent relay end to end (researcher -> coder -> reviewer).

Each driver runs as its own subprocess, in order, from the project root.
Stops on the first failure. Writes:
  runs/relay-2026-11-25.jsonl — one JSON object per agent (the RELAY_JSON
    line each driver prints) plus a header line with the run metadata.
  runs/relay-2026-11-25.log   — full stdout of all three drivers.
Usage: python3 scripts/run_relay.py
"""
import json
import os
import subprocess
import sys

PROJECT_ROOT = os.path.expanduser("~/workspace/makefun/contextcon")
RUN_DATE = "2026-11-25"
AGENTS = ["researcher", "coder", "reviewer"]


def main():
    os.makedirs(f"{PROJECT_ROOT}/runs", exist_ok=True)
    log_path = f"{PROJECT_ROOT}/runs/relay-{RUN_DATE}.log"
    jsonl_path = f"{PROJECT_ROOT}/runs/relay-{RUN_DATE}.jsonl"
    summaries = []
    with open(log_path, "w", encoding="utf-8") as log:
        for agent in AGENTS:
            print(f"=== {agent} ===")
            log.write(f"=== {agent} ===\n")
            proc = subprocess.run(
                [sys.executable, f"agents/{agent}.py"],
                cwd=PROJECT_ROOT, capture_output=True, text=True)
            log.write(proc.stdout)
            log.write(proc.stderr)
            print(proc.stdout, end="")
            if proc.stderr.strip():
                print(proc.stderr, end="", file=sys.stderr)
            if proc.returncode != 0:
                print(f"RELAY STOPPED: {agent} exited {proc.returncode}")
                log.write(f"RELAY STOPPED: {agent} exited {proc.returncode}\n")
                sys.exit(1)
            summary = None
            for line in proc.stdout.splitlines():
                if line.startswith("RELAY_JSON "):
                    summary = json.loads(line[len("RELAY_JSON "):])
            if summary is None:
                print(f"RELAY STOPPED: {agent} printed no RELAY_JSON summary")
                sys.exit(1)
            summaries.append(summary)
    with open(jsonl_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"run": "relay", "date": RUN_DATE,
                            "datapack": "contextcon-workbench"}) + "\n")
        for s in summaries:
            f.write(json.dumps(s) + "\n")
    print("RELAY COMPLETE: 3/3 agents, see runs/relay-2026-11-25.jsonl")
    print(json.dumps([{"agent": s["agent"], "memory_id": s.get("memory_id"),
                       "recall_count": s.get("recall_count")} for s in summaries], indent=2))


if __name__ == "__main__":
    main()
