#!/usr/bin/env python3
"""Handoff package checker — the package invariants that are MECHANICAL
(docs/contracts/handoff-package.md): every required member present, and every
operate-or-maintain line in `operations-runbook.md` — bullet, numbered step,
or table row — carries a who-can-do-this tag `[you]` / `[hired]` (FR-83; a
table row's tag opens its first cell — the maintenance schedule's natural
format is a table, so tables are checked, not exempt). Code-fence content and
table header/separator rows are structure, not operate lines. The
plain-language invariant (NFR-1) is NOT mechanical — it rides house review +
the AC-26 field test, never this checker.

A project with no `docs/handoff/` yet is 'not built' — reported, never a failure
(the tested empty case). Exit codes: 0 ok/not-built · 1 findings · 2 bad
invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

REQUIRED_MEMBERS = (
    "README.md", "what-it-is-and-why.md", "user-guide.md", "admin-guide.md",
    "operations-runbook.md", "ownership-and-keys.md", "running-cost.md",
    "honest-state.md", "warranty.md", "promised-and-proven.md",
)
PACKAGE_DIR = os.path.join("docs", "handoff")

_BULLET = re.compile(r"^\s*[-*]\s+(\S.*?)\s*$")
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(\S.*?)\s*$")
_TAG_OPENS = re.compile(r"^\[(you|hired)\]\s")
_FENCE = re.compile(r"^\s*(```|~~~)")


def _table_cells(line: str) -> list[str] | None:
    """Cells of a markdown table row, or None for a non-table line."""
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|") and len(s) > 1):
        return None
    return [c.strip() for c in s[1:-1].split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-+:?", c) for c in cells if c) and any(cells)


def _untagged_runbook_lines(text: str) -> list[tuple[int, str]]:
    """(line_number, content) of every operate/maintain line missing its
    [you]/[hired] tag — bullets, numbered steps, and table data rows. Code
    fences and table header/separator rows are structure, never flagged."""
    lines = text.splitlines()
    out: list[tuple[int, str]] = []
    in_fence = False
    for i, line in enumerate(lines, 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _BULLET.match(line) or _NUMBERED.match(line)
        if m:
            if not _TAG_OPENS.match(m.group(1)):
                out.append((i, m.group(1)))
            continue
        cells = _table_cells(line)
        if cells is None or _is_separator_row(cells):
            continue
        # a header row is the row a separator immediately follows
        nxt = _table_cells(lines[i]) if i < len(lines) else None
        if nxt is not None and _is_separator_row(nxt):
            continue
        first = next((c for c in cells if c), "")
        if first and not _TAG_OPENS.match(first + " "):
            out.append((i, " | ".join(c for c in cells if c)))
    return out


def check_package(root: str) -> dict:
    """Verify the handoff package under `root`. {built, ok, findings}. `built`
    is False (and ok True) when no package exists yet — nothing to check."""
    root = os.path.abspath(root)
    pkg = os.path.join(root, PACKAGE_DIR)
    if not os.path.isdir(pkg):
        return {"built": False, "ok": True, "findings": []}

    findings: list[str] = []
    for m in REQUIRED_MEMBERS:
        if not os.path.isfile(os.path.join(pkg, m)):
            findings.append(f"missing required member: {PACKAGE_DIR}/{m}")

    runbook = os.path.join(pkg, "operations-runbook.md")
    if os.path.isfile(runbook):
        try:
            with open(runbook, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            text = None
            findings.append(f"could not read operations-runbook.md: {exc}")
        if text is not None:
            for i, content in _untagged_runbook_lines(text):
                findings.append(
                    f"{PACKAGE_DIR}/operations-runbook.md:{i} untagged operate/maintain "
                    f"line — must open [you] or [hired]: {content[:60]}")

    return {"built": True, "ok": not findings, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Check handoff package invariants (members + who-can-do-this tags)")
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"handoff_package_check: --root is not a directory: {root}", file=sys.stderr)
        return 2

    result = check_package(root)
    if args.json:
        print(json.dumps(result, indent=2))
    elif not result["built"]:
        print(f"handoff package: not built ({PACKAGE_DIR}/ absent) — nothing to check.")
    elif result["ok"]:
        print("handoff package: OK — all required members present, every runbook line tagged.")
    else:
        print("handoff package: FINDINGS —")
        for f in result["findings"]:
            print(f"  - {f}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
