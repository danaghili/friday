# Contract: the lane-open sentinel

The arming contract for guard #6 — lane close without its trail
(TECHNICAL_SOW_REBUILD FR-55 guard #6, FR-62, AC-23). Producers: the
maintenance-lane doors (bug / patch — U3 work) and any spine surface that
opens a feature-lane change; they write the sentinel when a lane opens and
NEVER remove it themselves — removal is the guard's disarm-on-pass, or the
PM's conscious escalation. Consumer: `hooks/lane_close_gate.py` at Stop
time. Both sides cite THIS file.

## The shape

One JSON object at `<shared .friday>/lane-open` (substrate root — worktrees
share it, per Appendix B):

```json
{"lane": "bug|patch|feature", "id": "<the change's id>",
 "trail": "<worktree-root-relative path the lane committed to>",
 "regression-test": "<tests/*.py path — REQUIRED when lane=bug>",
 "blast-radius": ["<repo-relative path prefix or glob>", "..."]}
```

- The lane door declares the trail path AT OPEN — elicit once, consume many;
  the guard never guesses where trails live.
- **`regression-test`** (REQUIRED when `lane=bug`, consumer:
  `hooks/bug_close_gate.py` + `tools/bug_close_check.py`, guard #11, S-1): a
  worktree-root-relative `tests/*.py` path naming the committed regression
  test the bug fix must carry — no bug closes without one. The bug door arms
  at fix-start, after the PM confirms the diagnosis (D-0069); its trail and
  regression-test paths are declared in the `docs/BUGS.md` entry at intake
  and consumed verbatim here (diagnosis runs lane-free, so the guard never
  fires on the diagnosis gate's own pause).
- **`blast-radius`** (REQUIRED when `lane=patch`, consumer:
  `hooks/blast_radius_guard.py` + `tools/blast_radius_check.py`, guard #12,
  S-2): a list of repo-relative path prefixes or fnmatch globs the patch
  declared AT OPEN as everything it may touch, tests included. `lane_open`
  unions the lane's own `trail` path into this list by construction — the
  mandated record-write is never blocked by the lane's own guard (NF12,
  D-0112).
- While the sentinel exists, the session cannot conclude unless the trail at
  that path passes `tools/trail_check.py` (contract:
  docs/contracts/change-trail.md), decision references cross-checked against
  `docs/DECISIONS.md`.
- **Disarm paths, exactly two:** (1) the lane's OWNING guard removes the
  sentinel on pass — `hooks/bug_close_gate.py` for `lane=bug` (its bar is
  trail AND regression test; D-0023), `hooks/lane_close_gate.py` for every
  other lane (bar: the trail); one owner per lane, never both; (2) it is
  cleared deliberately (`lane_clear` / `tools/lane.py clear`) — either the
  conscious **PM escalation** (`by=pm`, the default, named in the block
  message) or a **door's own honest re-route/close** (`by=lead`: a patch
  outgrowing its radius, a bug closing unpindownable); the journal records
  which, so a lead's re-route is never stamped a PM escalation.
- An unreadable sentinel fails OPEN and stays in place (visible rot, guard
  #21's territory), never blocks.

Tests: `tests/test_guard_lane_close.py` (positive control, all four
fail-open controls, disarm-on-pass, sentinel edges).
