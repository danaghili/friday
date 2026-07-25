#!/usr/bin/env python3
"""Guard #1 — profile validity after profile writes (PostToolUse Write|Edit|
MultiEdit, BLOCK tier; TECHNICAL_SOW_REBUILD FR-55 guard #1).

Arms ONLY when the written file is the USER-GLOBAL profile: its normalized
path ends with `/.claude/CLAUDE.md` (a `.claude` DIRECTORY component) — a
project's own root CLAUDE.md must never match, regardless of content. Not
gated on fs.is_friday_project: the profile is user-global, written by
/friday:profile from anywhere, not scoped to any one project. The judgment
(are all ten pinned subsections present with content) lives in
tools/profile_check.py.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402


def _is_global_profile_path(path: str) -> bool:
    norm = os.path.normpath(os.path.abspath(path)).replace(os.sep, "/")
    return norm.endswith("/.claude/CLAUDE.md")


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    if fs is None:
        return 0
    try:
        tool_input = event.get("tool_input") or {}
        path = tool_input.get("file_path")
        if not isinstance(path, str) or not path.strip():
            return 0
        if not _is_global_profile_path(path):
            return 0

        checker = os.path.join(plugin_root, "tools", "profile_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--file", path], timeout_s=timeout)
        action = _guard.decide(verdict, "block", _guard.block_message(
            "this write to the collaboration profile left it structurally broken",
            (verdict.get("summary") or "one or more subsections are missing or "
             "empty") + ". Every friday session reads this profile — a "
            "half-written one silently degrades how every project collaborates "
            "with you.",
            "restore the missing subsections (run /friday:profile to regenerate "
            "rather than hand-editing)",
            "if this partial shape is intentional, record a decision via "
            "tools/decisions_append.py naming ~/.claude/CLAUDE.md"))
        if action.kind == "block":
            print(json.dumps(_guard.emit_block("PostToolUse", action.reason)))
        elif action.detail:
            print(f"profile_guard: no verdict, failing open: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"profile_guard: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
