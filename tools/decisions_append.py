#!/usr/bin/env python3
"""friday decision-log append CLI (A.4 step 1, A.6 — the shared writer).

Both capture channels use this ONE tool:
  Channel A (pm-ratified, harness-guaranteed): hooks/decision_capture.py
  invokes it when — and only when — the narrow [FRIDAY-DECISION] ask shape
  resolves, so the model's judgment picks the shape and the harness guarantees
  the write.
  Channel B (model-autonomous, self-recorded): the build agent invokes it
  directly the moment a choice clears the three-part bar. Honesty for this
  channel is post-build reconciliation (extractor-vs-synthesis-vs-DECISIONS
  diff) + the capture-integrity timestamp-spread check — not the harness.

Usage:
  python3 tools/decisions_append.py --title "..." --decision "..." --why "..." \
      --rejected "..." [--channel pm-ratified|model-autonomous] \
      [--weight one-way|two-way] [--floor none|schema-data|auth-security|external-api|friday-claims|spend] \
      [--back-filled] [--when ISO8601Z] [--root DIR] [--json]
  python3 tools/decisions_append.py --init [--root DIR] [--project NAME]

`--init` writes the A.2 empty form (used by /adopt and /init); it refuses to
clobber an existing file (idempotent: exit 0 with a note). Appends echo the
exact appended entry so the transcript carries the durable record.

Exit codes: 0 written/ok · 2 bad invocation (nothing written).
Pure stdlib.
"""
# Contract: docs/contracts/decision-capture.md — this writer is a named producer;
# cited on both sides of the handoff (A14).
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decisions  # noqa: E402
import friday_substrate as fs  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Append one entry to docs/DECISIONS.md")
    ap.add_argument("--init", action="store_true", help="write the A.2 empty form and exit")
    ap.add_argument("--project", default=None, help="project name for the H1 (init only)")
    ap.add_argument("--title")
    ap.add_argument("--decision")
    ap.add_argument("--why")
    ap.add_argument("--rejected")
    ap.add_argument("--channel", default="model-autonomous", choices=decisions.CHANNELS)
    ap.add_argument("--weight", default="two-way", choices=decisions.WEIGHTS)
    ap.add_argument("--floor", default="none", choices=("none", *decisions.FLOORS))
    ap.add_argument("--back-filled", action="store_true",
                    help="entry records a decision made before the log/writer existed (A.4)")
    ap.add_argument("--when", default=None, help="real decision time (default: now)")
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    ap.add_argument("--cap", type=int, default=decisions.DEFAULT_CAP)
    ap.add_argument("--override-grant", default=None,
                    help="record a guard override-grant for this target path/element "
                         "(FR-55: the structured authorization guards #3/#5/#7/#10 require)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"decisions_append: --root is not a directory: {root}", file=sys.stderr)
        return 2

    wroot = fs.resolve_worktree_root(root)
    path = os.path.join(wroot, decisions.DEFAULT_PATH)

    if args.init:
        # Substrate-hygiene guard (D-0007, live incident in the loop-gate
        # drill): a project without a `.friday/` gitignore rule lets any
        # `git add -A` commit the runtime substrate, and a later worktree
        # checkout then materializes a STALE COPY that shadows the shared
        # one (preserve-list §4.5). Init therefore always ensures the rule.
        gi_path = os.path.join(wroot, ".gitignore")
        try:
            with open(gi_path, encoding="utf-8") as fh:
                gi = fh.read()
        except OSError:
            gi = ""
        if ".friday/" not in gi and ".friday" not in gi.split():
            with open(gi_path, "a", encoding="utf-8") as fh:
                if gi and not gi.endswith("\n"):
                    fh.write("\n")
                fh.write("# friday runtime substrate — regenerable but load-bearing; NEVER commit\n"
                         ".friday/\n")
            print(f"decisions_append: added .friday/ to {gi_path}")
        if os.path.isfile(path):
            print(f"decisions_append: {path} already exists — leaving it untouched")
            return 0
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(decisions.empty_form(args.project or os.path.basename(wroot), args.cap))
        print(f"decisions_append: initialized empty decision log at {path}")
        return 0

    missing = [f for f in ("title", "decision", "why", "rejected")
               if not getattr(args, f)]
    if missing:
        print(f"decisions_append: missing required --{', --'.join(missing)}", file=sys.stderr)
        return 2

    if args.floor != "none" and args.channel == "model-autonomous":
        # S-1: floor-category decisions are surfaced + one-way regardless. A
        # solo/parked build may still record them, but never silently.
        print(f"decisions_append: WARNING — floor category {args.floor!r} recorded "
              "model-autonomous; the hardening pass scrutinizes these first (S-2), "
              "and the PM should ratify or reverse it at the next gate.",
              file=sys.stderr)

    try:
        id_str, entry = decisions.append_entry(
            root, title=args.title, decision=args.decision, why=args.why,
            rejected=args.rejected, channel=args.channel, weight=args.weight,
            floor=args.floor, back_filled=args.back_filled, when=args.when,
            cap=args.cap, override_grant=args.override_grant)
    except ValueError as exc:
        print(f"decisions_append: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"decisions_append: write failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"ok": True, "id": id_str, "path": path}))
    else:
        print(entry, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
