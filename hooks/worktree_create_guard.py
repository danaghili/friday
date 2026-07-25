#!/usr/bin/env python3
"""Guard #18a — worktree-create substrate-sharing check (WorktreeCreate,
BLOCK tier; TECHNICAL_SOW_REBUILD FR-55 guard #18a).

THE ACTIVE-HOOK HAZARD (probe-hook-events.md): WorktreeCreate is not a
passive observer — the harness requires the new path back on stdout (or
hookSpecificOutput.worktreePath) or creation fails outright. So this guard
inverts the usual shape: valid-fail withholds the path (creation fails —
that IS the block, reported on stderr since there is no permission-deny
channel here); valid-pass OR no-verdict ALWAYS echoes the path back —
fail-open must never break worktree creation, the single most disruptive
thing a broken guard could do here.

**DISABLED — NOT WIRED (2026-07-14, live probe on Claude Code 2.1.209; full
record: docs/research/rebuild/probe-worktree-hooks.md).** The probe proved
this design unimplementable as a passive gate: (1) the real payload carries
`name` (a worktree NAME — none of the path keys guessed below exist);
(2) a wired WorktreeCreate hook is a PROVISIONER — the harness requires
"the directory it created as the last line of its stdout", and an
empty-stdout hook FAILS creation outright ("hook succeeded but returned no
worktree path") with no fallback to default creation. So ANY passive
wiring of this file breaks every worktree creation — the exact hazard the
seam brief named. Whether #18a becomes a real provisioner (replicating the
default `.claude/worktrees/<name>` convention) or relocates to a passive
event is a PM disposition; until then this file and its tests document the
intended block semantics only.

Requested-path key (KNOWN WRONG per the probe — kept for the disabled
implementation the tests pin): tried in order `worktree_path`, `path`,
then `tool_input.path`. No path found at all → print nothing, exit 0.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402


def _requested_path(event: dict) -> str | None:
    for key in ("worktree_path", "path"):
        val = event.get(key)
        if isinstance(val, str) and val.strip():
            return val
    tool_input = event.get("tool_input")
    if isinstance(tool_input, dict):
        val = tool_input.get("path")
        if isinstance(val, str) and val.strip():
            return val
    return None


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()

    requested = _requested_path(event)
    if requested is None:
        return 0

    def emit_path() -> None:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "WorktreeCreate", "worktreePath": requested}}))

    if fs is None:
        emit_path()  # substrate unimportable — fail open, never break creation
        return 0
    try:
        wroot = fs.resolve_worktree_root(cwd)
        checker = os.path.join(plugin_root, "tools", "worktree_create_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(
            [sys.executable, checker, "--path", requested, "--root", wroot],
            timeout_s=timeout)
        if verdict.get("verdict") == "valid-fail":
            reason = _guard.block_message(
                f"creating a worktree at {requested}",
                verdict.get("summary") or
                "the requested path would not share this project's substrate",
                "choose a different path for the new worktree — anywhere "
                "outside .friday/ and outside another unrelated git repo's tree",
                "there is no override — the requested path itself must change")
            print(reason, file=sys.stderr)
            return 0  # withholding worktreePath IS the block

        if verdict.get("verdict") != "valid-pass" and verdict.get("detail"):
            print(f"worktree_create_guard: no verdict, failing open: "
                  f"{verdict['detail']}", file=sys.stderr)
        emit_path()
    except Exception as exc:
        print(f"worktree_create_guard: {exc}", file=sys.stderr)
        emit_path()  # our own bug must never break creation either
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
