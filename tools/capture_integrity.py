#!/usr/bin/env python3
"""Capture-integrity check — the §6.6 timestamp-spread smell detector.

Channel B (model-autonomous) cannot be harness-guaranteed, so its honesty is
enforced by reconciliation: self-recorded entries CLUSTERED at one moment are
a retro-fabrication smell (a decision log reconstructed at the end is a
rationalization, not a record). Entries tagged `back-filled: true` are exempt
BY DESIGN — that tag exists precisely so honest back-fills (A.4) are never
misread as fabrication.

Warn-level only (a smell, not proof): the §6.7 extractor-vs-synthesis diff is
the structural half; this is the temporal half.

Exit codes: 0 (always, unless malformed log — 1) · findings ride the JSON.
"""
# Contract: docs/contracts/decision-capture.md — this integrity checker is a named
# consumer; cited on both sides of the handoff (A14).
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decisions  # noqa: E402
import friday_substrate as fs  # noqa: E402

CLUSTER_WINDOW_MIN = 15   # >= MIN_ENTRIES live entries inside this window = smell
MIN_ENTRIES = 4


def _ts(entry: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(entry.get("when", "").replace("Z", "+00:00"))
    except ValueError:
        return None


def check(root: str) -> dict:
    path = os.path.join(fs.resolve_worktree_root(root), decisions.DEFAULT_PATH)
    parsed = decisions.parse_file(path)
    if not parsed["ok"]:
        return {"ok": False, "findings": [
            {"severity": "blocking", "detail": f"DECISIONS.md malformed: {parsed['errors'][:3]}"}],
            "summary": "capture-integrity: log malformed"}

    live = [e for e in parsed["entries"] if not e["back_filled"]]
    stamps = sorted(t for t in (_ts(e) for e in live) if t)
    findings: list[dict] = []
    if len(stamps) != len(live):
        findings.append({"severity": "warn",
                         "detail": f"{len(live) - len(stamps)} live entrie(s) with "
                                   "unparseable timestamps"})
    if len(stamps) >= MIN_ENTRIES:
        span_min = (stamps[-1] - stamps[0]).total_seconds() / 60
        if span_min < CLUSTER_WINDOW_MIN:
            findings.append({"severity": "warn", "detail": (
                f"{len(stamps)} self-recorded entries span only {span_min:.0f} "
                f"minutes — end-clustered timestamps are the retro-fabrication "
                "smell this check exists for (as-you-go means spread across the "
                "build; back-fills must carry back-filled: true)")})
    return {"ok": True, "findings": findings,
            "entries": len(parsed["entries"]), "live": len(live),
            "back_filled": len(parsed["entries"]) - len(live),
            "summary": ("capture-integrity: spread looks organic"
                        if not findings else
                        f"capture-integrity: {len(findings)} smell(s)")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = check(os.path.abspath(args.root))
    print(json.dumps(res) if args.json else res["summary"])
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
