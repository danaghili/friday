---
name: feature
description: run when the PM asks for new scope on a delivered project — a scaled mini one-shot
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:feature` — offer it before any work: “That's new scope on a delivered project — run `/friday:feature` to take it through discovery and a scaled build?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:feature` — a mini-one-shot against a TSOW slice: incremental growth through the same discovery→build→synthesis recipe, scaled down.

### Phase 1: Increment discovery (the same ceremony as bootstrap, scoped — never skipped)

A new feature is a new requirement entering the system; it gets the same heavy front the project got. **You do not interpret the ask and codify your own understanding** (DF-022 — "almost no back-and-forth" is the recorded failure mode; decide-then-ratify is pretend front-loading). Spawn `friday:bootstrap:friday-brainstormer` (model: **opus** — named explicitly, never inherited), telemetry via the single primitive: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-brainstormer --phase feature:increment-discovery`. Spawn message carries: the PM's ask verbatim, the TSOW path, `docs/DECISIONS.md` + the synthesized architecture set as read-first context (the system exists; it grills about the *change*, not the project), the output path and number — `docs/increments/INC-<nnn>.md`, zero-padded file (`INC-001`), dotted IDs on the unpadded number (`1.m`) — the `friday-docs: available` stamp (or a plain-Read pointer to `${CLAUDE_PLUGIN_ROOT}/docs/teammate-contract.md`; § Bootstrap Relay Protocol binds the dialog), and the explicit Read list (project `CLAUDE.md` reaches ZERO subagents). Relay the grilling dialog faithfully — the non-proceed gate, one-way-door teach-backs, and second-PM-read bind exactly as at bootstrap. **Nothing is codified until the grilling completes.**

The increment oracle is a SEPARATE document (DF-023): `docs/increments/INC-<n>.md`, its own scaled spine — problem/why-now, in/out scope, criticality mark, dotted requirement IDs (`FR-n.m` / `AC-n.m` / `S-n.m`, globally unique; `verify_coverage.py` closes over TSOW + increments), known-hard pins where real. `docs/TECHNICAL_SOW.md` gets exactly ONE appended line under `## Increments`: `- INC-<n> — <title> → docs/increments/INC-<n>.md (approved <date>)` — a pointer, never the spec. The TSOW stays bounded; the body stays the untouched oracle (PROP-060c). The gate is the PM approving the WRITTEN increment file — their own read, not your summary.

### Phase 2: Mini one-shot

Build the slice in this context, under the full `/friday:build` Phase-2 rules (two-channel `DECISIONS.md` capture, floor override, selective TDD on any logic-core the slice adds, hands-on verification). The TSOW is never edited beyond that single pointer line, and the increment file is oracle-frozen once approved — drift goes to `DECISIONS.md`, exactly like the TSOW body. The lightest slice still leaves an audit trail: at minimum its decision entries + journal events — "too small to record" is never a reason for zero record (ISSUE-004's lesson).

### Phase 3: Re-synthesize + close the slice

1. `/friday:reference` — re-extract, re-synthesize the touched sections (regenerate-via-git-diff), diff oracle clean.
2. Coverage: add `disposition:` lines for the increment's IDs inside `docs/reviews/coverage.md`'s FRIDAY-DISPOSITIONS block (only lines inside the block count — `verify_coverage.py` closes over TSOW + increments).
3. **Blast-radius check:** if the slice touched a floor category or a shared primitive, run `/friday:harden` scoped to the increment (post-incremental hardening is exactly what that command retains it for); otherwise the release-gate suite re-run + Layer-1 claim audit suffices.
4. Re-stamp liveness on touched records; commit (never push).
