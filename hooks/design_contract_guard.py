#!/usr/bin/env python3
"""Guard #10 — design-contract gate (PreToolUse Edit|Write|MultiEdit, BLOCK
tier; TECHNICAL_SOW_REBUILD FR-55 guard #10; D-0018 event mapping).

Cheap short-circuit BEFORE spawning a checker: only a path under
docs/contracts/ or docs/design/ is even a candidate. The judgment (is the
file already committed — i.e., a LOCKED contract — and if so does the
decision log carry its re-sync record) lives in
tools/design_contract_check.py.
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_GLOBS = (os.path.join("docs", "contracts", "*"), os.path.join("docs", "design", "*"))


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
        if not any(fnmatch.fnmatch(rel, g) for g in _GLOBS):
            return 0

        checker = os.path.join(plugin_root, "tools", "design_contract_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--path", path, "--root", wroot],
            timeout_s=timeout)
        action = _guard.decide(verdict, "block", _guard.block_message(
            f"this edit to {path} — a locked design contract",
            (verdict.get("summary") or "the file is committed and no re-sync "
             "decision names it") + ". A design contract is cited by name on "
            "both sides of a filesystem handoff; editing it silently breaks "
            "the other side's assumption without a trace.",
            "if the re-sync is intentional, record it with: python3 "
            "tools/decisions_append.py --title \"...\" --override-grant "
            "<contract-path> ... — the entry must carry an override-grant "
            "naming the contract's exact repo-relative path — then retry the edit",
            "a decision entry carrying an override-grant for the path unlocks "
            "this edit; a brand-new (uncommitted) file is never blocked"))
        if action.kind == "block":
            print(json.dumps(_guard.emit_block("PreToolUse", action.reason)))
        elif action.detail:
            print(f"design_contract_guard: no verdict, failing open: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"design_contract_guard: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
