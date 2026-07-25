#!/usr/bin/env python3
"""Guard #8's checker — code-graph freshness (TECHNICAL_SOW_REBUILD FR-56
guard #8, FR-71; fourteenth session decision: warn, never block).

The ordering rule kills the docs-in-graph circularity: code lands → docs
regenerate → the graph refreshes LAST. Between refreshes the graph is
stale-FLAGGED with a visible "N commits behind" — this checker computes N.

Mechanics: `<shared .friday>/graph.stamp` holds the commit hash the graph
was last refreshed at (written by the refresh flow — U6 work; this checker
is the U1 warn exemplar and the stamp's contract). Absent stamp →
valid-pass: no graph has been adopted, nothing can be stale (graphify is a
SOFT integration, FR-68). Stamp == HEAD ancestry-count 0 → valid-pass.
N > 0 → valid-fail with the N-commits-behind summary (the warn-tier guard
turns this into a systemMessage, never a block). Unresolvable stamp or git
failure → no-verdict (fail-open).

Verdict rides stdout as ONE JSON object (FR-61). Exit 0 pass/no-verdict ·
1 fail · 2 bad invocation. Pure stdlib.
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


def check(root: str) -> dict:
    try:
        stamp_path = os.path.join(fs.friday_dir(root), "graph.stamp")
        try:
            with open(stamp_path, encoding="utf-8") as fh:
                stamp = fh.read().strip()
        except OSError:
            return {"verdict": "valid-pass",
                    "summary": "no graph stamp — no code graph adopted, nothing "
                               "to be stale"}
        if not stamp:
            return {"verdict": "no-verdict", "detail": "graph.stamp is empty"}
        proc = subprocess.run(
            ["git", "-C", root, "rev-list", "--count", f"{stamp}..HEAD"],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_S)
        if proc.returncode != 0:
            return {"verdict": "no-verdict",
                    "detail": f"git could not resolve the stamp: "
                              f"{(proc.stderr or '').strip()[:200]}"}
        behind = int(proc.stdout.strip())
        if behind == 0:
            return {"verdict": "valid-pass", "summary": "code graph is current"}
        return {"verdict": "valid-fail", "behind": behind,
                "summary": f"the code graph is {behind} commit(s) behind — "
                           "answers from it may cite lines that moved; it "
                           "refreshes after the next docs regeneration "
                           "(code → docs → graph, in that order)"}
    except Exception as exc:
        return {"verdict": "no-verdict", "detail": f"internal error: {exc}"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guard #8 checker: graph freshness")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    res = check(os.path.abspath(args.root))
    print(json.dumps(res))
    return 1 if res["verdict"] == "valid-fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
