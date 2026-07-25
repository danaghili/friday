---
name: init
description: the discovery front door — profile → TSOW → front-loaded UX → substrate seeding
friday-lane: true
disable-model-invocation: true
---

You are the lead running `/friday:init` — the discovery front door (profile → TSOW → front-loaded UX → substrate), skipping any stage whose output already exists. The bootstrap is **highly interactive**: this is the heavy front that buys walk-away autonomy during `/friday:build`.

**Seam semantics (binding):** a named next command is **invoked by you**, never handed back to the PM to type — *unless a PM gate is explicitly the point of the seam*. In this command there is exactly one such gate: the final hand-off to `/friday:build` (building is the PM's go).

**Every bootstrap spawn** carries the spawn-telemetry stamp (`python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent <name> --phase init:<stage>`), the explicit Read list (project `CLAUDE.md` reaches ZERO subagents), and a plain-Read pointer to `${CLAUDE_PLUGIN_ROOT}/docs/teammate-contract.md` (§ Bootstrap Relay Protocol binds the dialog).

### Stage 0: Detect (idempotent — re-running init must never clobber)

Check in this exact order and report to the PM before proceeding:

```
Bootstrap check:
0. Client intake (./intake-output.md or docs/intake/intake-output.md): [present / missing — client project?]
1. User profile (~/.claude/CLAUDE.md FRIDAY-PROFILE markers): [present / missing]
2. TSOW (docs/TECHNICAL_SOW.md): [present / missing]
3. UX artifacts (docs/design/mockups/handoff.md or docs/design/ux-flows.md): [present / missing / n/a — headless]
4. Substrate (CLAUDE.md with FRIDAY-CLAIMS + FRIDAY-STATE): [configured / missing / placeholder]
5. Build record (docs/DECISIONS.md): [present — a build has run / missing]
6. Git repository: [.git present / missing] · origin remote: [present — {URL} / missing]
7. Existing delivery config (workflows, deploy config): [findings / none]

Proposing to run: {stages} · Skipping: {stages}
```

`AskUserQuestion` to confirm before any spawns. Hard guards:
- FRIDAY-STATE block already present → report the current state and stop (offer `/friday:resume` to pick up, or `/friday:feedback` if something needs rethinking).
- Check 5 `present` → this project has already built; do **NOT** re-run init (it could clobber `CLAUDE.md` and the record) — offer `/friday:backfill` (migrate an old-friday record) or `/friday:feature` (new scope) and stop.
- Existing never-friday code with no TSOW → offer `/friday:adopt`; on confirm, invoke it.

**Stage 0a — client intake:** if `intake-output.md` exists, normalise to `docs/intake/intake-output.md`, surface a one-paragraph summary, `AskUserQuestion` (Carry forward / Amend / Ignore). On Carry, stash the **CLIENT INTAKE BRIEF** and inject it verbatim into the Brainstormer and Strategist spawns. On Amend, record the amendment in `intake-output.md` itself — never a silent rewrite. If missing AND this looks like client work, offer `/friday:intake` first (its decisions can't be retrofitted).

**Stage 0b — per-project profile overrides:** if the FRIDAY-PROFILE exists, one confirm-tap: keep the global **Audience / Learning-Preference / Awareness** values for this project, or override any of the three (the Strategist bakes the confirmed values into project `CLAUDE.md`).

**Stage 0c — git baseline (before any journaled spawn):** missing `.git` → `git init` + initial commit — the `.friday/` substrate is keyed to the git common dir and worktree sharing depends on it. Record the baseline commit hash in the journal (`state-transition` event).

### Stage 1: Profiler (skip if FRIDAY-PROFILE present)

Spawn `friday:bootstrap:friday-profiler`; relay its interview batches (QUESTION_PAYLOAD ↔ ANSWERS). Output: the FRIDAY-PROFILE block in `~/.claude/CLAUDE.md`.

### Stage 2: Brainstormer → the TSOW (skip if docs/TECHNICAL_SOW.md present)

Spawn `friday:bootstrap:friday-brainstormer` (inject the CLIENT INTAKE BRIEF + any `/friday:research` findings). Relay the grilling-protocol dialog faithfully. The hard non-proceed gate, the one-way-door teach-backs, and the post-write second-PM-read are the Brainstormer's own contract — your job is faithful relay, **including having the PM read the actual written file** (not your summary) before accepting DONE.

### Stage 3: Front-loaded UX (skip if artifacts present, or n/a for headless projects)

When the TSOW has a user-facing surface: spawn `friday:roles:friday-ux-designer` — the whole UI is designed once, here, so the one-shot build implements against a settled visual contract. Iterate ≤3 times.

### Stage 4: Substrate seeding (Strategist)

Spawn `friday:bootstrap:friday-strategist` (model: **opus** — writing `CLAUDE.md` is decision-making, not templating). Its spawn message carries the TSOW path + intake brief + Stage-0 check 6/7 findings (so brownfield delivery/VCS state is proposed back, never re-derived) + the explicit Read list. Relay its context-elicitation batch FIRST (what the PM already runs, delivery preference, operational constraints, and — asked once here as a concrete scenario and then read from the record forever — **which single event this project could not tolerate** (data loss, a leak, downtime, a wrong charge…); intake omits this by design (D-0046), so init is its asker — facts only the PM holds), then its stack-confirmation table, exposure/environments/scale beats, and the approval gate — the stack is **grounded in the PM's answers and confirmed with the PM, never decided unilaterally**, and open `verify` rows sequence research before build.

The Strategist writes `CLAUDE.md` with: tech-stack **fitness verdicts** (not a bare list), exposure/deployment profile, environments, scale profile, the reuse catalog, the recorded **intolerable-event** answer from the relay above (the tolerance question the security reviewer and architect read from the record forever, never re-asked), and the typed **FRIDAY-CLAIMS block** (one grep-able line per checkable claim: `stack:` / `non-goal:` / `threshold:` / `world:` / `provenance:` — never `ci-gate:` at bootstrap; the delivery work adds that line when it wires the workflow), plus the **FRIDAY-STATE block**: `state: substrate-seeded` · `tsow: docs/TECHNICAL_SOW.md` · `since: <now>`.

It also seeds the project's native `.claude/` (committed `settings.json` + path-scoped `rules/*.md`) per `docs/contracts/claude-scaffold.md` — the contract owns the seeding rules; init's local part: conflicts with pre-existing `.claude/` content reach the PM through the Strategist's relay, and re-running init never clobbers.

### Stage 5: Mechanical seeding + gate (you)

1. `python3 "${CLAUDE_PLUGIN_ROOT}/tools/decisions_append.py" --init --root . --project <name>` — writes the empty-form decision log AND ensures the `.friday/` gitignore rule (never commit the runtime substrate).
2. `mkdir -p docs/reviews docs/architecture`.
3. **Substrate gate (mandatory, never skipped):** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_state.py" --root . --json` must pass (the K0 gate: TSOW present, FRIDAY-CLAIMS well-formed) — quote the real output. Blocking failure → route to the owning stage (S4 Strategist, S2 Brainstormer) and re-run; never proceed on a broken substrate.
4. Print the summary + the one PM-gated next step: **`/friday:build`**. If the Strategist left research items open, the recommendation is `/friday:research` first, then `/friday:build` — never a bare build past an open risk.

No phase/wave/feature tree is materialized — that ceremony is retired.

### What you DON'T do

- Materialize feature directories, roadmaps, or wave trees (the TSOW is the plan)
- Proceed past a failing K0 gate, or re-init a project with a build record
- Skip the PM's second read of the written TSOW, or decide the stack on the PM's behalf
