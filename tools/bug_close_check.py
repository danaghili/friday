#!/usr/bin/env python3
"""Guard #11's checker — bug-close gate (TECHNICAL_SOW_REBUILD FR-55 guard
#11, S-1: "Bug closure is guard-gated: no closure without the committed
regression test and the completed trail"). Contract:
docs/contracts/lane-open.md's `regression-test` field (required when
lane=bug).

Three mechanical requirements, all must hold:
  1. The sentinel's `regression-test` field names an EXISTING `tests/*.py`
     file (worktree-root-relative). Existence is what is mechanically
     checked here; S-1's commit requirement lands in the fix commit itself.
  2. The sentinel's `trail` field, delegated whole to
     tools/trail_check.py's check_text() (one grammar, one home — this
     checker never re-derives the trail grammar), passes.
  3. The `docs/BUGS.md` ledger entry for the closing bug id exists and its
     `**Status:**` line no longer reads open (journey audit NF11) — a bug
     that closes while the dedup ledger still calls it open poisons every
     future duplicate-and-past-ruling grep.

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
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trail_check  # noqa: E402


def _ledger_status_issue(root: str, bug_id) -> str | None:
    """Requirement 3 — the ledger agreement. Returns the issue text, or None
    when the ledger and the close agree. A sentinel without an id has nothing
    to cross-check (fail open toward the other two requirements)."""
    if not isinstance(bug_id, str) or not bug_id.strip():
        return None
    bug_id = bug_id.strip()
    path = os.path.join(root, "docs", "BUGS.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return (f"docs/BUGS.md is missing — the {bug_id} entry the intake step "
                "mints was never written")
    heading = re.compile(rf"^##\s+{re.escape(bug_id)}(\s|—|$)")
    in_entry = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_entry = bool(heading.match(line))
            continue
        if in_entry and line.lstrip().startswith("**Status:**"):
            status_val = line.split("**Status:**", 1)[1].strip()
            if status_val.lower().startswith("open"):
                return (f"the {bug_id} ledger entry still reads Status: open — "
                        "flip it (e.g. `fixed <date> (…)`) before closing")
            return None
    return (f"docs/BUGS.md has no `## {bug_id}` entry — the ledger the "
            "bug/feedback lanes grep for past rulings never got this bug")


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

    ledger_issue = _ledger_status_issue(root, sentinel.get("id"))
    if ledger_issue:
        return {"verdict": "valid-fail",
                "summary": f"regression test OK ({reg_test}), trail valid, but "
                           f"the ledger disagrees: {ledger_issue}"}

    return {"verdict": "valid-pass",
            "summary": f"bug closure OK: regression test {reg_test} exists, "
                       "trail valid, ledger status flipped"}


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
