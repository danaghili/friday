#!/usr/bin/env python3
"""friday compaction-note CLI — the mission/orientation write door (INC-001
FR-1.5/FR-1.6; contract: docs/contracts/compaction-package.md).

The orchestrator authors its mission note at lane entry (its layer-1
equivalent — nobody spawns it); any agent doing non-trivial work jots and
tops up its orientation note here. Text arrives on stdin or via --file;
writes go through the single substrate writer, never raw.

Usage:
  python3 "${CLAUDE_PLUGIN_ROOT}/tools/compaction_note.py" \
      --layer mission|orientation --agent friday-lead \
      [--session-id <sid>] [--file <path>] [--cwd .]

Exit codes: 0 written (path echoed) · 2 bad invocation, nothing written.
Pure stdlib.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write a compaction-package layer")
    ap.add_argument("--layer", required=True,
                    help=f"one of {'|'.join(fs.COMPACTION_LAYERS)}")
    ap.add_argument("--agent", required=True, help="agent slug, e.g. friday-lead")
    ap.add_argument("--session-id", default=None,
                    help="drawer key (default: newest session lock)")
    ap.add_argument("--file", default=None, help="read text from file instead of stdin")
    ap.add_argument("--cwd", default=".", help="project root (default: cwd)")
    args = ap.parse_args(argv)

    cwd = os.path.abspath(args.cwd)
    if not fs.should_engage(cwd):
        print(f"compaction_note: {cwd} is not a friday project — refusing to "
              "create a stray drawer", file=sys.stderr)
        return 2
    if args.layer not in fs.COMPACTION_LAYERS:
        print(f"compaction_note: --layer must be one of "
              f"{'|'.join(fs.COMPACTION_LAYERS)}, got {args.layer!r}", file=sys.stderr)
        return 2
    try:
        if args.file is not None:
            with open(args.file, encoding="utf-8") as fh:
                text = fh.read()
        else:
            text = sys.stdin.read()
    except OSError as exc:
        print(f"compaction_note: {exc}", file=sys.stderr)
        return 2
    if not text.strip():
        print("compaction_note: refusing to write an empty note", file=sys.stderr)
        return 2

    sid = args.session_id or fs.current_session_id(cwd)
    try:
        path = fs.compaction_write_layer(cwd, session_id=sid, agent=args.agent,
                                         layer=args.layer, text=text)
    except (OSError, ValueError) as exc:
        print(f"compaction_note: {exc}", file=sys.stderr)
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
