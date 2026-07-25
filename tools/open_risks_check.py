#!/usr/bin/env python3
"""Guard #5's checker — build-past-open-risks (TECHNICAL_SOW_REBUILD FR-55
guard #5; D-0018 event mapping: "a CLAUDE.md write that leaves the governing
TSOW's stack-risk register holding open rows while build-in-progress is
claimed").

Only engages when FRIDAY-STATE declares `state: build-in-progress`; its
`tsow:` file is read and searched for a heading containing "risk register"
(case-insensitive — the TSOW's own heading is "### Stack-risk register").
The first markdown table found in that section's body is parsed row by row;
a row is OPEN when its cells (joined) contain the word "verify" and do NOT
contain "settled" (the table's own convention: an open row's Verdict column
reads exactly "verify"; a resolved one reads "settled — <evidence>"). An
open row is EXCUSED only when docs/DECISIONS.md contains a distinctive
token drawn from that row's first (Element) cell — the longest bare word in
it, stripped of markdown — i.e., the PM has put an override on record.

Empty cases (all valid-pass, tested): not build-in-progress; no tsow: file
or it is unreadable; the tsow file has no heading containing "risk
register"; that section holds no markdown table. Pure stdlib.

Verdict rides stdout as ONE JSON object (FR-61). Exit 0 pass · 1 fail · 2
bad invocation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402
import decisions  # noqa: E402

_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def _distinctive_token(cell: str) -> str:
    """The single longest bare word in a table cell — deterministic and crude
    by design (this excuse path is a mechanical string search, not judgment)."""
    words = _WORD_RE.findall(cell)
    return max(words, key=len) if words else cell.strip()


def _risk_register_rows(tsow_text: str) -> list[list[str]] | None:
    """[[cell, cell, ...], ...] for the first markdown table under a heading
    containing "risk register"; None if no such section or no table."""
    lines = tsow_text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"^#{1,6}\s+.*risk register", ln, re.I):
            start = i + 1
            break
    if start is None:
        return None
    body: list[str] = []
    for ln in lines[start:]:
        if re.match(r"^#{1,6}\s+", ln):
            break
        body.append(ln)

    table_lines = [ln for ln in body if ln.strip().startswith("|")]
    if len(table_lines) < 2:  # need at least a header + separator
        return None
    rows = []
    for ln in table_lines[2:]:  # skip header row + the --- separator row
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if cells:
            rows.append(cells)
    return rows or None


def check(root: str) -> dict:
    root = os.path.abspath(root)
    try:
        with open(os.path.join(root, "CLAUDE.md"), encoding="utf-8") as fh:
            claude_text = fh.read()
    except OSError:
        return {"verdict": "valid-pass", "summary": "no CLAUDE.md — nothing to check"}

    state_block = taglines.block_typed(claude_text, "FRIDAY-STATE")
    if state_block is None or state_block.get("state", [None])[0] != "build-in-progress":
        return {"verdict": "valid-pass", "summary": "not build-in-progress — nothing to check"}

    tsow_vals = state_block.get("tsow", [])
    tsow_rel = tsow_vals[0] if tsow_vals else ""
    try:
        with open(os.path.join(root, tsow_rel), encoding="utf-8") as fh:
            tsow_text = fh.read()
    except OSError:
        return {"verdict": "valid-pass",
                "summary": f"tsow: {tsow_rel!r} unreadable — no risk register to check"}

    rows = _risk_register_rows(tsow_text)
    if rows is None:
        return {"verdict": "valid-pass",
                "summary": "no stack-risk register section (or no table in it) — "
                           "nothing to check"}

    try:
        with open(os.path.join(root, "docs", "DECISIONS.md"), encoding="utf-8") as fh:
            decisions_text = fh.read().lower()
    except OSError:
        decisions_text = ""

    open_elements: list[str] = []
    for cells in rows:
        row_text = " ".join(cells).lower()
        if "verify" not in row_text or "settled" in row_text:
            continue
        element = cells[0]
        if not decisions.has_override_grant(decisions_text, element):
            open_elements.append(element)

    if open_elements:
        return {"verdict": "valid-fail", "open_rows": open_elements,
                "summary": f"the stack-risk register holds {len(open_elements)} open "
                           f"row(s) with no decision on record: "
                           + "; ".join(open_elements)}
    return {"verdict": "valid-pass",
            "summary": f"stack-risk register OK: {len(rows)} row(s), none open-and-undocumented"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guard #5 checker: build-past-open-risks")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    res = check(args.root)
    print(json.dumps(res))
    return 1 if res["verdict"] == "valid-fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
