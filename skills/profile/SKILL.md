---
name: profile
description: run when the PM wants friday tuned to how they work — the one-time preferences interview
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:profile` — offer it before any work: “Shall friday learn how you like to work — run `/friday:profile`, the one-time preferences interview?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the **lead** of a friday agent team running `/friday:profile` — a one-time user-preferences interview that captures or updates the PM's per-user collaboration and formatting preferences.

> **Requires** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. If not enabled, tell the PM to set it in `~/.claude/settings.json` (`{"env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}}`) and restart the Claude Code session. Then stop — friday cannot operate without it.

## Your job

Create a single-teammate agent team with one Profiler, run the interview-by-relay loop, and write the result to `~/.claude/CLAUDE.md` between `<!-- FRIDAY-PROFILE:BEGIN -->` markers.

Emit dispatch telemetry through the single primitive at spawn/first-response/completion: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-profiler --phase profile:interview` (skip silently outside a friday project — the profiler is user-global).

## Workflow

### 1. Create the team

Create an agent team with one teammate:

- **Name:** `profiler`
- **Subagent type:** `friday-profiler`
- **Model:** haiku — pinned (a preferences questionnaire is cheap-model work; D-0116)

Before spawning, resolve the plugin root: `echo "${CLAUDE_PLUGIN_ROOT}"`, falling back to `~/.claude/plugins/marketplaces/local/friday` if empty (paste the expanded absolute path below — never the literal `${CLAUDE_PLUGIN_ROOT}`, teammates don't inherit the lead's shell env).

Spawn it with this kickoff prompt:

```
Run the preferences interview. $ARGUMENTS

friday-docs: unavailable
Teammate contract — plain-Read it before your first action: {resolved-abs-plugin-root}/docs/teammate-contract.md (your role file names which sections bind you)

Read ~/.claude/CLAUDE.md first to detect whether a FRIDAY-PROFILE block already
exists. If yes, run in re-run mode (ask the user which sections to update via a
single multiSelect QUESTION_PAYLOAD). If no, run first-time mode (batch all 16
questions into 1-3 QUESTION_PAYLOADs — including the Audience archetype + two
topical free-text fields + Learning Preference added by PROP-001 / PROP-003,
and Awareness (decision teach-back) added by PROP-039).

Surface every question to me (the lead) via SendMessage using the QUESTION_PAYLOAD
format defined in your role file. I will translate each into AskUserQuestion calls
and SendMessage you the ANSWERS back. When all answers are collected, write the
profile block and SendMessage me DONE with a summary.
```

### 2. Relay loop

Whenever the Profiler sends a `QUESTION_PAYLOAD` message:

1. Parse the payload (it can contain 1 or many questions in one batch).
2. Translate it into one `AskUserQuestion` call (batching multiple questions where the schema allows — up to 4 per call) or several sequential calls if there are more than 4.
3. Collect the PM's answers.
4. SendMessage the Profiler an `ANSWERS` block:

   ```
   ANSWERS
   =======
   Q1: {selected label}{, notes: "..." if user added free-text}
   Q2: {selected label}
   ...
   ```

If the Profiler sends a `RELAY` message instead (free-text summary or recap), just present it to the PM as a regular message and wait for their reply, then `SendMessage` `PM_REPLY` back with their words.

### 3. Completion

When the Profiler sends `DONE`:

1. Read `~/.claude/CLAUDE.md` to verify the FRIDAY-PROFILE block was written between the markers.
2. Surface a recap to the PM (the captured preferences in a clean table).
3. Briefly flag any tension between selected preferences (e.g., "Verbose comments + strict review will combine for heavy ceremony — re-run anytime to dial back").
4. Clean up the team (tell the Profiler teammate to shut down, then clean the team).

### 4. Suggest next steps

```
Profile saved. These preferences are now active in every Claude Code session.

Next steps:
- If this is for a new project: /friday:init
- If you just wanted to update the profile: you're done
```

## Notes

- **Single-teammate teams** are valid; they exist to give you persistent SendMessage continuity with the Profiler across the multi-round interview without respawning.
- The lane's flow above is the only entry — there is no separate legacy profiler agent (a pre-rename warning against `friday-v3-profiler` collided into self-contradiction when the 0.4.0 rename unified the names; removed per the structure audit).
- **Arguments:** `$ARGUMENTS` may be empty (default behavior) or contain hints like "communication only" to scope a re-run. Pass them verbatim to the Profiler.
