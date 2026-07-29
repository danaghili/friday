---
name: research
description: run when a flagged question needs evidence — parallel researcher lanes over one question
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:research` — offer it before any work: “That question needs evidence, not instinct — run `/friday:research` to fan researcher lanes over it?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:research` — a conditional evidence fanout: parallel Researcher lanes over one question, triggered by the TSOW's stack-risk register (or an explicit PM ask).

**Trigger discipline:** this fires when a TSOW stack-risk entry flags a risk as research-mandated, or the PM asks. It is NOT a routine step — an unflagged stack runs without it.

1. Decompose the question into 2–4 genuinely distinct angles (never overlapping lanes).
2. Spawn one Researcher per lane (`friday-researcher`, model: **sonnet** — explicit, never inherited). Telemetry per lane via the single primitive: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-researcher --phase research:<lane>`. Each spawn message carries the question, ITS one angle, the don't-cover list (the other lanes' angles — blindness between lanes is the design), the target context (`--for` a TSOW section or DECISIONS entry), the `friday-docs: available` + `context7: available` stamps (or a plain-Read pointer to `${CLAUDE_PLUGIN_ROOT}/docs/teammate-contract.md`), and an explicit Read list — project CLAUDE.md reaches zero subagents.
3. Synthesize the lane reports yourself: agreements, conflicts (name which lane said what), and a recommendation with confidence. Findings that change a TSOW-adjacent call are surfaced to the PM as a decision-ask and captured in `DECISIONS.md`. **Persist the record:** each lane report and your synthesis lands in `docs/research/<topic>/*.md`, and every file carries the typed `consumer:` tag line naming what consumes it (guard #14 — `python3 "${CLAUDE_PLUGIN_ROOT}/tools/research_orphan_check.py"` valid-fails any research file without one; a report that names no consumer is an orphan by definition).
4. The register entry that triggered the sweep gets its verdict recorded back into the TSOW's stack-risk register table by the PM's approval (the TSOW is the PM's document pre-build; post-approval it is the oracle and findings go to DECISIONS.md instead).

Builder AND tester later receive the same findings as **shared facts, independent verdicts** — a hallucinated expected value is worse than a hallucinated API.
