# The increment-discovery slice of a dispatch briefing

The feature lane's own additions to the shared skeleton — nothing here is wanted by any other dispatching lane, which is why it lives in this folder rather than beside the template (INC-208, D-0083's boundary rule; anything a second lane turns out to need moves to the shared home, and a genuine toss-up stays shared).

**Use with the template, never instead of it.** The skeleton, the typed line, and the never-belongs list are single-homed in `${CLAUDE_PLUGIN_ROOT}/docs/dispatch-briefing-template.md`; every plugin-side path named here resolves through the plugin root, because a bare relative path resolves against the PM's own project instead (INC-208 KH-3). This file fills slots 3, 4, 5 and 7 of that skeleton with what increment discovery specifically needs.

## Slot 3 — the read-first list for increment discovery

The helper is grilling about a CHANGE to a system that already exists, so it reads the system before it reads the ask: the source proposal (the ask's body, never a substitute for the grilling), the parent oracle `docs/TECHNICAL_SOW.md` (pointer-only growth under `## Increments`), `docs/DECISIONS.md` for the decisions the change collides with, the synthesized architecture set, the lane surfaces the change touches, and the repo's own id-numbering rule (ids allocate inside the machine's configured range).

## Slot 4 — the output path and its shape

`docs/increments/INC-<nnn>.md`, allocated inside this machine's id range, zero-padded in the filename and unpadded in the dotted requirement ids (`FR-<n>.m` / `AC-<n>.m` / `S-<n>.m`, globally unique — `verify_coverage.py` closes over the TSOW plus every increment). The increment is a SEPARATE oracle document, never an edit to the TSOW body. Its spine carries a `## Non-goals reversed` section, whose empty case is exactly one line saying nothing was reversed, and any out-of-scope list carries the era-stamp wording that dates the stance.

## Slot 5 — the rules that bind an increment-discovery dispatch

The project `CLAUDE.md` reaches zero subagents, so the authoring conventions it owns travel in the briefing itself: prose is one paragraph per line and never hard-wrapped mid-phrase; a derivable figure never appears in prose; a rule with a home is cited rather than restated; contracts are named on both sides of every handoff; a script-checked claim is a typed tag line. The relay protocol binding the grilling dialog is `${CLAUDE_PLUGIN_ROOT}/docs/teammate-contract.md` § Bootstrap Relay Protocol, and the one-way-door rule in that same file governs any collision with a recorded stance.

## Slot 7 — what is not the helper's call

Nothing is codified until the grilling closes and the PM approves the written increment on their own read. The helper never decides the ask, never answers a question on the PM's behalf, and never writes the file before the answers come back. Question batches are self-contained — the PM sees each question card with zero surrounding context, so every question carries its own context inside its text, recommendation first, consequences forward.
