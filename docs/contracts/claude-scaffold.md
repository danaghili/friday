# Contract: the target project's native `.claude/` scaffold

The ownership doctrine for every file friday seeds into a target project's
`.claude/` directory (INC-006, D-0092). Producers: the Strategist at
`/friday:init` Stage 4 (the write side) and the `/friday:adopt` /
`/friday:backfill` doors (the parity side). Consumers: the adopt/backfill
doors as the parity side that enforces never-clobber, plus any future
seeding surface. Both sides cite THIS file; no surface carries its own copy
of these rules (single-homing, D-0083).

## What is seeded (the full seedable set)

| File | Source | Carries |
|---|---|---|
| `.claude/settings.json` | the confirmed stack + friday's project env needs | committed project settings: an `env` block (the home for any project-level env friday introduces — e.g. a compaction override pair) and a `permissions.allow` list derived from the confirmed stack |
| `.claude/rules/*.md` | the confirmed stack + the Profiler's coding preferences — the same sources `docs/standards/*` draws from | path-scoped conventions: each rule carries a `paths:` frontmatter glob and the **actual convention text**, so the harness auto-loads it when Claude reads a matching file |

Nothing else is seeded. `settings.local.json` is the PM's personal file —
friday never writes it.

## Ownership: seeded once, project-owned

Every seeded file is written **once** by the named friday surface and is the
**project's property from that moment**. friday never regenerates a seeded
file over PM edits — there is no refresh pass, no sync, no template
re-application. A change the PM makes IS the file's new truth.

## Never-clobber (the adopt/backfill parity rule)

A target may already have `.claude/` content. Seeding is **add-only**:

- a **pre-write existence check** guards every file — an already-present
  file is **skipped and reported**, never overwritten (the same shape as
  init's Stage-0 idempotence);
- only missing files are written;
- a skipped file whose absence-of-content would matter (e.g. an existing
  `settings.json` with no env home, or content that contradicts what
  seeding would have written) is surfaced for the **PM's disposition
  through the surface's own escalation channel** — adopt's findings brief
  (`docs/contracts/findings-brief.md`; adopt is a sanctioned producer
  there), the Strategist's PM relay at init (an override lands as a
  decision entry), backfill's up-front migration plan — never silently
  merged, never silently dropped.

## Rules: structural insurance, single-homed by scope

A seeded rule exists so the right convention is in front of the model
**because the harness matched a file path**, not because an agent remembered
to read `docs/standards/`. Two rules keep that insurance honest:

- **No dead globs.** Every `paths:` glob is derived from the project's
  declared structure (`docs/standards/project-structure.md`) on greenfield,
  or the real extracted layout on adopt — never a guessed path. A seeded
  glob must resolve against the actual tree (≥1 target) at seed time, and
  the seeding surface **quotes the resolution output** (glob → N targets)
  in its completion relay — a prose count is not evidence. A rule that
  never fires is a false sense of insurance, worse than no rule.
- **Single-homing by scope.** A **path-scoped** convention lives in its
  `rules/*.md` file, carrying the full convention text (a pointer back to
  `docs/standards/` would weaken the insurance to a habit). A
  **general/cross-cutting** convention stays in `docs/standards/*`. No
  convention text appears in both homes — that duplication is the exact
  drift the single-homing rule (D-0083) exists to prevent.

## The permissions allowlist: conservative by construction

- Seed only **read-mostly, stack-obvious** verbs: the test runner, the
  linter, read/list inspection commands.
- **No write-capable or destructive command is ever seeded into `allow`** —
  those stay prompted. A wrongly-granted destructive permission is a silent
  footgun; a prompt is a two-second tap.
- **Workspace-trust note:** project-level `allow` rules and hooks activate
  only after the PM trusts the workspace — the seeded list is inert until
  then. (Doc-proven: `docs/research/claude-directory-inventory.md`.)

## Secrets

Seeded settings carry env **names** and non-secret project config only.
Secret values live in the operator's secrets manager and transfer
out-of-band; a seeded `settings.json` is never a place a secret value lands
(ADR-003).

## Deferred vehicles (sanctioned, not built — each gated by a stated reason)

- `skills/run` / `skills/verify` (bundling launch/smoke scripts) — input is
  a real build's run/verify procedure; seeded at post-build close when one
  exists.
- Ops skills (deploy, backup-restore drill) — input is an operations
  runbook; a reconcile-time vehicle.
- Architecture-layer generated rules — a **generated** artifact
  (regenerated on every `/friday:reference`, never hand-edited), the
  opposite ownership class from everything above; belongs with the
  reference/synthesis engine, not this doctrine.
- Project `agents/`, `workflows/`, `output-styles/`, and `agent-memory/`
  for friday roles — future vehicles; `agent-memory/` is its own increment.

A surface that wants to seed one of these first extends THIS contract.
