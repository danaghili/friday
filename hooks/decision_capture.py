#!/usr/bin/env python3
"""Channel-A decision capture — the harness-guaranteed DECISIONS.md write.

Bound ONCE on PostToolUse (matcher: AskUserQuestion). Fires the DECISIONS.md
append ONLY for the narrow decision-ask shape (§6.6): the question's first
line is `[FRIDAY-DECISION] <title>` followed by typed decision:/why:/
rejected:/floor:/weight: lines. Ordinary permission dialogs and clarifying
questions NEVER parse, so the log is never flooded with permission-grant
noise — the model's judgment picks the shape, the harness guarantees the
write.

The PM's chosen option (extracted best-effort from the tool response; the
response shape is host-version-dependent, so extraction degrades to
"(answer not extracted from tool response)" rather than skipping the write —
a pm-ratified decision must never be silently lost because a payload key
moved) is recorded as the decision outcome; the ask's rejected: line plus the
non-chosen options are the rejected-alternatives record.

Always exits 0; a failed append is reported to stderr (the Channel-B fallback:
the lead re-records it by hand with decisions_append.py).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402


def _first_question(tool_input: object) -> tuple[str | None, list[str]]:
    ti = tool_input if isinstance(tool_input, dict) else {}
    questions = ti.get("questions")
    if isinstance(questions, list) and questions and isinstance(questions[0], dict):
        q = questions[0].get("question")
        options = [o.get("label") for o in (questions[0].get("options") or [])
                   if isinstance(o, dict) and isinstance(o.get("label"), str)]
        return (q if isinstance(q, str) else None), options
    return None, []


def _extract_answer(tool_response: object) -> str | None:
    """Best-effort walk of the response for a chosen-answer string."""
    if isinstance(tool_response, str):
        return tool_response.strip() or None
    if isinstance(tool_response, dict):
        for key in ("answer", "answers", "response", "responses", "selected",
                    "choices", "result", "content"):
            val = tool_response.get(key)
            got = _extract_answer(val)
            if got:
                return got
    if isinstance(tool_response, list):
        parts = [p for p in (_extract_answer(v) for v in tool_response) if p]
        return "; ".join(parts) or None
    return None


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None or event.get("tool_name") != "AskUserQuestion":
        return 0
    try:
        if not fs.should_engage(cwd):
            return 0
        question, options = _first_question(event.get("tool_input"))
        if not question:
            return 0
        import decisions
        ask = decisions.parse_decision_ask(question)
        if ask is None:
            return 0  # not the decision-ask shape — never capture ordinary dialogs

        answer = _extract_answer(event.get("tool_response")) \
            or "(answer not extracted from tool response — see the ask mirror)"
        not_chosen = [o for o in options if o and o not in answer]
        rejected = ask["rejected"] or "-"
        if not_chosen:
            rejected += " · options not chosen: " + "; ".join(not_chosen)
        weight = ask["weight"]
        if ask["floor"] != "none":
            weight = "one-way"  # PROP-044 categorical override, enforced here too

        id_str, _ = decisions.append_entry(
            cwd, title=ask["title"],
            decision=f"{answer}" + (f" — {ask['decision']}" if ask["decision"] else ""),
            why=ask["why"] or "(why not stated in the ask)",
            rejected=rejected, channel="pm-ratified", weight=weight,
            floor=ask["floor"])
        print(f"decision_capture: wrote {id_str} (pm-ratified)", file=sys.stderr)
    except Exception as exc:
        print(f"decision_capture: FAILED to write the pm-ratified entry: {exc} — "
              "re-record it with tools/decisions_append.py", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
