#!/usr/bin/env python3
"""The code-graph query router (FR-68, FR-70) — the ONE seam every explore
consumer (adopt's read pass, harden's scout, feature's blast-radius read) calls
to ask the code graph a question, so the detect-and-prefer-or-fall-back logic
lives in exactly one tested place instead of being re-described in each command.

SOFT integration (FR-68): graphify installed AND a graph built for this project
→ route to `graphify query` (rich traversal, source_location citations); absent,
no graph yet, or graphify errors → answer from friday's OWN extracted structure
(`docs/architecture/generated/architecture-ir.json`, produced by /friday:reference).
Either backend is AST-derived, so both are EXTRACTED-grade.

FR-70 rides along in every result: cite EXTRACTED edges as evidence, treat
INFERRED as leads. The router surfaces the rule; the consumer honours it.

Result rides stdout as ONE JSON object. Exit 0 always (a query is advisory);
2 on bad invocation. Pure stdlib; graphify is shelled out to, never imported.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

GRAPHIFY_TIMEOUT_S = 120
EVIDENCE_RULE = ("cite EXTRACTED edges as evidence; INFERRED edges are leads to "
                 "verify, never proof (FR-70)")
_WORD = re.compile(r"[A-Za-z0-9_]{3,}")


def _graph_present(root: str) -> bool:
    return os.path.isfile(os.path.join(root, "graphify-out", "graph.json"))


def _graphify_runner(question: str, root: str) -> dict:
    try:
        proc = subprocess.run(["graphify", "query", question], cwd=root,
                              capture_output=True, text=True, timeout=GRAPHIFY_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "answer": f"graphify query failed: {exc}"}
    out = proc.stdout.strip() or proc.stderr.strip()
    return {"ok": proc.returncode == 0, "answer": out}


def _ir_fallback(question: str, root: str) -> dict:
    ir_path = os.path.join(root, "docs", "architecture", "generated",
                           "architecture-ir.json")
    try:
        with open(ir_path, encoding="utf-8") as fh:
            ir = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {"backend": "friday-own", "modules": [],
                "note": f"no extracted IR at {os.path.relpath(ir_path, root)} — "
                        "run /friday:reference to build friday's own index",
                "evidence_rule": EVIDENCE_RULE}
    tokens = {w.lower() for w in _WORD.findall(question)}
    hits = []
    for mod in ir.get("modules", []):
        hay = f"{mod.get('id', '')} {mod.get('path', '')}".lower()
        if any(tok in hay for tok in tokens):
            hits.append({"id": mod.get("id"), "path": mod.get("path"),
                         "loc": mod.get("loc")})
    note = ("matched friday's own extracted modules" if hits else
            "no modules matched — broaden the query or re-run /friday:reference")
    return {"backend": "friday-own", "modules": hits[:25], "note": note,
            "evidence_rule": EVIDENCE_RULE}


def query(question: str, root: str = ".", *, has_graphify: bool | None = None,
          graph_present: bool | None = None, runner=None) -> dict:
    root = os.path.abspath(root)
    if has_graphify is None:
        has_graphify = shutil.which("graphify") is not None
    if graph_present is None:
        graph_present = _graph_present(root)
    if has_graphify and graph_present:
        result = (runner or _graphify_runner)(question, root)
        if result.get("ok"):
            return {"backend": "graphify", "answer": result.get("answer", ""),
                    "evidence_rule": EVIDENCE_RULE}
        # graphify errored → graceful fallback, and say why (FR-68).
        fb = _ir_fallback(question, root)
        fb["note"] = f"graphify present but errored ({result.get('answer', '')[:120]}); " \
                     f"fell back to friday's own index"
        return fb
    return _ir_fallback(question, root)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ask the code graph (FR-68/FR-70)")
    ap.add_argument("question")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    print(json.dumps(query(args.question, os.path.abspath(args.root))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
