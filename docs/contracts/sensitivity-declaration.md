# Contract: the sensitivity declaration — the floor, the treatment set, and the record something opens

The producer/consumer contract for INC-108's record of what a project holds: which stores land inside the sensitivity floor, the closed treatment set every such store answers, and the durable declaration the deep clean reads back and the handover carries. **Owner of the record:** `tools/sensitivity_declaration.py` — nothing else writes `docs/SENSITIVITY.md` (the D-0135 pattern). **Producers:** the interrogation's compliance row at initial design, the feature door's discovery when a change introduces a store or widens one, and the deep clean's catch-up for stores that came through neither — each ask riding a stop that already exists (FR-108.6, D3). **Consumers:** the deep clean's read-back (FR-108.7), the client handover's plain-language files (FR-108.11), and the coverage discipline through the requirement ids each line carries. Both sides cite THIS file; no surface restates a treatment (D6).

## The floor (FR-108.1, D2 — a minimum, never a catalogue)

The named classes: **the special categories** (health foremost — the specimen's class), **credentials and keys**, **payment instruments**, and **children's data**. The list is explicitly a floor: a store holding something it does not name is declared with the class the project names for it, receives the full treatment set, and counts exactly as much as a listed member. `unclassified`, `out of scope` and silence are not outcomes (AC-108.5). The mechanical member spellings live in the owning tool's `FLOOR` tuple; this section is the defining statement.

## The treatment set (FR-108.3 — six treatments, each one a sentence; this is the single home)

1. **At rest** — what protects this data where it physically sits, and whether that protection has been verified rather than assumed.
2. **Copies** — every place a copy of this store lands (backups, dumps, exports, logs, analytics, a third party) and how long each of them keeps it.
3. **Deletion** — when the person withdraws consent or asks to be forgotten, which of those copies the deletion actually reaches, and how long any residue lives.
4. **Reach** — which roles, surfaces and people inside the system can read it.
5. **Basis** — the recorded reason this data is held at all.
6. **What the person is told** — whether the project's own statement to the person it is about agrees with the answers to the first three.

The first three are the storage side the evidence says gets missed — the audited project's own GDPR section answers collection completely and storage not at all; the sixth is what makes a contradiction between the project's records detectable at the read-back (FR-108.7). **Every treatment returns an answer or `not-applicable — <reason>`; a blank is a finding on the store, and prose that considers an area without answering its treatment is a blank** (FR-108.2, D1 — the closed set exists because a good open question already failed on the specimen). The answer to a treatment that binds the project to a posture becomes a numbered requirement in the oracle being authored at that moment — the declaration points at the requirement and never replaces it (FR-108.4, D5, KH-2).

## The record (`docs/SENSITIVITY.md` — OQ-108.2's shape)

```
<!-- FRIDAY-SENSITIVITY:BEGIN -->
sensitive-store: <store> · class: <class> · declared: <date> · requirements: FR-n.m,S-n.m|none
<!-- FRIDAY-SENSITIVITY:END -->

<!-- FRIDAY-SENSITIVITY-COPIES:BEGIN -->
copy: <artefact> · lifetime: <how long> · declared: <date>
<!-- FRIDAY-SENSITIVITY-COPIES:END -->

## <store> — treatment answers
<!-- FRIDAY-SENSITIVITY-ANSWERS-<store>:BEGIN -->
at-rest: <answer>        (…one typed line per treatment, all six, house tag-line grammar)
<!-- FRIDAY-SENSITIVITY-ANSWERS-<store>:END -->
```

- **One typed line per store**, carrying store, class, date, and the requirement ids its answers produced; the per-store answers block is the pointer target (FR-108.5). A committed record, deliberately not a claim line: friday's claim lines are checked mechanically against real manifests and a classification is a judgement — the secret-store declaration's own reasoning, followed (D-0167, D4).
- **Store identity is the store's own name** (OQ-108.4): the declaration is a LIVING record — re-declaring a store updates it, a changed answer is the same store with a new date. Deliberately NOT INC-107's append-per-identity scheme: a deferral is an utterance whose edit is a new decision; a store is a thing whose answers evolve. The two quarries do not share the answer, and this sentence is where that was checked.
- **A shared copy is answered once** (FR-108.8, D7, KH-4): project-level copy artefacts and their lifetimes live in the copies block alone; a store's `copies:` answer cites the token `project-copies` (plus any copies specific to itself); a store-level answer naming a project artefact is refused at declare time and convicted by `check` if hand-edited in — two stores behind one dump can never hold two different answers about it.
- **The empty case is dated and reasoned** (D12): `sensitive-stores: none — <reason> · declared: <date>`. An absent record means never-asked and is never clean; the none-line and store lines cannot coexist. A malformed line is kept and flagged, never dropped.

## What this record is NOT

- **Not a compliance verdict** (S-108.5): it says what a store holds, what protects it, how long copies live and what deletion reaches; no output states that a project satisfies or fails a regulation.
- **Not a data reader** (S-108.3, KH-6): the owning tool takes names, shapes and postures as arguments and opens no file but its own record; nothing it writes can carry a stored value — the repository-carries-names, store-carries-values invariant inherited at full strength.
- **Not the project-level at-stake answer** (FR-108.9, D8): the strategist's exposure profile keeps its own name, granularity and job — it calibrates how hard a reviewer looks and never becomes a requirement; neither vocabulary is derived from the other, and no surface here re-asks it.
- **Not a gate** (S-108.1, S-108.4): the pass reports and never blocks, and friday changes no project's storage posture — the remedy for a bad answer is a requirement the PM decides on.
