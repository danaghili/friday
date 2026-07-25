#!/usr/bin/env python3
"""Guard #11's checker — bug-close gate (TECHNICAL_SOW_REBUILD FR-55 guard
#11, S-1: "Bug closure is guard-gated: no closure without the committed
regression test and the completed trail"). Contract:
docs/contracts/lane-open.md's `regression-test` field (required when
lane=bug).

Two mechanical requirements, both must hold:
  1. The sentinel's `regression-test` field names an EXISTING `tests/*.py`
     file (worktree-root-relative). Existence is what is mechanically
     checked here; S-1's commit requirement lands in the fix commit itself.
  2. The sentinel's `trail` field, delegated whole to
     tools/trail_check.py's check_text() (one grammar, one home — this
     checker never re-derives the trail grammar), passes.

The owning hook (hooks/bug_close_gate.py) disarms the sentinel on this
checker's pass — bug lanes have exactly one owner (D-0023); this checker
only judges.
An unreadable sentinel here is an operational hazard, not a judgment —
no-verdict, fail-open (the hook's own pre-read already gated on lane=="bug"
before invoking this checker; a race or corruption between those two reads
degrades gracefully).

Verdict rides stdout as ONE JSON object (FR-61 shape, consumed by
hooks/_guard.py). Exit 0 pass · 1 fail · 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trail_check  # noqa: E402


def check(root: str, sentinel_path: str) -> dict:
    root = os.path.abspath(root)
    try:
        with open(sentinel_path, encoding="utf-8") as fh:
            sentinel = json.load(fh)
    except Exception as exc:
        return {"verdict": "no-verdict", "detail": f"sentinel unreadable: {exc}"}

    reg_test = sentinel.get("regression-test")
    if not isinstance(reg_test, str) or not reg_test.strip():
        return {"verdict": "valid-fail",
                "summary": "the lane-open sentinel carries no regression-test "
                           "field — a bug closure requires one (S-1)"}
    if not (reg_test.startswith("tests/") and reg_test.endswith(".py")):
        return {"verdict": "valid-fail",
                "summary": f"regression-test {reg_test!r} is not a tests/*.py path"}
    if not os.path.isfile(os.path.join(root, reg_test)):
        return {"verdict": "valid-fail",
                "summary": f"regression-test names {reg_test!r} but that file "
                           "does not exist — the regression test S-1 "
                           "requires is missing"}

    trail_rel = sentinel.get("trail")
    if not isinstance(trail_rel, str) or not trail_rel.strip():
        return {"verdict": "valid-fail",
                "summary": "the lane-open sentinel carries no trail field"}
    try:
        with open(os.path.join(root, trail_rel), encoding="utf-8") as fh:
            trail_text = fh.read()
    except OSError as exc:
        return {"verdict": "valid-fail",
                "summary": f"trail file missing or unreadable: {exc}"}

    decisions_text = None
    decisions_log_error = None
    try:
        with open(os.path.join(root, "docs", "DECISIONS.md"), encoding="utf-8") as fh:
            decisions_text = fh.read()
    except OSError as exc:
        decisions_log_error = str(exc)

    trail_res = trail_check.check_text(trail_text, decisions_text=decisions_text,
                                       decisions_log_error=decisions_log_error)
    if trail_res["verdict"] != "valid-pass":
        return {"verdict": "valid-fail", "errors": trail_res.get("errors", []),
                "summary": f"regression test OK ({reg_test}) but the trail is "
                           f"invalid: {trail_res.get('summary')}"}

    return {"verdict": "valid-pass",
            "summary": f"bug closure OK: regression test {reg_test} exists, "
                       "trail valid"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guard #11 checker: bug-close gate")
    ap.add_argument("--root", required=True)
    ap.add_argument("--sentinel", required=True)
    args = ap.parse_args(argv)
    res = check(args.root, args.sentinel)
    print(json.dumps(res))
    return 1 if res["verdict"] == "valid-fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
