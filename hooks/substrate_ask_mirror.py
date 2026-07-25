#!/usr/bin/env python3
"""Substrate-dialog mirror hook — KEPT mechanism (fire-before-the-dialog
harness capture; the proven local mechanism §6.6 builds Channel A on).

Bound TWICE: PermissionRequest (side-effecting tools) and PreToolUse
(AskUserQuestion — not gated by the permission system, so this is its only
attachment point). Mirrors the about-to-be-shown dialog into
`.friday/asks/<ask-id>-request.md` under the SHARED substrate root
(Appendix B) BEFORE the PM answers, so an unanswered decision-ask survives a
crash: `/friday:resume` re-surfaces the one the session STALLED on (a pending
question never evaporates).

NEVER blocks, never alters the dialog, always exits 0 — the native prompt
renders exactly as if this hook were not installed. The paired
substrate_ask_cleanup.py retires the mirror on resolution;
decision_capture.py (Channel A) fires the DECISIONS.md write when — and only
when — the ask carries the narrow [FRIDAY-DECISION] shape.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_PERMISSION_TOOL_NAMES = frozenset(
    {"Bash", "Edit", "MultiEdit", "Write", "NotebookEdit", "WebFetch"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _mint_ask_id(asks_dir: str) -> str:
    """Millisecond id with a collision check against the CURRENT listing."""
    now = datetime.now(timezone.utc)
    base = now.strftime("%Y%m%d-%H%M%S-") + f"{now.microsecond // 1000:03d}"
    try:
        existing = set(os.listdir(asks_dir))
    except OSError:
        existing = set()
    candidate, suffix = base, 1
    while f"ask-{candidate}-request.md" in existing:
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate


def _permission_content(tool_name: str, tool_input: object) -> tuple[str, str, str | None]:
    ti = tool_input if isinstance(tool_input, dict) else {}
    if tool_name == "Bash" and isinstance(ti.get("command"), str):
        return ("Run this Bash command?",
                f"Claude wants to run:\n\n```\n{ti['command']}\n```", None)
    fp = ti.get("file_path") or ti.get("notebook_path") or ti.get("url")
    if isinstance(fp, str) and fp:
        return (f"Allow {tool_name} on {fp}?",
                f"Claude wants to use {tool_name} on `{fp}`.", None)
    return (f"Allow {tool_name}?", f"Claude wants to use {tool_name}.",
            "```json\n" + json.dumps(ti, indent=2, sort_keys=True) + "\n```")


def _question_content(tool_input: object) -> tuple[str, str, str | None, list[dict]]:
    """Multi-question calls fold questions 2..n into context (fully
    enumerated, nothing dropped) rather than flattening option lists."""
    ti = tool_input if isinstance(tool_input, dict) else {}
    questions = ti.get("questions")
    if isinstance(questions, list) and questions and all(isinstance(q, dict) for q in questions):
        first = questions[0]
        first_text = first.get("question")
        if isinstance(first_text, str) and first_text:
            options = [{"value": o.get("label"), "description": o.get("description")}
                       for o in (first.get("options") or [])
                       if isinstance(o, dict) and isinstance(o.get("label"), str)]
            if len(questions) == 1:
                header = first.get("header")
                ctx = f"({header})" if isinstance(header, str) and header else None
                return first_text, first_text, ctx, options
            ctx_lines = []
            for i, q in enumerate(questions, start=1):
                ctx_lines.append(f"**{i}. {q.get('question', '(unlabeled)')}**")
                for opt in q.get("options") or []:
                    if isinstance(opt, dict):
                        ctx_lines.append(f"   - {opt.get('label', '?')}")
                ctx_lines.append("")
            return (f"({len(questions)} questions) {first_text}", first_text,
                    "\n".join(ctx_lines).strip(), [])
    return ("AskUserQuestion (unrecognized payload)",
            "AskUserQuestion (unrecognized payload)",
            "```json\n" + json.dumps(ti, indent=2, sort_keys=True) + "\n```", [])


def _compose(headline, question_body, context_body, options, tool_name,
             session_id, now_iso) -> str:
    lines = [f"# Ask: {_one_line(headline)}", "",
             "**Feature:** -", "**Phase:** session",
             f"**From:** {tool_name} (via substrate-ask-mirror hook)",
             f"**Session:** {session_id}",
             f"**Queued:** {now_iso} by substrate-ask-mirror",
             "**Delivery:** tty", "", "## Question", "", question_body, ""]
    if context_body:
        lines += ["## Context", "", context_body, ""]
    if options:
        lines += ["## Options", ""]
        for i, opt in enumerate(options, start=1):
            suffix = f" — {opt['description']}" if opt.get("description") else ""
            lines.append(f"{i}. **{opt['value']}**{suffix}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    fs = load_substrate(plugin_root_from(sys.argv))
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    hook_event_name = event.get("hook_event_name") or ""
    if fs is None:
        return 0
    try:
        if not fs.should_engage(cwd):
            return 0
        tool_name = event.get("tool_name")
        if not isinstance(tool_name, str) or not tool_name:
            return 0
        session_id = event.get("session_id")
        session_id = session_id if isinstance(session_id, str) and session_id else "unknown"

        if hook_event_name == "PermissionRequest":
            if tool_name not in _PERMISSION_TOOL_NAMES:
                return 0
            headline, body, ctx = _permission_content(tool_name, event.get("tool_input"))
            options: list[dict] = []
        elif hook_event_name == "PreToolUse" and tool_name == "AskUserQuestion":
            headline, body, ctx, options = _question_content(event.get("tool_input"))
        else:
            return 0

        asks_dir = os.path.join(fs.friday_dir(cwd), "asks")
        os.makedirs(asks_dir, exist_ok=True)
        ask_id = f"ask-{_mint_ask_id(asks_dir)}"
        content = _compose(headline, body, ctx, options, tool_name, session_id,
                           _now_iso())
        final_path = os.path.join(asks_dir, f"{ask_id}-request.md")
        fd, tmp = tempfile.mkstemp(prefix=f"{ask_id}.", dir=asks_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp, final_path)
        except Exception:
            with contextlib.suppress(OSError):
                os.remove(tmp)
            raise
    except Exception as exc:  # never break the dialog it mirrors
        print(f"substrate_ask_mirror: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
