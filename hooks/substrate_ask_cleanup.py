#!/usr/bin/env python3
"""Substrate-dialog cleanup hook — KEPT (resolution tracking / orphan sweep).

Pairs with substrate_ask_mirror.py. Bound four ways:
  PostToolUse / PostToolUseFailure (tool-scoped): the gated tool call just
    resolved — retire exactly the ONE mirror whose **Session:** matches this
    event's session_id. Zero matches is the steady state (most PostToolUse
    fires were never behind a dialog) and stays SILENT; multiple matches is
    surfaced to stderr and refused (never guessed at).
  Stop / SubagentStop (sweep): retire EVERY still-pending mirror for this
    session with resolution "session-ended" — honest ("we only know the
    session ended"), never a fabricated "answered". A hard kill leaves the
    mirror pending indefinitely, which is the honest surface.

Always exits 0; failure degrades to "no cleanup".
"""
from __future__ import annotations

import contextlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_REQUEST_NAME_RE = re.compile(r"^ask-(\d{8}-\d{6}-\d{3}(?:-\d+)?)-request\.md$")
_SESSION_LINE_RE = re.compile(r"^\*\*Session:\*\*\s*(.+?)\s*$")
_TOOL_SCOPED = frozenset({"PostToolUse", "PostToolUseFailure"})
_SWEEP = frozenset({"Stop", "SubagentStop"})


def _matches(fs, cwd: str, session_id: str) -> list[tuple[str, str]]:
    asks_dir = os.path.join(fs.friday_dir(cwd), "asks")
    try:
        names = os.listdir(asks_dir)
    except OSError:
        return []
    out = []
    for name in sorted(names):
        m = _REQUEST_NAME_RE.match(name)
        if not m:
            continue
        path = os.path.join(asks_dir, name)
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    sm = _SESSION_LINE_RE.match(line.rstrip("\n"))
                    if sm:
                        if sm.group(1) == session_id:
                            out.append((f"ask-{m.group(1)}", path))
                        break
        except OSError:
            continue
    return out


def _retire(fs, cwd: str, ask_id: str, path: str, resolution: str | None) -> None:
    data: dict = {"ask": ask_id, "via": "tty", "writtenTo": None}
    if resolution:
        data["resolution"] = resolution
    fs.append_journal_line(cwd, fs.build_journal_line(
        "question-answered", "session", by="session", data=data))
    with contextlib.suppress(OSError):
        os.remove(path)


def main() -> int:
    fs = load_substrate(plugin_root_from(sys.argv))
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    hook_event_name = event.get("hook_event_name") or ""
    session_id = event.get("session_id")
    session_id = session_id if isinstance(session_id, str) and session_id else None
    if fs is None or not session_id:
        return 0
    try:
        if not fs.should_engage(cwd):
            return 0
        matches = _matches(fs, cwd, session_id)
        if hook_event_name in _TOOL_SCOPED:
            if len(matches) == 1:
                _retire(fs, cwd, *matches[0], resolution=None)
            elif len(matches) > 1:
                print(f"substrate_ask_cleanup: {len(matches)} session-matched "
                      f"mirrors for {session_id!r}; expected one — no-op",
                      file=sys.stderr)
        elif hook_event_name in _SWEEP:
            for ask_id, path in matches:
                _retire(fs, cwd, ask_id, path, resolution="session-ended")
    except Exception as exc:
        print(f"substrate_ask_cleanup: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
