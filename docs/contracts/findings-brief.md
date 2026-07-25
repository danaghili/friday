# Contract: the findings brief

The producer/consumer contract for findings briefs (TECHNICAL_SOW_REBUILD
US-12: FR-63, FR-65; AC-16; the FR-42 proof rule made structural via the §7
pin "PoC-or-informational discipline"; thirteenth session decision).
Producers: harden's find pass, security, redteam, adopt. Consumers:
`tools/findings_brief_check.py`, the document gate (guard #9), harden's fix
loop, PM dispositions. Both sides cite THIS file; neither invents its own
shape.

## The shape

```
findings-brief: source=harden|security|redteam|adopt count=N

## F-n — <title> (severity: act-now|before-growth|track|informational)
evidence: <exact file:line, or a PoC pointer>
explained: <plain words a stranger can act on>
fixed-when: <how we'd know it's fixed>

## Checked
<REQUIRED when count=0 — what was examined, non-empty>
```

- The `findings-brief:` tag line is the FIRST non-blank line (tag-line
  grammar, `tools/taglines.py`).
- `count` states the TRUE number of findings — a header that lies about its
  own count is refused.
- Finding numbers are unique. Any `## F-…` heading that does not fully parse
  is an error, never tolerated prose — a bad heading must not silently drop
  a finding.
- Every finding carries all three fields, non-empty.
- **The PoC cap is structural.** `evidence: none — <reason>` is legal ONLY at
  severity `informational` (every source). A finding that points at nothing
  cannot hold a grade above informational — no PoC, nothing above
  informational (FR-42). The seeded plausible-but-false finding lands as
  informational or is rejected, never graded higher (AC-8 inherits this).
- **The empty case is first-class (FR-65):** `count=0` requires a non-empty
  `## Checked` section — "no findings" only counts when the brief says what
  was examined.

## Verification

`python3 tools/findings_brief_check.py --file <brief>` prints ONE
typed-verdict JSON object (`valid-pass`/`valid-fail` — FR-61 shape, consumed
by `hooks/_guard.py`). A missing/unreadable brief FILE is `valid-fail`: the
gate fires at consumption time, and consuming an absent document is the
failure. Exit codes: 0 pass · 1 fail · 2 bad invocation.

Tests: `tests/test_findings_brief_check.py` (all four sources, the count=0
empty case, seeded-malformed refusals, the PoC cap both ways, skeleton
integration).
