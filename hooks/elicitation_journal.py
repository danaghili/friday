#!/usr/bin/env python3
"""Guard #16 — elicitation journaling (Elicitation + PermissionDenied, SILENT
tier; TECHNICAL_SOW_REBUILD FR-57 guard #16: "elicitation Q&A journaling
including denied permissions"). Both doc-only harness events per
probe-hook-events.md — fine if they never fire.

No checker, no user-visible message ever — this guard only journals, via
the single writer (friday_substrate.append_journal_line +
build_journal_line), never writing `.friday/` files directly. Engages only
in a friday project (fs.should_engage) so a bare Elicitation/PermissionDenied
never seeds a stray `.friday/` in an arbitrary directory. Stdout always
stays empty; always exits 0.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_EXCERPT_KEYS = ("tool_name", "question", "message", "reason")
_EXCERPT_MAX = 200


def _excerpt(event: dict) -> str:
    parts = []
    for key in _EXCERPT_KEYS:
        val = event.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(f"{key}={val.strip()[:_EXCERPT_MAX]}")
    tool_input = event.get("tool_input")
    if isinstance(tool_input, dict):
        questions = tool_input.get("questions")
        if isinstance(questions, list) and questions and isinstance(questions[0], dict):
            qtext = questions[0].get("question")
            if isinstance(qtext, str) and qtext.strip():
                parts.append(f"question={qtext.strip()[:_EXCERPT_MAX]}")
    return " ".join(parts)[:300] if parts else "(no excerpt fields present)"


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
        hook_event_name = event.get("hook_event_name") or "Elicitation"
        fs.append_journal_line(cwd, fs.build_journal_line(
            "elicitation", "session", by="session",
            data={"hook_event_name": hook_event_name, "excerpt": _excerpt(event)}))
    except Exception as exc:
        print(f"elicitation_journal: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
