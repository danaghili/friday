# Contract: the compaction package

The producer/consumer contract for compaction continuity (INC-001: FR-1.2,
FR-1.3, FR-1.4, FR-1.8, FR-1.12; decisions D-0070..D-0075). Producers:
`hooks/compaction_steering.py` (assembles the steering spec the summarizer
follows), `hooks/compaction_filing.py` (files the finished summary),
`tools/spawn_telemetry.py` + lane surfaces (persist mission/orientation
layers) — all writing through `tools/friday_substrate.py`'s compaction verbs,
never by raw copy (D-0003). Consumers: `hooks/compaction_reorient.py`
(SessionStart source=compact) and `/friday:resume`'s orientation read. Both
sides cite THIS file; neither invents its own shape.

**This is NOT the seam handoff.** `.friday/seam-handoff.md` is the build-unit
fork brief — a different mechanism, owned by `tools/seam_handoff.py` (write +
`--clear`; its docstring is the shape authority) with `/friday:resume` step 5
as its consumer (D-0117 — no separate contract file exists for it, and none is
owed). The two names are never conflated (TSOW §13 landmine; INC-001 KH-6).

## The drawer layout

```
<shared .friday>/compaction/<session-id>/<agent-slug>/
├── mission.md        # layer 1 — spawn prompt verbatim (spawner-written) or
│                     #   the orchestrator's self-authored lane-entry note
├── orientation.md    # layer 2 — the agent's own "what I learned" note
├── current.md        # layer 3 — the latest ATTRIBUTED floor summary, verbatim
└── generations/      # append-only archive: <iso-ts>.md, NEVER overwritten;
                      #   same-second filings get a -N suffix
```

- **`mission.md` written as a dispatch briefing opens with one typed line** (INC-208 FR-208.4, D-0179): `dispatch: lane=<lane> role=<agent-slug> drawer=<path> template=<path>`, the first non-blank line, parsed by `tools/taglines.py` — no new parser, the same leading-tag-line shape the change trail uses. Producer: any lane composing from `${CLAUDE_PLUGIN_ROOT}/docs/dispatch-briefing-template.md`, which cites this contract back. Consumer: `${CLAUDE_PLUGIN_ROOT}/tools/dispatch_briefing_check.py`, which reports a briefing whose line omits a required field and a recorded dispatch whose briefing was never saved — report only, never a gate.
- **The lane-entry variant carries no such line, and is never checked.** The orchestrator's self-authored note is nobody's briefing; the checker scopes its worklist to the dispatches the journal records rather than to the files that exist, so a note in a drawer nobody dispatched into is invisible to it by construction (INC-208 KH-1).
- `<session-id>` and `<agent-slug>` are sanitized (path-safe, no dot-runs).
- The shared drawer `unattributed/` holds summaries whose self-ID line failed
  to parse: archived generations only — an unattributed summary can NEVER
  create or update any `current.md`.
- **Empty case:** no compaction yet → no `compaction/` dir (or an empty
  drawer). `compaction_read_package` returns the all-None package; every
  reader accepts it silently.

## The floor summary (layer 3) shape

The steering spec mandates; the filer parses line one; the rest is
agent-owned prose:

```
handoff-of: <agent-slug> — <scope, free text>

<current objective / where the work got to — short>
<WHAT WAS TRIED AND RULED OUT — the section that must survive>
<pointer to the live task list for outstanding work — never a copy>
<agent-declared addendum, when the agent named things its future self needs>
```

- Line 1 grammar: `handoff-of: <slug>[ — <scope>]`, slug `[a-z0-9][a-z0-9-]{0,63}`
  (`friday_substrate.parse_handoff_header` is the single parser). The slug
  `unattributed` is RESERVED (D-0078): the parser refuses it (archive-only
  filing) and `compaction_write_layer` raises on it — the fallback drawer can
  never grow a `current.md` or layer files.
- **The summarizer envelope (D-0077):** the raw `compact_summary` payload
  arrives wrapped in `<analysis>…</analysis><summary>…</summary>`; the
  handoff lives inside the summary block. The parser sees through the
  envelope (`strip_summarizer_envelope`, first non-empty line); generations
  archive the RAW payload, an attributed `current.md` holds the stripped
  handoff body.
- A summary missing its floor sections still files (archive always); the
  reorient side flags a floor-incomplete current summary rather than failing.

## Write rules (the single-writer invariant)

- Every write goes through `friday_substrate.compaction_file_summary` /
  `compaction_write_layer`. Hooks and commands never `cp` or `open()` into
  `.friday/compaction/` directly.
- `generations/` is append-only: filing never deletes, truncates, or
  overwrites an existing generation.
- `current.md` moves only on a parsed self-ID line (FR-1.4); `mission.md` and
  `orientation.md` are living records their owner may overwrite.
- Every filing emits one `compaction-filed` journal event (agent, attributed,
  generation path); telemetry failure never blocks the filing.

## Read rules (re-orientation, FR-1.8/FR-1.9/FR-1.13)

- The main session's package is delivered by push: `compaction_reorient.py`
  injects mission + orientation + latest current + the task-list reminder,
  plus the deterministic backfill (FRIDAY-STATE, open-lane sentinel, git
  HEAD, decisions tail) rebuilt from records — never trusted to the summary.
- A subagent's package is delivered by pull: its spawn message names its
  drawer path and the rule "after any compaction, re-read your package
  first"; the floor summary preserves that recovery line. (Push for
  subagents is unproven — INC-001 KH-2; the pull path assumes nothing.)
- `/friday:resume` reads the main session's package as an orientation source
  alongside its existing record reconnaissance.

Tests: `tests/test_substrate_compaction.py` (verbs, filing semantics, empty
case); hook behavior in `tests/test_hooks_compaction.py`.
