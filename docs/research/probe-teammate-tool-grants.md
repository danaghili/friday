# Probe: does a subagent definition's `tools` allowlist bind?

**Date:** 2026-07-28 · **Claude Code:** v2.1.220 · **Method:** documentation sweep +
config audit + empirical probe, transcript-verified · **Confidence:** High
(harness transcript evidence, not self-report)

**Answer: it depends entirely on HOW the agent is spawned — and the switch is one
optional argument.**

consumer: D-0132 + tools/spawn_grant_check.py (grant-binding roles spawn un-named); INC-201 FR-201.8 (agents/roles/experiment-runner.md's grant-binding line)

- **Spawned WITHOUT a `name`** → an ordinary subagent, and the allowlist **binds
  exactly as documented**, including per-role MCP scoping. friday's own
  security-reviewer role came up holding precisely the six tools its file
  declares and nothing else.
- **Spawned WITH a `name`** → an in-process teammate, and the definition file is
  **ignored wholesale**: `tools`, `disallowedTools`, `model`, `permissionMode`,
  `skills` and `mcpServers` all fail to apply. The same role came up holding all
  eight direct tools plus ~300 MCP tools, and ran a shell command.

**Root cause, visible in the spawn metadata.** Passing `name` overwrites the
recorded `agentType` with that name (`friday:roles:friday-security-reviewer`
becomes `named-control`). The definition is then looked up under a type that
does not exist, the lookup returns nothing, and the spawn code falls through to
its "no definition" branch — which grants **every** tool:

```js
tools: i?.tools ? Co([...i.tools, /* 5 team tools */]) : ["*"],
...i && {customAgentType: i.agentType},
...i?.model && {model: i.model}
```

`i` is the resolved definition. Every symptom follows from `i` being falsy: no
tool list, no model, no permission mode, and no `customAgentType` field in the
metadata (absent on every teammate measured here, present on none).

The failure is **not** the permission mode, and **not** the agent-teams feature
as such. friday can keep agent teams on and get real tool grants by not naming
the roles it spawns.

Recorded here rather than in `DECISIONS.md` because it is a measured fact about
the harness, not a choice friday made (`docs/research/` is the home for
load-bearing facts that outlive the work that found them — the same shelf as
`probe-hook-events.md`).

## Verdict table

| Claim | Verdict | Confidence | Evidence |
| --- | --- | --- | --- |
| **friday can get real tool grants without changing any setting** | **TRUE** | High | the named/un-named control pair below — omit `name` at spawn |
| Passing `name` at spawn replaces the recorded `agentType` | **TRUE** | High | metadata: `named-control` vs `friday:roles:friday-security-reviewer` |
| An **ordinary subagent** honours its definition's `tools` allowlist | **TRUE** | High | 3 headless runs + friday's real security-reviewer role |
| …and its **MCP tool scoping** | **TRUE** | High | exactly its 3 declared `friday-docs` tools, not ~300 |
| …still honours it under `--dangerously-skip-permissions` | **TRUE** | High | run A below — bypass on, allowlist held |
| A **teammate** honours its definition's `tools` allowlist | **FALSE** | High | transcript below |
| A teammate honours `disallowedTools` | **FALSE** | High | `echo DENY_PROBE_BASH_RAN` succeeded from a definition denying `Bash` |
| A teammate honours the definition's `model` | **FALSE** | High | definition said `sonnet`; all 7 turns ran `claude-opus-5` |
| A teammate honours the definition's `permissionMode` | **FALSE** | High | definition said `acceptEdits`; ran `bypassPermissions` |
| A teammate honours `skills` / `mcpServers` | **FALSE (documented)** | High | stated in the agent-teams page |
| A **built-in** restricted type binds as a teammate | **FALSE** | High | `Explore` (documented: no `Write`) wrote *and* edited a file |
| Permission mode is what breaks the tool grant | **FALSE** | High | run A: bypass on, grant still held |
| The reviewers' read-only sandbox (S-3) is enforced *as friday runs them* | **FALSE** | High | follows from the teammate rows |

## What the documentation says

- **Subagents** (`code.claude.com/docs/en/sub-agents`): `tools` is an allowlist —
  *"Tools the subagent can use. Inherits every tool available to subagents if
  omitted."* **This page is accurate** — it describes the ordinary path, and the
  ordinary path behaves exactly as written.
- **Agent teams** (`code.claude.com/docs/en/agent-teams`): *"The teammate honors
  that definition's `tools` allowlist and `model`."* **This sentence is wrong for
  this version.** Neither is honoured.
- The same page correctly warns that `skills` and `mcpServers` are not applied to
  teammates. That carve-out is real but **incomplete** — the true list of ignored
  frontmatter fields is at least six.
- It also states *"Teammates start with the lead's permission settings"* — true,
  and confirmed in every spawn record. But permission inheritance turns out not
  to be what breaks the tool grant.

## Config audit (ruling out our own misconfiguration)

- `~/.claude/settings.json`: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`; a
  `permissions.allow` list of 14 read-only shell commands (an auto-approval list
  — it affects prompting, never capability); **no `permissions.deny`**; no
  `permissions.defaultMode`.
- The lead session runs `bypassPermissions` (from the launch flag, not config).
  Every teammate spawn record inherits it.
- Project `.claude/settings.json`: hooks and two env vars only; no permissions.
- `.claude-plugin/plugin.json`: declares one MCP server (`friday-docs`).
- No `disallowedTools` anywhere in the tree.

## Method

Probes were spawned with deliberately restricted definitions, told to attempt
each forbidden tool, to treat a clean failure as the **desired** result, and
never to work around an obstacle (a helpful agent that routes around the block
destroys the measurement).

**Verification did not rest on any agent's report.** The first probe went idle
without delivering one. Two independent channels were used instead: files the
agents were asked to write were read directly from disk, and their session
transcripts (`~/.claude/projects/<project>/<session>/subagents/agent-*.jsonl`)
were parsed for real `tool_use` blocks and their results. The transcript is the
harness's own record of what was called. Spawn metadata
(`agent-*.meta.json`) supplied `taskKind`, `permissionMode` and `model`.

## Evidence 1 — the teammate path (the failure)

Teammate from `friday-security-reviewer`, whose definition declares exactly
`Read, Grep, Glob` plus three `friday-docs` tools:

| Tool called | In the allowlist? | Result |
| --- | --- | --- |
| `Bash` | **no** | `GRANT_PROBE_BASH_OK` |
| `Write` | **no** | file created on disk, read back independently |
| `ToolSearch` | **no** | succeeded |
| `mcp__plugin_friday_friday-docs__status` | **no** | real data (`decision_count: 131`) |
| `mcp__plugin_friday_friday-docs__list_sections` | yes (control) | real data |

No call errored. No call was refused.

Two further teammates confirmed the pattern from different angles: one whose
definition **explicitly denied** `Bash` ran `echo DENY_PROBE_BASH_RAN` clean;
the built-in `Explore` type, documented as having no `Write`, both wrote and
edited a file. Both verified from their transcripts, not their reports.

### The full inventory — the part that matters most

A second probe enumerated everything in its pool. The six-tool allowlist
resolved to **the entire session tool pool**:

- **All eight direct tools:** `Agent`, `Artifact`, `Bash`, `Edit`, `Read`,
  `Write`, `Skill`, `ToolSearch`. Note `Agent` — a role declared read-only could
  spawn further agents.
- **Every MCP tool from every server connected to the session**, roughly 300
  across eleven servers — including the user's **Gmail, Slack, Google Drive,
  Google Calendar, Home Assistant, and browser automation**.

The security reviewer is the role friday points at code it assumes may be
hostile, under a written promise of read-only, no network. Run as a teammate,
that role holds the user's mail, chat, files, calendar, home automation and a
browser.

## Evidence 2 — the ordinary path (it works), and the isolation runs

Same fixture definition (`tools: Read, Write, Grep, Glob`), spawned from
headless `claude --print` sessions. All three produced **ordinary subagents** —
their metadata carries no `taskKind`, `teamName` or team fields, only
`spawnDepth: 1`.

| Run | Permission mode | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | Pool | `Bash` |
| --- | --- | --- | --- | --- |
| baseline | `acceptEdits` | `0` | exactly the 4 granted | **absent** |
| A | **`bypassPermissions`** | `0` | exactly the 4 granted | **absent** |
| B | `acceptEdits` | **`1`** | exactly the 4 granted | **absent** |
| (this session) | `bypassPermissions` | `1` | **all 8 + ~300 MCP** | **present, executed** |

**Run A is the load-bearing one:** it bypasses permissions exactly as the live
session does, and the grant still holds. Bypassing approval does not conjure an
ungranted tool — tool *presence* sits upstream of the permission check.

**Run B did not test what it was designed to test.** Setting the teams
environment variable in `--print` mode did not produce a teammate; headless mode
appears never to enter that path. So B is a third repetition of the ordinary
path, not the teams cell.

## Evidence 3 — the controlled pair that isolates the cause

friday's **real** `friday:roles:friday-security-reviewer` role, spawned twice
from this same live session with the identical prompt and the identical
background setting. The only difference is the `name` argument.

| | `name` omitted | `name: "named-control"` |
| --- | --- | --- |
| recorded `agentType` | `friday:roles:friday-security-reviewer` | **`named-control`** |
| `customAgentType` | (n/a — ordinary path) | **absent** (definition not resolved) |
| `taskKind` | absent — ordinary subagent | `in_process_teammate` |
| `spawnDepth` | 1 | 0 |
| model | — | `opus` (lead's, not the file's) |
| tool pool | **exactly its 6 declared tools** | all 8 direct + ~300 MCP |
| `Bash` | **absent** | present, and **executed** (`57 CLAUDE.md`) |

Both tool pools were taken from the agents' own reports; the `Bash` execution in
the named run is confirmed from its transcript's `tool_use` record.

This pair is the whole finding. One optional argument decides whether a role
file is a constraint or a wish.

## Not yet established

- **A teammate in a session that is NOT permission-bypassed.** The one untested
  cell, and it cannot be reached from here (teammates exist only in interactive
  sessions, and a teammate's own `permissionMode` is ignored). **Deliberately not
  pursued** — the PM ruled it not worth the effort on 2026-07-28, correctly: the
  cause is now fully explained by the overwritten `agentType`, and no permission
  setting can make a `sonnet` definition run on `claude-opus-5`.
- **Whether an un-named subagent supports the brainstormer's multi-turn PM
  relay.** It is resumable by agent id, which suggests yes, but the grilling
  protocol is the one lane where this must be proven before it is changed.
- Whether this is a regression or has always been so. Nothing here dates it.

## What this means for friday

**The fix is available and cheap: do not pass `name` when spawning a role.**
No settings change, no dropping agent teams, nothing global. What it costs is
the teammate features that ride on the name — direct PM-to-teammate dialog in
the agent panel, addressing by name over `SendMessage`, and the shared task
list. An un-named subagent is still resumable by its agent id, so a multi-turn
relay (the brainstormer's grilling) is not obviously lost; that is worth
confirming before any lane is changed.

Until a lane actually changes, these remain true:

1. **The S-3 sandbox on `agents/roles/security-reviewer.md` and
   `agents/roles/redteam-reviewer.md` is not real** — *as friday actually runs
   them*, i.e. named. Both say *"No Bash, no Write, no network — the code under
   review may fight back."* Measured above: that role holds a shell, the user's
   mail, chat, files, calendar, home automation and a browser. Un-named, the
   same file delivers exactly what it promises.
2. **Every role file's tool list** is intent rather than constraint **whenever
   the role is spawned with a name**.
3. **PROP-201 / INC-201's mechanism works after all.** Removing `Bash` from the
   tools list does constrain an ordinary subagent. The increment is not blocked;
   it gains a prerequisite — the runner must be spawned un-named, or the tool
   grant it relies on evaporates.
4. **D-0124's framing** holds only for the named path: there, the tool grant
   does not merely fail to express "only this one command", it expresses
   nothing at all.
