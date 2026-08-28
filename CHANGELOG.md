# Changelog

## 0.7.2 — stack-agnostic guards: the bug close and the committed-test watch stop assuming Python

Two fixes from friday's first TS/Vitest projects, each pinned red-first and
closed through the bug lane.

- **Guard #11 accepts any existing, test-shaped regression test (BUG-010):** the declared path must exist and carry "test" or "spec" in its filename — the project's own convention — replacing the tests/*.py pin that blocked every honest TS/Vitest bug close (D-0185).
- **Guard #7 watches the dotted test-file family (BUG-011):** `*.test.*` / `*.spec.*` in any directory are protected beside tests/*.py, so committed TS/Vitest tests get the same mid-build edit protection as Python ones (D-0186).

## 0.7.1 — the audit batch completes: turned-around questions, counted rules, failure paths, loose deferrals, sensitive data, event-armed staleness

The rest of the external-audit batch, plus the hardening the release's own
reconcile run convicted.

- **The question turns around (INC-104):** every change-lane now asks what depends on the thing being changed, at the stop it already has — consumers enumerated from every source at once with openable evidence, one typed reckoning per consumer with silence removed from the vocabulary, a clearance that names what would prove it wrong and what exercises it or lands as not-proven with the work still landing, the person a first-class source, process-level dependants a named class, a deep-clean catch-up for changes that met no lane, and friday's own record written for real over its own contract set.
- **Declared conventions and baseline invariants get counted, judged and answered (INC-105):** the conformance sweep (checks + baseline + cycle walk), the judge's second worklist with its sibling envelope, and the one deviations ledger widened to rule-shaped acceptances; reports at both run-moments, blocks nowhere
- **What a person sees when it breaks gets a reviewer (INC-106):** the failure-path pass lands in the tester role at both existing review moments — designed states as the post-build oracle (floor where none exist, standard always named), comparable paths compared with variance a finding, inert states judged as the absences they are, read always / drive where safe / not-demonstrated an honest third outcome — riding the findings-brief grammar as its fifth producer, blocking nowhere
- **A committed sentence stops rebinding to its reader (INC-110):** the reader-relative family is banned from one home, the conformance sweep gains a source-reaching invariant with possessive-aware quote guards, nineteen standing sentences are anchored or made operative with the false-as-read set cleared under the recorded §9 amendment, and the rule is the first of the authoring family to reach managed projects — seeded at scaffold, bound at the synthesis contract, and named as structurally out of the document probe's reach
- **Loose deferrals get a route back (INC-107):** the comment-block scan, the in-context reading, the bring-it-back home test, PM-word capture into the parked ledger's new loose-deferral source, and a committed answered set whose flatten-stable identity ends the re-ask; the change-time ask rides build/feature/patch closes; found live on the audited tree including a deferral the external audit missed
- **Sensitive data gets a closed question set and a record something opens (INC-108):** the six-treatment declaration with silence not in the vocabulary, posture answers becoming numbered requirements, the store-enumeration catch-up naming every blind spot, the deep clean's read-back where two project records disagreeing is a quoted no-side finding, and the client handover telling the owner what data they now hold; proven on the audited tree where the consent model that answered collection perfectly had answered storage not at all
- **Time stops being the only proxy for rot (INC-109):** the due greeting gains an event arm counting mutating closes from the project's own committed change trails (first lines only, strictly after the last verification), firing on whichever arm trips first as one message naming a hand-reproducible count with its lane breakdown; a count that cannot be taken is named, never a silent zero — the defect the corrected journal-source design would have shipped, proven dead by the fresh-clone criterion
- **Reconcile hardening:** the conformance sweep skips gitignored and archived trees, four hand-built substrate paths route through the one path owner, and decision capture plus the maintainability gate consume their logic cores across a subprocess boundary instead of importing record owners in-process.

## 0.7.0 — standing care: proposal pipeline, secrets posture, the operations battery, dependency watching, the doc-truth probe

The audit-hardened update: eleven lab increments re-curated through the
standing release recipe — the standing-care line plus the first three builds
of the external-audit batch.

- **Proposal pipeline (INC-202):** the idea ledger becomes a five-stage
  pipeline — fenced live headers over frozen bodies, a mover that is
  both-halves-or-neither, a six-class drift checker blocking at the feature
  close.
- **Prose that can't rot (INC-203):** two authoring rules with one home each
  bound into the synthesis and its contract, the house rules deduplicated to
  single homes, the flagship rot class named for the doc-truth probe.
- **Secrets get a home (INC-204):** the secret-store question asked once at
  setup and recorded as a typed declaration (a decline is an accepted risk
  with the PM's reason), a value-blind posture checker, secret-scan seeds
  (gitleaks CI, trufflehog pinned verified-only).
- **Plans that stay true (INC-205):** the plan-up-front rule binds the build
  lead in its one contract home; the live progress list fires by name in
  build/feature/resume; crash recovery reads the real list or honestly
  rebuilds.
- **Dated stances (INC-206):** launch-era decisions become dated context —
  a collision with a recorded stance is surfaced with the trade-off on the
  table, reversals are recorded, and the close strikes the claim lines a
  reversal invalidates.
- **JS/TS extraction (INC-207):** the architecture extractor learns
  JavaScript/TypeScript — path-identity modules, alias-aware imports with
  named refusals, folder-derived routes; the size rule keeps the oracle
  honest at scale.
- **One briefing home (INC-208):** every dispatching lane composes its spawn
  briefing from one template file and saves it at dispatch; a report-only
  checker names any dropped piece.
- **Compaction guardrail seed (INC-209):** every scaffolded project gets the
  guardrail as a standard seed — the scaffold doctrine owns the values, the
  tool reads them from it, a decline is recorded once and never re-asked.
- **Doc-truth probe for managed projects (INC-101):** four claim classes in
  one portable read-only role, record-set scope derived at run time against
  a per-project size bar, the handover gate refusing an unread record.
- **Operations battery (INC-102):** operational promises get one home and
  real teeth — the battery contract single-homes rows, kinds, and verdict
  grammar; typed verdicts whose drill rows expire against real git history;
  a value-blind job photograph; stranger-proof asks.
- **Dependency watching (INC-103):** watcher coverage counted from the
  project on every run (vendor-declared indicator map, loud in every
  staleness direction), advisory scans pinned to a vetted scanner, a
  standing battery row aging advisories from their own publication dates
  with a no-fix path through the parked ledger, tree-generated watcher +
  report-only scan seeds.
- Code map regenerated (227 modules, 316 edges); 1194 tests green on the
  public tree.

## 0.6.0 — maintainability standards, the sandboxed experiment runner, seam closes

The first post-release update: the two lab lines merged and re-curated
through the standing release recipe.

- **Per-project maintainability standards (INC-8):** a written, per-project
  code-health rubric with stdlib measurers (complexity / size / duplication),
  the maintainability-judge role bounded to the measured breach set, a typed
  envelope + deviations ledger with dangerous-file floors, and a warn-first
  Stop-gate hook.
- **Structural-seam closes (INC-200):** the build→harden→close chain is
  dispatch-live (harden model-invocable, the closer auto-chained off harden's
  approving verdict), `tsow-approved` wired into state, ops and running-cost
  routes made real spawns at their named moments, state advisories and due
  signals, and the experiment request/consent contracts.
- **Sandboxed experiment runner (INC-201):** the runner loses the shell; its
  executor becomes a tool it is granted via the new `friday-experiments` MCP
  server — a four-move closed request grammar, consent records, and an
  end-to-end-tested request→run→report loop.
- Code map regenerated (196 modules, 280 edges); 959 tests green on the
  public tree.

## 0.5.0 — vnext (replace-in-place rebuild)

The ceremony-relocation rebuild: heavy front · light middle · synthesized
back. Built one-shot, foundation-first, by its own recipe (ID-9 self-build).

- **Foundation:** single substrate writer with worktree-shared `.friday/`
  (git common dir — ADR-001); typed tag-line grammar; DECISIONS.md two-channel
  capture (harness-guaranteed pm-ratified asks + self-recorded autonomous
  entries, D-NNNN under an advisory lock, A.2 empty form, PROP-023 archive
  discipline); the single spawn-telemetry primitive (ISSUE-006 fixed) with a
  mechanical coverage check over every command surface.
- **Doc synthesis:** stdlib-ast extractor emitting the A.1 IR + mermaid
  (regenerated, never hand-edited); DECISIONS-grounded arc42 synthesis; the
  extractor-vs-synthesis diff as QA oracle incl. seeded-failure detection and
  the uncaptured-why honesty finding.
- **State model:** K0–K8 project-level lifecycle (replaces the 8-checkpoint
  ceremony) enforced by detector→sentinel→stop-gate hooks with in-hook
  ISSUE-007 identity checks, receipts backstop, and a fail-closed Codex gate.
- **Surface:** 26 commands (6 kept, 20 relocated/retargeted — `wave-review`'s
  hardening machinery lives on as `/friday:harden`; `orchestrate`/`implement`/
  `phase`/`wave-design`/`loop`/`archive` retired with their preserve-worthy
  mechanics relocated); 12 agents (planner, scaffolder, developer-as-standing-
  role, reviewer-strategic retired); friday-docs MCP cargo retargeted to the
  DECISIONS/arc42 substrate (retrieval design unchanged: live-parse,
  exact-match, never RAG — ADR-002).
- Notable one-way doors: D-0002 (0.5.0 replace-in-place), D-0003 (shared
  substrate import over per-hook duplication), D-0004 (decision-log grammar).
- Known deferrals: arc42 sections 02/03/06/07/10–12 await the first real
  deployment history; `/friday:handoff` source-list refresh tracked as an
  `[ACTION]` line; full §14 dogfood at production scale (a small-scale drill
  passed — see docs/reviews/).

## 0.4.0 and earlier

See the v0.4.x history in the predecessor repository (checkpoint-era friday).
