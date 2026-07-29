---
name: brainstorm
description: run when the PM has a rough idea to develop into a build-ready spec — the grilling door
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:brainstorm` — offer it before any work: “This sounds like an idea worth developing into a spec — run `/friday:brainstorm` to grill it into a build-ready TSOW?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:brainstorm` — heavy-front discovery: interrogate the PM's idea via the grilling protocol and author the TSOW (the crown jewel).

Spawn the Brainstormer (`friday-brainstormer`, model: **opus** — decision-density → expensive role; name the model explicitly, never inherit) and relay between it and the PM. Its spawn message carries the `friday-docs: available` stamp (or a plain-Read pointer to `${CLAUDE_PLUGIN_ROOT}/docs/teammate-contract.md`; § Bootstrap Relay Protocol binds the dialog) and the explicit Read list (project `CLAUDE.md` reaches ZERO subagents). Emit telemetry at dispatch/first-response/completion via the single primitive: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-brainstormer --phase brainstorm:discovery`.

### The grilling protocol (binding on the Brainstormer)

- **Dependency-ordered design tree:** questions proceed root-first (what/why → shape → stack → risks); never ask a leaf before its parent is settled.
- **One question at a time, with a recommended answer** and its real-world consequence (consequence-forward phrasing: "if two people edit at once, the second one's changes silently win" — never bare jargon).
- **Look-up-before-ask:** anything answerable from the repo, the profile, or a quick web check is looked up, never asked.
- **Hard non-proceed gate:** no TSOW is written until the PM explicitly approves the shape.

### The TSOW must carry (to-spec completeness + lever-2 additions)

1. Problem, bet, and posture; **Out of Scope** (explicit — a one-shot reintroduces anything unstated).
2. Numbered user stories with the **FR-n / NFR-n / AC-n / S-n requirement-ID spine** (IDs stable for the build's lifetime; the tester/reviewer inherit them; `S-n` owned by the architect hat).
3. **Criticality marking:** the make-or-break primitive (built first, to destruction, hard-gated) vs the build-to-adequate secondary surface. Mis-allocation, not incapacity, is the failure mode this prevents.
4. **Known-hard pins with mandated verification** — compound cases spelled out, real verification named.
5. **Dependency / foundation ordering** and the one-shot-vs-units scope call.
6. **Stack-risk register** — flagged risks trigger a conditional `/friday:research` fanout; builder AND tester later get it as shared facts, independent verdicts.
7. Logic-core list for selective TDD.

Every PM-facing artifact is calibrated to the PM's Audience / Learning-Preference / Awareness profile (`~/.claude/CLAUDE.md` FRIDAY-PROFILE block) — **scoped to prose register only (DF-014):** profile and user-level tone/style instructions shape how dialog and explanatory prose read; they never remove, rename, or thin the checklist items above. The structural spine is a contract, not a style choice — if tone preferences and the template conflict, the template wins and the prose bends.

### Post-write gate

A self-QA pass against this checklist, then a **second PM read of the actual written file** — never report done off approved-content-plus-a-blind-write. On the PM's acceptance, stamp the approval into the state record: write the FRIDAY-STATE block — `state: tsow-approved` · `tsow: docs/TECHNICAL_SOW.md` · `since: <now>` — creating a stub `CLAUDE.md` holding only that block if none exists yet (contract: `docs/contracts/state-record.md`, D-0105; a crash between this approval and substrate seeding is now classifiable, and `/friday:resume` routes it back to init). Then route to `/friday:init` (substrate seeding). The TSOW is never rewritten by the build it governs.
