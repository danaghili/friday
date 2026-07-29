# Contract: the PARKED ledger (docs/PARKED.md)

The waiting room, made real (D-0108 — task #23). "Good idea, not now" used to
be recorded as rejection, and rejection has no re-presentation path; parking's
entire difference is that it comes back. **Owner of the record:**
`tools/parked.py` — nothing else writes the file (the D-0135 pattern).
**Producers (on the PM's word only):** `/friday:feedback` (outcome `parked`),
`/friday:redteam` (a candidate requirement the PM defers), discovery's conscious
exclusions, the lead's own deferrals. **Consumer:** `/friday:reconcile` §5 —
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
- The source vocabulary is CLOSED: `feedback | redteam | discovery | lead`.
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

## What this ledger is NOT

- Not a triage queue: nothing enters without the PM choosing "not now".
- Not a dispositioned-deferral store for findings — harden/security dispositions
  keep their own homes; reconcile's roundup sweeps those separately.
- Not friday-dev's idea ledger — that is `proposals/` (PROP-109's era rules).
