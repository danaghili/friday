#!/usr/bin/env python3
"""Guard #1's checker — profile validity (TECHNICAL_SOW_REBUILD FR-55 guard
#1: "profile validity after profile writes"). Ground truth for the required
shape came from reading the real ~/.claude/CLAUDE.md profile this Friday
Profiler writes.

Engages only when the document carries an H2 heading exactly `##
Collaboration Preferences` — its absence means this write is not a profile
at all (a project's own CLAUDE.md, or any other document) → valid-pass,
the tested empty case. When present, every one of the ten pinned `###`
subsections must exist in its body (before the next H2) with at least one
non-empty `- ` bullet line beneath it:

    Communication, Code comments, Error handling, Test discipline,
    Review pickiness, Refactor stance, Audience, Learning preference,
    Awareness (decision teach-back), Formatting defaults

A missing or content-empty subsection is named in plain words → valid-fail.
All present with content → valid-pass. An unreadable file is an operational
hazard, not a content judgment → no-verdict (fail-open).

Verdict rides stdout as ONE JSON object (FR-61 shape, consumed by
hooks/_guard.py). Exit 0 pass/no-verdict · 1 fail. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

HEADING = "Collaboration Preferences"
REQUIRED_SUBSECTIONS = (
    "Communication", "Code comments", "Error handling", "Test discipline",
    "Review pickiness", "Refactor stance", "Audience", "Learning preference",
    "Awareness (decision teach-back)", "Formatting defaults",
)

_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
_H3_RE = re.compile(r"^###\s+(.+?)\s*$")


def _is_bullet(line: str) -> bool:
    s = line.strip()
    return s.startswith("-") and len(s) > 1 and s[1:].strip() != ""


def check_text(text: str) -> dict:
    lines = text.splitlines()

    start = None
    for i, ln in enumerate(lines):
        m = _H2_RE.match(ln)
        if m and m.group(1).strip() == HEADING:
            start = i + 1
            break
    if start is None:
        return {"verdict": "valid-pass",
                "summary": f"no '## {HEADING}' heading — not a profile write"}

    body: list[str] = []
    for ln in lines[start:]:
        if _H2_RE.match(ln):
            break
        body.append(ln)

    sections: dict[str, list[str]] = {}
    current = None
    for ln in body:
        m = _H3_RE.match(ln)
        if m:
            current = m.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(ln)

    missing = [name for name in REQUIRED_SUBSECTIONS if name not in sections]
    empty = [name for name in REQUIRED_SUBSECTIONS
            if name in sections and not any(_is_bullet(ln) for ln in sections[name])]

    problems: list[str] = []
    if missing:
        problems.append(f"missing subsection(s): {', '.join(missing)}")
    if empty:
        problems.append(f"empty subsection(s) (no bullet lines): {', '.join(empty)}")

    if problems:
        return {"verdict": "valid-fail", "problems": problems,
                "summary": f"profile INVALID: {'; '.join(problems)}"}
    return {"verdict": "valid-pass",
            "summary": f"profile OK: all {len(REQUIRED_SUBSECTIONS)} subsections "
                       "present with content"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guard #1 checker: profile validity")
    ap.add_argument("--file", required=True)
    args = ap.parse_args(argv)
    try:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(json.dumps({"verdict": "no-verdict",
                          "detail": f"profile file unreadable: {exc}"}))
        return 0
    res = check_text(text)
    print(json.dumps(res))
    return 1 if res["verdict"] == "valid-fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
