# Contract: the change trail (one shape, three sizes)

The producer/consumer contract for change trails (TECHNICAL_SOW_REBUILD
US-12: FR-62, FR-65; AC-16; §7 pin "Trail grammar at three sizes"; third
session decision). Producers: the bug, patch, and feature lanes — the feature
lane's trail is emitted by spine surfaces under build law; this contract
closes over it without editing any spine surface. Consumers:
`tools/trail_check.py`, guard #6 (lane close without its trail), guard #11
(bug closure), AC-23's trail-closure bar, and the due signal's event-arm
counter (`tools/state_advisory_check.py --mode due`, INC-109), which reads
each trail's first tag line — lane and date only, never the body — to count
mutating closes since the record was last verified (bar and scope:
`docs/contracts/state-record.md`, cited never restated). Both sides cite THIS
file; neither invents its own shape.

## The shape

```
trail: lane=bug|patch|feature id=<token> date=<ISO8601>

## Asked
<what was asked or found — non-empty prose>

## Decisions
- D-NNNN — <title>
(…one bullet per decision made along the way — references into
docs/DECISIONS.md; OR, when no decisions arose, exactly this line:)
decisions: none — change fully specified by the ask

## Proof
proof: <real command output, quoted — at least one line; never empty>

changelog: <one line — exactly one in the document>
```

- The `trail:` tag line is the FIRST non-blank line (tag-line grammar,
  `tools/taglines.py`). `lane` is the closed vocabulary above; `id` is the
  change's own identifier (BUG-NNN, PATCH-NNN, INC-n — whatever the lane
  allocated); `date` is ISO-8601 (date-only or full timestamp).
- The three sections appear once each, in order: Asked → Decisions → Proof.
- **Decisions are POINTERS, never copies.** The entries themselves live in
  `docs/DECISIONS.md` (single writer: `tools/decisions_append.py`); the trail
  cites them as `- D-NNNN — <title>`. Two copies would drift. The empty case
  (`decisions: none — change fully specified by the ask`) is a first-class,
  tested form (FR-65) — the sentinel and references never coexist.
- **Proof has no empty case — proof is the point.** At least one `proof:`
  tag line quoting real output. Prose alone is not proof.
- A change that ran INC-104's enumerating ask quotes its consumer-reckoning output as one of its `proof:` lines — the seam is named from the record's side at `docs/contracts/reckoning-record.md` § Where it lives relative to the lane's trail; the grammar above is unchanged (any real output is already a legal proof line, so `tools/trail_check.py` needs no new rule).
- Exactly one `changelog:` line per trail.
- A doc refresh where behavior changed rides the lane's own close (FR-62);
  it is verified by the doc-truth pass, not by this grammar.

## Verification

`python3 tools/trail_check.py --file <trail> [--decisions-log docs/DECISIONS.md]`
prints ONE typed-verdict JSON object (`valid-pass`/`valid-fail` — FR-61 shape,
consumed by `hooks/_guard.py`). Evidence rules:

- A missing/unreadable trail FILE is `valid-fail` — the absent record is the
  exact failure guard #6 exists to catch.
- With `--decisions-log`: a cited D-NNNN absent from a READABLE, cleanly
  parsing log is a provable lie → `valid-fail`. An unreadable or unparseable
  log degrades to structural-only with a note in the summary — a missing log
  is not a lie (fail-open doctrine).

Tests: `tests/test_trail_check.py` (all three lanes under the one grammar,
the empty-decisions case, seeded-malformed refusals, cross-check both ways,
skeleton integration).
