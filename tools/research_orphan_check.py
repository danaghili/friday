#!/usr/bin/env python3
"""Guard #14's checker — research-consumer orphans (TECHNICAL_SOW_REBUILD
FR-56 guard #14, S-4: "reconcile's roundup re-surfaces any surviving orphans
as warnings"). WARN-tier machinery — the matching is deliberately CRUDE and
documented, not precise: token containment of the `consumer:` value against
the repo's own file listing.

Every `docs/research/**/*.md` file is scanned for a `consumer:` typed tag
line (taglines.parse_typed_line). A file counts as orphaned when EITHER it
carries no `consumer:` line at all, OR its value is not the literal
`"rebuild build pass"` sentinel AND contains no token that appears as a
substring of any repo file path (and no repo file path appears as a
substring of the value — covers a token quoted the other way round).

Empty case (valid-pass, tested): no docs/research/ directory at all —
nothing to sweep. Pure stdlib.

Verdict rides stdout as ONE JSON object (FR-61). Exit 0 pass · 1 fail · 2
bad invocation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

_EXCLUDED_WALK = {".git", "__pycache__", ".friday", "node_modules", ".venv", "venv"}
_TOKEN_RE = re.compile(r"[A-Za-z0-9_.-]+")
_EXEMPT = "rebuild build pass"


def _repo_paths(root: str) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_WALK]
        for fn in filenames:
            out.append(os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/"))
    return out


def _is_consumed(consumer_val: str, repo_paths: list[str]) -> bool:
    cv = consumer_val.strip()
    if not cv:
        return False
    for p in repo_paths:
        if p and (p in cv or cv in p):
            return True
    tokens = [t for t in _TOKEN_RE.findall(cv) if len(t) >= 3]
    return any(tok in p for tok in tokens for p in repo_paths)


def check(root: str) -> dict:
    root = os.path.abspath(root)
    research_dir = os.path.join(root, "docs", "research")
    if not os.path.isdir(research_dir):
        return {"verdict": "valid-pass", "summary": "no docs/research/ directory — nothing to sweep"}

    repo_paths = _repo_paths(root)
    orphans: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(research_dir):
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                continue
            consumer_val = None
            for ln in text.splitlines():
                parsed = taglines.parse_typed_line(ln)
                if parsed and parsed[0] == "consumer":
                    consumer_val = parsed[1]
                    break
            if consumer_val is None:
                orphans.append(f"{rel} (no consumer: line)")
                continue
            if consumer_val.strip() == _EXEMPT:
                continue
            if not _is_consumed(consumer_val, repo_paths):
                orphans.append(f"{rel} (consumer: {consumer_val})")

    if orphans:
        return {"verdict": "valid-fail", "orphans": orphans,
                "summary": f"{len(orphans)} research brief(s) with no findable consumer: "
                           + "; ".join(orphans)}
    return {"verdict": "valid-pass",
            "summary": "every research brief's consumer: resolves to something in the repo"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guard #14 checker: research-consumer orphans")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    res = check(args.root)
    print(json.dumps(res))
    return 1 if res["verdict"] == "valid-fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
