#!/usr/bin/env python3
"""Guard #4's checker — the foundation gate (TECHNICAL_SOW_REBUILD FR-55
guard #4, restating K0 stranger-proof at Stop time: a build claimed in
progress must have its foundation — the FRIDAY-CLAIMS block and the oracle
its tsow: field names — actually hold).

valid-fail when EITHER: (a) FRIDAY-CLAIMS fails verify_claims.well_formed
(structural check only — a missing block, an empty block, or an unparseable
claim line); or (b) FRIDAY-STATE's tsow: value is missing or names a file
that does not exist under root. Both good → valid-pass. No FRIDAY-STATE
block at all (not a build) → valid-pass — this checker only judges a build
already claimed in progress; the hook's own cheap pre-check makes that the
only path that reaches here in practice, but the checker stays self-
contained for direct invocation.

Verdict rides stdout as ONE JSON object (FR-61 shape, consumed by
hooks/_guard.py). Exit codes: 0 pass · 1 fail · 2 bad invocation.
Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402
import verify_claims  # noqa: E402


def check(root: str) -> dict:
    root = os.path.abspath(root)
    try:
        with open(os.path.join(root, "CLAUDE.md"), encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return {"verdict": "valid-pass", "summary": "no CLAUDE.md — no build to judge"}

    state_block = taglines.block_typed(text, "FRIDAY-STATE")
    if state_block is None:
        return {"verdict": "valid-pass", "summary": "no FRIDAY-STATE block — not a build"}

    problems: list[str] = []
    wf, errs = verify_claims.well_formed(text)
    if not wf:
        problems.append("FRIDAY-CLAIMS not well-formed: " + "; ".join(errs))

    tsow_vals = state_block.get("tsow", [])
    tsow = tsow_vals[0] if tsow_vals else ""
    if not tsow.strip():
        problems.append("FRIDAY-STATE's tsow: value is missing")
    elif not os.path.isfile(os.path.join(root, tsow)):
        problems.append(f"FRIDAY-STATE names tsow: {tsow!r} but that file does not exist")

    if problems:
        return {"verdict": "valid-fail", "problems": problems,
                "summary": f"foundation INVALID: {len(problems)} problem(s) — {problems[0]}"}
    return {"verdict": "valid-pass",
            "summary": f"foundation OK: claims well-formed, tsow: {tsow} exists"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guard #4 checker: foundation gate (K0)")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    res = check(args.root)
    print(json.dumps(res))
    return 1 if res["verdict"] == "valid-fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
