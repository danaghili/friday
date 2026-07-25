#!/usr/bin/env python3
"""Guard #14 — research-consumer orphans (Stop, WARN tier;
TECHNICAL_SOW_REBUILD FR-56 guard #14, S-4).

Cheap no-op: one stat() when docs/research/ does not exist at all. The
judgment (does every research brief's consumer: value resolve to something
findable in the repo) lives in tools/research_orphan_check.py — deliberately
crude, documented, never blocking.
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
        wroot = fs.resolve_worktree_root(cwd)
        if not os.path.isdir(os.path.join(wroot, "docs", "research")):
            return 0
        checker = os.path.join(plugin_root, "tools", "research_orphan_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--root", wroot], timeout_s=timeout)
        action = _guard.decide(
            verdict, "warn",
            verdict.get("summary") or "one or more research briefs have no "
                                      "findable consumer")
        if action.kind == "warn":
            print(json.dumps(_guard.emit_warn(action.reason)))
        elif action.detail:
            print(f"research_orphan_warn: no verdict, staying quiet: "
                  f"{action.detail}", file=sys.stderr)
    except Exception as exc:
        print(f"research_orphan_warn: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
