#!/usr/bin/env python3
"""Codex CLI stop gate — friday's enforcement gate ported (gate ONLY; the
role/command system is not ported). Regenerated against the K-rules (A.3).

Deliberate divergences from the Claude Code original (hooks/state_stop_gate.py),
both required by the Codex substrate:
1. **No sentinel precondition.** The Claude original acts on a sentinel armed
   by a SubagentStop-scoped detector keyed to Claude-specific agent types,
   which don't reliably exist on Codex. Rather than ship a port that silently
   never fires, this version runs the verifier DIRECTLY on every stop event.
2. **FAIL CLOSED.** The Claude hook runner fails open by platform fact; Codex
   lets us do better — a missing or crashing verifier BLOCKS (exit 1) instead
   of waving the stop through. "Cannot end while the record is verifiably
   broken" is the whole guarantee being ported.

Contract: exit 0 = allow stop · exit 1 = block (reason on stdout) ·
the deliberate-handoff escape is the same: remove the blocking condition
consciously (fix the record), not silently.

This portability is a consequence, not a feature request: friday earned
file-based state for parallel-safety and auditability, and substrate
independence fell out — the record IS files, so any host that can run
python3 can enforce it.
"""
# Contract: docs/contracts/state-record.md — this ported gate is a named consumer;
# cited on both sides of the handoff (A14).
from __future__ import annotations

import json
import os
import subprocess
import sys

_ADAPTER_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_ADAPTER_DIR)


def main() -> int:
    cwd = os.environ.get("CODEX_PROJECT_DIR") or os.getcwd()
    marker = os.path.join(cwd, "docs", "TECHNICAL_SOW.md")
    claude_md = os.path.join(cwd, "CLAUDE.md")
    engaged = os.path.isfile(marker) or (
        os.path.isfile(claude_md)
        and "FRIDAY-STATE:BEGIN" in open(claude_md, encoding="utf-8",
                                         errors="replace").read())
    if not engaged:
        return 0  # not a friday project — never block foreign work

    verifier = os.path.join(_TOOLS_DIR, "verify_state.py")
    if not os.path.isfile(verifier):
        print("friday codex gate: verify_state.py MISSING — failing closed "
              "(the record cannot be verified, so the session must not "
              "conclude as done). Reinstall the friday plugin tools.")
        return 1
    try:
        proc = subprocess.run([sys.executable, verifier, "--root", cwd, "--json"],
                              capture_output=True, text=True, timeout=60)
        result = json.loads(proc.stdout or "{}")
    except Exception as exc:
        print(f"friday codex gate: verifier crashed ({exc}) — failing closed.")
        return 1
    if result.get("ok"):
        return 0
    print("friday codex gate: the project state record is INCONSISTENT — "
          "do not conclude.\n" + result.get("summary", "") + "\n"
          f'Re-run: python3 "{verifier}" --root . --json')
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
