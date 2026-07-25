# Architecture — friday (vnext)

Index of the synthesized set. Structure is extracted deterministically
(`generated/` — regenerate via `/friday:reference`, never hand-edit);
rationale is grounded in `docs/DECISIONS.md`; the extractor-vs-synthesis diff
is the QA oracle.

- `01-introduction-and-goals.md` — purpose + quality goals `[TSOW + code]`
- `04-solution-strategy.md` — the recipe + key mechanism choices `[code + DECISIONS.md]`
- `05-building-blocks.md` — component inventory + diagram `[generated IR; oracle-verified]`
- `08-crosscutting-concepts.md` — the invariants that bind every module `[code]`
- `decisions/` — sparse high-value ADRs, each citing its D-NNNN sources
  (worktree-shared substrate · exact-match retrieval · secrets boundary)
- `generated/` — architecture-ir.json · dependency-graph.md · api-surface.md

Confidence note (honesty over polish): 05 and `generated/` are
code-grounded — reliable by construction. 01/04 are capture-grounded — as
good as `DECISIONS.md` (77 entries, two channels, as-you-go). Where a why
is uncaptured the sections say so rather than inventing one. Sections
02/03/06/07/10-12 of the full arc42 skeleton are deliberately deferred to the
first `/friday:reference` run over a real deployment history — writing them
now would be template-filling, exactly what the grounding discipline forbids.

**Last-verified:** 2026-07-24 (reconcile deep clean, post vnext-adopt-O merge 85df28c) · **Record-status:** verified
