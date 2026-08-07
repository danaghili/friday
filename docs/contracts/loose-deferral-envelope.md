# Contract: the loose-deferral seam — the envelope and the answered set

The producer/consumer contract for INC-107's two record shapes: the **envelope** a deep-clean run writes to present candidate deferrals, and the **answered set** that makes the PM's answers durable so the next run does not ask again. One seam, one contract (OQ-107.4): the two shapes are written and read by the same machinery at the same run-moment, and a reader following either half needs the other in view.

## Why a sibling of the maintainability envelope, not a reuse of it

The maintainability envelope's contract (`docs/contracts/maintainability-envelope.md`) states why IT is a sibling of the findings brief: that brief carries a *severity* axis, the envelope a *disposition* axis, and overloading one grammar makes every reader guess which meaning a field holds. The same reasoning applies again and produces the same answer (D10). This seam's axis is neither severity nor a disposition against a declared number — it is **whether a decision has a route back**, and the answer comes from the PM rather than from a judge. So: its own contract, built on the same structural pattern, reusing the house tag-line grammar (`tools/taglines.py`), with its own first-class empty case.

## Shape 1 — the envelope (per-run presentation)

**Producer:** the deep clean's loose-deferral pass — the scan (`tools/loose_deferral_scan.py`), the reading, and the home test feed it; the lead writes it THROUGH the checker. **Consumers:** `tools/loose_deferral_envelope_check.py` (well-formedness) and the PM presentation the deep clean builds from it. Machine-local by design: the envelope is the run's report, the answered set below is the durable memory.

```
loose-deferral-envelope: source=deep-clean count=N remainder=R recognized=K unread=U unparsed=P

## LD-n — <file>:<start>-<end> (recommend: capture|dismiss|leave-standing|already-homed)
id:      <the answered-set identity digest — tools/loose_deferrals.py>
text:    <flattened, value-masked block text>
reading: <the in-context read — why this is or is not a real deferral (FR-107.3)>
home:    homed|homeless|unanswerable — <what was read and what it said (FR-107.4)>

## Unreached        (REQUIRED when unread+unparsed > 0)
unread: <path>
unparsed: <path>

## Scanned          (REQUIRED when count=0 — the first-class empty case)
<what was scanned — non-empty>
```

- The `loose-deferral-envelope:` tag line is the FIRST non-blank line. `source` is the closed producer set (today: `deep-clean` alone). `count` states the TRUE number of `## LD-n` candidates — a header that lies about its own count is refused.
- `remainder` is FR-107.7's named number: what the capped run ranked but did not present, carried to the next run, never omitted. `recognized` is FR-107.6's: how many previously-answered candidates the run recognised and passed over. Both ride the tag line so a capped run and a no-re-ask run are honest by construction.
- The reported unit is the comment block (FR-107.2): `<start>-<end>` is the block's line range, and the recommendation names one of the four answers of FR-107.5 in recommend-verb form (`capture | dismiss | leave-standing | already-homed`). The recommendation is the model's; the ANSWER is the PM's (S-107.5) and lands in the answered set, never here.
- Every candidate carries all four fields. `id` is the answered-set identity digest, so the envelope and the durable record name a candidate identically. `text` is the scan's flattened block text with value-shaped tokens withheld (S-107.4). `home` must be one of the three ruled words with its evidence attached — `unanswerable` is FR-107.8's fourth unreached class, named per candidate.
- **The home test itself (FR-107.4 — this is its operative statement; the lanes cite it):** the question is never whether a record is cited but whether the cited record brings the decision back. A record that merely explains the reasoning is not a home — the deferral is `homeless`. A live work item in the project's own plan or tracker is — `homed`, with the item named. A citation that is closed, shipped, or absent is `homeless`, and the dead citation is part of the finding's evidence. Answering costs a read of the project's plan for every candidate that names anything: the accepted cost of D1, taken because the cheap mechanical sort files the flagship specimen with the healthy majority.
- **A malformed candidate is never silently dropped.** Any `## LD-…` heading that does not fully parse is an error (S-107.2) — a dropped candidate is exactly the silent miss this line of work exists to end.
- Candidate numbers are unique.
- **What the scan could not reach is named, line by line** (FR-107.8): declared `unread`/`unparsed` counts must match the `## Unreached` section's typed lines. **The empty case is first-class:** `count=0` requires a non-empty `## Scanned` section — a run that reached nothing must not read the same as a run that found nothing.
- **The presentation cap is the project's own** (FR-107.7, OQ-107.3): the `FRIDAY-LOOSE-DEFERRAL` block beside the other measured bars in `docs/standards/coding-standards.md`, typed line `loose-deferral: presented <= N`, read by `tools/loose_deferrals.py:presented_cap` with the tool-owned default — cited here, never restated.

### Where it lives

One path authority (the D-0148 pattern): `tools/friday_substrate.py`'s `loose_deferral_envelope_path(cwd)`. The producer never hand-builds the path: it writes THROUGH the checker (`python3 tools/loose_deferral_envelope_check.py --write --root <project dir>`, body on stdin), which validates FIRST and lands the file only on `valid-pass` — a malformed envelope bounces with its errors and touches nothing. The checker prints ONE JSON object on stdout (the FR-61 shape): `{"verdict": "valid-pass"|"valid-fail", "errors": [...], ...}`; a missing envelope FILE is `valid-fail` — consuming an absent document is the failure.

## Shape 2 — the answered set (durable, committed)

**Owner of the record:** `tools/loose_deferrals.py` — nothing else writes `docs/LOOSE-DEFERRALS.md` (the D-0135 pattern). **Producers:** the deep clean's presentation moment, recording the PM's answer per candidate — including junk rejections (FR-107.3), because a rejection that is not recorded is a question the next run asks again. **Consumer:** the next run's recognition pass (`recognize`), which splits scan candidates into new versus answered and counts what it passed over. COMMITTED rather than substrate-side because durability across clones is the whole point (OQ-107.4, D-1070): a machine-local answered set re-asks everything on the second clone.

```
<!-- FRIDAY-ANSWERED:BEGIN -->
answered: <id12> <date> captured|dismissed|left-standing|already-homed — <detail> · file: <path>
<!-- FRIDAY-ANSWERED:END -->
```

- **Identity (D9, OQ-107.2, KH-2):** `<id12>` is a digest of the file path plus the block's whitespace-flattened text. A reformat that re-wraps the comment changes nothing flattened — same identity, passed over. An edited comment is a changed decision — new identity, re-presented. A moved file re-presents: the accepted cost, taken over collapsing two identical decisions in different files into one identity.
- **The answer vocabulary is CLOSED** — FR-107.5's four, refused otherwise. `captured` must name its `PARK-` entry in the detail: a capture claim with no ledger id claims a route back that does not exist. The capture itself goes through the parked ledger's own tool under that ledger's contract (`docs/contracts/parked-ledger.md` — the fifth source, FR-107.11), which supplies the grammar, the required revisit condition, and the PM-word rule; none of that is restated here.
- `detail` is free prose and may contain the grammar's own glyphs; the parser anchors on the LAST ` · file: ` marker, so wording cannot shift the fields.
- **Empty case:** `_Nothing answered._` on its own line — a written fact; an absent file is also valid (a project whose deep clean has not run this pass).
- A malformed line is kept and flagged by the reader, never silently dropped.

## What this seam is NOT

- Not a triage queue and not a nag: an answered candidate does not return unless its comment changed (FR-107.6 — the no-nagging ruling, obeyed by mechanism).
- Not a findings brief and not a maintainability envelope: no severity axis, no disposition-against-a-bar axis — those grammars keep their own homes.
- Not a document hunter: no candidate originates in a document (D4, FR-107.12); documents are read only to answer the home question, and that read is named in the candidate's evidence.
