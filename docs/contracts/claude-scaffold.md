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
| `.claude/settings.json` | the confirmed stack + friday's project env needs | committed project settings: an `env` block (the home for any project-level env friday introduces, and the home of the compaction guardrail — § The compaction guardrail below) and a `permissions.allow` list derived from the confirmed stack |
| `.claude/rules/*.md` | the confirmed stack + the Profiler's coding preferences — the same sources `docs/standards/*` draws from | path-scoped conventions: each rule carries a `paths:` frontmatter glob and the **actual convention text**, so the harness auto-loads it when Claude reads a matching file |

Nothing else is seeded into `.claude/`. Seeds outside `.claude/` live in their own sections below (§ The delivery-configuration seed; § The dependency-update seeds). `settings.local.json` is the PM's personal file — friday never writes it.

## The compaction guardrail (INC-209 — this contract owns the values)

**The pair is a standard seed.** Every project friday scaffolds gets `CLAUDE_CODE_AUTO_COMPACT_WINDOW` = `"1000000"` and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` = `"40"` in its committed `settings.json` `env` block — a standard seed written for every project, never an illustration of what the env block may carry (INC-209 FR-209.1, D1; the pair's origin is D-0070, and the deferral that kept it in friday's own repo is reversed at INC-209 § 9). THIS contract is the single home of those two values: every seeding surface cites this section by name and restates neither of them, because two copies of a number are two numbers that can drift apart (D-0083).

**What it buys, and the assumption it carries.** The pair moves a session's automatic tidy-up early — to the fraction of the window the percentage names — so friday's continuity machinery has room to work in rather than firing when the context is already nearly full. The values assume a session running on a large-window model. On a project pinned to a smaller-window model the trigger sits out of reach, and a model that would have tidied up early of its own accord stops doing so. friday cannot read which model a session runs, and the model can change between one session and the next, so the assumption is **stated out loud at setup and never detected** — an undetectable assumption named plainly is honest, the same assumption dressed as detection is not (INC-209 KH-3).

**The block explains itself where it lives.** The settings format carries no comment syntax, so the explanation rides in a `$comment` key beside the block — the convention friday's own settings file already uses for exactly this purpose — naming what the pair does and that it is the project's to change from the moment it is written. A collaborator opening the file learns why it is there without leaving the file (INC-209 FR-209.3).

**It is a shared default, not a personal preference.** The pair goes into the committed project settings because what it protects — the cost and quality of that project's sessions — is a property of the project rather than of the person. An individual may override it in their own `settings.local.json`, which friday never writes (INC-209 D6, S-209.2).

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

**One narrow exception, scoped to the compaction pair by name (INC-209 FR-209.4, D2).** friday may add `CLAUDE_CODE_AUTO_COMPACT_WINDOW` and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` — that pair **and nothing else** — into an existing `settings.json`, and only after an **explicit** PM yes at the door that offered it. It never alters a value already present for either setting, never rewrites an existing `$comment`, and never touches any other key, value, or ordering in the file: a PM who set their own number keeps it. Without a yes the file is left byte-identical. The exception is scoped to this pair **by name**, so extending it to a second setting is an edit to THIS contract rather than a generous reading of it — no lane, skill, or agent may widen it in its own text (INC-209 S-209.5). Only the doors named in § The retrofit doors may take it. Everything else above is unchanged: any other file is still skipped whole and reported, and so is `settings.json` itself whenever consent is absent.

**Why the exception exists at all.** Never-clobber skips whole files, and every friday-scaffolded project already has a `settings.json` by construction — so without this, the projects that most need the guardrail are exactly the ones no retrofit could ever reach, and the PM would hand-edit the file himself. That is the manual step INC-006 diagnosed and did not remove. The exception is the narrowest thing that closes it (INC-209 § 1, KH-1).

## The retrofit doors (the only surfaces that may take the exception)

- **`/friday:adopt` and `/friday:backfill`** on the parity side, where an existing `settings.json` already reaches the PM through the surface's own escalation channel named above — adopt's findings brief, backfill's up-front migration plan.
- **`/friday:patch`** as the one-tap route, for a project that needs this and nothing else.
- **`/friday:init` on greenfield needs no exception**: it writes the file fresh, so the standard seed lands through the ordinary write path.

No other surface may take the exception, and each door cites THIS contract by name rather than restating it. **Before a door offers, it reads the target project's decision record**: a recorded decline means the door says nothing at all (INC-209 FR-209.6, D7). A decline is recorded through the project's own decisions writer, carrying the PM's reason as given, so a settled answer is never re-asked at the next door. A recorded yes needs no re-reading — the report-only check already reports the pair as present.

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
- **The don't-read rule (INC-204 FR-204.8, D11).** One seeded rule covers the stack's **value files** — the files whose content is secret values (the dotenv class; a stack-native `secrets.yaml`; a compose env file). Its globs derive from the **confirmed stack's value-file names** rather than the declared structure — the same live-resolution requirement binds, and **example files are excluded by name** (`tools/secret_names.py` legitimately reads those; a don't-read glob that covers the example file would break the ownership inventory). Its text instructs, at the exact moment the harness matches a read: this file carries secret values — do not open, quote, or summarize it; names belong in the example file, values in the store the `FRIDAY-SECRET-STORE` block declares. A stack whose value files do not exist on the real tree seeds no rule — the empty case, reported honestly, never a dead glob.

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

## The delivery-configuration seed (INC-204 FR-204.6)

A managed project's CI secret scan is **lifted, not designed** (INC-204 D7): the job below is copied from a working production setup and pinned by tag-verified commit SHAs (supply-chain vet on the record: `docs/DECISIONS.md: D-0169`). It scans the **full git history** — removing a committed secret is a history rewrite, not an edit, so a clean working tree proves nothing about history — and a finding blocks the pull request.

- **When:** seeded alongside the `.claude/` set by the same producing surface (the Strategist at init Stage 4; adopt/backfill parity) **when Stage 0 found a GitHub origin remote**. A project with no GitHub remote gets nothing — a workflow that can never run is dead config, the same false insurance as a dead glob. When delivery is wired later, that wiring work seeds this file from THIS contract (the moment the Strategist's standing `ci-gate:` forward reference already names).
- **Ownership:** identical to every other seeded file — written once, project-owned, add-only under the pre-write existence check. A project whose workflows already scan for secrets (any tool) is **skipped and reported**, never replaced or doubled.
- **Not seeded:** a `.gitleaks.toml`. That file is per-project tuning born from a project's first findings (path + regex allowlisting, preferred over fingerprint baselines); the action auto-detects one at the repo root if the project later adds it. Seeding an empty allowlist would be designing, not lifting.

The template (`.github/workflows/secret-scan.yml`):

```yaml
# Seeded by friday (docs/contracts/claude-scaffold.md — INC-204 FR-204.6).
# Secret scan over FULL git history; pins are tag-verified commit SHAs.
name: secret-scan
on: [push, pull_request]

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
        with:
          fetch-depth: 0 # full history, not the default shallow clone
      - uses: gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e # v3.0.0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## The dependency-update seeds (INC-103 FR-103.7/FR-103.8 — extending the delivery-configuration section's doctrine)

Two seeds, one doctrine (INC-103 D10 — no new timing rule; the existing one taken twice, once per half):

- **When:** the same producing surface and the same GitHub-origin condition as the secret scan above; the watcher file additionally waits for the merge-reaches-production question (below) — it never rides in silently. No GitHub remote → neither is seeded, and the delivery work lifts them from this contract when it wires CI.
- **Ownership:** identical to every seeded file — written once, project-owned, add-only under the pre-write existence check. An existing watcher configuration or advisory-scanning workflow is **skipped and reported, never replaced, doubled, or edited** (S-103.4).
- **Vendor facts:** vets and dated behaviour live in the decision log (`docs/DECISIONS.md: D-1033, D-1036`), never here as standing facts (INC-103 D9).

**1. The update watcher (`.github/dependabot.yml`) — FR-103.7.** Seeded ONLY after the merge-reaches-production question has been asked and its answer recorded (FR-103.9, S-103.3 — the question's own home is the setup relay). The answer is a typed line in the project `CLAUDE.md`, beside its sibling declarations: `merge-deploys: <yes|no|unknown> — <the PM's answer in their own words> (asked <date>)` — `unknown` is a first-class recorded answer, distinct from the line being absent (absent means never asked, and the relay asks). Where the operations battery's restart row already holds a verdict on how the system comes back (`python3 "${CLAUDE_PLUGIN_ROOT}/tools/ops_battery.py" read --root .`), that verdict is the answer's source and the question is not re-asked — the line records it citing the verdict's date. The `updates:` entries are **generated at seed time from the tree-side derivation** — `python3 "${CLAUDE_PLUGIN_ROOT}/tools/watcher_coverage.py" kinds --root . --json` — one entry per kind present, `directory` from the evidence paths' own locations, and the derivation's output quoted in the completion relay as evidence, never as a prose count. **No fixed ecosystem list exists in this contract, and the seeded file carries no comment describing its own scope** — the file the audited project carried did, and that claim was false the day it mattered (S-103.2, KH-1); coverage is only ever the comparison's own output, re-derived at any deep clean. Each generated entry carries a weekly schedule, grouped minor-and-patch updates where the ecosystem versions that way, and an explicit `cooldown` value, set in the skeleton below — an explicit value is a decision on the record where a platform default is a vendor's choice that can change again (D9; the value lifted from the audited project's own production file, where its reasoning is written beside it). Where a watcher configuration already exists, the seed is skipped per the Ownership rule and the comparison runs against what is already there, reporting any uncovered kind. The entry skeleton (ecosystem and directory are generated; the rest is the template):

```yaml
# Seeded by friday (docs/contracts/claude-scaffold.md — INC-103 FR-103.7).
# Entries generated from this tree at seed time.
version: 2
updates:
  - package-ecosystem: "<from the derivation>"
    directory: "<from the evidence paths>"
    schedule:
      interval: "weekly"
    cooldown:
      default-days: 7
    groups:
      minor-and-patch:
        patterns: ["*"]
        update-types: ["minor", "patch"]
```

**2. The advisory-scan step (`.github/workflows/dependency-scan.yml`) — FR-103.8.** Runs on change and **reports without failing the job** — report-only by plain shell semantics (the trailing `|| true`), never by a platform option whose behaviour would need re-verifying at every vendor change (KH-3). **Its stated job is producing evidence the standing dependency-advisory row consumes (`docs/contracts/ops-battery.md`), not vigilance** — nobody has to read its output for the mechanism to work; the row produces its verdict either way (KH-5). The binary is pinned by version and release checksum; the actions by tag-verified commit SHAs.

The template (`.github/workflows/dependency-scan.yml`):

```yaml
# Seeded by friday (docs/contracts/claude-scaffold.md — INC-103 FR-103.8).
# Evidence for the operations battery's dependency-advisory row; reports,
# never gates (INC-103 D2) — the trailing `|| true` is the report-only rule.
name: dependency-scan
on: [push, pull_request]

jobs:
  osv-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
      - name: advisory scan (report-only)
        run: |
          curl -sSL -o osv-scanner \
            https://github.com/google/osv-scanner/releases/download/v2.4.0/osv-scanner_linux_amd64
          echo "15314940c10d26af9c6649f150b8a47c1262e8fc7e17b1d1029b0e479e8ed8a0  osv-scanner" | sha256sum -c -
          chmod +x osv-scanner
          ./osv-scanner scan source -r --format json --all-packages . > osv-results.json || true
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        if: always()
        with:
          name: osv-scan-results
          path: osv-results.json
```

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
