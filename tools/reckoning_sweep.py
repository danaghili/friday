#!/usr/bin/env python3
"""The deep clean's catch-up sweep — what never came through a lane
(INC-104 FR-104.9, D1; OQ-104.4).

The three lanes ask the turned-around question at the moment of change; a
shared thing hand-edited on a Tuesday meets no lane and no question. This
sweep asks the project's own history which changes landed since the last
clean run and names those carrying no record of having been reconciled —
the reckoning record (`tools/reckoning.py`, contract:
`docs/contracts/reckoning-record.md`) is the record it consults, and a
`searched:` line under the change's id is what "reconciled" means.

OQ-104.4 is resolved by taking INC-102 FR-102.4's answer rather than
inventing a second one (D-0088): a dated line in the project's own record —
here the state record's `last-verified:` stamp — compared against commit
dates STRICTLY after it, with git-cannot-answer reported as could-not-verify
and never folded into nothing-moved.

- A commit naming a lane id (BUG-/PATCH-/INC-) counts as reconciled only if
  the RECORD carries that id — the id in a message is not the record.
- A commit touching only `docs/RECKONINGS.md` is never a finding: recording
  the catch-up's own answers must not feed the next sweep forever.
- Four outcomes, all distinct (AC-104.9): findings · nothing-outstanding ·
  could-not-anchor (no stamp to measure from) · could-not-verify (git
  cannot answer). Report-only — exits 0 whatever it finds (S-104.1); the
  reconciling itself is the lane's work under the lane's rules (S-104.3).

Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402
import reckoning  # noqa: E402
import taglines  # noqa: E402

GIT_TIMEOUT_S = 10
_LANE_ID_RE = re.compile(r"\b(?:BUG|PATCH|INC)-\d+\b")
# The record of answers is not a shared thing (the same exclusion
# consumer_scan.py makes): a commit that only records reckonings is the
# sweep's own paperwork, never its next finding.
_RECORD_FILE = "docs/RECKONINGS.md"

# The closed outcome vocabulary's single home is the contract's catch-up
# section (docs/contracts/reckoning-record.md); this tuple is the
# operational copy and a committed test locks the two together.
OUTCOMES = ("findings", "nothing-outstanding", "could-not-anchor",
            "could-not-verify")


def _git_lines(root: str, *args: str) -> list[str] | None:
    """One git query; None when git cannot answer — the caller must treat
    None as could-not-verify, never as nothing-moved (FR-102.4's rule)."""
    try:
        proc = subprocess.run(["git", "-C", root, *args],
                              capture_output=True, text=True,
                              timeout=GIT_TIMEOUT_S)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def _anchor(root: str) -> str | None:
    """The last clean run's `last-verified:` stamp from the state record's
    own block — absent file or absent stamp is could-not-anchor."""
    path = os.path.join(fs.resolve_worktree_root(root), "CLAUDE.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    typed = taglines.block_typed(text, "FRIDAY-STATE")
    if not typed or "last-verified" not in typed:
        return None
    return typed["last-verified"][0]


def _commits_since(top: str, anchor: str) -> list[dict] | None:
    lines = _git_lines(top, "log", "--format=%h\t%cs\t%s")
    if lines is None:
        return None
    out = []
    for line in lines:
        sha, date, subject = (line.split("\t", 2) + ["", ""])[:3]
        if date > anchor:
            files = _git_lines(top, "show", "--name-only", "--format=",
                               sha) or []
            out.append({"sha": sha, "date": date, "subject": subject,
                        "files": files})
    return out


def _outstanding(root: str, commits: list[dict]) -> list[dict]:
    found = []
    for c in commits:
        files = [f for f in c["files"] if f != _RECORD_FILE]
        if not files:
            continue
        ids = _LANE_ID_RE.findall(c["subject"]) or [c["sha"]]
        if any(reckoning.has(root, i)["recorded"] for i in ids):
            continue
        found.append({"change": ids[0], "date": c["date"],
                      "subject": c["subject"], "files": files})
    return found


def sweep(root: str = ".") -> dict:
    """One catch-up pass. The outcome vocabulary is closed and every state
    is a written fact — nothing-outstanding is a sweep that RAN and found
    nothing, never a sweep that could not look."""
    top = fs.resolve_worktree_root(root)
    if _git_lines(top, "rev-parse", "--git-dir") is None:
        return {"outcome": "could-not-verify", "anchor": None,
                "outstanding": [], "dirty": [],
                "reason": "git cannot answer here — not folded into "
                          "nothing-moved"}
    anchor = _anchor(root)
    if anchor is None:
        return {"outcome": "could-not-anchor", "anchor": None,
                "outstanding": [], "dirty": [],
                "reason": "no last-verified stamp to measure from — the "
                          "state record has never recorded a clean run"}
    commits = _commits_since(top, anchor)
    if commits is None:
        return {"outcome": "could-not-verify", "anchor": anchor,
                "outstanding": [], "dirty": [],
                "reason": "git cannot answer here — not folded into "
                          "nothing-moved"}
    outstanding = _outstanding(root, commits)
    status = _git_lines(top, "status", "--porcelain") or []
    dirty = [ln[3:].strip() for ln in status
             if ln[3:].strip() and ln[3:].strip() != _RECORD_FILE]
    outcome = "findings" if outstanding else "nothing-outstanding"
    return {"outcome": outcome, "anchor": anchor,
            "outstanding": outstanding, "dirty": dirty}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", default=".")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    out = sweep(args.root)
    if args.json:
        print(json.dumps(out, indent=2))
        return 0
    line = f"catch-up: {out['outcome']}"
    if out.get("anchor"):
        line += f" (since {out['anchor']})"
    if out.get("reason"):
        line += f" — {out['reason']}"
    print(line)
    for item in out["outstanding"]:
        print(f"  {item['change']} {item['date']} — {item['subject']} "
              f"[{', '.join(item['files'])}]")
    for path in out["dirty"]:
        print(f"  uncommitted: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
