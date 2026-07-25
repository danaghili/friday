#!/usr/bin/env python3
"""friday spawn-telemetry CLI — the ONE spawn/accept/done journal primitive.

ISSUE-006 (the fix, NFR-4): old friday had ~65 prose-described journal appends
across 11 command files and 9+ spawning surfaces that never got instrumented,
because instrumentation was retrofitted piecemeal. In vnext there is exactly
one code path that emits a spawn/accept/done event — this tool — and every
surface that spawns work calls it; none hand-rolls its own journal write.
`tools/verify_spawn_coverage.py` mechanically checks that every command
surface that dispatches agents cites this tool.

Usage (from any command playbook, at dispatch / first-response / completion):
  python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn \
      --agent friday-tester --phase harden:tester [--feature F001] \
      [--by lead] [--data '{"model":"sonnet"}'] [--cwd .]

Events: spawn (dispatch sent) · accept (agent's first response observed) ·
done (agent reported complete). Envelope + atomicity via friday_substrate
(the single journal writer). Refuses to run outside a friday project — a
mistyped --cwd must not lazy-create a stray `.friday/`.

At spawn, `--prompt-file` also persists the prompt as the agent's mission
layer (INC-001 FR-1.5) — this tool is a WRITER side of the compaction
package; contract: docs/contracts/compaction-package.md.

Exit codes: 0 appended (exact line echoed) · 2 bad invocation, nothing written.
Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402

SPAWN_EVENTS = ("spawn", "accept", "done")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Append one spawn-telemetry event to .friday/journal.jsonl")
    ap.add_argument("--emit", required=True,
                    help=f"one of {'|'.join(SPAWN_EVENTS)}")
    ap.add_argument("--agent", required=True, help="agent name, e.g. friday-tester")
    ap.add_argument("--phase", required=True,
                    help='command-qualified phase, e.g. "harden:tester"')
    ap.add_argument("--feature", default="-")
    ap.add_argument("--by", default="lead", choices=fs.BY_VOCABULARY)
    ap.add_argument("--data", default=None, help="optional JSON OBJECT merged into data")
    ap.add_argument("--cwd", default=".", help="project root (default: cwd)")
    ap.add_argument("--prompt-file", default=None,
                    help="spawn only (INC-001 FR-1.5): file holding the spawn "
                         "prompt verbatim; persisted as the agent's mission "
                         "layer via the substrate verb")
    ap.add_argument("--session-id", default=None,
                    help="drawer key for --prompt-file (default: newest session lock)")
    args = ap.parse_args(argv)

    if args.emit not in SPAWN_EVENTS:
        print(f"spawn_telemetry: --emit must be one of {'|'.join(SPAWN_EVENTS)}, "
              f"got {args.emit!r}", file=sys.stderr)
        return 2
    cwd = os.path.abspath(args.cwd)
    if not os.path.isdir(cwd):
        print(f"spawn_telemetry: --cwd is not a directory: {cwd}", file=sys.stderr)
        return 2
    if not fs.should_engage(cwd):
        print(f"spawn_telemetry: {cwd} is not a friday project — refusing to "
              "create a stray journal", file=sys.stderr)
        return 2

    data: dict = {"agent": args.agent}
    if args.data is not None:
        try:
            extra = json.loads(args.data)
        except json.JSONDecodeError as exc:
            print(f"spawn_telemetry: --data is not valid JSON: {exc}", file=sys.stderr)
            return 2
        if not isinstance(extra, dict):
            print("spawn_telemetry: --data must be a JSON object", file=sys.stderr)
            return 2
        data.update(extra)

    if args.prompt_file is not None and args.emit != "spawn":
        print("spawn_telemetry: --prompt-file is a spawn-time capture (FR-1.5); "
              f"not valid with --emit {args.emit}", file=sys.stderr)
        return 2

    try:
        line = fs.build_journal_line(args.emit, args.phase, args.feature, args.by, data)
        fs.append_journal_line(cwd, line)
    except (ValueError, OSError) as exc:
        print(f"spawn_telemetry: {exc}", file=sys.stderr)
        return 2

    if args.prompt_file is not None:
        try:
            with open(args.prompt_file, encoding="utf-8") as fh:
                prompt = fh.read()
            sid = args.session_id or fs.current_session_id(cwd)
            fs.compaction_write_layer(cwd, session_id=sid, agent=args.agent,
                                      layer="mission", text=prompt)
        except (OSError, ValueError) as exc:
            # capture is best-effort: the spawn event stands even if the
            # mission write fails — visible, never blocking (INC-001 FR-1.5)
            print(f"spawn_telemetry: mission capture failed: {exc}", file=sys.stderr)

    print(json.dumps(line, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
