# Contract: the conformance sweep and its envelope (docs/standards + .friday/conformance-envelope.md)

The producer/consumer contract for the conformance capability (INC-105 FR-105.2, FR-105.5, FR-105.7, FR-105.8, FR-105.9; D8, D9, D11). Producers: `tools/conformance_checks.py` (the written-check block's owner), `tools/conformance_sweep.py` (layer 1 — counts, never judges), `tools/import_cycles.py` (the graph tier), and the maintainability judge (layer 2 — `agents/roles/maintainability-judge.md` § The second worklist — conformance findings) writing the envelope through `tools/conformance_envelope_check.py`. Consumers: the hardening pass and the deep clean (`skills/harden/SKILL.md`, `skills/reconcile/SKILL.md`); the tester's failure-path pass, which contributes its countable checks to the written-check block and runs them from it itself where no sweep-carrying moment fires (`agents/roles/tester.md` § The failure-path pass — INC-106 D2, FR-106.6); and the deviations ledger for accepted breaches (`docs/contracts/standards-deviation.md` — the rule-shaped entry). Both sides cite THIS file; neither invents its own shape. **The enforcement gate (`hooks/maintainability_gate.py`) is deliberately NOT a consumer — it never reads this envelope, which is what makes the never-block ruling structural rather than promised (D6, D8, AC-105.8).**

## Why a sibling of the maintainability envelope, not a reuse of it

The existing envelope types every finding as a measured number exceeding a declared ceiling over a closed metric vocabulary, and its consumer is a gate that matches breaches numerically; a conformance breach has no number, and entering it there would change what the armed gate blocks on. The sibling reasoning of `docs/contracts/maintainability-envelope.md` § Why a sibling applies again unchanged and is cited, not restated: same structural pattern, same tag-line grammar (`tools/taglines.py`), its own contract.

## The check grammar (FR-105.2 — the single home; OQ-105.1)

A written check is one typed line in the `FRIDAY-CONFORMANCE` block beside the project's measured bars (`docs/standards/coding-standards.md`), owned by `tools/conformance_checks.py`, readable and editable by a person (D1):

```
conformance: <id> <kind> · rule: <prose> · from: <path>[ · anchor: <exact phrase>][ · scope: <globs>][ · pattern: <regex>][ · except: <globs>]
```

- The kind vocabulary is closed — exact search or a graph walk, never a similarity judgement (OQ-105.1): **forbid** (every match of `pattern` is a finding), **require** (every `scope` file lacking `pattern` is a finding; scope and pattern both mandatory), **cycle** (`tools/import_cycles.py` over the extracted graph; no pattern, scope or except), **unchecked** (found-not-checked persisting as a first-class line — a rule harvested with no check can never be absent from a report, FR-105.3).
- Segments are emitted in the fixed order shown and peeled rightmost-first (the anchor lesson of `docs/contracts/parked-ledger.md`); a hand-written line out of order surfaces as could-not-run with its reason, never as a silently different check.
- `anchor` is the exact phrase from the `from` document that keeps the check honest: the check is **orphaned** when the document is gone or the phrase left it (FR-105.3's mirror), with the block's own lines cut from the search so a check living in the standards file cannot self-satisfy.
- Every check carries an eight-hex content fingerprint derived from its normalized line, and the report shows it — which version of a check ran is always answerable (AC-105.6, KH-4).
- **Exceptions are pattern-shaped and single-homed here (FR-105.9, S-105.5):** comma-separated globs on the check line. A glob whose basename is empty, `*` or `**` excludes a whole directory tree — the audit's own carve-out disease — and is **refused by name** with the check still running minus it. An exception a project declares inside a source file is **refused by name**: a line carrying the literal token `conformance-except` still counts as a finding and the report names the refusal, because scattering exceptions across the tree is itself the disease this grammar exists to end (FB-06's resolved residue).

## The baseline line grammar (FR-105.4 — the invariants nobody writes down)

friday's shipped catalog is `docs/conformance-baseline.md` (the plugin's own file, never the project's), a `FRIDAY-BASELINE` block of typed lines:

```
baseline: <id> <forbid|require|cycle> · rule: <prose> · when: <condition> · provenance: <mark>[ · scope: <globs>][ · pattern: <regex>]
```

- `when` is D5's switch-on condition, a closed mechanical vocabulary: **always**, **exists: <globs>** (a file of this shape is in the tree), **found: <regex>** (a line of this shape is in the tree). Exact, never a similarity judgement. An invariant whose condition does not hold is **switched-off-here** — named in the report every run, never presented as something to decline, and not by itself a stain on the verdict (correct non-engagement is not a silence about something owed).
- `provenance` is D4's honest tail and begins with **scarred** (an em-dash and the named finding behind it) or **unscarred** (plausible, no finding behind it — the mark that makes the fuller-list ruling's noise question answerable later from data, KH-6).
- Declining an invariant that does apply lands as an accepted risk with its reason in the deviations ledger under the existing aging — the same decline shape as the secret-store declaration, cited rather than restated (D3).

## The sweep report (FR-105.5, FR-105.8 — the three silences named)

`tools/conformance_sweep.py --root . --json` emits one report: every finding carries the check id, its rule, the source that produced it (`declared` or `baseline`, with the baseline's provenance mark riding along), and **path plus line number only — never the matched line's content (S-105.4, KH-5)**. Beside the findings, every state that is not a finding is named as itself and never absorbed into a clean line (S-105.2, KH-2): **clean checks** (ran and found nothing — a distinct outcome, with what was checked counted), **found-not-checked**, **switched-off-here** (with its condition), **out-of-reach** (a cycle check with no extracted graph — the reach is INC-207 D1's, cited), **could-not-run** (a malformed or invalid line, WITH its reason), **orphaned** (still run, and named), **refused excepts**, and **unread** files. The verdict is `clean` only when there are no findings and no dirtying silences; the sweep exits 0 whatever it finds (S-105.1).

## The two run-moments (FR-105.11, D7 — the ride rules' single home)

Both consuming lanes cite this section and restate nothing of it.

- The lane runs `tools/conformance_sweep.py --root . --json` mechanically at the hardening pass and at the deep clean, **before** spawning the maintainability judge, so the findings ride the judge's existing spawn **in the same spawn message** as its second worklist — neither moment grows a new ceremony.
- Every non-finding state in the report (the full set is § The sweep report above) is surfaced to the PM as itself, never absorbed into a clean line.
- A bars-less project has no judge spawn to ride: the sweep still runs and its report is surfaced with findings named un-judged — a named absence, never silence.
- Only the deep clean carries the harvest (D7); its corpus, bound and output rules are the reconcile lane's brief (`skills/reconcile/conformance-harvest.md`), lane-homed per D-0083.
- Outside these two moments there is exactly one other runner of the written checks: the tester's failure-path pass, where no sweep-carrying moment fired (the feature slice close, its stand-alone dispatch, an adopted tree no lane moment has reached) — it runs them itself from the block and folds what returns into its brief; no judge and no envelope ride that run, and where the sweep DID run it never re-runs them (`agents/roles/tester.md` § The failure-path pass — INC-106 D2, FR-106.6).
- Nothing at either moment blocks — the consumer note at the top of this file is the never-block ruling's single statement.

## The envelope (FR-105.7 — the judge's written answers)

```
conformance-envelope: source=harden|reconcile count=N

## C-n — <check-id> @ <location> (answer: breach|not-a-breach|accepted)
rule:   <the written rule the judge reasoned against — quoted, the anchor>
from:   <where the rule is written>
reason: <plain words>

## Checked            (REQUIRED when count=0 — the first-class empty case)
<what was swept — non-empty>
```

- The `conformance-envelope:` tag line is the FIRST non-blank line; `source` names the run moment; `count` states the true number of answered findings and a header that lies about it is refused. **There is no `armed` field by design** — this envelope cannot express a block.
- The answer vocabulary is closed: **breach** (the code violates the written rule — it becomes ordinary work under a lane, never a stopped close), **not-a-breach** (the census member does not violate the rule on inspection — the precision work KH-1 makes the whole increment), **accepted** (the project keeps the breach — recorded in the deviations ledger as a rule-shaped entry, FR-105.10).
- Every answer carries `rule:` and `from:` — the judge's iron rule holds here exactly as on the measured worklist: an unanchored verdict is rejected. The line moved by INC-105 §9 is *measured-versus-taste* to *anchored-versus-taste*; taste stays out.
- A malformed `## C-…` heading is an error, never tolerated prose; finding numbers are unique; `count=0` requires a non-empty `## Checked` section.

## Where the envelope lives

One path authority (the D-0148 pattern): `tools/friday_substrate.py`'s `conformance_envelope_path(cwd)` — the shared `.friday/conformance-envelope.md`. The judge never hand-builds the path: it writes THROUGH the checker (`python3 tools/conformance_envelope_check.py --write --root <project dir>`, body on stdin), which validates FIRST and lands the file only on `valid-pass` — a malformed envelope bounces with its errors and touches nothing.

## The accepted breach and the ledger

An `accepted` answer lands in `docs/STANDARDS-DEVIATIONS.md` through `tools/standards_deviations.py` as a rule-shaped entry — title `conformance <check-id> @ <location>` — beside the number-shaped entries, one list (D8: a project's accepted deviations are one question with one answer). The entry grammar, its parse-back rule, the unchanged empty form and the archive discipline live at `docs/contracts/standards-deviation.md`, amended on both sides of this seam.

## Verification

Tests: `tests/test_conformance_checks.py` (the grammar, all kinds, territory refusal, fingerprints, orphan both directions, the empty case), `tests/test_conformance_sweep.py` (full recall, value-blindness over a planted value, the three silences, unreadable-as-unread, orphaned-still-runs, verdict honesty), `tests/test_import_cycles.py` (cycles found, deferred-as-evidence both directions, out-of-reach and empty distinct), `tests/test_conformance_envelope_check.py` (the envelope's shape, the closed answer set, the lying count, the empty case, the write-through door), `tests/test_standards_deviations.py` (the rule-shaped entry beside the number-shaped one, titles parsing back, the empty form byte-identical).
