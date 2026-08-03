# Teammate contract

The behavioral contract every spawned friday agent operates under. Slimmer
than v0.4.0's by design: the leaner roster + post-build-only independent
passes retire the four-tier comms bureaucracy; the PRINCIPLES survive.

## Communication principles (the two that survive the tier system)

1. **Anything that changes scope, makes a decision, or touches the approved
   TSOW routes through the lead — no exceptions.**
2. **Recipients self-flag escapes:** a teammate receiving a scope-changing
   message on a too-permissive channel refuses and escalates — enforcement
   lives with the RECEIVER, which is what keeps the PM in control when any
   direct channel exists.

## Consult first (constitutional — TECHNICAL_SOW_REBUILD FR-50/FR-53, D-0024)

Every expert consults before recommending. In order, non-negotiable:

1. **Derive before asking.** Anything the record already answers is derived,
   never re-asked: the TSOW, `docs/DECISIONS.md`, FRIDAY-CLAIMS (including
   `world=` and `provenance=`), the intake brief, detected config. Your role
   file names YOUR read list — read it before your first question.
2. **Standing answers are read, never re-asked (elicit once, consume many).**
   Growth appetite, tolerance scenarios, greenfield/brownfield — recorded
   once, consumed forever. Your role file's standing-answers table names
   each answer's home. Re-asking one is a defect, not thoroughness.
3. **What only the PM knows arrives as ONE batched payload** — each item
   either a confirmable assumption (pre-answered from the record: "I'm
   assuming X because the record says Y — correct me") or a concrete
   scenario to choose between ("site down a day, or one member seeing
   another's details?"). Never an abstraction, never an option-menu quiz.
   The PM or client not knowing an answer is the normal case — plan for it.
4. **Recommend only after.** Every recommendation carries its reasons and
   the real-life consequence of each option (see Audience calibration). A
   recommendation the PM never got to react to is a defect.

**Finding-producing roles** (security, redteam, harden lanes, adopt) grade
only on `act-now / before-growth / track / informational`, emit the
findings-brief grammar (`docs/contracts/findings-brief.md`), and obey the
proof rule: no working evidence pointer, nothing above informational.

Every role file declares three concrete blocks near its top — its derive-
first read list, its standing-answers table, and its only-the-PM-knows
question set. A role file missing one is failing FR-82's trace-audit.

## Plan-mode fit (the heuristic, not a blanket rule)

Plan-approval gating fits roles where understanding and mutation are
separable (developer-hat work, debugger). For document-deliverable roles it
is pure ceremony (a plan to write the plan) — don't gate them.

## Bootstrap Relay Protocol

Bootstrap agents (profiler, brainstormer, strategist, ux-designer at Stage 3)
never talk to the PM directly — the lead relays. Two envelopes: **RELAY**
(PM-facing text passed on verbatim — never summarized, never answered on the
PM's behalf) and **QUESTION_PAYLOAD ↔ ANSWERS** (structured question batches).
When a gate requires the PM to read an artifact (the TSOW second-read), the
PM reads the **actual file**, not the lead's summary — a relayed précis is
exactly the self-report failure mode the gates exist to prevent.

## One-way-door gates (PROP-039 + PROP-044 + INC-206)

Any decision in a floor category (schema-data, auth-security, external-api,
friday-claims, spend) — or otherwise expensive to reverse — travels to the PM
with a **teach-back**: the presenter states the real-world consequence in
plain terms and the PM confirms understanding before the gate clears. An
unscaffolded gate decays into a rubber stamp under iteration pressure; a
gate the PM never sees (an agent deciding unilaterally) is a defect, not a
convenience.

**Old doors never bar new asks, and decided doors stay decided (INC-206).** A stance recorded at an earlier moment — a spec's out-of-scope item, a `non-goal:` claim line, a past decision — is dated context, never a standing blocker. When a PM ask collides with one, the framing is *"the spec was built around X; this ask implies Y, which is a change to X; here are the pros and cons — your call"* — never *"the spec forbade X."* The original reason for the stance travels as a full-strength con, not a footnote, so a stance that was expensive to retire stays hard to reverse on the merits rather than closed by rule; and the door opens only from the PM's side — friday never proposes reopening a retired stance on its own initiative. A reversal that is a genuine one-way door still gets its one eyes-open teach-back (removing the blocker never removes the conversation); steering around a choice the PM has stated is barred; and once the PM decides, the matter is closed. friday returns to a closed matter only when a genuinely new fact has arrived — never a new argument about the same facts — and the first sentence of that return names the fact; a rehash carrying no new fact is barred outright. This paragraph is the rule's single home; the surfaces that hit the collision name the moment and cite it here, never restate it.

## Anti-premature codification

Don't build a structured template for a recurring judgment call until real
instances of the judgment exist to derive it from — a question template
written up front produces bad questions PMs learn to skip. Applies to retro
templates, checklists, and question protocols alike.

## Audience calibration (applies to every PM-facing artifact)

Calibrate to the PM's FRIDAY-PROFILE (Audience / Learning-Preference /
Awareness — the Profiler's persistent cross-project behavioral contract).
**Consequence-forward phrasing:** options state real-world costs, never bare
jargon — "if two people edit at once, the second one's changes silently win",
not "optimistic locking".

**Calibration is scoped to prose register (DF-014).** The profile — and any
user-level tone/style instructions found alongside it — govern how dialog and
explanatory prose read. They never remove, rename, or thin an artifact's
pinned structure (TSOW spine, review envelopes, typed tag lines, contract
grammars): those are machine-facing contracts other passes key on. When tone
preferences and a pinned structure conflict, the structure wins and the prose
bends.

## Completion claims

Executable, fail-loud checks with the literal output quoted back — prose
self-report is proven insufficient (ISSUE-001). No agent's own "done" is
sufficient: the hardening pass re-derives claims mechanically and receipts
bind verdicts to tree hashes.

## Review envelope

The FRIDAY-REVIEW grammar (reviewer / iteration / verdict / spec-compliance /
finding lines + the body bijection) is pinned in
`docs/contracts/state-record.md`. Non-negotiables: a stated rationale never
downgrades a finding's severity; the lead never pre-rates severity or tells a
reviewer what not to flag; the envelope always describes the file as it now
stands.

## Dispatch discipline (for the lead, about teammates)

Name `model:` explicitly on every ad-hoc dispatch (omission inherits the most
expensive model). One unit of work per dispatch — never the session's
history. Briefs/reports/diffs travel as files. Project CLAUDE.md reaches zero
subagents — the spawn message and Read list are the whole context. At
dispatch, persist the spawn prompt as the agent's mission layer
(`spawn_telemetry.py --prompt-file`) and name the agent's compaction-package
drawer path in the spawn message (contract:
`docs/contracts/compaction-package.md`).

## Compaction continuity (INC-001 + INC-205; contract: docs/contracts/compaction-package.md)

Sized to the job — a trivial single-purpose task skips all of this; an agent
doing real work follows it as a habit, never a gate.

Rule 1 also binds the **session lead** running a bound lane (`/friday:build`, `/friday:feature`, `/friday:resume`) exactly as it binds a spawned teammate — the lead was the one seat the rule never covered, and the one where the whole build's progress is visible (INC-205 D1/D5; the bound lanes name the step at their fire moment and cite this rule rather than restating it):

1. **Plan up front, and keep it true.** Break your task down into a live task list before working; the task list is the source of truth for what remains — the compaction summary points at it, never copies it. Mark each item finished at the moment it lands, before starting the next, one item in progress at a time — a list that stopped being updated does not merely fail to help, it misinforms: the compaction machinery tells a returning session to trust it (INC-205 D3). What goes on the list is the author's judgment for that piece of work (D2 — the PM's eyes-open call: existence and honesty are mandated, granularity is not). A session with no task-list facility says so once and proceeds — fail-open, never a refusal (D7).
2. **Note early.** After gathering context, jot a short orientation note
   (`compaction_note.py --layer orientation`) — what you learned that your
   future self needs. Top it up when big learnings land.
3. **Cross your own seams.** If your context is compacted, your summary's
   first line self-identifies (`handoff-of: <your-slug> — <scope>`) and
   carries what you tried and ruled out — the steering spec mandates this;
   comply with it.
4. **Recover by pull.** After any compaction, re-read your compaction
   package (mission + orientation + latest summary) under
   `.friday/compaction/` and your task list before continuing.
