#!/usr/bin/env python3
"""Stop gate — the keystone of the K-rule pair: refuses to let the session
CONCLUDE while the project state record is known-inconsistent (a state was
declared that the artifacts do not back).

Cheap no-op everywhere except a friday project with an armed sentinel (~one
stat() per turn elsewhere). When `<shared .friday>/state-inconsistent` exists:
re-run the verifier (it may have been fixed); PASS → disarm + allow; FAIL →
emit {"decision":"block","reason": summary + owner-routed fixes}. Deliberate
human escalation is NOT blocked — removing the sentinel is the conscious
handoff path — and Claude Code caps consecutive Stop-blocks, so this can
never hard-lock a session. Always exits 0; the block rides the JSON decision.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        sentinel = os.path.join(fs.friday_dir(cwd), "state-inconsistent")
        if not os.path.isfile(sentinel):
            return 0
        if not fs.is_friday_project(cwd):
            try:
                os.remove(sentinel)
            except OSError:
                pass
            return 0

        verifier = os.path.join(plugin_root, "tools", "verify_state.py")
        # FAIL-OPEN: block ONLY on a fresh, CONFIRMED verifier FAIL. A missing,
        # crashing, timing-out, or unparseable verifier means we cannot confirm
        # the inconsistency is still live — and a false block stalls a working
        # session, which is worse than a miss (asymmetric tolerance). In those
        # cases we ALLOW the Stop; the sentinel stays armed, so a later Stop with
        # a working verifier still catches a genuine inconsistency.
        if not os.path.isfile(verifier):
            return 0
        try:
            proc = subprocess.run(
                [sys.executable, verifier, "--root", cwd, "--json"],
                capture_output=True, text=True, timeout=60)
            result = json.loads(proc.stdout) if proc.stdout.strip() else None
        except Exception as exc:
            print(f"state_stop_gate: verifier unrunnable, failing open: {exc}",
                  file=sys.stderr)
            return 0
        # A real verdict is a JSON object carrying "ok". Its ABSENCE (empty or
        # malformed output — the shape a crashing verifier leaves) means we could
        # not confirm the inconsistency, so fail OPEN rather than block on a
        # non-answer. verify_state exits non-zero on a genuine FAIL but still
        # emits the verdict JSON, so a real inconsistency is honored below.
        if not isinstance(result, dict) or "ok" not in result:
            print("state_stop_gate: verifier produced no verdict, failing open",
                  file=sys.stderr)
            return 0
        if result.get("ok"):
            try:
                os.remove(sentinel)
            except OSError:
                pass
            return 0
        summary = result.get("summary") or "The project state record is inconsistent."

        # $CLAUDE_PLUGIN_ROOT expands only inside hook execution — interpolate
        # the path THIS hook resolved so the command is copy-runnable.
        reason = (
            "The friday project state record is INCONSISTENT — the declared "
            "state is not backed by its artifacts, so do not report the build "
            "closed or end here.\n\n"
            f"{summary}\n\n"
            "Re-run the verifier and fix by the failure's owner "
            "(closer: K1/K2/K3/K5/K7/K8 close-record gaps · lead: K0 substrate "
            "gaps · project: K4 — use the closed state vocabulary, never invent "
            "a status string):\n"
            f'  python3 "{verifier}" --root . --json\n'
            "If you are deliberately handing the inconsistency to the PM, "
            "remove .friday/state-inconsistent first."
        )
        print(json.dumps({"decision": "block", "reason": reason}))
    except Exception as exc:
        print(f"state_stop_gate: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
