#!/usr/bin/env python3
"""Channel-A decision capture — the harness-guaranteed DECISIONS.md write.

Bound ONCE on PostToolUse (matcher: AskUserQuestion). Fires the DECISIONS.md
append ONLY for the narrow decision-ask shape (§6.6): a question whose first
line is `[FRIDAY-DECISION] <title>` followed by typed decision:/why:/
rejected:/floor:/weight: lines. EVERY question in the ask is checked — a
multi-question card writes one entry per decision-shaped question (BUG-004 /
D-0118; the first-question-only read silently lost later rulings). Ordinary
permission dialogs and clarifying questions NEVER parse, so the log is never
flooded with permission-grant noise — the model's judgment picks the shape,
the harness guarantees the write.

The PM's chosen option is resolved PER QUESTION: the response's answers
container is matched by the question's own text or header (dict keys or
{question, answer} list items). The unscoped whole-response walk survives
only for single-question asks, where attribution is unambiguous — on a
multi-question card it is exactly the BUG-004 mash-up. The response shape is
host-version-dependent, so extraction degrades to "(answer not extracted from
tool response — re-record with tools/decisions_append.py)" rather than
skipping the write — a pm-ratified decision must never be silently lost
because a payload key moved.

Always exits 0; a failed append is reported to stderr (the Channel-B fallback:
the lead re-records it by hand with decisions_append.py).
"""
# Contract: docs/contracts/decision-capture.md — this hook is the named
# Channel-A producer; the [FRIDAY-DECISION] ask grammar is owned there,
# cited on both sides of the handoff (A14).
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402


FALLBACK = ("(answer not extracted from tool response — re-record with "
            "tools/decisions_append.py)")

# Container keys a host may nest the answers under (host-version-dependent).
_ANSWER_KEYS = ("answer", "answers", "response", "responses", "selected",
                "choices", "result", "content")


def _questions(tool_input: object) -> list[tuple[str, str | None, list[str]]]:
    """ALL questions in the ask as (text, header, option-labels) — never just
    the first (BUG-004)."""
    ti = tool_input if isinstance(tool_input, dict) else {}
    out: list[tuple[str, str | None, list[str]]] = []
    for q in (ti.get("questions") or []) if isinstance(ti.get("questions"), list) else []:
        if not isinstance(q, dict) or not isinstance(q.get("question"), str):
            continue
        header = q.get("header")
        options = [o.get("label") for o in (q.get("options") or [])
                   if isinstance(o, dict) and isinstance(o.get("label"), str)]
        out.append((q["question"], header if isinstance(header, str) else None,
                    options))
    return out


def _extract_answer(tool_response: object) -> str | None:
    """Unscoped best-effort walk for a chosen-answer string. Safe ONLY for a
    single-question ask — on a multi-question response it cannot attribute
    answers to questions (the BUG-004 mash-up)."""
    if isinstance(tool_response, str):
        return tool_response.strip() or None
    if isinstance(tool_response, dict):
        for key in _ANSWER_KEYS:
            got = _extract_answer(tool_response.get(key))
            if got:
                return got
    if isinstance(tool_response, list):
        parts = [p for p in (_extract_answer(v) for v in tool_response) if p]
        return "; ".join(parts) or None
    return None


def _lookup_in_dict(container: dict, keys: list[str]) -> str | None:
    """A dict keyed by question text/header → that question's answer."""
    for k, v in container.items():
        if isinstance(k, str) and k.strip() in keys:
            got = _extract_answer(v)
            if got:
                return got
    return None


def _lookup_in_list(container: list, keys: list[str]) -> str | None:
    """A list of {question|header, answer} items → the matching item's answer."""
    for item in container:
        if not isinstance(item, dict):
            continue
        label = item.get("question") or item.get("header")
        if isinstance(label, str) and label.strip() in keys:
            got = _extract_answer(item.get("answer") or item.get("response")
                                  or item.get("selected") or item.get("label"))
            if got:
                return got
    return None


def _lookup_by_question(container: object, question: str,
                        header: str | None) -> str | None:
    """Match THIS question's answer inside one container: a dict keyed by
    question text/header, or a list of {question|header, answer} items."""
    keys = [question.strip()] + ([header.strip()] if header else [])
    if isinstance(container, dict):
        got = _lookup_in_dict(container, keys)
        if got:
            return got
    if isinstance(container, list):
        return _lookup_in_list(container, keys)
    return None


def _answer_for(tool_response: object, question: str, header: str | None,
                single: bool) -> str | None:
    """Per-question answer resolution; the unscoped walk only when the ask
    had one question (attribution unambiguous)."""
    containers = [tool_response]
    if isinstance(tool_response, dict):
        containers += [tool_response[k] for k in _ANSWER_KEYS
                       if k in tool_response]
    for c in containers:
        got = _lookup_by_question(c, question, header)
        if got:
            return got
    return _extract_answer(tool_response) if single else None


def _capture_one(cwd: str, decisions, ask: dict, answer: str,
                 options: list[str]) -> str:
    """Compose and append ONE pm-ratified entry for one decision-shaped
    question; returns the allocated D-NNNN id."""
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
    return id_str


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
        questions = _questions(event.get("tool_input"))
        if not questions:
            return 0
        import decisions
        single = len(questions) == 1
        wrote: list[str] = []
        for question, header, options in questions:
            ask = decisions.parse_decision_ask(question)
            if ask is None:
                continue  # not the decision-ask shape — never capture ordinary dialogs

            answer = _answer_for(event.get("tool_response"), question, header,
                                 single) or FALLBACK
            wrote.append(_capture_one(cwd, decisions, ask, answer, options))
        if wrote:
            print(f"decision_capture: wrote {', '.join(wrote)} (pm-ratified)",
                  file=sys.stderr)
    except Exception as exc:
        print(f"decision_capture: FAILED to write the pm-ratified entry: {exc} — "
              "re-record it with tools/decisions_append.py", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
