#!/usr/bin/env python3
"""INC-101 FR-101.3 / FR-101.4 — derive the document-truth probe's record set.

The record set is the documents the project's role files declare as their
outputs, plus the project's front page — derived at run time so a role that
gains a new declared output joins the probe's scope with no edit anywhere
(INC-101 D2, AC-101.4). The size bar is the project's own, read from the
declared-bar home (`docs/standards/coding-standards.md`, FRIDAY-DOC-PROBE
block, line `doc-probe: read-kb <= N`); a project with no line gets
DEFAULT_READ_KB below, and a malformed line is surfaced in `bar_error`,
never silently defaulted. Members are split into within-bar (the probe reads
these) and over-bar (the probe NAMES these as unread — S-101.4: a read that
could not happen is never a read that found nothing).

Usage:
  python3 tools/doc_probe_scope.py --root <project> [--roles-dir <agents>] --json

Exit codes: 0 (the report is the product; an empty record set is a valid,
distinct outcome, not an error). Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# The oracle's declared default for a project with no doc-probe line, in KB of
# record-set bytes read before the remainder is named unread. Chosen against
# real measurements (OQ-101.2; the numbers live in the build trail / DECISIONS,
# never in prose): twice the larger of the two measured record sets — friday's
# own and the audited production project's — so both read whole with headroom.
DEFAULT_READ_KB = 1536

_BLOCK_RE = re.compile(
    r"<!--\s*FRIDAY-DOC-PROBE:BEGIN\s*-->(.*?)<!--\s*FRIDAY-DOC-PROBE:END\s*-->",
    re.S,
)
_BAR_RE = re.compile(r"^doc-probe:\s*read-kb\s*<=\s*(\d{1,6})\s*$")
_FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def _split_outputs(value: str) -> list[str]:
    """Split a declared-outputs value on top-level commas; an item's leading
    path token is the member, annotations in parentheses or backticks drop."""
    items, buf, depth = [], [], 0
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    items.append("".join(buf))
    paths = []
    for item in items:
        token = item.strip().split(" ")[0].split("(")[0].strip().strip("`")
        if token:
            paths.append(token)
    return paths


def declared_outputs(roles_dir: Path) -> list[str]:
    """Every path declared on an `outputs:` frontmatter line under roles_dir,
    in file order, deduplicated."""
    seen, ordered = set(), []
    for role_file in sorted(roles_dir.rglob("*.md")):
        m = _FRONT_RE.match(role_file.read_text(encoding="utf-8", errors="replace"))
        if not m:
            continue
        for line in m.group(1).splitlines():
            if not line.startswith("outputs:"):
                continue
            for path in _split_outputs(line[len("outputs:"):]):
                if path not in seen:
                    seen.add(path)
                    ordered.append(path)
    return ordered


def read_bar(root: Path) -> tuple[dict, str | None]:
    std = root / "docs" / "standards" / "coding-standards.md"
    if not std.is_file():
        return {"read_kb": DEFAULT_READ_KB, "source": "default"}, None
    block = _BLOCK_RE.search(std.read_text(encoding="utf-8", errors="replace"))
    if not block:
        return {"read_kb": DEFAULT_READ_KB, "source": "default"}, None
    error = None
    for line in block.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("<!--"):
            continue
        m = _BAR_RE.match(line)
        if m:
            return {"read_kb": int(m.group(1)), "source": "declared"}, None
        error = f"malformed doc-probe bar line: {line!r}"
    return {"read_kb": DEFAULT_READ_KB, "source": "default"}, error


def derive(root: Path, roles_dir: Path) -> dict:
    members: list[dict] = []
    missing: list[str] = []
    patterned: list[str] = []
    out_of_tree: list[str] = []
    unreadable: list[str] = []
    member_paths: set[str] = set()

    def add(rel: str) -> None:
        # A declaration the tool cannot resolve is still named, in its honest
        # bucket (S-101.4): a template is not a missing file, and a path
        # outside the project is not the project's record.
        if "<" in rel or "*" in rel:
            patterned.append(rel)
            return
        if rel.startswith("~") or rel.startswith("/"):
            out_of_tree.append(rel)
            return
        target = root / rel
        if target.is_file():
            if not os.access(target, os.R_OK):
                if rel not in unreadable:
                    unreadable.append(rel)
                return
            if rel not in member_paths:
                member_paths.add(rel)
                members.append({"path": rel, "bytes": target.stat().st_size})
        elif target.is_dir() or rel.endswith("/"):
            if target.is_dir():
                for doc in sorted(target.rglob("*.md")):
                    add(str(doc.relative_to(root)))
            else:
                missing.append(rel)
        else:
            missing.append(rel)

    add("README.md")
    if "README.md" not in member_paths and "README.md" not in missing:
        missing.append("README.md")
    for rel in declared_outputs(roles_dir):
        add(rel)

    bar, bar_error = read_bar(root)
    budget = bar["read_kb"] * 1024
    within, over, used = [], [], 0
    for m in members:
        if used + m["bytes"] <= budget:
            within.append(m)
            used += m["bytes"]
        else:
            over.append(m)

    report = {
        "ok": True,
        "members": members,
        "missing": missing,
        "patterned": patterned,
        "out_of_tree": out_of_tree,
        "unreadable": unreadable,
        "bar": bar,
        "within_bar": within,
        "over_bar": over,
    }
    if bar_error:
        report["bar_error"] = bar_error
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="project root")
    ap.add_argument(
        "--roles-dir",
        default=None,
        help="role tree carrying outputs: declarations (default: the plugin's own agents/)",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    roles_dir = (
        Path(args.roles_dir).resolve()
        if args.roles_dir
        else Path(__file__).resolve().parent.parent / "agents"
    )
    report = derive(root, roles_dir)
    if args.json:
        print(json.dumps(report))
    else:
        for m in report["members"]:
            mark = "over-bar" if m in report["over_bar"] else "within"
            print(f"{m['path']}\t{m['bytes']}B\t{mark}")
        for rel in report["missing"]:
            print(f"{rel}\tMISSING")
        print(f"bar: {report['bar']['read_kb']}kb ({report['bar']['source']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
