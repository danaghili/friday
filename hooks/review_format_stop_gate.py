#!/usr/bin/env python3
"""Stop gate — review-format backstop for the case where the PostToolUse
bounce is ignored (enforcement never depends on the writer heeding its own
feedback). Acts only when `<shared .friday>/review-format-invalid` is armed:
re-verify in the recorded strictness; artifact gone → disarm; PASS → disarm;
FAIL → block with the failures + fix route (SendMessage the owning reviewer —
never edit its review yourself). Always exits 0.
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
        sentinel = os.path.join(fs.friday_dir(cwd), "review-format-invalid")
        if not os.path.isfile(sentinel):
            return 0
        if not fs.is_friday_project(cwd):
            try:
                os.remove(sentinel)
            except OSError:
                pass
            return 0
        try:
            with open(sentinel, encoding="utf-8") as fh:
                rel_path = fh.readline().strip()
                mode = fh.readline().strip()
                armed_summary = fh.read().strip()
        except OSError:
            rel_path, mode, armed_summary = "", "sweep", ""
        artifact = rel_path if os.path.isabs(rel_path) else os.path.join(cwd, rel_path)
        if not rel_path or not os.path.isfile(artifact):
            try:
                os.remove(sentinel)  # archived/reshaped — release
            except OSError:
                pass
            return 0

        verifier = os.path.join(plugin_root, "tools", "verify_review_format.py")
        # FAIL-OPEN: block ONLY on a fresh, CONFIRMED verifier FAIL. A missing,
        # crashing, timing-out, or unparseable verifier cannot confirm the
        # artifact is still malformed — and a false block stalls a working
        # session (a false block is worse than a miss). Those cases ALLOW the
        # Stop; the sentinel stays armed for a later, runnable re-check.
        if not os.path.isfile(verifier):
            return 0
        cmd = [sys.executable, verifier, "--file", artifact, "--json"]
        if mode == "strict":
            cmd.append("--strict-missing")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            result = json.loads(proc.stdout) if proc.stdout.strip() else None
        except Exception as exc:
            print(f"review_format_stop_gate: verifier unrunnable, failing open: {exc}",
                  file=sys.stderr)
            return 0
        # A real verdict is a JSON object carrying "ok"; its absence (empty or
        # malformed output — the shape a crashing verifier leaves) fails OPEN
        # rather than blocking on a non-answer.
        if not isinstance(result, dict) or "ok" not in result:
            print("review_format_stop_gate: verifier produced no verdict, failing open",
                  file=sys.stderr)
            return 0
        if result.get("ok"):
            try:
                os.remove(sentinel)
            except OSError:
                pass
            return 0
        summary = result.get("summary") or armed_summary or "A review artifact fails its FRIDAY-REVIEW checks."
        detail = "\n".join(f"  x {f['check']} — {f['detail']}"
                           for f in (result.get("failures") or [])
                           if f.get("severity") == "blocking")
        print(json.dumps({"decision": "block", "reason": (
            f"A review artifact ({rel_path}) is MALFORMED — its envelope "
            "cannot be trusted by the claim audit or the close gate. Do not "
            "report the review complete or end here.\n\n"
            f"{summary}\n{detail}\n\n"
            "Route the fix to the REVIEWER that owns the artifact (SendMessage "
            "it the failures — never edit its review yourself), then re-run:\n"
            f'  python3 "{verifier}" --file "{rel_path}" --json\n'
            "If deliberately handing this to the PM, remove "
            ".friday/review-format-invalid first.")}))
    except Exception as exc:
        print(f"review_format_stop_gate: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
