#!/usr/bin/env python3
"""Lane CLI — the maintenance doors' one mechanical call for opening,
inspecting, and clearing a lane (U3; contract: docs/contracts/lane-open.md;
helpers + rules: friday_substrate.lane_open / lane_clear — this file is
deliberately thin).

Usage:
  python3 tools/lane.py open  --lane bug|patch|feature --id <ID> --trail <path>
                              [--regression-test <declared-test-path>]   (REQUIRED for bug)
                              [--blast-radius <prefix-or-glob>]...  (REQUIRED for patch)
                              [--root DIR]
  python3 tools/lane.py status [--root DIR]
  python3 tools/lane.py clear  [--by pm|lead] [--root DIR]
                              # by=pm (default): the conscious PM-escalation path.
                              # by=lead: a door's own honest re-route/close (the
                              #   journal names who actually cleared, never a lie).

Exit codes: 0 ok · 2 contract violation / bad invocation (nothing written).
Disarm-on-pass belongs to the owning guard, never to this CLI. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    op = sub.add_parser("open")
    op.add_argument("--root", default=".")
    op.add_argument("--lane", required=True)
    op.add_argument("--id", required=True)
    op.add_argument("--trail", required=True)
    op.add_argument("--regression-test", default=None)
    op.add_argument("--blast-radius", action="append", default=None)

    st = sub.add_parser("status")
    st.add_argument("--root", default=".")

    cl = sub.add_parser("clear")
    cl.add_argument("--root", default=".")
    cl.add_argument("--by", default="pm", choices=("pm", "lead"),
                    help="who cleared it: pm (default, escalation) or lead (a door's re-route)")

    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)

    if args.cmd == "open":
        try:
            path = fs.lane_open(root, lane=args.lane, id=args.id,
                                trail=args.trail,
                                regression_test=args.regression_test,
                                blast_radius=args.blast_radius)
        except ValueError as exc:
            print(f"lane: {exc}", file=sys.stderr)
            return 2
        print(f"lane open: {path}")
        return 0

    sentinel = os.path.join(fs.friday_dir(root), "lane-open")
    if args.cmd == "status":
        try:
            with open(sentinel, encoding="utf-8") as fh:
                print(fh.read().strip())
        except OSError:
            print("no lane open")
        return 0

    # clear
    print("cleared" if fs.lane_clear(root, by=args.by) else "no lane open — nothing cleared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
