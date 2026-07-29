# Changelog

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
