# The build story — how friday built itself

*The curated proof-story of friday's own construction. friday is an ID-9
self-build: the recipe that built it is the recipe it ships. The full raw
record — every decision entry, study artifact, and audit — lives in the
private lab this repository was curated from; what follows is the narrative
and the load-bearing decisions, told honestly.*

## The bet

Most AI coding tools add capability; friday adds governance. The founding
observation, written into the very first decision entry: **every handoff seam
between agents is where integration failures live.** So the recipe removes
seams from the middle and spends its ceremony at the edges:

**Heavy front · light middle · synthesized back.**

- **Heavy front** — a dedicated interrogator (the grilling protocol) presses
  a rough idea into a build-ready Technical Scope of Work. The PM approves
  the *written file* on their own read — never a summary — and that approval
  is the one big gate. Everything downstream is measured against it.
- **Light middle** — one continuous build pass, architect and developer hats
  in a single context. The build stalls on questions only the PM can answer
  (it never parks them), records every decision as it goes — with the roads
  not taken — and never edits its own oracle.
- **Synthesized back** — documentation is extracted from the code and
  grounded in the decision log, with the extractor-vs-synthesis diff as a
  checked oracle. Docs that drift from the code are a *detected defect*, not
  a quiet embarrassment.

## The doctrine

friday never trusts its own self-report. The whole control plane follows
from that one sentence:

- **Oracles everywhere.** The approved TSOW is the build's oracle (a hook
  physically guards it from edits); the code is the documentation's oracle;
  requirement coverage closes over both, ID by ID.
- **Two-channel decision capture.** PM-gated choices surface in a typed ask
  shape — a hook writes the decision log automatically when the PM answers,
  so the harness guarantees the record. Autonomous choices are logged at
  decision time, never batched. The **Rejected** line is the most important
  one: finished code can never show the roads not taken.
- **Independent hardening, once.** After the build, fresh-context agents
  re-derive every completion claim, refute-hunt the diff, run the release
  gate, and verify the security promises — over a sanitized read-only mirror.
  Hardening *finds*; the PM decides what gets fixed. A reproduced defect gets
  a failing test before its fix.
- **Fail-open hooks, fail-closed backstops.** Some forty hooks fire across
  the session lifecycle, and every one degrades to *not blocking* — a false
  block is worse than a miss. The durable guarantees are out-of-band:
  tree-hash receipts, and stop-gates that refuse to close a state the
  artifacts on disk don't back.
- **Secrets are names, never values.** No friday code path reads a secret
  value — structurally, not by policy.

## The rebuild

The first working friday accumulated ceremony: per-feature checkpoint files,
wave trees, approval queues. The v0.5 rebuild (July 2026) was a deliberate
demolition — the whole system rebuilt through its own recipe, with the old
system's hard-won lessons written into the new TSOW as named requirements so
the one-shot build couldn't drop them silently. Five command surfaces were
killed, the checkpoint ceremony retired, and the recipe compressed into the
shape above. Version stayed at 0.5.0 — humility before the Definition-of-Done
gate, on the record.

## The increments

After the rebuild closed, growth continued through the same mechanics —
each increment its own grilled, PM-approved oracle:

1. **Compaction continuity** — hooks steer, file, and re-orient across
   context compaction, so even the model's memory management is under
   contract. Validated live: the first real auto-compaction produced a
   steered, attributed summary and mid-procedure resumption.
2. **Lanes become skills** — the command surfaces migrated to the skills
   substrate, with a generated index that can never drift from the lanes it
   describes.
3. **Lane bundling** — the single-homing rule: a file lives with the one
   lane that uses it, or once in shared docs, never both.
4. **Runtime scriptification** — repeated ad-hoc scripts earn promotion to
   tools through a ranked candidate register, by danger × identical-operation,
   never raw frequency.
5. **Proposals ledger** — one file per proposal, folders as status; a ship
   requires validated evidence, not intention.
6. **Project-owned `.claude/` scaffold** — new projects are seeded with
   settings and path-scoped rules derived from their confirmed stack, so
   conventions load structurally instead of relying on agent memory.
7. **Model-invocable lanes** — the typed-only wall retired for an
   offer-first discipline: friday may recognize the moment, but only the PM
   opens the door.
8. **Going public** — this release: a fresh, curated, MIT-licensed
   repository; the lab stays private and intact.

## The field trial

Before going public, friday ran on real projects — greenfield builds
scaffolded through `/friday:init` and an existing system brought under
management with `/friday:backfill`. The deep-clean audit (`/friday:reconcile`)
ran end-to-end on friday's own repository — six record verifiers, a
re-proof of the living-system rows by spawned experts, the full guard
battery, and a parked-pile roundup — and the release decision itself went
through the same grilling protocol as any other increment, one-way doors
teach-backed and all.

That last part is the point. The tool you're reading about was used, at
every step, to build and govern itself — and the record it kept is why this
story can be told without guessing.

*Generated as the curated proof-story for the public release (INC-8,
approved 2026-07-25). The raw decision log (100+ entries), study artifacts,
and audits remain in the private lab, per the same decision that shipped
this repo.*
