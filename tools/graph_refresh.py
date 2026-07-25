#!/usr/bin/env python3
"""The code-graph refresh flow (FR-71) — the "refresh flow" that guard #8
(graph_freshness_check.py) names as the writer of `graph.stamp`.

Ordering (FR-71): code lands → docs regenerate → THIS runs LAST, so the graph
never maps stale docs. `/friday:reference` runs the graphify rebuild as its
final phase, then calls this to record freshness.

SOFT integration (FR-68) — the whole logic is a three-way decision:
  - graphify installed AND a graph is built for this project → stamp it HEAD.
  - graphify installed but no graph built yet → nothing to stamp; say so.
  - graphify absent → friday's own extractor (architecture-ir.json) is the graph;
    there is no ADOPTED graph, so no stamp (guard #8 valid-passes on an absent
    stamp). Either way friday's own index stays whole.

This tool records freshness; it does not build the graph — that is the reference
command's job (it can drive graphify's full pipeline). Keeping the build out of a
deterministic script avoids coupling friday to graphify's internals (NFR-3: no
runtime dep) and keeps this core testable.

Verdict rides stdout as ONE JSON object. Refresh is advisory — exit 0 on every
real outcome; 2 only on bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402

GIT_TIMEOUT_S = 5


def _head(root: str) -> str:
    try:
        proc = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _graph_present(root: str) -> bool:
    """A graphify graph has been built for this project."""
    return os.path.isfile(os.path.join(root, "graphify-out", "graph.json"))


def refresh(root: str, *, has_graphify: bool | None = None,
            graph_present: bool | None = None, head: str | None = None) -> dict:
    root = os.path.abspath(root)
    if has_graphify is None:
        has_graphify = shutil.which("graphify") is not None
    if graph_present is None:
        graph_present = _graph_present(root)
    if head is None:
        head = _head(root)

    if not has_graphify:
        return {"backend": "friday-own", "stamped": False,
                "reason": "graphify not installed — friday's own index is the "
                          "graph; there is no adopted graph to stamp"}
    if not graph_present:
        return {"backend": "graphify", "stamped": False,
                "reason": "graphify installed but no graph built for this project "
                          "yet — run /graphify here first"}
    if not head:
        return {"backend": "graphify", "stamped": False,
                "reason": "not a git repo / no HEAD — cannot stamp a commit"}
    fs.graph_stamp_write(root, head)
    return {"backend": "graphify", "stamped": True, "commit": head,
            "summary": "code graph stamped at HEAD — guard #8 now reads it current"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Refresh-flow stamp for the code graph (FR-71)")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    print(json.dumps(refresh(os.path.abspath(args.root))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
