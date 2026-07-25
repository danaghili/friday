#!/usr/bin/env python3
"""Guard #18a's checker — worktree-create substrate-sharing check
(TECHNICAL_SOW_REBUILD FR-55 guard #18a; probe-hook-events.md's
active-hook hazard: WorktreeCreate is a PRODUCER, not an observer — the
harness requires the new path back on stdout or creation fails outright).

valid-fail ONLY in two narrow cases (both mean the new worktree would NOT
share this project's substrate, breaking Appendix B's worktree rule):
  1. the requested path is inside this project's shared `.friday/`
     directory (resolved via friday_substrate.friday_dir — the git-
     common-dir parent, never assumed to equal --root);
  2. the requested path's nearest EXISTING ancestor is itself inside
     another, unrelated git repo (its `git rev-parse --show-toplevel`
     differs from --root's own toplevel).

Everything else — including a fresh location outside any git repo at all,
the ordinary case for a new sibling worktree — is valid-pass. Any git or
filesystem failure while resolving either check is unjudgeable →
no-verdict (fail-open; the hook treats no-verdict exactly like valid-pass
here — creation must never be blocked by our own inability to judge).

Verdict rides stdout as ONE JSON object (FR-61 shape, consumed by
hooks/_guard.py). Exit 0 pass/no-verdict · 1 fail · 2 bad invocation.
Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402

GIT_TIMEOUT_S = 5


def _nearest_existing_ancestor(path: str) -> str:
    anc = path
    while not os.path.exists(anc):
        parent = os.path.dirname(anc)
        if parent == anc:
            return anc
        anc = parent
    return anc


def check(path: str, root: str) -> dict:
    root = os.path.abspath(root)
    abs_path = os.path.abspath(path)

    friday_dir = os.path.normpath(fs.friday_dir(root))
    try:
        common = os.path.commonpath([abs_path, friday_dir])
    except ValueError:
        common = None  # e.g. different drives — cannot be inside it
    if common == friday_dir:
        return {"verdict": "valid-fail",
                "summary": f"{path} is inside this project's shared .friday "
                           "directory — creating a worktree there would "
                           "corrupt the substrate every session shares"}

    anc = _nearest_existing_ancestor(abs_path)
    try:
        proc = subprocess.run(["git", "-C", anc, "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, timeout=GIT_TIMEOUT_S)
    except Exception as exc:
        return {"verdict": "no-verdict", "detail": f"git unrunnable: {exc}"}
    if proc.returncode != 0:
        return {"verdict": "no-verdict",
                "detail": f"no git repo found near {path}: "
                          f"{(proc.stderr or '').strip()[:200]}"}
    other_top = os.path.normpath(proc.stdout.strip())

    r_top = os.path.normpath(fs.resolve_worktree_root(root))
    if other_top != r_top:
        return {"verdict": "valid-fail",
                "summary": f"{path} resolves to a different git repo "
                           f"({other_top}) than this project's ({r_top}) — "
                           "the new worktree would not share this project's "
                           "substrate"}
    return {"verdict": "valid-pass",
            "summary": f"{path} shares this project's git tree — safe to create"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guard #18a checker: worktree-create sharing")
    ap.add_argument("--path", required=True)
    ap.add_argument("--root", required=True)
    args = ap.parse_args(argv)
    res = check(args.path, args.root)
    print(json.dumps(res))
    return 1 if res["verdict"] == "valid-fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
