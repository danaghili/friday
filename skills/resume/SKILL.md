---
name: resume
description: crash reconnaissance against the mid-build state model — reconstruct, then continue
friday-lane: true
disable-model-invocation: true
---

You are the lead running `/friday:resume` — crash reconnaissance against the mid-build state model: reconstruct where a dead session left the build and continue safely.

**Files are authoritative; the journal is a hint, never trusted alone.**

(Any agent you dispatch during recovery emits telemetry via `spawn_telemetry.py` --emit spawn/accept/done.)

### Phase 1: Liveness

List `.friday/sessions/*.lock` (the substrate is shared across worktrees — one place to look). For each lock: a `ts` older than ~60s with its `pid` dead = a crashed session (absence-of-ticking IS the crash signal — no other crash detector exists); a fresh `ts` = a LIVE concurrent session — do not touch its work; ask the PM before proceeding.

### Phase 2: Reconstruct

1. `CLAUDE.md` FRIDAY-STATE block → the declared state (`tsow-approved | substrate-seeded | build-in-progress | post-build-review-recorded | closed`; the vocabulary is CLOSED — contract: `docs/contracts/state-record.md`).
2. `python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_state.py" --root . --json` → does the record back the declaration? (Precision-first: an in-flight trail is consistent; a declared close without artifacts is the finding.)
3. `tail .friday/journal.jsonl` → last events (state-transition, decision-captured, spawn/done, session-end vs nothing = hard crash mid-turn).
4. `docs/DECISIONS.md` tail + `git status --porcelain` + `git log --oneline -5` → what was actually mid-flight. `.friday/asks/` → a pending decision-ask the dead session was STALLED on. Re-surface it FIRST, before any other re-entry step, as a fresh **live** decision-ask (so the answer lands in `DECISIONS.md` via the capture hook) — an unanswered question survives the crash; it never evaporates.
5. `.friday/seam-handoff.md` if present → a deliberate seam was forced — but presence is not proof of liveness (NF13): cross-check its `Generated` stamp and named next-unit against the current FRIDAY-STATE, `git log` since that stamp, and the journal before honoring it. A brief the work has outlived (unit already shipped, state past it, or commits show the named work done) is STALE — surface it to the PM and clear it through the single writer (`python3 "${CLAUDE_PLUGIN_ROOT}/tools/seam_handoff.py" --root . --clear --reason "<why>"`), never resume from it. A live brief → the next unit starts from it.
6. The main session's compaction package if present (`.friday/compaction/<newest session>/friday-lead/` — mission, orientation, `current.md`; contract: `docs/contracts/compaction-package.md`) → the dead session's own continuity record: its lane-entry mission, what it learned, and what its last compaction preserved. A different mechanism from the seam handoff in step 5 — never conflate the two.

### Phase 3: Classify + continue

- `tsow-approved` → the session died between TSOW approval and substrate seeding (the stub-CLAUDE.md window — D-0105). Offer `/friday:init`: it skips Stage 2 (TSOW present) and resumes at the un-run stages, ending with the Strategist's seed.
- `substrate-seeded`, nothing dirty → offer `/friday:build`.
- `build-in-progress`, dirty tree → summarize the reconstruction to the PM (state, last journal events, dirty files, last decisions) and offer: continue the build in-context / re-verify first. On continue, re-read the TSOW section in flight before writing anything.
- `post-build-review-recorded` → **spawn `friday-closer`** (model: **haiku** — named, never inherited; telemetry: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-closer --phase resume:close`; spawn message carries the resolved `<tools>` path, the TSOW path, and the explicit Read list — D-0104) for the K-gated close.
- `closed` but verifier fails → route to `/friday:reconcile`.
- Armed sentinels (`.friday/state-inconsistent`, `.friday/review-format-invalid`) → surface them FIRST; they explain why the previous session couldn't conclude.
