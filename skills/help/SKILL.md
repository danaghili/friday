---
name: help
description: run when the PM asks what friday can do or where they are — the generated command index
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:help` — offer it before any work: “Want the map of friday's commands — run `/friday:help` for the generated index and a where-am-I readout?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the **lead** of a friday session running `/friday:help` — a generated index of every friday command, grouped by the life of a project, built fresh from the lane files themselves, plus a **where-am-I** readout when you are inside a project. You write nothing: the index is regenerated on every run, so it can never drift from the commands it describes. Your only job is to run the scripts and show the PM their output — an index the model composes but never invents, and a state readout the model reads but never guesses.

> **Generated, never stored.** This command produces no file. The index is rebuilt each run from each lane's one authoritative field — a command file's line-1 opener, or a lane-skill's frontmatter `description` (a lane lives in `commands/<lane>.md` OR `skills/<lane>/SKILL.md`, INC-002) — so there is no second source of truth to fall out of date. If a one-liner looks wrong, the fix is that lane's own file — never here.

> **Requires** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — though this command is lead-driven (no teammate spawn), the variable is required because friday's other commands assume it.

## Phase 1: Extract (generate fresh from the lane files)

Run the shared lane parser — the same pipeline that generates the README command table, so the live index and that table can never disagree on a parse:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/gen_command_index.py" --commands-dir "${CLAUDE_PLUGIN_ROOT}/commands" --skills-dir "${CLAUDE_PLUGIN_ROOT}/skills" --json
```

It returns one merged JSON array of `{"name", "description"}` over both lane homes: a `commands/<lane>.md` description is line 1's text after the opener em-dash; a `skills/<lane>/SKILL.md` with `friday-lane: true` (a lane-skill — the explicit lane marker, INC-007) contributes its frontmatter `name` + `description` (a SKILL.md has no line-1 opener; its line 1 is `---`). A noticing-skill (no marker) is a watcher, never an index row. Every description is capped at ~90 chars (`…` if capped); a non-canonical opener or a missing frontmatter description self-flags with a fix-it note as its description (the lane still appears; it self-flags rather than vanishing). **A lane whose one authoritative field the parser can't read is a lane whose documentation disagrees with itself — that mismatch is reported here, in place, never hidden.** A **shadow** (the same lane in both homes — the command silently wins, probe-proven) is reported on stderr and self-flagged in the row; surface it to the PM as a defect, never hide it. Both conventions live once, in `tools/gen_command_index.py`.

**Degraded fallback (plugin root unresolvable):** glob `commands/*.md` and `skills/*/SKILL.md`. For a command, read **line 1 only** and apply the opener convention by hand — name and description from `` running `/friday:<name>` — <description> `` (em-dash separator, U+2014). For a skill, read the frontmatter block only: it is a lane iff `friday-lane: true`; take `name` + `description` from the frontmatter. A non-matching line 1 or missing description self-flags with the fix-it note instead of vanishing.

(This command spawns nothing; if that ever changes, cite `spawn_telemetry.py` at the dispatch point — the coverage check will hold you to it.)

## Phase 2: Group (the one curated part) — by the life of a project

Sort each extracted command into a lifecycle group using this name → group map. This map is the **only** hand-maintained part — keep it short and honest:

```
starting:   profile, init, intake, brainstorm, design-system, research, adopt, backfill
building:   build, resume
checking:   harden, security, redteam
changing:   feature, patch, bug, feedback
records:    reference, reconcile, handoff, help
```

**Drift guard (forward).** Any extracted lane (from either home) whose name is **not** a key in this map goes under a final group **`Uncategorized — add to the group map in skills/help/SKILL.md`**. A newly-added lane self-flags here instead of silently disappearing.

**Stale-entry guard (reverse).** Any map key with **no matching lane in either home** — no `commands/<name>.md` **and** no lane-skill at `skills/<name>/SKILL.md` (the defined absent state, INC-002) — is a dead entry from a deleted or renamed lane — surface it on its own line, **`stale group-map entry: {name} — remove from skills/help/SKILL.md`**, so the map can't accumulate names for lanes that no longer exist. A lane that lives in the skills home (e.g. `feedback`, a lane-skill) is present, not stale — the guard checks both homes before flagging.

## Phase 3: Print the index

Print the grouped index to the PM. Walk the groups in map order (`starting → building → checking → changing → records`, then `Uncategorized` if non-empty); within each group, list commands in the map's order. Pad the command column so the em-dashes align.

```
friday commands

Starting a project
  /friday:profile      — <description>
  /friday:init         — <description>
  ...

Building
  /friday:build        — <description>
  /friday:resume       — <description>

Checking the work
  ...

Changing a delivered project
  ...

Keeping the records honest
  /friday:reference    — <description>
  /friday:reconcile    — <description>
  /friday:handoff      — <description>
  /friday:help         — <description>

Generated from each lane's one authoritative field — a command file's line-1
opener, or a lane-skill's frontmatter description. If a one-liner looks wrong,
fix that lane's own file — there is no list to edit here.
```

If `--group=<name>` was passed, print only that group (and the footer).

## Phase 4: Where am I? (only inside a friday project)

If a friday project exists here (`.friday/` present, or `CLAUDE.md` carries the FRIDAY markers), read the current state deterministically and tell the PM **where they are and the sensible next command** — the readout is script-derived, same project same answer, never a guess:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_state.py" --root . --json
python3 "${CLAUDE_PLUGIN_ROOT}/tools/open_risks_check.py" --root .
```

Compose one plain-English line from the two outputs: the state, and the next step it implies. **The honest next step is sometimes a refusal:** if `open_risks_check` reports an open risk, the next step is **`/friday:research` first — building is blocked until it's closed**, not `/friday:build`. Otherwise name the natural next door for the state. Show the state verbatim from the script; never assert a state the script didn't return.

## The stranger's front door (no friday project here)

If there is no friday project (no `.friday/`, no FRIDAY markers in `CLAUDE.md`), this is someone's first meeting with friday. Give them, in this order:

1. **What friday is, in three sentences** — an expert team that interrogates an idea into a build-ready spec, builds it in one focused pass, then hardens and documents it independently; every big decision is made while it's still cheap to change, and written down.
2. **A pointer to the manual** (`docs/` / the README).
3. **The recommended first step:** `/friday:profile` to tune how it works with you, then `/friday:init` to take stock and start.

## What you DON'T do

- Write or cache any file — the index and the readout are generated fresh every run; there is no `help` artifact to drift.
- Hand-maintain command descriptions here — they live in each command's line 1.
- Silently drop a command — an unmapped one shows under `Uncategorized`; an unparseable opener shows with a fix-it note.
- Assert a project state the state script didn't return, or recommend a bare `/friday:build` while a risk is open.
- Spawn a teammate — this is lead-only.
- "Improve" a description you read — if it reads badly, that's a finding about the command file, not something to paper over here.

## Arguments

`/friday:help` — full index (every lane, from `commands/` and the lane-skills in `skills/`, grouped by the life of a project) plus the where-am-I readout when inside a project.

`/friday:help --group=<name>` — show only one group: `starting` | `building` | `checking` | `changing` | `records`.

## Key principles

1. **Generated from source, never hand-maintained** — the lane files are the single source of truth; the index is derived from each lane's one authoritative field (line-1 opener or frontmatter description) every run, so it cannot go stale.
2. **The curated map flags its own staleness** — any lane the map doesn't know surfaces under `Uncategorized`; any map key with no lane in either home surfaces as a stale entry. Both point at the exact fix.
3. **Nothing vanishes silently, no mismatch is hidden** — an unmapped lane self-flags; a non-canonical opener or missing frontmatter description self-flags with a fix-it note; a broken field IS a reported lane-vs-doc mismatch; a shadow (one lane, both homes) is reported, never swallowed.
4. **The readout is deterministic** — where-am-I comes from `verify_state.py` + `open_risks_check.py`, not the model's memory; same project, same answer.
5. **No artifact, no drift** — writing nothing is the feature: a checked-in index would become a third thing to keep in sync, which is the rot this command exists to avoid.
