# The dispatch briefing template

The fill-in skeleton for the briefing a lane writes when it starts a helper agent. One home, cited by name from every lane that dispatches (INC-208 FR-208.1, D-0178); the rule it serves is single-homed in `${CLAUDE_PLUGIN_ROOT}/docs/teammate-contract.md` § Dispatch discipline and the saved briefing's shape is owned by `${CLAUDE_PLUGIN_ROOT}/docs/contracts/compaction-package.md` — this file cites both and restates neither, and every path it names resolves through the plugin root because a bare relative path resolves against the PM's own project instead (INC-208 KH-3).

**Why this file exists rather than a paragraph in each lane's playbook.** The skeleton was described in prose in several playbooks and reassembled from memory at every dispatch, and reassembly drops pieces silently: at INC-208's discovery, every briefing that existed on disk was missing the helper's recovery-drawer path, including the one that spawned that very discovery. Prose in one more place would have been the same mechanism. So the words live here, and `${CLAUDE_PLUGIN_ROOT}/tools/dispatch_briefing_check.py` reads the briefings that were actually sent and names what is missing — report only, never a block.

## The typed line (required, first non-blank line)

A briefing opens with one typed tag line carrying the four fields the checker validates. Grammar is the shared tag-line reader's (`${CLAUDE_PLUGIN_ROOT}/tools/taglines.py`), the same leading-tag-line shape the change trail uses — no new parser, no marker fence for a single line:

```
dispatch: lane=<lane> role=<agent-slug> drawer=<path> template=<path>
```

- `lane` — the lane dispatching, as its skill folder names it (`feature`, `bug`, `harden`).
- `role` — the helper's agent slug, exactly as `--agent` receives it.
- `drawer` — the helper's compaction-package drawer path, the piece that went missing on every briefing before this template existed. Instance-suffix it when a lane dispatches the same role twice in one session, so the second briefing never overwrites the first agent's notes.
- `template` — this file's path (or the lane's own slice, when one adds fields).

A briefing whose first non-blank line is not this line is reported **unchecked** rather than passed: silence there would be the checker certifying a file it never read.

## The skeleton (fill every slot; delete nothing)

1. **Who you are and what lane you are in.** The role's own contract governs its craft; the briefing says which job this dispatch is.
2. **The ask, verbatim.** The PM's own words where the work started from a PM ask — never your paraphrase of them (a paraphrase is a decision the PM never made).
3. **Read-first list, explicit and complete.** The project `CLAUDE.md` reaches zero subagents, so the read list plus this briefing is the helper's whole context. Name every file it must consume before working, in the order that makes them make sense.
4. **The output path, and its shape.** Where the work lands, and which contract or grammar the artifact must satisfy — cited by name, so the helper reads the contract rather than inventing a shape.
5. **The rules that bind this dispatch.** Anything the helper cannot derive from its own role file: authoring conventions of the project it is writing into, gates it must clear, protocols it runs under (the relay protocol, the non-proceed gate).
6. **The docs-access stamp.** `friday-docs: available` when the MCP doc server is running, so the helper queries the contract set instead of guessing at it — or, when it is not, a plain-Read pointer to `${CLAUDE_PLUGIN_ROOT}/docs/teammate-contract.md` naming the section that binds this dispatch. One or the other on every briefing: a helper with neither reconstructs the rules from memory, which is the failure this whole template exists to end.
7. **The drawer path, and the recovery instruction.** Where its compaction package lives, and the standing instruction to re-read that package after any compaction before continuing.
8. **What is NOT its call.** The decisions reserved to the PM or the lead — so a helper that meets one recognises it as a gate rather than an obstacle.
9. **How to return.** What its final message must contain, and what it must not (a summary the PM will read for themselves is noise; raw structured data is the return value).

## What never belongs in a briefing

- **A tool grant, or anything implying one.** How an agent is dispatched — its model, whether it is named, and therefore whether its declared tool list binds — stays with the dispatch call and the role file (INC-208 S-208.5, `${CLAUDE_PLUGIN_ROOT}/tools/spawn_grant_check.py`).
- **A secret value.** Names, never values — the invariant is single-homed in the project's own `docs/standards/coding-standards.md` (the PROJECT's file, deliberately relative — this one is read in the PM's tree, not the plugin's).
- **The session's history.** One unit of work per dispatch; briefs, reports and diffs travel as files.

## Saving it

Persist the briefing verbatim as the helper's mission layer at dispatch time — `spawn_telemetry.py --prompt-file` does this in the same call that records the spawn. A briefing that is never saved is invisible to crash recovery and to the checker alike, and the checker reports exactly that.
