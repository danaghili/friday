# Contract: the project state record (FRIDAY-STATE + close artifacts)

The single contract for the mid-build state model (A.3, replaces the retired
8-checkpoint lifecycle). Producers: the TSOW-approval moment (`/friday:brainstorm`'s
post-write gate / init Stage 2 — writes `state: tsow-approved`, creating a stub
`CLAUDE.md` holding only this block when none exists yet; D-0105/D-0114),
`/friday:init` (seed), `/friday:build` (transitions), the closer (close),
`/friday:adopt` (pins the PM-confirmed target state at adoption close —
D-0149), `/friday:backfill` (maps the old lifecycle onto this vocabulary at
migration), and `tools/state_record.py` (the dirty bit — § below). Consumers:
`tools/verify_state.py` (K0–K8), `hooks/state_sentinel.py` /
`state_stop_gate.py`, `tools/codex-adapter/`, `/friday:resume`,
`/friday:reconcile`. Both sides cite THIS file.

## FRIDAY-STATE block (in the project CLAUDE.md; typed tag lines)

```
<!-- FRIDAY-STATE:BEGIN -->
state: tsow-approved | substrate-seeded | build-in-progress | post-build-review-recorded | closed
tsow: docs/TECHNICAL_SOW.md
since: <ISO-8601Z of the last transition>
last-verified: <date> (close)          # closed only — PROP-028 dirty bit; the annotation names the writer-moment: (close) = closer, (adopt) = adoption close, bare date = reconcile (D-0141)
record-status: verified | stale        # closed only — PROP-028 dirty bit
reconcile-due: <N>d                    # closed only, OPTIONAL — D-0111 due-signal bar
<!-- FRIDAY-STATE:END -->
```

`reconcile-due:` is the project's own staleness bar for the D-0111 due-signal
(default 30d when absent): at session start on a closed project,
`hooks/due_signal.py` warns — never blocks — when `last-verified:` has aged past
it, and when no handover package exists at `docs/handoff/README.md`. A malformed
bar is surfaced, never silently replaced by the default. Consumer:
`tools/state_advisory_check.py --mode due`.

The state vocabulary is CLOSED (K4) — queue/status state is a known string or
file-presence, never an invented value.

## The PROP-028 dirty bit — who writes it (D-0106)

Mutating a closed record flips `record-status: stale`; only a passing
`/friday:reconcile` run flips it back. That sentence was true as a promise long
before anything performed it: reconcile faithfully cleared a flag nothing set,
so drift after close was invisible. `tools/state_record.py` is the missing half
and the ONE writer of the field. It edits that single line and leaves every
other byte alone — rebuilding the block from parsed fields would reorder it and
rewrite a record the closer's K5 gate, the foundation gate and the build-epoch
resolver all read.

Both directions live in that one file deliberately, so what the bit MEANS cannot
drift between the lane that raises it and the lane that lowers it:

- **Setters — `/friday:feature`, `/friday:patch`, `/friday:bug`** call
  `--mark stale` at their close, because they landed changes on a project whose
  record still claims it was verified. `last-verified:` is deliberately
  untouched: the distance between it and now is the whole signal, and moving it
  here would erase the gap in the act of recording it.
- **Clearer — `/friday:reconcile`, exclusively** calls `--mark verified`, on a
  clean run only. That re-dates `last-verified:` in the same move, because a
  clean reconcile IS a fresh confirmation — including over a record that was
  already `verified`, which would otherwise age forever and read as neglect.
  The rewrite drops the closer's `(close)` annotation on purpose: after a
  reconcile the stamp is a reconcile, not a close (D-0141).

Not-applicable is the ordinary case, not an error. Every lane calls this on
every run, and most projects are mid-build, have no state block, or have no
`CLAUDE.md` at all — each of those is a quiet, successful no-op that exits 0 and
never lazily creates the field. A **closed** record missing the field is the one
refusal: `verify_state`'s K5 already blocks a close without it, so its absence
is a real breach to surface, not this tool's to paper over.

## Where "verified" was verified — the companion stamp

`tools/state_record.py` also writes `<shared .friday>/state-verified.stamp` when
it clears the bit: the commit the record was verified AT. It lives in the
substrate rather than in the block above on purpose — the block is read by the
closer's K5 gate, the foundation gate and the epoch resolver, and adding a field
would be a contract change for all of them.

Best-effort by design. No git, no repo, or an unwritable substrate leaves no
stamp, and marking stale never touches it (the backstop below must keep knowing
where `verified` was). Consumer: `tools/state_advisory_check.py`.

**What the backstop deliberately cannot see (D-0143).** It asks "did anything
other than friday's own record-keeping move since the stamp?", so it ignores
changes to `CLAUDE.md` and to `.friday/`. Without that it would fire the instant
reconcile succeeded — verifying the record rewrites the record — and a warning
that cries wolf on its own success gets ignored. The cost is real and named: a
meaningful edit to `CLAUDE.md` alone (say a FRIDAY-CLAIMS change) will not trip
it. That gap is covered elsewhere — `verify_claims.py` checks those claims
against reality, and reconcile re-runs it — so the miss is bounded rather than
silent. A project closed before the stamp existed has none, and an absent stamp
means silence, never a guessed baseline.

## Lane × state legality (warn-tier advisory — D-0107)

The rules below are the POLICY; `tools/state_advisory_check.py` is only the
mechanism that applies them. Both sides cite this file. Edit the table to change
what friday considers a contradiction — no code change needed.

Every outcome here is a **warning the PM sees, never a block** (D-0107): the old
cost was an invisible contradiction, and the cost of a hard gate would be a
false block, which this house holds to be strictly worse. Two mechanical notes:
"re-seeding" means a write that moves `state:` **backwards** along the vocabulary
order above — there is no skill-entry event to ask which lane is running, so the
action is inferred from the write itself. And an **empty block is valid**: zero
rules, total silence. A rule that does not parse is reported, never dropped.

```
illegal: <action> when <state>[,<state>...] — <why, in words the PM reads>
```

<!-- FRIDAY-LANE-LEGALITY:BEGIN -->
illegal: reseed-state when tsow-approved,substrate-seeded,build-in-progress,post-build-review-recorded,closed — re-seeding a project that is already under way, which would reset the record of work that has really happened
illegal: handoff-package when tsow-approved,substrate-seeded,build-in-progress,post-build-review-recorded — packaging a handover for work that is not finished, so the owner would receive a project the record does not claim is done
<!-- FRIDAY-LANE-LEGALITY:END -->

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
