---
name: redteam
description: run when the PM asks what nobody thought to promise — hunt the unpromised doors
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:redteam` — offer it before any work: “Worried about what nobody promised — run `/friday:redteam` to hunt the unpromised doors?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:redteam` — hunt the doors **nobody thought to promise**, and make the spec smarter for it (contract: the approved `/friday:redteam` behavior paragraph; the reviewer's own contract is `agents/roles/redteam-reviewer.md` — this door spawns what that contract expects). It runs inside hardening's find pass and standalone via `$ARGUMENTS`.

### 1. The worklist is imagination disciplined by structure

The reviewer derives its own worklist — it reads the spec and asks **what it never imagined**, then attacks: business rules (skip the workflow, buy without paying, keep watching after canceling), operations (the never-restored backup — *restore it*; the single point of failure; the disk that fills), assumptions (client-side state trusted as truth; the "nobody would ever" that somebody will). Same machinery as security — narrow adversaries, fresh context, **experiments over opinions**. Point it at the record; don't hand it a checklist.

### 2. Spawn the reviewer, sandboxed

**Spawn it un-named — pass no agent name.** The role file declares a read-only grant, and that grant is the reviewer's whole containment while it reads code assumed hostile. Naming a spawned agent overwrites its recorded type, so the role file cannot be resolved and the spawn falls back to granting **every tool in the session** — measured, not assumed (`docs/research/probe-teammate-tool-grants.md`). The cost is that it can no longer be addressed by name mid-run; relay through the lead instead.

spawn-unnamed: friday-redteam-reviewer

Spawn `friday-redteam-reviewer` (model: **opus** — stated explicitly, never inherited; telemetry: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-redteam-reviewer --phase redteam:review`). The spawn message carries the sanitized-mirror path (read-only; the system may fight back — guard #13; `tools/sanitized_mirror.py`), the friday-docs spawn stamp, and the audience overlay. The reviewer DESIGNS the experiment and INTERPRETS it; execution belongs to the harden pass's experiment-runner lane — where no runner was available, the finding says "reasoned, not demonstrated," and the proof rule grades it no higher than informational. For a large system this fan-out scales through harden's finding engine — see `skills/harden/SKILL.md`.

### 3. The proof law, then feed the spec

Findings obey the same proof law — **demonstrated, never speculated** (the workflow actually skipped, the restore actually failed) — graded act-now / before-growth / track / informational on the findings-brief grammar (`docs/contracts/findings-brief.md`), the PM's name on any accepted risk. A redteam finding is **different in kind**: it usually means the spec had a blind spot, so a **confirmed finding feeds back as a candidate requirement** — into the waiting room or a new increment, not merely a fix. The operational adversary attacks what `friday-operations` runs; its confirmed findings route there to fix and own. Named-vuln classes and scans are `/friday:security`'s — cross-reference, never duplicate.

### 4. Surface and route on the PM's word

You persist the returned brief (the reviewer writes nothing) and surface it: the most dangerous finding first, the counts, the top recommended routes. Offer to file candidate requirements / `[ACTION]` notes / accepted risks — **file nothing without PM approval.**

**The waiting room is a real place (D-0108).** A candidate requirement the PM wants but defers goes into the PARKED ledger, not into thin air: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/parked.py" append --root . --source redteam --what "<the candidate requirement>" --revisit-when "<what makes it timely>"` (contract: `docs/contracts/parked-ledger.md`). Reconcile's roundup re-presents it — that re-presentation path is what separates a parked requirement from a dropped one. An accepted risk is different and keeps its own recording (the PM's name on it); park requirements, never risks.

**Enact the operations route — the dispatch, not just the sentence (INC-200).** The operational adversary's confirmed findings are promised to `friday-operations` "to fix and own" (`agents/roles/redteam-reviewer.md`: *three lanes, one seam each — attack (you), verify (security), own and fill (operations)*); that promise now has a spawn behind it. Once the PM has dispositioned the findings, **offer** the dispatch for the ops-tagged set; on an explicit yes, spawn **`friday-operations`** (model: **sonnet** — named, never inherited; telemetry: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-operations --phase redteam:ops-route`). Its spawn message carries the PM-approved ops-tagged findings with their cross-references, the rest of the skeleton composed from the briefing template (`${CLAUDE_PLUGIN_ROOT}/docs/dispatch-briefing-template.md` — composed from the file, never from memory: a reassembled briefing drops pieces silently, and every briefing on disk before INC-208 was missing one), saved at dispatch with `--prompt-file`, the explicit Read list, and its compaction drawer path — role contract: `agents/roles/operations.md`. **At disposition, never at discovery**, and when this run was invoked by `/friday:harden`, harden owns the merged dispatch across both channels and this one does NOT fire (D5). A declined offer dispatches nothing.

### Close

The PM knows where the system bends when someone leans on it who never read the spec — and the spec gets smarter every time. Commit on the PM's word; never push unless they say so.
