#!/usr/bin/env python3
"""Guard — standing-care due-signals (SessionStart, WARN tier; D-0111).

Thin per the skeleton doctrine: read event → run_checker → decide → emit. The
judgement lives in `tools/state_advisory_check.py --mode due`; the threshold is
the project's own `reconcile-due:` line (contract: `docs/contracts/
state-record.md`).

Two signals, both scoped to a CLOSED project, because that is where silence is
most costly (NF10 — nothing anywhere used to say a finished project's handover
was due, and a closed record's re-verification has no build rhythm to ride):

1. closed + no `docs/handoff/README.md` → the handover never happened;
2. closed + `last-verified:` older than the project's bar → a reconcile is due.

**Natural moments only — no cron, no nagging** (D-0111's exact ruling). This
fires once, at session start, and deliberately NOT on the `compact` source: a
compaction re-entry is the middle of work, not a moment the PM is choosing what
to do next. Never blocks; a broken checker stays silent (no-verdict fail-open).

Cheap no-op: the checker stops at the first read of the state record for every
project that is not closed, which is almost all of them, almost always.
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
    if event.get("source") == "compact":
        return 0  # mid-work re-entry, not a natural moment (D-0111)
    try:
        wroot = fs.resolve_worktree_root(cwd)
        checker = os.path.join(plugin_root, "tools", "state_advisory_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--root", wroot, "--mode", "due"],
            timeout_s=timeout)
        action = _guard.decide(
            verdict, "warn",
            verdict.get("summary") or "a standing-care item may be due")
        if action.kind == "warn":
            print(json.dumps(_guard.emit_warn(action.reason)))
        elif action.detail:
            print(f"due_signal: no verdict, staying quiet: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"due_signal: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
