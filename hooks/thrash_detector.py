#!/usr/bin/env python3
"""Guard #17 — thrash detector (PostToolUse Write|Edit|MultiEdit, WARN tier;
TECHNICAL_SOW_REBUILD FR-56 guard #17: "the same file churning without a
decision recorded").

No external checker — the journal itself is the evidence, read straight
through friday_substrate's single-writer contract. Every qualifying edit
first journals a `file-edited` event (repo-relative path); the hook then
reads the journal's last 200 lines and counts `file-edited` events for that
SAME path. At ≥5, it looks for a `decision-captured` event anywhere after
the earliest of those edits — if none appears, the file has been churning
with no decision on record, which warns (never blocks: circling is a
caution, not a lie).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_THRESHOLD = 5
_WINDOW = 200


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        if not fs.is_friday_project(cwd):
            return 0
        tool_input = event.get("tool_input") or {}
        path = tool_input.get("file_path")
        if not isinstance(path, str) or not path.strip():
            return 0

        wroot = fs.resolve_worktree_root(cwd)
        rel = os.path.relpath(os.path.abspath(path), wroot).replace(os.sep, "/")

        fs.append_journal_line(cwd, fs.build_journal_line(
            "file-edited", "session", by="tool", data={"path": rel}))

        journal_path = os.path.join(fs.friday_dir(cwd), "journal.jsonl")
        try:
            with open(journal_path, encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError:
            return 0

        entries = []
        for ln in lines[-_WINDOW:]:
            try:
                entries.append(json.loads(ln))
            except (ValueError, TypeError):
                continue

        edit_indices = [i for i, e in enumerate(entries)
                        if e.get("event") == "file-edited"
                        and (e.get("data") or {}).get("path") == rel]
        if len(edit_indices) < _THRESHOLD:
            return 0

        earliest = edit_indices[0]
        decided_after = any(e.get("event") == "decision-captured"
                            for e in entries[earliest:])
        if not decided_after:
            print(json.dumps(_guard.emit_warn(
                f"{rel} has churned {len(edit_indices)} times without a "
                "recorded decision — if you are circling, record the "
                "decision or ask the PM")))
    except Exception as exc:
        print(f"thrash_detector: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
