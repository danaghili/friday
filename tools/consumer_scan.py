#!/usr/bin/env python3
"""The mechanical half of the consumer enumeration — two needles, one walk
(INC-104 FR-104.2, FR-104.7, FR-104.8; OQ-104.3).

The enumerating question — *who is standing outside this, depending on it?* —
takes four sources at once. This scan runs the two mechanical ones and states
plainly that it cannot run the other two:

  - **declared** — citations of the changed thing's PATH, the existing
    contract-citation scan read inside out (D5): a surface that names
    `docs/contracts/reckoning-record.md` has declared itself a consumer
    of it.
  - **name-match** — an exact search of the tree for the changed thing's own
    NAME. The audited project's two cleared scripts both carried the changed
    label literally; the supervisor that broke carried no name at all, which
    is why `reading` and `person` exist and why this scan's limits ride its
    output rather than a caveat somebody maintains.

Design rules, each load-bearing:

  - **Names, never values (S-104.4, AC-104.7):** a matching line can carry a
    credential in the clear — a deploy script with an inline token is the
    ordinary case. Evidence is `path:line names <name>`, the path and the
    fact of the match; no matched line's content is ever reproduced.
  - **Too common is an answer, not a truncation (OQ-104.3):** past the bound
    the scan returns ZERO candidates and the measured spread — a partial
    list would lie by omission, and the other sources carry the enumeration.
  - **Process-shaped files carry a hint (FR-104.7):** a supervisor
    definition, a schedule, a Procfile found BY NAME is flagged
    `kind_hint: process` so the recorder lists it beside the code rather
    than as more code. The hint is a nudge, never the class ruling — that
    belongs to whoever records the reckoning.
  - **Report-only (S-104.1):** exit 0 whatever it finds.

The reckoning record this feeds is `tools/reckoning.py`'s
(contract: `docs/contracts/reckoning-record.md`). Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reckoning  # noqa: E402

SKIP_DIRS = frozenset((".git", ".friday", "node_modules", "__pycache__",
                       ".venv", "venv", ".tox", "dist", "build"))
# The record of answers is not itself a consumer — scanning it would return
# every past reckoning of the same name as a fresh candidate, forever.
EXCLUDED_FILES = frozenset(("docs/RECKONINGS.md",))
# Filename shapes that usually mean "a piece of running process, not code":
# supervisors, schedules, boot definitions, runbooks (FR-104.7).
PROCESS_HINTS = (".plist", ".service", ".timer", "crontab", "cron.d",
                 "procfile", "docker-compose", "supervisor", "launchd",
                 "runbook")
# OQ-104.3's bound: past this many matching FILES the name is reported as
# too common to search usefully. Calibrated against a real tree at the
# increment's acceptance runs, not estimated.
DEFAULT_TOO_COMMON_FILES = 30

CANNOT_RUN = {
    "reading": "what the model finds by reading runs in the lane, "
               "not in this scan",
    "person": "the person's answer arrives at the lane's own stop; "
              "no scan can produce it",
}


def _is_binary(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return b"\x00" in fh.read(8192)
    except OSError:
        return True


def _walk(root: str):
    """Yield (relpath, fullpath) for every file under root outside the
    skip set, in sorted order — the caller decides text vs binary so the
    skip tally lands in the report."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fname in sorted(filenames):
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel in EXCLUDED_FILES:
                continue
            yield rel, full


def _match_lines(text: str, needle: str) -> list[int]:
    return [i for i, line in enumerate(text.splitlines(), start=1)
            if needle in line]


def _kind_hint(rel: str) -> str:
    low = rel.lower()
    return "process" if any(h in low for h in PROCESS_HINTS) else "code"


def _candidate(rel: str, lines: list[int], verb: str, needle: str,
               source: str) -> dict:
    evidence = f"{rel}:{lines[0]} {verb} {needle}"
    if len(lines) > 1:
        evidence += f" ({len(lines)} matching lines)"
    return {"what": rel, "source": source, "evidence": evidence,
            "kind_hint": _kind_hint(rel)}


def scan(root: str = ".", *, name: str, path: str | None = None,
         too_common_files: int | None = None) -> dict:
    """Run both mechanical sources over one walk. `name` drives the
    exact-name search; `path` (the changed thing's file path, when it has
    one) drives the declared-citation scan — absent, that source is
    honestly `skipped`, never quietly empty."""
    bound = too_common_files or DEFAULT_TOO_COMMON_FILES
    name_hits: list[dict] = []
    declared_hits: list[dict] = []
    files = binary = 0
    for rel, full in _walk(root):
        if rel == path:
            continue
        if _is_binary(full):
            binary += 1
            continue
        files += 1
        with open(full, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        lines = _match_lines(text, name)
        if lines:
            name_hits.append(_candidate(rel, lines, "names", name,
                                        "name-match"))
        if path:
            cited = _match_lines(text, path)
            if cited:
                declared_hits.append(_candidate(rel, cited, "cites", path,
                                                "declared"))
    name_match: dict = {"state": "ran", "files_matched": len(name_hits),
                        "candidates": name_hits}
    if len(name_hits) > bound:
        name_match = {"state": "too-common", "files_matched": len(name_hits),
                      "candidates": [],
                      "reason": f"the name matched in {len(name_hits)} "
                                f"files against a bound of {bound} — too "
                                "common to search usefully; the other "
                                "sources carry the enumeration (OQ-104.3)"}
    declared: dict = ({"state": "ran", "candidates": declared_hits}
                      if path else
                      {"state": "skipped", "candidates": [],
                       "reason": "the changed thing has no file path to "
                                 "cite — nothing can have declared itself"})
    return {"ok": True, "name": name, "path": path,
            "declared": declared, "name_match": name_match,
            "cannot_run": dict(CANNOT_RUN),
            "limits": [reckoning.NAMELESS_LIMIT],
            "scanned": {"files": files, "skipped_binary": binary}}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", default=".")
    p.add_argument("--name", required=True,
                   help="the changed thing's own name — the exact literal")
    p.add_argument("--path", default=None,
                   help="the changed thing's file path, when it has one")
    p.add_argument("--too-common-files", type=int, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    out = scan(args.root, name=args.name, path=args.path,
               too_common_files=args.too_common_files)
    if args.json:
        print(json.dumps(out, indent=2))
        return 0
    for src in ("declared", "name_match"):
        block = out[src]
        line = f"{src}: {block['state']}"
        if block.get("reason"):
            line += f" — {block['reason']}"
        print(line)
        for c in block["candidates"]:
            print(f"  {c['evidence']} [{c['kind_hint']}]")
    for source, why in out["cannot_run"].items():
        print(f"cannot run {source}: {why}")
    for limit in out["limits"]:
        print(f"limit: {limit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
