#!/usr/bin/env python3
"""Guard #7 — committed-test edit (PreToolUse, BLOCK tier; TECHNICAL_SOW_REBUILD
FR-55 guard #7, AC-13/14/15; probe: docs/research/rebuild/
probe-guard7-committed-test.md, measured 55–68 ms — inside the PreToolUse
budget).

Thin per the skeleton doctrine: read event → run_checker → decide → emit.
The judgment lives in tools/committed_test_check.py (typed verdict; the
whole fail-open matrix is normalized by _guard.run_checker). Not
subagent-scoped: fires for every session's Edit/Write/MultiEdit/NotebookEdit
in a friday project — identity self-verify is N/A here by design.

Env: FRIDAY_GUARD_TIMEOUT_S overrides the checker budget (tests use it to
exercise the timeout fail-open control without waiting out the default).
Always exits 0; a block rides the JSON (house idiom).
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
        if not fs.is_friday_project(cwd):
            return 0
        tool_input = event.get("tool_input") or {}
        # Payload is tool-specific (probe payload notes): Edit/Write/MultiEdit
        # carry file_path, NotebookEdit carries notebook_path. No path → this
        # call touches nothing this guard watches.
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not isinstance(path, str) or not path.strip():
            return 0

        checker = os.path.join(plugin_root, "tools", "committed_test_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--path", path, "--repo", cwd],
            timeout_s=timeout)
        action = _guard.decide(verdict, "block", _guard.block_message(
            f"this edit to {path} — a test file committed before the build started",
            (verdict.get("summary") or "the file predates the build epoch with no "
             "permission record") + ". Committed tests are the build's oracle: "
            "changing one mid-build can quietly change what \"passing\" means.",
            "if the test itself is wrong, ask the PM first; once they agree, "
            "record it with: python3 tools/decisions_append.py --title "
            "\"PM permits editing <file>\" --override-grant <file-path> ... — "
            "the entry must carry an override-grant naming the file's exact "
            "repo-relative path — then retry the edit",
            "a decision entry carrying an override-grant for the path unlocks "
            "this edit; writing a NEW test file is never blocked"))
        if action.kind == "block":
            print(json.dumps(_guard.emit_block("PreToolUse", action.reason)))
        elif action.detail:
            print(f"committed_test_guard: no verdict, failing open: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"committed_test_guard: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
