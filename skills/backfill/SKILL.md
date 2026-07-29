---
name: backfill
description: migrate a project built by an older friday onto the current substrate
friday-lane: true
disable-model-invocation: true
---

You are the lead running `/friday:backfill` — migrate a project built by an **older friday** onto the current substrate; the marketplace promise is that an upgrade **never orphans a project and never invents its past** (contract: the approved `/friday:backfill` behavior paragraph). Code that has never known friday at all is `/friday:adopt`'s door — the two are disjoint front doors, never a pipeline (journey audit J8).

### 1. Read the old record, show the plan BEFORE touching anything

Inventory the old shapes read-only (`docs/development-plan/**` checkpoint files, `FEATURES.md`, the old journal, any ADRs). Then show the PM the migration plan before a single file changes: **what carries over directly**, **what changes form**, **what the old version recorded that the new one no longer needs**, and — honestly — **what the new version expects that the old records simply don't contain**. **Fail-closed:** where the old trail is unparseable where you expected structure, STOP and surface it — never guess a migration.

### 2. Declare gaps, never fabricate them

A record the old friday didn't keep stays an **acknowledged blank**, not an invented entry. Mine the old trail's *real* decisions (architecture files, approval records, ADRs) into `DECISIONS.md` tagged `--back-filled` with their original dates where recoverable — the three-part bar applies retroactively; no manufactured entries for routine work. Coverage dispositions reconstruct from the old AC tables where they exist; unrecoverable IDs are marked `deferred — pre-migration, evidence not carried`.

### 3. Archive the originals — all of them, in original form

The old records AND all of the old friday's documentation — checkpoint files, feature trees, generated docs, everything its ceremony produced — are **archived in their original form, never deleted**; history stays readable as it was written. Old per-feature files are left in place, untouched; nothing new is written there.

### 4. Migrate the state and the docs

Map the old lifecycle to FRIDAY-STATE — all features closed + released → `closed` (carry the dirty-bit fields); anything in flight → `build-in-progress`. Run `/friday:reference` in full; the synthesized arc42 set becomes the living documentation, and old `docs/reference/` content is cited, never duplicated. Seed any missing native `.claude/` surfaces (committed settings.json + path-scoped `rules/*.md`) per `docs/contracts/claude-scaffold.md` — the contract owns the seeding rules; backfill's local part: seeding rides the §1 migration plan (add-only — what the project already has carries over untouched; only what is missing gets written), and a conflict is surfaced in that plan for the PM's word, never an overwrite.

### 5. Verify by the full battery; land it as ONE decision

The migrated record is verified end-to-end by the **full guardrail battery**, output quoted (`verify_state.py --json`, `verify_claims.py --all --json`, the synthesis diff, the doc-gate family) — a migration that fails its own gates is not done. It lands as **one recorded decision**: *migrated from version X to Y, with the map*. First real fixtures when this ships: this repo's own v0.4-era projects (`katy_video_platform`).

### Close

At the end the project speaks current friday, and nothing about its past was invented or lost. Commit on the PM's word; never push unless they say so.
