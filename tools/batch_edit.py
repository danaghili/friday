#!/usr/bin/env python3
"""Batch find-and-replace with an exactly-once refusal (INC-004 FR-4.2).

Replaces the hand-composition it was promoted from: the ad-hoc python heredoc
with an assert-unique edit list, written from scratch at every bulk retarget
(promoted per the register, proposals/_recurrence-candidates.md).

Contract (validate-all-then-apply — S-4.3, KH-1):
  - input: a JSON array of {"file": <path>, "old": <text>, "new": <text>}
    on stdin, or via --file <path>. Paths resolve against --root (default cwd).
  - every edit's `old` must occur EXACTLY ONCE in its file's current text
    (same-file edits validate sequentially against the in-memory result of
    the previous edit, in list order).
  - any zero-match, multi-match, missing/unreadable file, or empty `old`
    refuses the ENTIRE batch: nothing is written, each failure is reported.
  - --dry-run: validate and report verdicts, write nothing (exit reflects
    the verdict, so a caller can preview the exactly-once outcome).
  - empty edit list: clean no-op success (the grammar's empty case).

Exit codes: 0 all edits valid (and applied, unless --dry-run) · 1 batch
refused (nothing written) · 2 malformed input / usage.
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def run_batch(edits: list, root: str = ".", dry_run: bool = False):
    """(ok, results): validate every edit in order against in-memory text;
    write files only if ALL are valid and not dry_run. results carry one
    verdict dict per edit: {file, ok, count, reason}."""
    contents: dict[str, str] = {}
    results = []
    ok = True
    for e in edits:
        path = e.get("file", "")
        old = e.get("old", "")
        new = e.get("new", "")
        verdict = {"file": path, "ok": False, "count": 0, "reason": ""}
        results.append(verdict)
        if not path or not isinstance(old, str) or not isinstance(new, str):
            verdict["reason"] = "edit needs file/old/new strings"
            ok = False
            continue
        if old == "":
            verdict["reason"] = "empty `old` can never match exactly once"
            ok = False
            continue
        full = os.path.join(root, path)
        if path not in contents:
            try:
                with open(full, encoding="utf-8") as f:
                    contents[path] = f.read()
            except FileNotFoundError:
                verdict["reason"] = "file not found"
                ok = False
                continue
            except (OSError, UnicodeDecodeError) as exc:
                verdict["reason"] = f"unreadable: {exc.__class__.__name__}"
                ok = False
                continue
        count = contents[path].count(old)
        verdict["count"] = count
        if count != 1:
            verdict["reason"] = f"`old` matches {count} times (need exactly 1)"
            ok = False
            continue
        contents[path] = contents[path].replace(old, new, 1)
        verdict["ok"] = True
    if ok and not dry_run:
        for path in {r["file"] for r in results}:
            with open(os.path.join(root, path), "w", encoding="utf-8") as f:
                f.write(contents[path])
    return ok, results


def main() -> int:
    ap = argparse.ArgumentParser(
        description="batch find-and-replace; refuses the whole batch unless "
                    "every `old` matches exactly once (JSON edits on stdin)")
    ap.add_argument("--file", help="read the JSON edit list from a file instead of stdin")
    ap.add_argument("--root", default=".", help="base directory for edit paths")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate and report; write nothing")
    args = ap.parse_args()

    try:
        raw = open(args.file, encoding="utf-8").read() if args.file else sys.stdin.read()
        edits = json.loads(raw)
        if not isinstance(edits, list):
            raise ValueError("edit list must be a JSON array")
    except (OSError, ValueError) as exc:
        print(f"batch_edit: malformed input — {exc}", file=sys.stderr)
        return 2

    if not edits:
        print("batch_edit: empty edit list — nothing to do (ok)")
        return 0

    ok, results = run_batch(edits, root=args.root, dry_run=args.dry_run)
    for i, r in enumerate(results):
        mark = "ok" if r["ok"] else "REFUSED"
        note = r["reason"] or f"matches {r['count']} time(s)"
        print(f"  edit {i + 1}: {r['file']} — {mark} ({note})")
    if not ok:
        print(f"batch_edit: batch REFUSED — nothing written "
              f"({sum(1 for r in results if not r['ok'])} of {len(results)} edits failed)",
              file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"batch_edit: dry-run — all {len(results)} edit(s) valid; nothing written")
    else:
        print(f"batch_edit: applied {len(results)} edit(s) across "
              f"{len({r['file'] for r in results})} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
