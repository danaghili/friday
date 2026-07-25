---
name: bug
description: run when the PM reports something known to be broken — diagnosis first, fix on their word
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:bug` — offer it before any work: “That sounds broken — run `/friday:bug` for a diagnosis you can read before any fix?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:bug` — the lane for something known to be broken. The PM gets a **diagnosis they confirm before any code changes**, and a fix that can never quietly regress (contract: the approved `/friday:bug` behavior paragraph; the debugger's own contract is `agents/roles/debugger.md` — this door arms what that contract expects).

### Phase 1: Intake

- **One bug per report.** A mixed report is split into separate BUG-NNNs before anything else — mixed reports can't be closed cleanly.
- Complete the skeleton WITH the PM: **what I did / what I expected / what happened instead** (their words; fill gaps by asking, not guessing). If this run was routed from `/friday:feedback`, the conversation arrived with it — consume it, never re-ask.
- **Capture the environment while it's fresh**: branch + commit, OS/runtime versions, the data state that matters, exact reproduction steps as reported.
- **Duplicates and past rulings BEFORE any re-derivation**: grep `docs/BUGS.md` and `docs/feedback-log.md`; a match is cited and this report becomes `duplicate-of` (or reopens the old number on new evidence).
- Mint `BUG-NNN` (next number from `docs/BUGS.md`; create the file with an H1 if absent — growing-log discipline: cap 100, archive the oldest half to `docs/bugs/archive-NNN.md`).
- **Declare the close artifacts in the entry:** the minted record names its trail and regression-test paths (`**Trail:** docs/trails/BUG-NNN.md · **Regression test (declared):** tests/test_bug_NNN_<slug>.py`), declared in the `docs/BUGS.md` entry at intake. This is the declaration-before-action beat — the paths are elicited once, here, and consumed verbatim when the lane arms at fix-start; a later deviation is provable, not deniable.

### Phase 2: Diagnose (spawn or in-context)

Small and obvious → work in-context under the same discipline. Otherwise spawn the Debugger (`friday-debugger`, model: **sonnet** — named, never inherited; telemetry: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-debugger --phase bug:BUG-NNN`). The spawn message carries the completed skeleton, the environment capture, the routed conversation if one exists, the intake-declared trail and regression-test paths (the committed test lands at exactly the declared path — the close guard consumes it verbatim), and the explicit Read list.

The discipline is the debugger contract's, in force on BOTH paths:

- **Reproduce FIRST** — before prioritizing, before theorizing. Non-reproducible → a specific question back to the PM, not a stall; unpindownable → closed honestly as exactly that, reopenable on new evidence. That honest close carries no regression test and no armed lane — diagnosis runs lane-free, so there is no door to un-stick; write the honest trail and close the entry (Phase 5).
- **Written hypothesis loop** — predicted result stated before each experiment, one change at a time, reverted if it didn't help; every cycle lands in the trail's record, failures included.
- **Fix at the source** — the why-chain bottoms out in specific code with a mechanism, confirmed both ways. "It stopped happening" is never closure.

### Parallel fan-out (narrow)

For genuinely independent bugs in DISJOINT subsystems only (no shared state): one Debugger each, each in its own worktree (`git worktree add ../bug-NNN`). The `.friday/` substrate stays SHARED automatically (git common dir) — journal, decision ids, and the lane sentinel never fragment; never point a tool at a per-worktree substrate path. One lane-open sentinel means one lane at a time per project — diagnosis fans out lane-free; arm and close one confirmed fix at a time.

### Phase 3: The show-your-diagnosis gate — the PM confirms BEFORE any fix

Relay to the PM: reproduction, root cause, proposed fix, blast radius — plus the two drafted one-word calls (*how bad*, as a concrete consequence; *when*, fix now / next lane). **No source line changes until the PM confirms.** The turn ends here with the gate in the PM's hands — no lane is armed yet, so the pause is free. Three failed fix attempts after confirmation trips the circuit breaker: stop, hand the PM the audit trail and raw symptoms, withhold the pet theory so fresh eyes start clean.

### Phase 4: Arm the lane, then fix under build law

The PM's confirmation starts the fix — arm the lane NOW, with the exact paths the intake entry declared:

```
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lane.py" open --lane bug --id BUG-NNN \
  --trail docs/trails/BUG-NNN.md \
  --regression-test tests/test_bug_NNN_<slug>.py
```

This writes the `.friday/lane-open` sentinel (contract: `docs/contracts/lane-open.md`). From this moment the bug-close guard holds the door: the session cannot conclude until the named regression test exists AND the trail at `docs/trails/BUG-NNN.md` passes the change-trail grammar (`docs/contracts/change-trail.md`).

The reproduction becomes a **failing regression test at the declared path, committed FIRST**; the fix takes it green; the **full suite** proves nothing else broke — real output quoted. The path that carried this bug gets guards at the layers it fooled — part of this fix, targeted, never scattered.

### Phase 5: Close

Write the trail (in-context path) — or verify the Debugger's written trail (spawn path; its role contract claims the same artifact) — at `docs/trails/BUG-NNN.md` (change-trail grammar: Asked / Decisions as D-NNNN pointers or the explicit none-line / Proof with real output / one changelog line). Flip the `docs/BUGS.md` entry status. The lane's guards disarm on a passing close — a blocked close names exactly what's missing. **A non-reproducible or unpindownable bug reaches its verdict at diagnosis, before any lane is armed — write its honest trail (what was tried, failures included) and close the entry; there is no sentinel to clear. If a bug proves unpindownable only after the lane armed, clear it deliberately: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lane.py" clear --by lead` (your own honest close, recorded as exactly that — never stamped a PM escalation).** Commit on the PM's word; never push unless they say so.
