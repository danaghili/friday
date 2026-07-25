#!/usr/bin/env python3
"""INC-001 FR-1.2/FR-1.4 — compaction filing (PostCompact; the payload
carries the finished `compact_summary`, probe-proven). Contract:
docs/contracts/compaction-package.md.

Files every summary through the single substrate writer: an append-only
timestamped generation always; the authoring agent's `current.md` only when
the summary's first line self-identifies (`handoff-of: <slug> — <scope>`).
An unparseable header parks the summary in the unattributed drawer without
touching any current pointer — nothing is ever lost, nothing is ever
clobbered.

Fail-open: an error is stderr-only; the session is never blocked.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        if not fs.should_engage(cwd):
            return 0
        summary = event.get("compact_summary")
        if not isinstance(summary, str) or not summary.strip():
            return 0
        session_id = event.get("session_id") or "unknown-session"
        fs.compaction_file_summary(cwd, session_id=session_id, summary=summary)
    except Exception as exc:
        print(f"compaction_filing: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
