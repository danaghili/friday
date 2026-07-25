#!/usr/bin/env python3
"""Guards #12 / #12b's checker — patch blast-radius (TECHNICAL_SOW_REBUILD
FR-55 guard #12, FR-56 guard #12b, S-2: "Changes outside the declared blast
radius are guard-blocked at action time, with a Stop-time backstop
warning"). Contract: docs/contracts/lane-open.md's `blast-radius` field
(required when lane=patch).

Two modes sharing one radius-matching rule (a declared entry with no glob
metacharacter is a directory/file PREFIX; one with `*`/`?`/`[]` is an
fnmatch glob — so `tools/` catches every file under it and `tests/*.py`
catches exactly what it says):

  --mode edit (guard #12, PreToolUse): is --path inside the declared
  radius? Outside → valid-fail naming the radius.

  --mode diff (guard #12b, Stop backstop): every file `git diff --name-only
  HEAD` + `git ls-files --others --exclude-standard` reports for --root —
  i.e. everything actually changed or newly added this session — checked
  against the radius. Any file outside it → valid-fail listing them.

Both modes: an ABSENT or EMPTY blast-radius list is itself the lie a patch
without one tells → valid-fail. There is no tests/ exception — the radius
must list tests/ too if tests change (by design, no special-casing).
Unreadable sentinel or a git failure (diff mode) → no-verdict, fail-open.

Verdict rides stdout as ONE JSON object (FR-61 shape, consumed by
hooks/_guard.py). Exit 0 pass · 1 fail · 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys

GIT_TIMEOUT_S = 5
_GLOB_CHARS = set("*?[]")


def _matches(rel: str, pattern: str) -> bool:
    if ".." in pattern.replace("\\", "/").split("/"):
        return False  # A12/D-0040: a radius pattern can never reach outside the repo root
    if any(c in pattern for c in _GLOB_CHARS):
        return fnmatch.fnmatch(rel, pattern)
    pattern = pattern.rstrip("/")
    return rel == pattern or rel.startswith(pattern + "/")


def _load_radius(sentinel_path: str) -> tuple[list[str] | None, dict | None]:
    """(radius, error_verdict). error_verdict is set on an unreadable sentinel
    (no-verdict, fail-open); radius is [] when the field is absent/empty
    (a real, judgeable fact — not an operational hazard)."""
    try:
        with open(sentinel_path, encoding="utf-8") as fh:
            sentinel = json.load(fh)
    except Exception as exc:
        return None, {"verdict": "no-verdict", "detail": f"sentinel unreadable: {exc}"}
    radius = sentinel.get("blast-radius")
    if not isinstance(radius, list):
        return [], None
    return [r for r in radius if isinstance(r, str) and r.strip()], None


def check_edit(path: str, root: str, sentinel_path: str) -> dict:
    root = os.path.abspath(root)
    radius, err = _load_radius(sentinel_path)
    if err is not None:
        return err
    if not radius:
        return {"verdict": "valid-fail",
                "summary": "the lane-open sentinel declares no blast-radius — a "
                           "patch without one is the lie (S-2)"}
    rel = os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")
    if rel == ".." or rel.startswith("../"):
        return {"verdict": "valid-fail",  # A12/D-0040: the edit escapes the repo root
                "summary": f"{path} is outside the repository root — a patch's blast "
                           "radius cannot reach outside the project"}
    if any(_matches(rel, p) for p in radius):
        return {"verdict": "valid-pass",
                "summary": f"{rel} is inside the declared blast radius"}
    return {"verdict": "valid-fail",
            "summary": f"{rel} is outside the declared blast radius "
                       f"({', '.join(radius)})"}


def check_diff(root: str, sentinel_path: str) -> dict:
    root = os.path.abspath(root)
    radius, err = _load_radius(sentinel_path)
    if err is not None:
        return err
    if not radius:
        return {"verdict": "valid-fail",
                "summary": "the lane-open sentinel declares no blast-radius — a "
                           "patch without one is the lie (S-2)"}
    try:
        changed = subprocess.run(
            ["git", "-C", root, "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_S)
        untracked = subprocess.run(
            ["git", "-C", root, "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_S)
    except Exception as exc:
        return {"verdict": "no-verdict", "detail": f"git unrunnable: {exc}"}
    if changed.returncode != 0 or untracked.returncode != 0:
        return {"verdict": "no-verdict",
                "detail": f"git failed: {(changed.stderr or untracked.stderr or '').strip()[:200]}"}

    files = sorted({ln.strip() for ln in
                    (changed.stdout.splitlines() + untracked.stdout.splitlines())
                    if ln.strip()})
    outside = [f for f in files if not any(_matches(f, p) for p in radius)]
    if outside:
        return {"verdict": "valid-fail", "outside": outside,
                "summary": f"{len(outside)} changed file(s) fall outside the "
                           f"declared blast radius: {', '.join(outside)}"}
    return {"verdict": "valid-pass",
            "summary": f"all {len(files)} changed file(s) are inside the "
                       "declared blast radius"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guards #12/#12b checker: patch blast-radius")
    ap.add_argument("--root", required=True)
    ap.add_argument("--sentinel", required=True)
    ap.add_argument("--path", default=None, help="required in --mode edit")
    ap.add_argument("--mode", choices=("edit", "diff"), default="edit")
    args = ap.parse_args(argv)

    if args.mode == "edit":
        if not args.path:
            print(json.dumps({"verdict": "no-verdict", "detail": "--path required in edit mode"}))
            return 2
        res = check_edit(args.path, args.root, args.sentinel)
    else:
        res = check_diff(args.root, args.sentinel)
    print(json.dumps(res))
    return 1 if res["verdict"] == "valid-fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
