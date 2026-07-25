#!/usr/bin/env python3
"""Guard #5 — build-past-open-risks (PostToolUse Write|Edit|MultiEdit, BLOCK
tier; TECHNICAL_SOW_REBUILD FR-55 guard #5; D-0018 event mapping).

Cheap short-circuit BEFORE spawning a checker: only a write that lands on
the project's own CLAUDE.md is even a candidate — every other write is a
path-compare no-op. The judgment (is a build in progress, does its TSOW's
stack-risk register hold open rows with no decision on record) lives in
tools/open_risks_check.py.
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
        tool_input = event.get("tool_input") or {}
        path = tool_input.get("file_path")
        if not isinstance(path, str) or not path.strip():
            return 0
        wroot = fs.resolve_worktree_root(cwd)
        if os.path.abspath(path) != os.path.join(wroot, "CLAUDE.md"):
            return 0

        checker = os.path.join(plugin_root, "tools", "open_risks_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--root", wroot], timeout_s=timeout)
        action = _guard.decide(verdict, "block", _guard.block_message(
            "this CLAUDE.md write — the build's stack-risk register still "
            "holds open rows",
            (verdict.get("summary") or "one or more risk-register rows are "
             "still marked 'verify' with no decision on record") + ". A "
            "build-in-progress claim over an unresolved stack risk is the "
            "exact gap the plan's risk register exists to surface before "
            "it's buried in a build that's already underway.",
            "either settle the row (update the TSOW's Verdict column) or "
            "record the PM's call to proceed anyway with: python3 "
            "tools/decisions_append.py --title \"...\" --override-grant "
            "<risk-element> ... — the entry must carry an override-grant "
            "naming the risk element — then retry the write",
            "a docs/DECISIONS.md entry carrying an override-grant for the risk "
            "element unlocks this write"))
        if action.kind == "block":
            print(json.dumps(_guard.emit_block("PostToolUse", action.reason)))
        elif action.detail:
            print(f"open_risks_guard: no verdict, failing open: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"open_risks_guard: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
