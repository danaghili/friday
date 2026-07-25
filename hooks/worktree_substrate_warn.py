#!/usr/bin/env python3
"""Worktree-substrate warn (SessionStart, WARN tier; D-0023 item 3 —
replaces guard #18a's protection with a cheap, always-on detector instead
of trying to police creation itself).

Cheap-first, same shape as the graph_freshness_guard exemplar but with no
checker at all — pure stat logic, like teammate_idle_nudge.py: only a
LINKED worktree (fs.resolve_worktree_root(cwd) differs from
fs.resolve_project_root(cwd)) is even a candidate; every plain repo (or
non-repo) is a stat-free no-op. Inside a linked worktree, a LOCAL
`.friday/` directory at the worktree's own root that differs from the
SHARED `.friday/` (fs.friday_dir) means this worktree accidentally grew its
own copy of the substrate — Appendix B's rule (worktrees isolate code, they
share substrate) is broken, and anything written to the local copy is
stale or lost the moment another session touches the real one. Never
blocks: emit_warn only, naming the fix in plain words.
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
        wroot = os.path.normpath(fs.resolve_worktree_root(cwd))
        proot = os.path.normpath(fs.resolve_project_root(cwd))
        if wroot == proot:
            return 0  # not a linked worktree — cheap short-circuit

        local_friday = os.path.join(wroot, ".friday")
        shared_friday = os.path.normpath(fs.friday_dir(cwd))
        if (os.path.isdir(local_friday)
                and os.path.normpath(local_friday) != shared_friday):
            print(json.dumps(_guard.emit_warn(
                "this worktree carries its own copy of the project's internal "
                "notebook (.friday/), shadowing the shared one — records "
                "written here will be stale or lost. Delete this worktree-"
                "local .friday/ copy (it is regenerable) so this worktree "
                "shares the real one.")))
    except Exception as exc:
        print(f"worktree_substrate_warn: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
