#!/usr/bin/env python3
"""Guard — the state advisory (PreToolUse + Stop, WARN tier; D-0107).

Thin per the skeleton doctrine: read event → run_checker → decide → emit. The
judgement lives in `tools/state_advisory_check.py`; the POLICY lives in the
`FRIDAY-LANE-LEGALITY` table in `docs/contracts/state-record.md`. This file only
decides which question to ask.

**Two events, one concern — "the record and what is happening disagree."**

- **PreToolUse (Edit/Write/MultiEdit)** asks whether the change about to land
  contradicts the state the project is in. It must be PRE, not post: init
  re-seeding a live build overwrites the very state that made it wrong, so after
  the write the evidence is gone.
- **Stop** asks the PROP-028 dirty-bit question (D-0106/D-0141): a finished
  project whose record still claims `verified` while its code has moved.
  Feature, patch and bug are each instructed to mark the record stale; this
  notices when one of them did not, and it keys on the tree having moved rather
  than on which lane moved it — which is what lets it cover feature, the lane
  that opens no sentinel and so cannot be caught at lane-close.

**Never blocks, on either event** (D-0107). The old cost was an invisible
contradiction; the cost of a hard gate would be a false block, which this house
holds to be strictly worse. `_guard.decide(..., "warn", ...)` cannot block, and
no-verdict stays silent — a broken advisory says nothing rather than crying wolf.

Cheap no-op: PreToolUse returns immediately for a write with no file path, and
the Stop question stops at the first read of the state record on any project
that is not closed. Always exits 0.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_WRITE_TOOLS = ("Edit", "Write", "MultiEdit")


def _proposed_text(tool_input: dict) -> str:
    """The content this write would land, across the write tools' shapes.
    Best-effort: an unrecognised shape yields '' and the advisory stays quiet."""
    for key in ("content", "new_string"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        return "\n".join(e.get("new_string", "") for e in edits
                         if isinstance(e, dict))
    return ""


def _lane_start_argv(checker: str, event: dict, wroot: str) -> tuple[list, str] | None:
    tool_input = event.get("tool_input") or {}
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not path.strip():
        return None
    rel = os.path.relpath(os.path.abspath(path), wroot)
    return ([sys.executable, checker, "--root", wroot, "--mode", "lane-start",
             "--file", rel], _proposed_text(tool_input))


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        wroot = fs.resolve_worktree_root(cwd)
        checker = os.path.join(plugin_root, "tools", "state_advisory_check.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        if event.get("tool_name") in _WRITE_TOOLS:
            prepared = _lane_start_argv(checker, event, wroot)
            if prepared is None:
                return 0
            argv, stdin_text = prepared
        else:
            argv, stdin_text = ([sys.executable, checker, "--root", wroot,
                                 "--mode", "liveness"], None)

        verdict = _guard.run_checker(argv, timeout_s=timeout, stdin_text=stdin_text)
        action = _guard.decide(
            verdict, "warn",
            verdict.get("summary") or "this project's record and its current "
                                      "state may disagree")
        if action.kind == "warn":
            print(json.dumps(_guard.emit_warn(action.reason)))
        elif action.detail:
            print(f"state_advisory: no verdict, staying quiet: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"state_advisory: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
