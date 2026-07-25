#!/usr/bin/env python3
"""Guard #12 — patch blast-radius (PreToolUse Edit|Write|MultiEdit|
NotebookEdit, BLOCK tier; TECHNICAL_SOW_REBUILD FR-55 guard #12, S-2).
Contract: docs/contracts/lane-open.md (the `blast-radius` field, required
when lane=patch).

Arms when the shared `.friday/lane-open` sentinel exists AND its lane ==
"patch" — a cheap read-and-check before ever spawning a checker. The
judgment (is the touched path inside the sentinel's declared blast radius)
lives in tools/blast_radius_check.py --mode edit, shared with guard #12b's
Stop-time --mode diff backstop.
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
            print(f"blast_radius_guard: unreadable lane-open sentinel, failing "
                  f"open: {exc}", file=sys.stderr)
            return 0
        if lane.get("lane") != "patch":
            return 0

        tool_input = event.get("tool_input") or {}
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not isinstance(path, str) or not path.strip():
            return 0

        wroot = fs.resolve_worktree_root(cwd)
        checker = os.path.join(plugin_root, "tools", "blast_radius_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--path", path, "--root", wroot,
             "--sentinel", sentinel, "--mode", "edit"], timeout_s=timeout)
        action = _guard.decide(verdict, "block", _guard.block_message(
            f"this edit to {path} — outside the patch's declared blast radius",
            (verdict.get("summary") or "the path was not in the declared "
             "radius") + ". A patch declares upfront everything it may touch "
            "— the patch's declared edit area; an edit outside that area is "
            "either scope creep or an area that was declared too narrow.",
            "if this file genuinely belongs to the patch, widen the "
            "declared blast-radius in the lane-open sentinel (the lane door "
            "owns that), then retry the edit",
            "there is no ad-hoc override — the patch's own radius must "
            "include this path"))
        if action.kind == "block":
            print(json.dumps(_guard.emit_block("PreToolUse", action.reason)))
        elif action.detail:
            print(f"blast_radius_guard: no verdict, failing open: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"blast_radius_guard: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
