# Contract: the intake brief

The producer/consumer contract for intake briefs (TECHNICAL_SOW_REBUILD
US-10: FR-37/FR-38 extended by PM amendment 4; AC-7; FR-64's intake-brief
kind). Producer: `/friday:intake` (the client-work entry door). Consumers:
discovery and the strategist (FR-38 — the brief feeds both directly),
`tools/doc_gate.py --kind intake-brief`, guard #9 at consumption time, and
`/friday:handoff` (the ownership/keys + client-tier rows feed the client handoff
package — `docs/contracts/handoff-package.md`). Both sides cite THIS file;
neither invents its own shape.

## The shape

```
intake-brief: client=<name> date=<ISO8601>

## Formal — for sign-off
goals: <what the client is buying, in their words>
scope: <what is in>
exclusions: <what is out, said out loud>
budget: <the number and its shape>
timeline: <the date that matters and why>
approver: <who signs, by name>
data-sovereignty: <where data lives, what compliance applies>
hosting-sla: <who hosts, who answers when it's down>
payment-ip-exit: <payment terms, who owns the code, what exit looks like>
client-tier: <the right-sized tier — what this client does NOT need>

## Informal — workroom notes
<rapport, preferences, anything the next person should know — non-empty>

## Glossary
- <client term> — <plain words>
(…or, when no client-specific terms arose, exactly this line:)
glossary: none — no client-specific terms arose

## Brownfield — current state & direction   (present for an existing-site engagement; omitted for greenfield)
assessment: <current-state summary — what's there, what's dead, what's worth keeping>
direction: <the chosen shape — re-platform like-for-like / re-platform + tools / rebuild — and why, one line>
keys: <who controls domain, host, DNS, email, analytics, CMS — and any recovery risk>
```

- The `intake-brief:` tag line is the FIRST non-blank line (tag-line
  grammar); `client=` is non-empty, `date=` is ISO-8601.
- **Two halves, separated on purpose (FR-38):** the Formal half is the
  sign-off record; the Informal half is the workroom record. Section
  headings may carry a suffix after the word (`## Formal — for sign-off`),
  but the words `Formal`, `Informal`, `Glossary` open them.
- **The Formal half's ten fields are all load-bearing.** goals / scope /
  exclusions / budget / timeline / approver come from FR-38; the four
  consumer-expected fields — `data-sovereignty` (data sovereignty +
  compliance), `hosting-sla` (hosting + SLA ownership), `payment-ip-exit`
  (payment and IP exit terms), `client-tier` (client-tier right-sizing) —
  join by PM amendment 4 (2026-07-13). Longer prose may follow each typed
  line; the typed line itself must be present and non-empty.
- **The glossary's empty case is first-class (FR-65):** populated with
  `- <term> — <plain words>` entries, or exactly the sentinel above — never
  both, never silently blank. (AC-7's field test expects a populated one;
  the sentinel exists so a jargon-free client can't false-block the gate.)
- The greenfield/brownfield standing claim intake sets (FR-39/FR-66) lives
  in the project's FRIDAY-CLAIMS block, not in this brief — the brief is the
  interview record; the claim is the once-recorded fact experts read.
- **The Brownfield block is first-class OPTIONAL (PM amendment, D-0042):**
  present for an existing-site (brownfield) engagement — `assessment`,
  `direction`, `keys` are each load-bearing when the block is present — and
  omitted entirely for a greenfield one. It carries the interview's brownfield
  *output* (the current-state summary, the chosen direction, the keys/ownership
  picture); the world it reflects is the standing claim above, not repeated
  here. Absent = greenfield, a defined case the gate does not flag.

## Verification

`python3 tools/doc_gate.py --kind intake-brief --file <brief>` prints ONE
typed-verdict JSON object (FR-61 shape, consumed by `hooks/_guard.py`).
A missing/unreadable brief FILE is `valid-fail` — the gate fires at
consumption time. Exit codes: 0 pass · 1 fail · 2 bad invocation.

Tests: `tests/test_doc_gate.py` (valid + glossary empty case + per-field
refusals + header refusals + skeleton integration).
