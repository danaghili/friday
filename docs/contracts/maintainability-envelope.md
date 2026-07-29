# Contract: the maintainability envelope

The producer/consumer contract for the agent judge's disposition envelope
(INC-008 FR-8.4 / AC-8.4). **Producer:** the maintainability agent judge
(layer 2) at the harden / close / reconcile run points. **Consumers:**
`tools/maintainability_envelope_check.py` (well-formedness) and the enforcement
hook (layer 3, `hooks/maintainability_gate.py`), which blocks only on an
un-dispositioned finding. Both sides cite THIS file; neither invents its own
shape.

## Why a sibling of the findings brief, not a reuse of it

The findings brief (`docs/contracts/findings-brief.md`) carries a **severity**
axis (act-now / before-growth / track / informational). This envelope carries a
**disposition** axis (justified / unjustified against a declared number) — a
different question. Overloading one grammar with both would make every reader
guess which meaning a field holds. So this is its own contract, built on the
**same structural pattern** and **reusing the tagline grammar** (`tools/taglines.py`,
Pin #1) — a thin sibling that inherits proven machinery, never a parallel
from-scratch mechanism.

## The shape

```
maintainability-envelope: source=harden|close|reconcile count=N armed=true|false

## M-n — <metric> <measured> > <bar> @ <location> (disposition: justified|unjustified)
standard: <the cited written line/§section in coding-standards.md>
reason:   <plain words: the justification (justified) or why it must be fixed (unjustified)>
floor:    none|auth-security|schema-data

## Checked            (REQUIRED when count=0 — the first-class empty case)
<what was measured — non-empty>
```

- The `maintainability-envelope:` tag line is the FIRST non-blank line
  (tag-line grammar, `tools/taglines.py`). `source` ∈ `harden|close|reconcile`;
  `count` states the TRUE number of findings; `armed` ∈ `true|false` (whether the
  project has armed the hard block — warn-first starts `false`).
- `<metric>` is one of the closed maintainability vocabulary
  (`taglines.MAINTAINABILITY_METRICS`). `<measured>` and `<bar>` are the numbers
  the layer-1 measurer produced (`> ` between them is literal — every breach is an
  over-the-ceiling). `<location>` is `path:line:name` (or `path` / `<tree>` for
  file-size / duplication).
- **The disposition is the judge's verdict.** `justified` → the breach is recorded
  as an accountable deviation in `docs/STANDARDS-DEVIATIONS.md`. `unjustified` → it
  must be fixed and re-measured clean (Pin #2 / AC-8.2) or PM-overridden.
- Every finding carries all three fields — `standard` (the written line the judge
  reasoned against — an unanchored verdict is rejected), `reason` (plain words), and
  `floor`. `floor` ∈ `none|auth-security|schema-data`: a breach in an
  `auth-security` / `schema-data` file is **one-way and always-surfaced** even while
  the block is disarmed (S-8.3) — the checker exposes the field so the hook enforces it.
- `count` must be truthful: a header that lies about its own count is refused.
- **A malformed finding is never silently dropped.** Any `## M-…` heading that does
  not fully parse is an error, never tolerated prose — a dropped finding is exactly
  the drift this gate exists to catch.
- Finding numbers are unique.
- **The empty case is first-class:** `count=0` requires a non-empty `## Checked`
  section — "no breaches" only counts when the envelope says what was measured. This
  is the well-formed shape a non-adopter run (no declared bars → no breaches)
  produces, and it is tested.

## Where it lives

One path authority (D-0148): `tools/friday_substrate.py`'s `envelope_path(cwd)`
— the shared `.friday/maintainability-envelope.md`, resolved through the
substrate like every other shared record. The judge never hand-builds this
path: it writes THROUGH the checker (`python3 tools/maintainability_envelope_check.py
--write --root <project dir>`, body on stdin), which validates FIRST and lands
the file only on `valid-pass` — a malformed envelope bounces with its errors and
touches nothing. The enforcement hook reads the same verb. Producer and
consumer meeting at one resolver is the point: two hand-joined copies of the
same string is how they silently split.

## The verdict

The checker prints ONE JSON object on stdout (the FR-61 shape
`hooks/_guard.py` consumes): `{"verdict": "valid-pass"|"valid-fail", "errors": [...],
"count": N, "findings": [...], "summary": "…"}`. A missing/unreadable envelope FILE
is `valid-fail` — the gate fires at consumption time, and consuming an absent
document is the failure.
