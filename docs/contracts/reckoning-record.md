# Contract: the consumer reckoning record (docs/RECKONINGS.md)

The producer/consumer contract for the turned-around question's record (INC-104 FR-104.4, FR-104.5, FR-104.6, FR-104.8; D9). Producer: `tools/reckoning.py` — the record's only writer (the D-0135 pattern), owning `docs/RECKONINGS.md` in the project it runs against. Consumers: the change-lanes that carry the ask (`skills/patch/SKILL.md`, `skills/bug/SKILL.md`, `skills/feature/SKILL.md`), `skills/reconcile/SKILL.md`'s catch-up step, and `tools/reckoning_sweep.py` (reads `has` to find changes carrying no record of having been reconciled). Both sides cite THIS file; neither invents its own shape.

## The word

The per-consumer answer is a **reckoning**. It is deliberately not a *disposition* — that token already carries several unrelated meanings in this tree, and a new one would make every exact-phrase search for any of them return the others (D9, `docs/increments/INC-104.md` §4).

## The answers (closed set — this table is the single home)

| answer | what it says | carries beyond evidence |
|---|---|---|
| `moves-with-change` | the consumer is being changed as part of this work | nothing — the change itself is the answer |
| `cleared` | a claim that the consumer does not need to change | observable + exercised-by, BOTH mandatory |
| `not-proven` | the clearance's observable cannot be exercised from here, or nothing exercises it | observable + because |
| `not-a-consumer` | it appeared in the enumeration and, on inspection, does not depend on the thing | because |

Silence is not in the vocabulary: a consumer enumerated but carrying no reckoning line is an **unanswered finding** in the report layer, distinguishable from every answer above (FR-104.4, AC-104.6).

## The ask (single home — every lane cites this section, none restates it)

The enumerating question — *what else depends on the thing being changed?* — is the mirror of the confining question each lane already declares (*did I stay inside what I declared?*), and the two stay apart by name at every site (D8, KH-5). The ask's body lives here and nowhere else; a lane carries only which stop it rides and its change id.

- **Enumerate from every source at once (FR-104.2):** the mechanical needles via `tools/consumer_scan.py` (what declares itself by citing the changed thing's path; what carries the changed thing's own name), the model's own read on top, and the person's answer. Every candidate carries the source that found it and evidence a reader can open.
- **Process-level dependants are a named class (FR-104.7, D7):** how the system is started, what is scheduled, what supervises it, what a runbook step tells a person to do, what the person does by habit — enumerated beside the code, never left to whoever remembers.
- **The person is asked in one plain sentence a stranger could answer** (INC-102 FR-102.6 governs the phrasing; cited, not restated): state what you believe depends on the change, then ask what you missed, naming the not-code kinds out loud — *"is there anything else that uses this — a scheduled job, a script someone runs by hand, something that happens at reboot or deploy?"*
- **"Nothing that I know of" is an answer**, recorded as exactly that, never merged with the question not reaching them (FR-104.3, AC-104.5).
- **Nothing here blocks anything:** a not-proven or unanswered finding never stops a lane's close — the record is what changes, not the permission (FR-104.6, S-104.1, D4).

## The line shapes

Typed lines under the tag-line grammar (`tools/taglines.py` — its shape and empty-case rule are cited, not restated), inside the record's marker-fenced block:

```
<!-- FRIDAY-RECKONINGS:BEGIN -->
searched: change=<id> <date> declared=<ran|skipped> name-match=<ran|too-common|skipped> reading=<ran|skipped> person=<answered|nothing-known|not-asked> · name: <name> · not-covered: <derived>
reckoning: <answer> <code|process> change=<id> from=<source> <date> what: <consumer> · evidence: <prose>[ · observable: <prose>][ · exercised-by: <ref>][ · because: <reason>]
<!-- FRIDAY-RECKONINGS:END -->
```

A present-but-empty block holds exactly the sentinel `_No reckonings yet._`.

- The class vocabulary is **code** or **process** — the record lists a supervisor or a habit beside the files (FR-104.7).
- The source vocabulary is **declared** (a citation of the changed thing by name), **name-match** (the exact-name search), **reading** (what the model found by reading), **person** (the human's own answer) — every reckoning names the source that produced it and the evidence a reader can open (FR-104.2).
- Free-prose fields may contain ` · ` and marker-like words; the parser peels segments rightmost-first in reverse emission order (the anchor lesson of `docs/contracts/parked-ledger.md`), so the emitted shape always round-trips.
- One `reckoning:` line per (change, consumer) and one `searched:` line per change — latest call wins; history lives in git.

## The clearance rule (AC-104.2 — enforced at the only door)

- `cleared` with no named observable is **refused**, and the refusal says why: a clearance that names nothing that would prove it wrong is the untested sentence this record exists to end (FR-104.5).
- `cleared` whose observable nothing exercises **resolves to `not-proven`** with the fixed reason on the line — reported in the producer's result, never silent. The exerciser is a drill row where the observable belongs to a running system (INC-102's vocabulary, one home — D11), an ordinary committed test where it belongs to code (OQ-104.5: the test is named on the record's `exercised-by`, never discovered by convention).
- `not-proven` is a distinct recorded outcome and the work still lands — the lane closes regardless; the record is what changes, not the permission (FR-104.6, D4).

## The searched line (FR-104.8 — structural, never a caveat sentence)

- `not-covered` is **derived by the producer from the source states on every run**; there is no field through which a caller can write coverage prose, so a completeness claim has nowhere to live (S-104.2). The derivation always carries the exact-name search's honest limit — a dependency on a behaviour that carries no name in it cannot be found by the name search — and grows a clause for each source that did not run, a name too common to search (OQ-104.3), and a person not asked.
- The person states, never merged (AC-104.5): **answered** (a dependant came back — it lands as its own `from=person` reckoning), **nothing-known** ("nothing that I know of" is an answer), **not-asked** (no person answer reached this record — the question was not put, or was put and not engaged).
- A `searched:` line with zero reckonings is a record that the enumeration ran and found nothing — `has` reports it as reconciled, distinct from a change that carries no record at all (FR-104.9 reads exactly this distinction).

## The catch-up sweep (FR-104.9 — the outcome vocabulary's single home)

`tools/reckoning_sweep.py` asks the project's own history which changes landed since the last clean run and names those carrying no record here; it carries the operational copy of this closed outcome set, and a committed test locks the two together. Every outcome is a written fact:

- **findings** — changes since the anchor carrying no record of having been reconciled, each named with its files.
- **nothing-outstanding** — the sweep ran and found nothing, never a sweep that could not look.
- **could-not-anchor** — no `last-verified:` stamp to measure from; the state record has never recorded a clean run.
- **could-not-verify** — git cannot answer here; never folded into nothing-moved (the rule of INC-102 FR-102.4, taken per D-0088).

## Where it lives relative to the lane's trail (OQ-104.1)

A lane's change trail cites its change's reckonings as proof — a `proof:` line quoting the producer's real output — and never copies the lines; two copies would drift (the pointer rule of `docs/contracts/change-trail.md`, which names this seam from its side).

## The growing-log discipline

At more than the producer's `CAP` of typed lines, the producer archives the **oldest whole changes** — each change's `searched:` line and its reckonings together — to `docs/reckonings/archive-NNN.md`, oldest first, until the live record is back under the cap. Whole changes, never split, so `has` stays truthful for any change recent enough for the catch-up sweep to ask about; a change old enough to archive is older than the anchor of any honest clean run.

## The empty case and the record's honesty

- Absent file: the question was never asked here. Empty block (the sentinel above): initialized, nothing reckoned. Both are valid, distinct outcomes, never conflated with each other or with a clean result.
- A malformed line is kept and flagged, never dropped — a vanishing answer is the silent miss this record exists to end.
- The record carries names, never values: evidence is a path and the fact of a match, and nothing quoted into it reproduces a matched line's value-bearing content (S-104.4; the repository-carries-names, store-carries-values invariant is untouched and its single home governs).

## Verification

Tests: `tests/test_reckoning.py` (the vocabulary lock against this file's answers table, all four answers, both halves of the clearance rule, the derived not-covered statement, the person states, `has` both directions, the archival discipline, the empty case, malformed preservation, the anchor rule), `tests/test_consumer_scan.py` (the mechanical needles, value-blindness, the too-common bound, the stated unrunnable sources), `tests/test_reckoning_sweep.py` (the catch-up's outcome vocabulary locked to this file, both directions of AC-104.9, the anchor rules).
