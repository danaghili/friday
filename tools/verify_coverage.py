#!/usr/bin/env python3
"""Requirement-coverage verifier — retargeted to the TSOW §4 requirement-ID
spine (K7). Every FR/NFR/AC/S ID declared in docs/TECHNICAL_SOW.md — and in
any increment oracle under docs/increments/*.md (DF-023: increments are
separate spec documents, pointer-linked from the TSOW's `## Increments`
section, so the TSOW stays bounded) — must carry a closing disposition in
docs/reviews/coverage.md — implemented, or explicitly deferred WITH a reason.
Set-closure, one implementation (callers keep the disposition).

ID extraction is structural, not free-prose: an ID counts only where it
anchors a requirement row/bullet/bold token (`- **FR-1** …`, `| AC-2 |`,
`**S-1**:`) — a prose sentence mentioning "FR-1" does not mint a requirement.
Increment-minted IDs are dotted (`FR-1.1`) and extracted whole — never
truncated to a colliding parent ID. Empty case: an absent or .md-less
docs/increments/ is identical to TSOW-only behavior.

Disposition grammar (typed tag lines inside the FRIDAY-DISPOSITIONS block):
  disposition: <ID> implemented — <evidence>
  disposition: <ID> deferred — <reason>

Empty case: a TSOW with zero anchored IDs is vacuously closed (ok, noted);
an empty FRIDAY-DISPOSITIONS block is valid when there is nothing to cover.

Exit codes: 0 closed · 1 gaps · 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

_ANCHORED_ID_RE = re.compile(
    r"(?:^\s*[|\-*]\s*\**|\*\*)((?:FR|NFR|AC|S)-\d+(?:\.\d+)?)\b", re.M)
_DISPO_RE = re.compile(
    r"^((?:FR|NFR|AC|S)-\d+(?:\.\d+)?)\s+(implemented|deferred)\s+—\s+(.+)$")

# A2 (harden): a `deferred` disposition must cite a pm-ratified decision (D-NNNN) —
# a model-authored deferral with only a reason string is a gap, not a closure.
_DECISION_REF = re.compile(r"\bD-\d{4}\b")

TSOW_PATH = os.path.join("docs", "TECHNICAL_SOW.md")
INCREMENTS_DIR = os.path.join("docs", "increments")
LEDGER_PATH = os.path.join("docs", "reviews", "coverage.md")


def extract_tsow_ids(text: str) -> list[str]:
    seen: list[str] = []
    for m in _ANCHORED_ID_RE.finditer(text):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def parse_ledger(text: str) -> tuple[dict[str, dict], list[str]]:
    """{id: {state, note}} + errors. Absent block → ({}, [note])."""
    lines = taglines.block_lines(text, "FRIDAY-DISPOSITIONS")
    if lines is None:
        return {}, ["no FRIDAY-DISPOSITIONS block in the coverage ledger"]
    out: dict[str, dict] = {}
    errors: list[str] = []
    for ln in lines:
        parsed = taglines.parse_typed_line(ln)
        if not parsed or parsed[0] != "disposition":
            errors.append(f"non-disposition line inside the block: {ln!r}")
            continue
        m = _DISPO_RE.match(parsed[1])
        if not m:
            errors.append(f"disposition does not parse (need '<ID> "
                          f"implemented|deferred — <note>'): {parsed[1]!r}")
            continue
        out[m.group(1)] = {"state": m.group(2), "note": m.group(3)}
    return out, errors


def increment_files(root: str) -> list[str]:
    """Sorted .md paths under docs/increments/ — [] when the dir is absent
    (the defined empty case: identical to TSOW-only behavior)."""
    inc_dir = os.path.join(root, INCREMENTS_DIR)
    try:
        names = sorted(n for n in os.listdir(inc_dir) if n.endswith(".md"))
    except OSError:
        return []
    return [os.path.join(inc_dir, n) for n in names]


def check(root: str, tsow_path: str = TSOW_PATH,
          ledger_path: str = LEDGER_PATH) -> dict:
    """Set-closure of one oracle against one disposition file. Defaults are
    the main TSOW + coverage.md (behavior unchanged). A second oracle — Open
    Question 1: the rebuild TSOW — closes with its OWN ledger via the
    parameters; the two ID spaces are never joined (same-spelled IDs in the
    two oracles are different requirements). Increments fold in ONLY for the
    default oracle: they are minted against the main TSOW (skills/feature/
    SKILL.md pointer rule); a non-default oracle closes over exactly its
    own file."""
    tsow = os.path.join(root, tsow_path)
    try:
        with open(tsow, encoding="utf-8") as fh:
            ids = extract_tsow_ids(fh.read())
    except OSError:
        return {"ok": False, "gaps": [{"id": "-", "detail": f"missing {tsow_path}"}],
                "ids": [], "summary": f"coverage: missing {tsow_path}"}

    inc_paths = increment_files(root) if tsow_path == TSOW_PATH else []
    for path in inc_paths:
        with open(path, encoding="utf-8") as fh:
            for rid in extract_tsow_ids(fh.read()):
                if rid not in ids:
                    ids.append(rid)

    if not ids:
        return {"ok": True, "gaps": [], "ids": [], "increment_files": [],
                "summary": "coverage: TSOW declares no requirement IDs — vacuously closed"}

    ledger_abs = os.path.join(root, ledger_path)
    try:
        with open(ledger_abs, encoding="utf-8") as fh:
            ledger, errors = parse_ledger(fh.read())
    except OSError:
        ledger, errors = {}, [f"missing {ledger_path} while the TSOW declares "
                              f"{len(ids)} requirement IDs"]

    gaps = [{"id": "-", "detail": e} for e in errors]
    for rid in ids:
        if rid not in ledger:
            gaps.append({"id": rid, "detail": f"{rid} has no disposition"})
        elif ledger[rid]["state"] == "deferred":
            note = ledger[rid]["note"].strip()
            if not note:
                gaps.append({"id": rid, "detail": f"{rid} deferred without a reason"})
            elif not _DECISION_REF.search(note):
                gaps.append({"id": rid, "detail": f"{rid} deferred without citing a "
                                                  "pm-ratified decision (D-NNNN) — a model-authored "
                                                  "deferral is a gap, not a closure (A2)"})
    unknown = [rid for rid in ledger if rid not in ids]
    ok = not gaps
    scope = (f"{len(ids)} requirement IDs (TSOW + {len(inc_paths)} increment(s))"
             if inc_paths else f"{len(ids)} TSOW IDs")
    return {"ok": ok, "gaps": gaps, "ids": ids, "unknown_dispositions": unknown,
            "increment_files": [os.path.relpath(p, root) for p in inc_paths],
            "summary": (f"coverage: all {scope} dispositioned"
                        if ok else
                        f"coverage: {len(gaps)} gap(s) over {scope} — "
                        + "; ".join(g["detail"] for g in gaps[:5]))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--tsow", default=TSOW_PATH,
                    help="oracle to close (root-relative); a non-default oracle "
                         "closes over exactly its own file — increments never fold in")
    ap.add_argument("--ledger", default=LEDGER_PATH,
                    help="disposition file for THIS oracle (root-relative) — "
                         "each oracle keeps its own; ID spaces are never joined")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        print(f"verify_coverage: no such dir: {args.root}", file=sys.stderr)
        return 2
    res = check(os.path.abspath(args.root), tsow_path=args.tsow,
                ledger_path=args.ledger)
    print(json.dumps(res) if args.json else res["summary"])
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
