#!/usr/bin/env python3
"""Guard #12b — blast-radius Stop backstop (Stop, WARN tier;
TECHNICAL_SOW_REBUILD FR-56 guard #12b, S-2's Stop-time backstop warning).

Arms when the shared `.friday/lane-open` sentinel exists AND its lane ==
"patch" — same cheap read-and-check as guard #12. Reuses
tools/blast_radius_check.py's `--mode diff`: everything actually changed or
newly added this session, checked against the declared radius. Unlike
guard #12 (PreToolUse, blocks a single edit as it happens), this is a
whole-session sweep and NEVER blocks — emit_warn only, catching drift that
slipped past #12 (e.g. a tool #12 doesn't cover, or a radius edited mid-session).
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
            print(f"blast_radius_backstop: unreadable lane-open sentinel, "
                  f"staying quiet: {exc}", file=sys.stderr)
            return 0
        if lane.get("lane") != "patch":
            return 0

        wroot = fs.resolve_worktree_root(cwd)
        checker = os.path.join(plugin_root, "tools", "blast_radius_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--root", wroot, "--sentinel", sentinel,
             "--mode", "diff"], timeout_s=timeout)
        action = _guard.decide(
            verdict, "warn",
            verdict.get("summary") or "some changed files fall outside the "
                                      "patch's declared blast radius")
        if action.kind == "warn":
            print(json.dumps(_guard.emit_warn(action.reason)))
        elif action.detail:
            print(f"blast_radius_backstop: no verdict, staying quiet: "
                  f"{action.detail}", file=sys.stderr)
    except Exception as exc:
        print(f"blast_radius_backstop: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
