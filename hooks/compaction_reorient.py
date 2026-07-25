#!/usr/bin/env python3
"""INC-001 FR-1.8/FR-1.9 — post-compaction re-orientation (SessionStart,
matcher `compact`; additionalContext injection is probe-proven for the main
session). Contract: docs/contracts/compaction-package.md.

Delivers the main session's four-layer package by push: mission note,
orientation note, the latest attributed floor summary, and the task-list
reminder — plus the deterministic backfill rebuilt from friday's records
(open-lane sentinel, git HEAD), so re-entry never depends on the summary
alone (FR-1.9). Subagents are pull-based by design (KH-2) — this hook serves
the main session's drawer only.

Empty case: no package yet → inject nothing (a session that never compacted
context needs no re-orientation). Fail-open throughout.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

MAIN_AGENT = "friday-lead"
_CAP = 4000  # chars per layer in the injection; the files remain the record


def _clip(text: str | None) -> str | None:
    if text is None:
        return None
    return text if len(text) <= _CAP else text[:_CAP] + "\n[truncated — read the file]"


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        if event.get("source") != "compact" or not fs.should_engage(cwd):
            return 0
        session_id = event.get("session_id") or "unknown-session"
        pkg = fs.compaction_read_package(cwd, session_id=session_id, agent=MAIN_AGENT)
        if not any(pkg[k] for k in ("mission", "orientation", "current")):
            return 0
        parts = ["COMPACTION RE-ORIENTATION (contract: compaction-package). "
                 "Your durable package, rebuilt from records:"]
        if pkg["mission"]:
            parts.append("## Mission (self-authored at lane entry)\n" + _clip(pkg["mission"]))
        if pkg["orientation"]:
            parts.append("## Orientation note (what you learned early)\n" + _clip(pkg["orientation"]))
        if pkg["current"]:
            parts.append("## Latest floor summary (what the compaction kept)\n" + _clip(pkg["current"]))
        lane = os.path.join(fs.friday_dir(cwd), "lane-open")
        if os.path.isfile(lane):
            try:
                with open(lane, encoding="utf-8") as fh:
                    parts.append("## Open lane (record)\n" + fh.read().strip())
            except OSError:
                pass
        head = fs._git(cwd, "rev-parse", "--short", "HEAD")
        if head:
            parts.append(f"git HEAD: {head}")
        parts.append("Re-read your live task list (TaskList) before continuing — "
                     "it is the source of truth for outstanding work.")
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n\n".join(parts)}}))
    except Exception as exc:
        print(f"compaction_reorient: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
