# Contract: the standards-deviation ledger

The producer/consumer contract for `docs/STANDARDS-DEVIATIONS.md` (INC-008
FR-8.6; widened by INC-105 FR-105.10). **Producer / single writer:**
`tools/standards_deviations.py` (the agent judge routes a *justified* measured
breach here, and an `accepted` conformance answer as the rule-shaped entry —
seam: `docs/contracts/conformance-envelope.md`). **Consumers:**
`/friday:reconcile`'s cross-check of the `model-autonomous` channel, and the
PM or auditor reading the ledger. The enforcement gate
(`tools/maintainability_gate_check.py`) reads disposition from the judge
ENVELOPE, not from this ledger — it is deliberately not a consumer here. Both
sides cite THIS file; neither invents its own shape.

## Why a dedicated ledger, a sibling of the decision log

A justified breach is frequent (warn-first, on any real codebase) and carries a
different shape from a design decision — location, metric, the measured number,
the declared bar, a justification, a floor flag. Recording it as a decision-log
entry would drown the ~100 load-bearing design decisions that log exists to
protect (D4). So it is its OWN ledger, built from the decision log's proven
machinery — a single writer under an advisory lock, monotonic `SD-NNNN` ids from
the shared substrate counter, two channels, growing-log cap + archive, and a
byte-exact tested empty form — never a channel of `DECISIONS.md`.

**Two clean homes (KH-7, line amended by INC-105 §9 as of 2026-08-02):** an *anchored* breach lands here — measured against a declared bar, or a conformance breach against a written rule the entry quotes; a *taste* departure lands in an ADR (`docs/architecture/decisions/`). The judge routes by kind; the two never cross. Taste stays out of the ledger exactly as INC-008 pinned; the amendment's own reasoning is era-stamped in `docs/increments/INC-105.md` §9, not restated here.

## The shape

```
# Standards Deviations — <project>

<!-- FRIDAY-STANDARDS-DEVIATIONS v1 — append via tools/standards_deviations.py … -->

_No standards deviations recorded yet._            ← the empty form's sentinel

## SD-0001 — <metric> <measured> > <bar> @ <location>
**When:** <ISO-8601Z> · **Channel:** pm-ratified|model-autonomous · **Floor:** none|auth-security|schema-data
- **Justification:** <plain words: why this breach is accepted>
- **Standard:** <the cited coding-standards.md line / §section the judge reasoned against>

## SD-0002 — conformance <check-id> @ <location>
**When:** … · **Channel:** … · **Floor:** …                ← same meta line, same bullets
- **Justification:** <plain words: why this breach is accepted>
- **Standard:** <the written rule the check enforces — quoted, the anchor>
```

- The pinned H1 `# Standards Deviations …` is line 1.
- **The empty form is first-class:** the H1 + marker + the single sentinel
  `_No standards deviations recorded yet._` — never a zero-byte or bare-heading
  file. The first append REPLACES the sentinel; sentinel + entries must never
  coexist. Tested exactly.
- `SD-NNNN` ids are monotonic and unique, allocated under a lock against a
  shared-substrate counter (worktrees isolate the file but share the counter —
  ids never collide).
- **Channel** ∈ `pm-ratified` (the PM ratified the deviation) | `model-autonomous`
  (the judge recorded it; the autonomous ones are cross-checked at reconcile —
  the two-channel discipline).
- **Floor** ∈ `none | auth-security | schema-data`. A breach in an
  `auth-security` / `schema-data` file is recorded one-way regardless of the arm
  state (S-8.3) — the field is the durable evidence of that.
- The title `<metric> <measured> > <bar> @ <location>` parses back to its parts
  (a malformed title is a schema error, never silently kept).
- **The rule-shaped title alternative (INC-105 FR-105.10):** `conformance <check-id> @ <location>` — an `accepted` answer from the conformance envelope landing in this ONE ledger beside the number-shaped entries, because a project's accepted deviations are one question with one answer (INC-105 D8). It parses back to check-id and location under the same malformed-title rule; the `Standard` bullet quotes the written rule, which is what keeps the entry anchored. Producer doors: `append_rule_entry` in the module, `--check` on the CLI. The envelope side of the seam: `docs/contracts/conformance-envelope.md` § The accepted breach and the ledger.
- Growing-log discipline: at the entry cap (default 100) the oldest half MOVES to
  `docs/deviations/archive-NNN.md` — ids preserved, schema-valid; completion is a
  move, not a flag.
