# Contract: the PARKED ledger (docs/PARKED.md)

The waiting room, made real (D-0108 — task #23). "Good idea, not now" used to
be recorded as rejection, and rejection has no re-presentation path; parking's
entire difference is that it comes back. **Owner of the record:**
`tools/parked.py` — nothing else writes the file (the D-0135 pattern).
**Producers (on the PM's word only):** `/friday:feedback` (outcome `parked`),
`/friday:redteam` (a candidate requirement the PM defers), discovery's conscious
exclusions, the lead's own deferrals, and the deep clean's loose-deferral scan
(a deferral recovered from the project's own code, captured only when the PM
answers it — INC-107 §9, D11; the scan's seam: `docs/contracts/loose-deferral-envelope.md`).
**Consumer:** `/friday:reconcile` §5 —
the roundup lists every live entry, re-presents each for a fresh call (*still
deferred / worth doing now / no longer relevant*), and resolves the ones the PM
moves or kills. Both sides cite THIS file.

## The line (typed tag grammar, one per entry)

```
<!-- FRIDAY-PARKED:BEGIN -->
parked: PARK-001 2026-07-29 from:feedback — <what, PM prose> · revisit-when: <condition>
<!-- FRIDAY-PARKED:END -->
```

- Exactly D-0108's four fields: source, date, what, revisit-when. `revisit-when`
  is REQUIRED — an entry with no revisit condition is the limbo this ledger
  replaces.
- The source vocabulary is CLOSED: `feedback | redteam | discovery | lead | loose-deferral` (the fifth member is INC-107 §9's recorded widening — the set stays closed and an unknown value is still refused).
- `what` is free prose and may contain the grammar's own glyphs; the parser
  anchors on the LAST ` · revisit-when: ` marker, so PM wording cannot shift
  the fields.
- **Empty case:** `_Nothing parked._` on its own line — a written fact,
  distinguishable from a vandalised block, restored when the last entry
  resolves. An absent file is also valid (a project that never parked).
- A malformed line is kept and flagged by the reader, never silently dropped —
  a vanishing entry is a parked idea that will never be re-presented.

## Resolution and the retired numbers

Resolving replaces the line with a tombstone comment
(`<!-- resolved: PARK-NNN <date> by:<who> -->`). Ids are minted as
max-ever-seen + 1 across live lines AND tombstones, so a resolved number is
retired forever — an old conversation's "see PARK-007" can never come to point
at a stranger. The PM's fresh call itself is captured where decisions live
(`DECISIONS.md`, the feedback log); this ledger holds the waiting, not the
verdicts.

## The change-time ask (INC-107 FR-107.9, D3 — the ask's single home; the lanes cite it, never restate it)

The lanes that change things put one question to the PM at their close, riding a close moment that already exists — no new ceremony, the same placement discipline INC-104 D6 used for its sibling ask: **"Did this change leave anything for later — a follow-up we said we'd come back to, a case we consciously skipped?"**
A yes is captured here at that moment, while the person still holds the reasoning: `python3 tools/parked.py append --root . --source lead --what "<the deferral, PM prose>" --revisit-when "<the PM's own condition>"` — source `lead`, because a deferral chosen at a lane's close is a chosen wait made in conversation (the `loose-deferral` source names the other route: a deferral recovered from the project's code by the deep clean's scan, INC-107 §9).
The revisit condition is the person's, never invented — the tool refuses an empty one, and that refusal is the structural guarantee capture can never be automatic (D7, S-107.5).
A no costs one sentence and writes nothing.
The lane set is the PM's own: build, feature and patch (D3).
The deep clean's loose-deferral pass stays the safety net for everything that never came through a lane (D3; seam: `docs/contracts/loose-deferral-envelope.md`).

## What this ledger is NOT

- Not a triage queue: nothing enters without the PM choosing "not now".
- Not a dispositioned-deferral store for findings — harden/security dispositions
  keep their own homes; reconcile's roundup sweeps those separately.
  The carve-out this boundary does NOT cover: a PM-accepted standing risk with a revisit trigger — the advisory row's no-fix acceptance (`docs/contracts/ops-battery.md` § The advisory row's sources) and the failure-path pass's headless not-applicable (`agents/roles/tester.md` § The failure-path pass, INC-106 FR-106.7) — which is an acceptance, not a finding disposition, and lands here through `--source lead` on the PM's word.
- Not friday-dev's idea ledger — that is `proposals/` (PROP-109's era rules).
