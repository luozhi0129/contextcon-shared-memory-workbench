# Video script — Shared-Memory Workbench (≤ 5 minutes)

Target: ~4:30 read aloud (~680 words at ~150 wpm). On-screen cues in [brackets].
Narration is the only audio; the token counter stays visible from 2:30 on.

---

## 0:00–0:25 — The hook

[Screen: a chat window. A fresh agent is asked to continue a task from
yesterday. It replies: "Could you paste the context again?"]

"Every multi-agent project hits this moment. A new agent joins, or yesterday's
agent comes back, and the first thing it needs is the whole story again — the
spec, the results, the conversation. We paste it. Every time. And the longer
the project runs, the more we paste."

## 0:25–0:55 — The idea

[Screen: the workbench diagram — three agents around one datapack.]

"We built a shared-memory workbench on Meko. Every agent writes what it
learned into one shared datapack — dated, compressed, with facts, numbers,
and dates — and the next agent recalls it instead of being re-briefed. No
paste. No re-briefing. The question we asked is not whether that sounds good.
It's whether it actually saves anything. So we measured it."

## 0:55–1:40 — The relay

[Screen: terminal running `python3 scripts/run_relay.py`. Three agent
blocks appear in sequence.]

"Three agents relay one real task: research, implement, and review a memory
quality gate. The researcher writes the spec into the datapack. The coder
starts with nothing — no briefing, just one search — and recalls the spec
verbatim. It implements the gate and eleven tests. Eleven out of eleven pass.
Then the reviewer, also with zero briefing, recalls the coder's result and
the spec, re-runs the whole suite independently, and passes its verdict."

[Screen: audit view — three rows: researcher, coder, reviewer.]

"This is the audit view: who knew what, when, and based on which
conversation. The coder picked up exactly where the researcher stopped."

## 1:40–2:30 — The gate

[Screen: `scripts/memory_gate.py` + a rejected summary flashing red, then
an accepted one in green.]

"Before any of that is written, it has to pass the gate. A summary is not a
memory until it carries a date, a number, and a named fact. No date? Rejected.
No number? Rejected. Vague prose with no checkable fact? Rejected. The gate
runs in code, not in a prompt — eleven unit tests, four adversarial probes,
verified twice."

## 2:30–3:40 — The token counter

[Screen: the comparison table. Token counter visible throughout.]

"Now the measurement. Same relay, two ways, counted exactly in cl100k tokens.
With Meko recall: one thousand tokens. Without it — re-pasting the minimal
context each agent needs: eight hundred and thirty. At this scale, recall
costs slightly MORE. A hundred and seventy tokens more. We are not going to
pretend otherwise."

[Screen: the table highlights the reviewer's duplicate recall.]

"Here is why. At five memories, retrieval is imprecise. The reviewer recalled
the coder's result twice, plus a verdict it did not need. The re-paste
baseline is exactly the texts needed, and nothing else."

[Screen: the projection chart — paste baseline rising, recall flat.]

"But watch how the two costs grow. Re-paste grows with history: every new
memory and every new trace has to be pasted again at the next handoff. Recall
stays bounded by the retrieval limit — five memories, however long the
history is. From the measured per-unit costs, the lines cross at about seven
memories. One more relay iteration. Past thirteen, re-pasting costs more than
even the formal ceiling of recall. The saving is not in one handoff at toy
scale. It is in every handoff after the history grows up."

## 3:40–4:20 — What we learned

[Screen: the two findings, plain text.]

"Measuring found a real bug, too. Our relay's trace turns were never being
saved — a wrong parameter the server rejected, and nobody checked the return
value. Six traces, silently lost, across two runs. We fixed it, and we
corrected the record. And Meko's own token-savings field looked like a
placeholder, so we did not use it as evidence. If a number cannot be traced
to a run log, it does not go in the presentation."

## 4:20–4:30 — Close

[Screen: repo + demo links.]

"Shared-Memory Workbench. Recall wins once history passes seven memories —
and the measurement proves it. Code, run logs, and the demo are linked below.
Built on Meko's free tier: thirteen searches of a thousand, two datapacks
of ten."
