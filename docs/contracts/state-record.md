# Contract: the project state record (FRIDAY-STATE + close artifacts)

The single contract for the mid-build state model (A.3, replaces the retired
8-checkpoint lifecycle). Producers: `/friday:init` (seed), `/friday:build`
(transitions), the closer (close). Consumers: `tools/verify_state.py` (K0–K8),
`hooks/state_sentinel.py` / `state_stop_gate.py`, `tools/codex-adapter/`,
`/friday:resume`, `/friday:reconcile`. Both sides cite THIS file.

## FRIDAY-STATE block (in the project CLAUDE.md; typed tag lines)

```
<!-- FRIDAY-STATE:BEGIN -->
state: tsow-approved | substrate-seeded | build-in-progress | post-build-review-recorded | closed
tsow: docs/TECHNICAL_SOW.md
since: <ISO-8601Z of the last transition>
last-verified: <date> (close)          # closed only — PROP-028 dirty bit
record-status: verified | stale        # closed only — PROP-028 dirty bit
<!-- FRIDAY-STATE:END -->
```

The state vocabulary is CLOSED (K4) — queue/status state is a known string or
file-presence, never an invented value. Mutating a closed record flips
`record-status: stale`; only a passing `/friday:reconcile` run flips it back.

## Close artifacts (all under docs/reviews/ — K2/K3/K7 gate on them)

- `post-build-review.md` — FRIDAY-REVIEW envelope: `reviewer:` `iteration:`
  `verdict: approved|approved-with-minors|changes-required`
  `spec-compliance: meets-spec|deviations-noted|not-assessed` + zero or more
  `finding: <🔴|🟡|🟢> <id> <location> — <title>` lines, each bijecting with a
  body heading carrying `{glyph}-{id}`. Zero findings + approving verdict is
  the valid empty case.
- `release-gate.md` — FRIDAY-RELEASE-GATE block: `reviewer: friday-tester` ·
  `suite: pass|fail` · `build: pass|n/a` · `migration: pass|n/a`.
- `coverage.md` — FRIDAY-DISPOSITIONS block: one
  `disposition: <FR|NFR|AC|S>-<n>[.<m>] implemented|deferred — <note>` line per
  requirement ID anchored in the TSOW or in an increment oracle
  (`docs/increments/*.md` — dotted IDs are increment-minted, DF-023);
  deferred requires the note.

## Enforcement shape (the landmine list applies)

detector→sentinel→stop-gate, never a point-in-time check. The SubagentStop
matcher is NOT trusted (ISSUE-007 / #27755): the sentinel self-verifies agent
identity in-hook; a foreign event never arms and never clears; typeless
proceeds ONLY because K-rules are verified precision-first (TEST-07). Claude
hooks fail open; the receipts backstop (`tools/receipt.py`) and the fail-closed
Codex gate are the out-of-band guarantees.
