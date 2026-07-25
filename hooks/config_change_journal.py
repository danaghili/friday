#!/usr/bin/env python3
"""Guard #21 — config-change journaling (ConfigChange, SILENT tier;
TECHNICAL_SOW_REBUILD FR-57 guard #21: "guard tampering is visible, never
silent"). A doc-only harness event per probe-hook-events.md — fine if it
never fires.

No checker, no user-visible message — this only journals whatever
identifying fields the event itself carries (source/path keys, when
present), via the single writer. A guard's own configuration changing
mid-session is exactly the kind of tampering this record exists to make
visible after the fact, even though this guard itself takes no position on
whether a given change was legitimate.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_IDENTIFYING_KEYS = ("source", "path", "file", "setting", "key")


def _identifying_fields(event: dict) -> dict:
    return {k: event[k] for k in _IDENTIFYING_KEYS
            if isinstance(event.get(k), str) and event[k].strip()}


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
        fs.append_journal_line(cwd, fs.build_journal_line(
            "config-change", "session", by="session",
            data=_identifying_fields(event)))
    except Exception as exc:
        print(f"config_change_journal: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
