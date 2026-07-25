#!/usr/bin/env python3
"""State sentinel — the detector half of the K-rule pair (detector→sentinel→
stop-gate; successor to v0.4.0's checkpoint_sentinel, cargo replaced by A.3).

Dual-bound (two independent arming paths, per A.3's trigger bindings):
  1. SubagentStop (matcher friday-closer) — the moment the project record
     should be consistent. ISSUE-007 in-hook identity gate: the hooks.json
     matcher CANNOT be trusted (#27755) — a stop event typed as another agent
     neither arms nor clears (a foreign idle must never release an armed
     gate). A TYPELESS event PROCEEDS: verify_state is precision-first on
     partial state (TEST-07 corpus b), so an anonymous run is content-safe —
     the typeless-proceeds posture is kept ONLY because that is demonstrated.
  2. PostToolUse (matcher Write|Edit|MultiEdit) — a close-shaped write:
     CLAUDE.md written with text touching the FRIDAY-STATE block / state:
     line. Covers a close produced WITHOUT a closer stop (hand-edit, crashed
     closer). Non-matching writes no-op on string checks — per-write cost nil.

On either trigger: run tools/verify_state.py; PASS → remove the sentinel
(`<shared .friday>/state-inconsistent`); FAIL → arm it with the summary so
the Stop gate blocks conclusion. Extra arming is precision-safe: the gate
re-verifies and self-clears. Detection only — blocking is the Stop gate's job.
Always exits 0.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402


def _close_shaped_write(event: dict) -> bool:
    tool_input = event.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    if os.path.basename(path.replace(os.sep, "/")) != "CLAUDE.md":
        return False
    texts = [tool_input.get("content") or "", tool_input.get("new_string") or ""]
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict):
            texts.append(edit.get("new_string") or "")
    return any("FRIDAY-STATE" in t or "state:" in t for t in texts)


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0

    if event.get("hook_event_name") == "PostToolUse" and not _close_shaped_write(event):
        return 0
    if event.get("hook_event_name") == "SubagentStop":
        if fs.event_matches_agent(event, "closer") == "foreign":
            return 0  # never arm AND never clear on a foreign agent's event

    try:
        if not fs.is_friday_project(cwd):
            try:  # not a friday project — never arm here; clear any stray
                os.remove(os.path.join(fs.friday_dir(cwd), "state-inconsistent"))
            except OSError:
                pass
            return 0

        verifier = os.path.join(plugin_root, "tools", "verify_state.py")
        if not os.path.isfile(verifier):
            return 0
        proc = subprocess.run([sys.executable, verifier, "--root", cwd, "--json"],
                              capture_output=True, text=True, timeout=60)
        result = json.loads(proc.stdout or "{}")

        sentinel = os.path.join(fs.friday_dir(cwd), "state-inconsistent")
        if result.get("ok"):
            try:
                os.remove(sentinel)
            except OSError:
                pass
            return 0
        os.makedirs(os.path.dirname(sentinel), exist_ok=True)
        with open(sentinel, "w", encoding="utf-8") as fh:
            fh.write(result.get("summary", "Project state record inconsistent.") + "\n")
    except Exception:
        return 0  # detection hook must never disrupt the run
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
