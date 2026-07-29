# friday

**A team of expert assistants for building software with Claude Code.**

You bring an idea — or an existing codebase — and friday interrogates it into a
clear plan you approve, builds it in one focused pass, then independently checks
and documents the result. Every decision that would be expensive to get wrong is
put in front of you *while it's still cheap to change*, and written down, so the
project can always explain itself later.

**→ New here? Read the [full guide](docs/MANUAL.md)** — what every command does
for you, the shape of a project from start to finish, and which door to reach for
when.

## The shape of a project

*Heavy front · light middle · synthesized back.*

1. **Plan it.** `/friday:init` takes stock and runs `/friday:brainstorm`, which
   interrogates your idea into a build-ready plan (the **TSOW**). **You approve
   it — that's the one big gate**, and everything after is measured against it.
2. **Build it.** `/friday:build` builds the whole approved plan in one continuous
   pass, asking you only the costly decisions and recording every decision as it
   goes — so you can walk away while it works.
3. **Check it.** `/friday:harden` independently reviews, tests, and probes the
   result. It *finds* problems; **you** decide what to fix.
4. **Document it.** `/friday:reference` generates the architecture docs from the
   code and checks them against it, so they can never quietly drift.

Later, `/friday:feedback` is the front door for anything you notice, routing to
`/friday:patch`, `/friday:bug`, or `/friday:feature`; `/friday:reconcile`
deep-cleans the records before a release; `/friday:handoff` packages the finished
product for its owner. Inside any project, **`/friday:help` tells you where you
are and what to run next.**

## Commands

<!-- COMMAND-INDEX:BEGIN -->
| Command | What it does |
| --- | --- |
| `/friday:adopt` | bring a codebase that has never known friday under management, honestly |
| `/friday:backfill` | migrate a project built by an older friday onto the current substrate |
| `/friday:brainstorm` | run when the PM has a rough idea to develop into a build-ready spec — the grilling door |
| `/friday:bug` | run when the PM reports something known to be broken — diagnosis first, fix on their word |
| `/friday:build` | run when the PM says build the approved spec — the whole-TSOW free-run, not ad-hoc coding |
| `/friday:design-system` | run when the PM wants the interface settled — once, coherently, before any building |
| `/friday:feature` | run when the PM asks for new scope on a delivered project — a scaled mini one-shot |
| `/friday:feedback` | the free-form front door for anything the PM noticed — understand first, then route |
| `/friday:handoff` | run when a client-ownership handover package is due — written for a non-technical owner |
| `/friday:harden` | run when a completed build needs its independent hardening pass — the one review ceremony |
| `/friday:help` | run when the PM asks what friday can do or where they are — the generated command index |
| `/friday:init` | the discovery front door — profile → TSOW → front-loaded UX → substrate seeding |
| `/friday:intake` | run when client work arrives — capture the client's world before discovery begins |
| `/friday:patch` | run when the PM asks for a genuinely small change — text, copy, a config value, a pin |
| `/friday:profile` | run when the PM wants friday tuned to how they work — the one-time preferences interview |
| `/friday:reconcile` | run before a moment that deserves a clean conscience — the PM asks for a deep clean |
| `/friday:redteam` | run when the PM asks what nobody thought to promise — hunt the unpromised doors |
| `/friday:reference` | run when the docs must be regenerated from the code — structure plus grounded rationale |
| `/friday:research` | run when a flagged question needs evidence — parallel researcher lanes over one question |
| `/friday:resume` | crash reconnaissance against the mid-build state model — reconstruct, then continue |
| `/friday:security` | run when the PM asks whether the promised locks hold — proof or a finding, never a claim |
<!-- COMMAND-INDEX:END -->

Full plain-English descriptions, a glossary, and a "which command when" map:
**[docs/MANUAL.md](docs/MANUAL.md)**.

## Quick start

1. Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, then install:
   `/plugin marketplace add danaghili/friday` → `/plugin install friday@friday`.
2. `/friday:profile` once per person → `/friday:init` → approve the plan →
   `/friday:build` → `/friday:harden` → done.
3. Existing code? `/friday:adopt`. Upgrading an older-friday project?
   `/friday:backfill`.

## Under the hood

friday keeps itself honest by mechanism, not good intentions — it never trusts its
own self-report. Structure is extracted straight from the code; rationale is
grounded in the decision log; the difference between the two is a checked oracle.
Project state is a gated lifecycle (*plan approved → set up → building → reviewed →
closed*) enforced by hooks that fail **open** — a false block is worse than a miss,
so an unsure guard stays out of the way. Crash-resume, cost telemetry, and the
session journal live in the gitignored `.friday/` folder, shared across git
worktrees. Deep dive: **[docs/architecture/](docs/architecture/)**.

## Development

`python3 -m pytest tests/ -q` (the logic core is test-first). Docs regenerate via
`/friday:reference`; the byte-exact contracts cited on both sides of every handoff
live in `docs/contracts/` — never rename them.
