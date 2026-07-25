#!/usr/bin/env python3
"""Guard #10's checker — design-contract lock (TECHNICAL_SOW_REBUILD FR-55
guard #10; D-0018 event mapping: "an edit to a COMMITTED docs/contracts|
docs/design file with no DECISIONS.md re-sync record").

A file with git history (`git log -1` returns a commit) is a LOCKED
contract — editing it needs a recorded re-sync decision naming its exact
repo-relative path in docs/DECISIONS.md. An untracked/brand-new file (no
history yet) is still being authored, not yet locked → valid-pass. A git
failure (not a repo, git unrunnable) is unjudgeable → no-verdict, fail-open.

Verdict rides stdout as ONE JSON object (FR-61). Exit 0 pass · 1 fail · 2
bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

GIT_TIMEOUT_S = 5


def check(path: str, root: str) -> dict:
    root = os.path.abspath(root)
    rel = os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")
    try:
        proc = subprocess.run(
            ["git", "-C", root, "log", "-1", "--format=%H", "--", rel],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_S)
    except Exception as exc:
        return {"verdict": "no-verdict", "detail": f"git unrunnable: {exc}"}
    if proc.returncode != 0:
        return {"verdict": "no-verdict",
                "detail": f"git log failed: {(proc.stderr or '').strip()[:200]}"}

    commit = proc.stdout.strip()
    if not commit:
        return {"verdict": "valid-pass",
                "summary": f"{rel} has no git history — a new file, not yet a "
                           "locked contract"}

    try:
        with open(os.path.join(root, "docs", "DECISIONS.md"), encoding="utf-8") as fh:
            decisions_text = fh.read()
    except OSError:
        decisions_text = ""

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import decisions
    if decisions.has_override_grant(decisions_text, rel):
        return {"verdict": "valid-pass",
                "summary": f"docs/DECISIONS.md carries an override-grant for {rel} "
                           "— the re-sync decision is on record"}
    return {"verdict": "valid-fail",
            "summary": f"{rel} is a locked contract (committed at {commit[:8]}) and "
                       "docs/DECISIONS.md does not name it — an edit needs a "
                       "recorded re-sync decision"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guard #10 checker: design-contract lock")
    ap.add_argument("--path", required=True)
    ap.add_argument("--root", required=True)
    args = ap.parse_args(argv)
    res = check(args.path, args.root)
    print(json.dumps(res))
    return 1 if res["verdict"] == "valid-fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
