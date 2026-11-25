#!/usr/bin/env python3
"""Minimal Markdown -> HTML (stdlib only) for the ContextCon demo site.

Handles: headings, fenced code blocks, tables, bullet lists, bold, inline
code, links, horizontal rules, paragraphs. Escapes HTML everywhere else.
Usage: python3 render_site.py
Reads runs/token-comparison-2026-11-25.md and presentation.md from the
project root, writes docs/comparison.html and docs/presentation.html.
"""
import html
import os
import re
import shutil

BASE = os.path.expanduser("~/workspace/makefun/contextcon")
DOCS = os.path.join(BASE, "docs")

CSS = """body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 880px;
  padding: 0 1rem; color: #1a1a1a; line-height: 1.55; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: left; vertical-align: top; }
th { background: #f0f0f0; }
code { background: #f6f6f6; padding: 0.15em 0.3em; }
pre { background: #f6f6f6; padding: 1rem; overflow-x: auto; }
pre code { background: none; padding: 0; }
a { color: #0b5fff; }
nav { margin-bottom: 1.5rem; font-size: 0.95rem; }
nav a { margin-right: 1rem; }
"""


def inline(text):
    text = html.escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def is_table_sep(line):
    return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", line)) and "-" in line


def render(md):
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            buf, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>")
            i += 1
            continue
        if line.strip() in ("---", "***"):
            out.append("<hr>")
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and is_table_sep(lines[i + 1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            rows, i = [], i + 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = ["<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in header) + "</tr></thead><tbody>"]
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table>")
            out.append("\n".join(t))
            continue
        if line.strip().startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append("<li>" + inline(lines[i].strip()[2:]) + "</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if line.strip():
            buf = []
            while i < len(lines) and lines[i].strip():
                buf.append(lines[i].strip())
                i += 1
            out.append("<p>" + inline(" ".join(buf)) + "</p>")
            continue
        i += 1
    return "\n".join(out)


def page(title, body, nav=True):
    nav_html = ('<nav><a href="index.html">Home</a>'
                '<a href="audit.html">Audit view</a>'
                '<a href="comparison.html">Token comparison</a>'
                '<a href="presentation.html">Presentation</a>'
                '<a href="https://github.com/luozhi0129/contextcon-shared-memory-workbench">GitHub repo</a></nav>\n'
                if nav else "")
    return ("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">\n"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{html.escape(title)}</title>\n<style>{CSS}</style></head><body>\n"
            f"{nav_html}{body}\n</body></html>\n")


INDEX_BODY = """<h1>Shared-Memory Workbench</h1>
<p>Multi-agent shared-memory workbench — several agents and a user collaborate
on one long task across days with <strong>zero re-briefing</strong>, on Meko
as the context layer. Built for
<a href="https://www.hackerearth.com/community/challenges/hackathon/contextcon-remember-everything/">ContextCon: Remember Everything</a>
(YugabyteDB × HackerEarth).</p>
<h2>The idea in one line</h2>
<p>Every agent writes dated, compressed memory (facts / numbers / dates,
auto-expiring) into one shared Meko datapack and runs <code>context_search</code>
before starting work — so "where did we get to last time" is answered by the
datapack, not by re-pasting context.</p>
<h2>What is here</h2>
<ul>
<li><a href="audit.html">Memory audit view</a> — who knew what, when, based on what (rendered from the live datapack, 2026-11-25).</li>
<li><a href="comparison.html">Token-waste comparison, measured</a> — same relay, recall vs re-paste, exact cl100k_base token counts.</li>
<li><a href="presentation.html">Presentation</a> — problem, Meko usage, relay, measured comparison, gate.</li>
<li><a href="runs/relay-2026-11-25.jsonl">Relay run log (JSONL)</a> · <a href="runs/relay-2026-11-25.log">relay log</a> · <a href="runs/token-comparison-2026-11-25.md">comparison source (Markdown)</a></li>
</ul>
<h2>The honest result</h2>
<p>At toy scale (5 memories, 3 traces) recall costs slightly <em>more</em> than
re-pasting: 1,000 vs 830 tokens (−170, −20.5%). The saving appears as history
grows — the re-paste baseline passes the recall level at ~7 memories
(projection from measured per-unit costs). Every number traces to a run log in
the repo.</p>
<h2>Links</h2>
<ul>
<li>Repo: <a href="https://github.com/luozhi0129/contextcon-shared-memory-workbench">github.com/luozhi0129/contextcon-shared-memory-workbench</a></li>
<li>Meko: one datapack (<code>contextcon-workbench</code>), free tier — 13 context searches of 1,000 lifetime, 2 of 10 datapacks.</li>
</ul>
"""


def main():
    os.makedirs(os.path.join(DOCS, "runs"), exist_ok=True)
    open(os.path.join(DOCS, ".nojekyll"), "w").close()
    # Landing page
    open(os.path.join(DOCS, "index.html"), "w").write(page("Shared-Memory Workbench", INDEX_BODY))
    # Audit view (already HTML, add the site nav + styles)
    audit = open(os.path.join(BASE, "web", "audit.html")).read()
    audit = audit.replace("</head>", '<meta name="viewport" content="width=device-width, initial-scale=1">\n</head>')
    nav = ('<nav style="margin-bottom:1.5rem;font-size:0.95rem">'
           '<a href="index.html">Home</a> · <a href="comparison.html">Token comparison</a> · '
           '<a href="presentation.html">Presentation</a> · '
           '<a href="https://github.com/luozhi0129/contextcon-shared-memory-workbench">GitHub repo</a></nav>\n')
    audit = audit.replace("<body>", "<body>\n" + nav, 1)
    open(os.path.join(DOCS, "audit.html"), "w").write(audit)
    # Comparison + presentation, rendered from Markdown
    for src, dst, title in [
        ("runs/token-comparison-2026-11-25.md", "comparison.html", "Token-waste comparison — measured"),
        ("presentation.md", "presentation.html", "Shared-Memory Workbench — presentation"),
    ]:
        md = open(os.path.join(BASE, src)).read()
        open(os.path.join(DOCS, dst), "w").write(page(title, render(md)))
    # Run logs, served as downloads
    for f in ["relay-2026-11-25.jsonl", "relay-2026-11-25.log",
              "relay-2026-11-25-phase2.jsonl", "relay-2026-11-25-phase2.log",
              "relay-traces-2026-11-25.json", "token-comparison-2026-11-25.md"]:
        src = os.path.join(BASE, "runs", f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(DOCS, "runs", f))
    print("site written to", DOCS)


if __name__ == "__main__":
    main()
