#!/usr/bin/env python3
"""Guard #8 — graph freshness (PostToolUse Write|Edit|MultiEdit, WARN tier;
TECHNICAL_SOW_REBUILD FR-56 guard #8, FR-71). The warn-tier EXEMPLAR the
stamper copies: same skeleton shape as a blocking guard, but decide() runs
at tier='warn' and the emission is emit_warn — a systemMessage, never a
block (a stale graph is a caution, not a lie in the record).

Cheap no-op: one stat() when no graph stamp exists (graph never adopted —
the SOFT-integration posture, FR-68). Always exits 0.
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
        if not os.path.isfile(os.path.join(fs.friday_dir(cwd), "graph.stamp")):
            return 0
        checker = os.path.join(plugin_root, "tools", "graph_freshness_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--root", cwd], timeout_s=timeout)
        action = _guard.decide(
            verdict, "warn",
            verdict.get("summary") or "the code graph may be stale")
        if action.kind == "warn":
            print(json.dumps(_guard.emit_warn(action.reason)))
        elif action.detail:
            print(f"graph_freshness_guard: no verdict, staying quiet: "
                  f"{action.detail}", file=sys.stderr)
    except Exception as exc:
        print(f"graph_freshness_guard: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
