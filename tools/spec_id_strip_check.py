#!/usr/bin/env python3
"""Spec-ID ship-gate (A15 — enforces D-0044's strip-at-ship promise).

Internal requirement-ID tags (FR-/NFR-/US-/AC-/S-n) are KEPT through the build
for oracle traceability and STRIPPED before ship ([[spec-id-tags-internal-only]]).
That promise had no mechanical backstop; this is it. Run at the §10 ship pass over
the user-facing surfaces: any surviving spec-ID tag is a finding — a marketplace
stranger has no key for "FR-83". Two invocation shapes:

- explicit file paths (`commands/*.md`, `skills/**/SKILL.md`, …) — unchanged: a
  non-file path is a bad invocation (exit 2);
- `--skills-dir <dir>` — the surface-aware lane-folder mode (INC-003 FR-3.3):
  self-enumerates EVERY file in every lane folder, SKILL.md and bundled siblings
  alike, so a tag cannot ship by hiding in a bundled reference and no future
  author has to remember to widen a glob. Directories are walked, never passed
  as scan paths; a binary/non-UTF-8 sibling is skipped defensively, never a
  crash (KH-1). Empty case: no skills dir, or folders holding only their
  SKILL.md → scans exactly as the explicit-path shape does today.

NOT a build-time gate: mid-build the tags are supposed to be present, so this is
invoked deliberately at ship, never in the standing suite. Decision ids (D-NNNN)
are record references, not spec-ID tags, and are not flagged.

Exit codes: 0 clean · 1 surviving tags found · 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_SPEC_ID = re.compile(r"\b(?:FR|NFR|US|AC|S)-\d+\b")


def scan_text(text: str) -> list[dict]:
    """[{line, tag}] for every surviving spec-ID tag; [] when clean."""
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        for m in _SPEC_ID.finditer(line):
            out.append({"line": i, "tag": m.group(0)})
    return out


def scan_file(path: str) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return [{**h, "file": path} for h in scan_text(fh.read())]
    except OSError:
        return []


def scan_lane_dir(skills_dir: str) -> list[dict]:
    """Surface-aware mode (INC-003 FR-3.3): every file in every lane folder,
    bundled siblings included. Walks directories itself (never hands a folder
    to the file scanner) and skips a binary/unreadable sibling instead of
    crashing (KH-1). Empty case: missing dir or SKILL.md-only folders → the
    same hits the explicit-path shape produces."""
    hits: list[dict] = []
    if not os.path.isdir(skills_dir):
        return hits
    for lane in sorted(os.listdir(skills_dir)):
        folder = os.path.join(skills_dir, lane)
        if not os.path.isdir(folder):
            continue
        for root, _dirs, files in os.walk(folder):
            for name in sorted(files):
                path = os.path.join(root, name)
                try:
                    with open(path, encoding="utf-8") as fh:
                        text = fh.read()
                except (OSError, UnicodeDecodeError):
                    continue  # binary/asset sibling: skipped, never a hard error
                hits.extend({**h, "file": path} for h in scan_text(text))
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Flag surviving internal spec-ID tags (ship gate)")
    ap.add_argument("paths", nargs="*", help="surface file(s) to scan")
    ap.add_argument("--skills-dir", default=None,
                    help="lane-folder mode: self-enumerate every skill folder's "
                         "files, bundled siblings included (INC-003 FR-3.3)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not args.paths and not args.skills_dir:
        ap.print_usage(sys.stderr)
        print("spec_id_strip_check: give surface file(s) and/or --skills-dir",
              file=sys.stderr)
        return 2

    hits: list[dict] = []
    for p in args.paths:
        if not os.path.isfile(p):
            print(f"spec_id_strip_check: not a file: {p}", file=sys.stderr)
            return 2
        hits.extend(scan_file(p))
    if args.skills_dir:
        hits.extend(scan_lane_dir(args.skills_dir))

    if args.json:
        print(json.dumps({"ok": not hits, "hits": hits, "count": len(hits)}, indent=2))
    elif not hits:
        print("spec-id ship gate: clean — no internal FR-/NFR-/US-/AC-/S-n tags survive.")
    else:
        print(f"spec-id ship gate: {len(hits)} surviving tag(s) — strip before ship (D-0044):")
        for h in hits:
            print(f"  - {h['file']}:{h['line']} {h['tag']}")
    return 0 if not hits else 1


if __name__ == "__main__":
    sys.exit(main())
