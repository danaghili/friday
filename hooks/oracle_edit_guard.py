#!/usr/bin/env python3
"""Guard #3 — oracle-edit gate (PreToolUse Edit|Write|MultiEdit, BLOCK tier;
TECHNICAL_SOW_REBUILD FR-55 guard #3; D-0018 event mapping).

Thin per the skeleton doctrine: read event → run_checker → decide → emit.
Cheap short-circuit BEFORE spawning a checker: only a path matching
`docs/TECHNICAL_SOW*.md` is even a candidate oracle; every other edit is a
stat-free no-op. The judgment (is this oracle's coverage ledger already
mid-closure, and if so does the decision log carry the amendment) lives in
tools/oracle_edit_check.py.
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_ORACLE_GLOB = os.path.join("docs", "TECHNICAL_SOW*.md")


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
        rel = os.path.relpath(os.path.abspath(path), wroot)
        if not fnmatch.fnmatch(rel, _ORACLE_GLOB):
            return 0

        checker = os.path.join(plugin_root, "tools", "oracle_edit_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--path", path, "--root", wroot],
            timeout_s=timeout)
        action = _guard.decide(verdict, "block", _guard.block_message(
            f"this edit to {path} — an oracle whose closure is already underway",
            (verdict.get("summary") or "the oracle's coverage ledger already "
             "holds dispositions") + ". Once a coverage ledger starts closing "
            "over an oracle, the oracle is frozen: an unrecorded edit could "
            "quietly change what the ledger's dispositions were closing over.",
            "if the PM approves this change, record it with: python3 "
            "tools/decisions_append.py --title \"PM amends <oracle>\" "
            "--override-grant <oracle-path> ... — the entry must carry an "
            "override-grant naming the oracle's exact repo-relative path — "
            "then retry the edit",
            "a decision entry in docs/DECISIONS.md carrying an override-grant "
            "for the oracle path unlocks this edit"))
        if action.kind == "block":
            print(json.dumps(_guard.emit_block("PreToolUse", action.reason)))
        elif action.detail:
            print(f"oracle_edit_guard: no verdict, failing open: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"oracle_edit_guard: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
