#!/usr/bin/env python3
"""Guard #3's checker — oracle-edit gate (TECHNICAL_SOW_REBUILD FR-55 guard
#3; D-0018 event mapping: "a spec-write PreToolUse arms when its own
coverage ledger already holds a disposition — closure is underway, so drift
must go through the decision log, not a silent edit").

Mapping: docs/TECHNICAL_SOW.md's ledger is docs/reviews/coverage.md;
docs/TECHNICAL_SOW_REBUILD.md's is docs/reviews/coverage-rebuild.md — the
two oracles Open Question 1 / D-0015 actually names. An oracle basename
outside this closed pair cannot be judged — no-verdict, fail-open.

Armed ⇔ the mapped ledger exists AND its FRIDAY-DISPOSITIONS block holds ≥1
`disposition:` line (closure is underway). NOT armed (ledger absent, empty,
or zero disposition lines) → valid-pass — nothing to protect yet. Armed AND
docs/DECISIONS.md does not name the oracle's repo-relative path → valid-fail
(an undocumented drift on a frozen oracle). Armed AND DECISIONS.md names it
→ valid-pass (the PM amendment is on record).

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
import decisions  # noqa: E402

LEDGER_MAP = {
    "TECHNICAL_SOW.md": os.path.join("docs", "reviews", "coverage.md"),
    "TECHNICAL_SOW_REBUILD.md": os.path.join("docs", "reviews", "coverage-rebuild.md"),
}


def check(path: str, root: str) -> dict:
    root = os.path.abspath(root)
    basename = os.path.basename(path)
    ledger_rel = LEDGER_MAP.get(basename)
    if ledger_rel is None:
        return {"verdict": "no-verdict",
                "detail": f"no known coverage ledger mapped for oracle {basename!r}"}

    oracle_rel = os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")
    ledger_abs = os.path.join(root, ledger_rel)
    try:
        with open(ledger_abs, encoding="utf-8") as fh:
            ledger_text = fh.read()
    except OSError:
        return {"verdict": "valid-pass",
                "summary": f"{ledger_rel} does not exist — closure not underway, "
                           f"{basename} is not armed"}

    typed = taglines.block_typed(ledger_text, "FRIDAY-DISPOSITIONS")
    dispositions = (typed or {}).get("disposition", [])
    if not dispositions:
        return {"verdict": "valid-pass",
                "summary": f"{ledger_rel} carries no disposition: lines — closure "
                           f"not underway, {basename} is not armed"}

    decisions_abs = os.path.join(root, "docs", "DECISIONS.md")
    try:
        with open(decisions_abs, encoding="utf-8") as fh:
            decisions_text = fh.read()
    except OSError:
        decisions_text = ""

    if decisions.has_override_grant(decisions_text, oracle_rel):
        return {"verdict": "valid-pass",
                "summary": f"docs/DECISIONS.md carries an override-grant for "
                           f"{oracle_rel} — the PM amendment is on record"}
    return {"verdict": "valid-fail",
            "summary": f"{oracle_rel} is frozen (closure underway per "
                       f"{ledger_rel}, {len(dispositions)} disposition(s) "
                       "recorded) and docs/DECISIONS.md does not name it — "
                       "drift on a frozen oracle must go through the decision log"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guard #3 checker: oracle-edit gate")
    ap.add_argument("--path", required=True, help="the oracle path being edited")
    ap.add_argument("--root", required=True, help="project root")
    args = ap.parse_args(argv)
    res = check(args.path, args.root)
    print(json.dumps(res))
    return 1 if res["verdict"] == "valid-fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
