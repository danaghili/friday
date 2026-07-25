#!/usr/bin/env python3
"""Guard #11 — bug-close gate (Stop, BLOCK tier; TECHNICAL_SOW_REBUILD FR-55
guard #11, S-1: "Bug closure is guard-gated: no closure without the
committed regression test and the completed trail"). Contract:
docs/contracts/lane-open.md (the `regression-test` field, required when
lane=bug).

Arms when the shared `.friday/lane-open` sentinel exists AND its lane ==
"bug" — a cheap read-and-check before ever spawning a checker. The judgment
(does the sentinel name an existing committed regression test, does the
trail it points at pass tools/trail_check.py's grammar) lives in
tools/bug_close_check.py.

THIS GUARD OWNS BUG LANES OUTRIGHT (D-0023, interim finding): it judges the
full bug bar (trail AND regression test) and DISARMS the sentinel on pass.
hooks/lane_close_gate.py ignores lane=bug entirely — two guards sharing one
sentinel meant #6's disarm side-effect could erase the arming in the same
Stop where this gate blocked, letting the next Stop close a bug with no
regression test (the exact hole S-1 exists to close).
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
        except Exception as exc:
            print(f"bug_close_gate: unreadable lane-open sentinel, failing "
                  f"open: {exc}", file=sys.stderr)
            return 0
        if lane.get("lane") != "bug":
            return 0

        wroot = fs.resolve_worktree_root(cwd)
        checker = os.path.join(plugin_root, "tools", "bug_close_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--root", wroot, "--sentinel", sentinel],
            timeout_s=timeout)
        action = _guard.decide(verdict, "block", _guard.block_message(
            f"ending the session while the bug lane ({lane.get('id', '?')}) "
            "is still open without its regression test and trail",
            (verdict.get("summary") or "the sentinel's regression-test field "
             "or trail is missing or invalid") + ". A bug fix without a "
            "committed regression test is a fix that can silently break "
            "again — the test is the proof the bug stays dead.",
            "commit the regression test named in the lane-open sentinel and "
            "write a valid trail (docs/contracts/change-trail.md), then close "
            "the lane again",
            "if you are deliberately handing this unfinished lane to the PM, "
            "remove .friday/lane-open — the conscious escalation path"))
        if action.kind == "block":
            print(json.dumps(_guard.emit_block("Stop", action.reason)))
        elif verdict.get("verdict") == "valid-pass":
            try:
                os.remove(sentinel)  # bug lane properly closed — disarm
            except OSError:
                pass
        elif action.detail:
            print(f"bug_close_gate: no verdict, failing open: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"bug_close_gate: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
