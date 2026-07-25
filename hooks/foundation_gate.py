#!/usr/bin/env python3
"""Guard #4 — foundation gate (Stop, BLOCK tier; TECHNICAL_SOW_REBUILD FR-55
guard #4 — the K0 gate, restated stranger-proof).

Cheap pre-check reads CLAUDE.md directly and engages ONLY when its
FRIDAY-STATE block declares `state: build-in-progress` — every other state
(or no FRIDAY-STATE at all) is a stat-cheap no-op, never spawning a checker.
The judgment (is the claims block well-formed, does the named tsow: file
exist) lives in tools/foundation_check.py.
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
        try:
            with open(os.path.join(wroot, "CLAUDE.md"), encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return 0
        if "FRIDAY-STATE:BEGIN" not in text or "state: build-in-progress" not in text:
            return 0

        checker = os.path.join(plugin_root, "tools", "foundation_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--root", wroot], timeout_s=timeout)
        action = _guard.decide(verdict, "block", _guard.block_message(
            "ending the session while a build is claimed in progress but its "
            "foundation does not hold",
            (verdict.get("summary") or "the claims block or the named TSOW "
             "file is missing or malformed") + ". state: build-in-progress "
            "is a claim that the build's foundation record — the project "
            "claims and the plan document it points at — is real; that claim "
            "is never just asserted, it has to hold.",
            "fix the FRIDAY-CLAIMS block or the tsow: file it names (see the "
            "checker's detail above), then end the session again",
            "there is no override — a build cannot be claimed in progress "
            "over a broken foundation; fix the record itself"))
        if action.kind == "block":
            print(json.dumps(_guard.emit_block("Stop", action.reason)))
        elif action.detail:
            print(f"foundation_gate: no verdict, failing open: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"foundation_gate: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
