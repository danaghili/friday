# The friday recipe — heavy front · light middle · synthesized back

The methodology spine (successor to v0.4.0's workflow.md; the phase/wave/
feature ceremony it described is retired).

## The bet

One unbroken build context keeps cross-cutting concerns coherent; every
handoff seam is where integration failures live. So: invest heavily in
discovery (the TSOW), run the build as ONE free run with as-you-go capture,
keep independence for a single post-build hardening pass, and synthesize the
documentation from the build's own artifacts.

## The loop (make-or-break; built + verified first on any recipe change)

discovery (`/friday:brainstorm` → TSOW → `/friday:init`) → build
(`/friday:build`, two-channel DECISIONS.md capture) → synthesis
(`/friday:reference`: deterministic extractor + DECISIONS-grounded arc42, the
extractor-vs-synthesis **diff is the QA oracle**) → hardening
(`/friday:harden`) → K-gated close.

## Build model (one-shot target; verified-units fallback)

One-shot is the TARGET — the fallback to foundation-ordered units fires ONLY
when the measured TSOW scope verifiably exceeds the ~120k smart zone, never
presumed (the experimental record: every chunked-context build degraded
quality and raised cost). In-flight backstop: approaching the zone forces a
seam at a clean foundation boundary via **`seam-handoff`**
(`tools/seam_handoff.py` — an internal build-model primitive; NOT the
client-facing `/friday:handoff`). Shared primitives + substrate build FIRST,
in one head — a framework's cross-cutting concerns ARE its shared primitives
(the tag-line grammar, the single journal writer, the contract files, the
sentinel shape); ISSUE-006 stayed open in v0.4.0 precisely because journal
instrumentation was retrofitted piecemeal across separate command work.

## Enforcement doctrine (top-level, verbatim)

**Untrusted self-report + mechanical, independently-reproducible
re-verification, with asymmetric tolerance: a false block is worse than a
miss** (precedent: v2's bootstrap-hook false-positive incident). Three
layers: Layer-1 mechanical claim-audit (`git status --porcelain` scoped to
reported paths — never `git diff --stat`, which misses untracked files — plus
re-running stated commands) · Layer-2 fresh-context sonnet-pinned skeptics ·
the receipts backstop (`tools/receipt.py` — hooks fail open, MCP is advisory,
so the durable check is out-of-band: re-run fresh AND match the tree hash).
Every mechanical invariant gets a **detector→sentinel→stop-gate** triple,
never a point-in-time check.

## Landmines (each one has bitten; a rebuild re-breaks them if unnamed)

- SubagentStop matchers can't be trusted to filter by agent type
  (anthropics/claude-code#27755): every SubagentStop hook self-verifies
  identity in-hook; a foreign/typeless event never clears an armed gate.
- Exactly ONE spawn/accept/done telemetry primitive (`tools/spawn_telemetry.py`);
  every spawning surface calls it; `verify_spawn_coverage.py` enforces it.
- One canonical producer/consumer contract file per filesystem handoff
  (`docs/contracts/`), cited by name on both sides.
- friday-docs = live-parse + exact-after-normalization, never embeddings.
- Typed, grep-able tag lines for every script-checked claim; every grammar
  defines + tests its empty case.
- Project CLAUDE.md reaches zero subagents; >~25 KB docs go via get_section.
- Worktrees fragment gitignored state unless every writer resolves `.friday/`
  via `git rev-parse --git-common-dir` — worktrees isolate code, they share
  substrate; never resolve `.friday/` against cwd.
- The plugin manifest + self-hosted marketplace + single version source ARE
  the product surface.
- Growing logs get entry-cap+archive from day one; completion is a move.
- The lightest ceremony tier still keeps a minimal audit artifact — silent
  defection from the system costs more than the ceremony it avoids.
