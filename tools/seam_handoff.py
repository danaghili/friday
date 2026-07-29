#!/usr/bin/env python3
"""seam-handoff — the net-new build-model primitive (NOT skills/handoff/SKILL.md,
which is the client-facing deliverable; never conflate the two — §13).

When a one-shot run approaches the ~120k smart zone, the build forces a seam
at a clean foundation boundary instead of pushing past. This tool assembles
the carry-forward brief the NEXT unit starts from: the substrate the seam
carries is `DECISIONS.md` + architecture notes + the generated code-map —
never the session's history (fold resolved, already-logged decisions OUT; a
dispatch describes one unit of work).

Writes `<shared .friday>/seam-handoff.md` and journals a `state-transition`
event with `data: {"seam": true}`. `--clear` removes a stale brief through
this same single writer (journey audit NF13 — resume must never resume from
a seam the work outlived), journaling `{"seam": "cleared", "reason": ...}`.

Usage: python3 tools/seam_handoff.py --root . [--next "<one-line next-unit goal>"]
       python3 tools/seam_handoff.py --root . --clear [--reason "<why>"]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decisions  # noqa: E402
import friday_substrate as fs  # noqa: E402


def assemble(root: str, next_goal: str | None) -> str:
    wroot = fs.resolve_worktree_root(root)
    lines = ["# seam-handoff — carry-forward brief", "",
             f"Generated {fs.now_iso()} by tools/seam_handoff.py. The next unit "
             "STARTS from this brief + the files it names; it does not inherit "
             "the previous context.", ""]
    if next_goal:
        lines += ["## Next unit", "", next_goal, ""]

    lines += ["## Read list (in order)", "",
              "1. `docs/TECHNICAL_SOW.md` — the oracle (never edited by the build).",
              "2. `docs/DECISIONS.md` — every call already made; do not re-decide.",
              "3. `docs/architecture/README.md` + `docs/architecture/generated/` — the code-map.",
              "4. `CLAUDE.md` — FRIDAY-CLAIMS + FRIDAY-STATE.", ""]

    parsed = decisions.parse_file(os.path.join(wroot, decisions.DEFAULT_PATH))
    if parsed["ok"] and parsed["entries"]:
        lines += ["## Decision index (titles only — the log has the why)", ""]
        lines += [f"- {e['id_str']} — {e['title']} ({e['channel']}, {e['weight']})"
                  for e in parsed["entries"]]
        lines.append("")

    ir_path = os.path.join(wroot, "docs", "architecture", "generated",
                           "architecture-ir.json")
    if os.path.isfile(ir_path):
        try:
            with open(ir_path, encoding="utf-8") as fh:
                ir = json.load(fh)
            lines += ["## Code map (from the generated IR)", "",
                      f"{len(ir.get('modules', []))} modules · "
                      f"{len(ir.get('edges', []))} edges · "
                      f"{len(ir.get('routes', []))} routes", ""]
            lines += [f"- `{m['id']}` ({m['loc']} loc)" for m in ir.get("modules", [])]
            lines.append("")
        except (OSError, json.JSONDecodeError):
            pass

    try:
        status = subprocess.run(["git", "-C", wroot, "status", "--porcelain"],
                                capture_output=True, text=True, timeout=10).stdout
        lines += ["## Working tree at the seam", "", "```",
                  status.strip() or "(clean)", "```", ""]
    except OSError:
        pass

    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--next", dest="next_goal", default=None)
    ap.add_argument("--clear", action="store_true",
                    help="remove a stale brief (single-writer path; journals why)")
    ap.add_argument("--reason", default=None,
                    help="with --clear: why the brief is being cleared")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    if not fs.should_engage(root):
        print("seam_handoff: not a friday project", file=sys.stderr)
        return 2
    if args.clear:
        out = os.path.join(fs.friday_dir(root), "seam-handoff.md")
        if not os.path.isfile(out):
            print("seam_handoff: no brief to clear")
            return 0
        os.remove(out)
        fs.append_journal_line(root, fs.build_journal_line(
            "state-transition", "build:seam", by="lead",
            data={"seam": "cleared", "reason": args.reason or "unspecified"}))
        print(f"seam_handoff: cleared {out}")
        return 0
    brief = assemble(root, args.next_goal)
    out = os.path.join(fs.friday_dir(root), "seam-handoff.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(brief)
    fs.append_journal_line(root, fs.build_journal_line(
        "state-transition", "build:seam", by="lead", data={"seam": True}))
    print(f"seam_handoff: wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
