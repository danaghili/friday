#!/usr/bin/env python3
"""Guard #6 — lane close without its trail (Stop family, BLOCK tier;
TECHNICAL_SOW_REBUILD FR-55 guard #6, FR-62, AC-13/14/15/23).

Armed by the `<shared .friday>/lane-open` sentinel (contract:
docs/contracts/lane-open.md): a maintenance-lane door writes it when a lane
opens, carrying the trail path the lane committed to. At Stop time, an armed
sentinel means a change is still open — the session may not conclude until
the trail at that path passes tools/trail_check.py (contract:
docs/contracts/change-trail.md), decision references cross-checked against
docs/DECISIONS.md.

valid-pass → disarm (the lane is properly closed) and allow. valid-fail →
block with the four-part message. no-verdict → ALLOW and stay armed
(fail-open; a later Stop with a working checker still catches it) — the
same asymmetry as state_stop_gate.py. Removing the sentinel by hand is the
conscious PM-escalation path, and Claude Code caps consecutive Stop-blocks,
so this can never hard-lock a session.

BUG LANES ARE NOT MINE (D-0023, interim finding): every lane gets exactly
ONE Stop-time owner. lane=bug belongs wholly to hooks/bug_close_gate.py,
whose checker demands the regression test ON TOP of the trail and which
disarms on pass. If this guard also disarmed bug lanes on a passing trail,
its side-effect would erase the arming in the same Stop where the bug gate
blocked — reopening the very hole S-1 closes.

Cheap no-op everywhere: one stat() when no lane is open. Not
subagent-scoped (Stop is the session's own event) — identity self-verify is
N/A by design; the SubagentStop variant is a stamping-time decision for the
lane doors that run as teammates.

Env: FRIDAY_GUARD_TIMEOUT_S overrides the checker budget (tests exercise
the timeout control with it). Always exits 0; the block rides the JSON.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        sentinel = os.path.join(fs.friday_dir(cwd), "lane-open")
        if not os.path.isfile(sentinel):
            return 0
        try:
            with open(sentinel, encoding="utf-8") as fh:
                lane = json.load(fh)
            trail_rel = lane["trail"]
            lane_name, lane_id = lane.get("lane", "?"), lane.get("id", "?")
        except Exception as exc:
            # A sentinel we can't read is not a provable open lane — fail
            # open, leave it armed so the rot stays visible (guard #21's job).
            print(f"lane_close_gate: unreadable lane-open sentinel, failing "
                  f"open: {exc}", file=sys.stderr)
            return 0
        if lane_name == "bug":
            return 0  # one owner per lane: bug_close_gate judges AND disarms

        wroot = fs.resolve_worktree_root(cwd)
        checker = os.path.join(plugin_root, "tools", "trail_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker,
             "--file", os.path.join(wroot, trail_rel),
             "--decisions-log", os.path.join(wroot, "docs", "DECISIONS.md")],
            timeout_s=timeout)

        first_error = (verdict.get("errors") or ["the trail record is missing"])[0] \
            if verdict.get("verdict") == "valid-fail" else ""
        action = _guard.decide(verdict, "block", _guard.block_message(
            f"ending the session while the {lane_name} lane ({lane_id}) is "
            "still open without a valid change trail",
            "every change leaves a three-part record — what was asked, the "
            "decisions made, and proof it works. This one's record is missing "
            f"or incomplete: {first_error or 'see the trail checker'}",
            f"write the trail at {trail_rel} (shape: "
            "docs/contracts/change-trail.md), then close the lane again",
            "if you are deliberately handing this unfinished lane to the PM, "
            "remove .friday/lane-open — that is the conscious escalation "
            "path, and the missing trail becomes the PM's call"))
        if action.kind == "block":
            print(json.dumps(_guard.emit_block("Stop", action.reason)))
        elif verdict.get("verdict") == "valid-pass":
            try:
                os.remove(sentinel)  # lane properly closed — disarm
            except OSError:
                pass
        elif action.detail:
            print(f"lane_close_gate: no verdict, failing open (lane stays "
                  f"armed): {action.detail}", file=sys.stderr)
    except Exception as exc:
        print(f"lane_close_gate: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
