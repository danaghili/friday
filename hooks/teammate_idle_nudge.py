#!/usr/bin/env python3
"""Guard #15 — idle-teammate nudge (TeammateIdle, WARN tier;
TECHNICAL_SOW_REBUILD FR-56 guard #15). A doc-only event per
probe-hook-events.md (not empirically fired in this version) — fine if it
never fires; this guard simply reacts when it does.

No checker: there is no ground truth to verify, only the event itself to
react to. Always emits a warning naming the idle agent when the event
carries one; never blocks (TeammateIdle has no block channel in any case —
_guard.emit_block would raise for it). Always exits 0.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402
from _hookutil import read_event  # noqa: E402

_NAME_KEYS = ("agent_type", "subagent_type", "agentType", "subagentType", "teammate", "name")
_AGENT_OBJ_KEYS = ("type", "name", "agent_type")


def _agent_label(event: dict) -> str:
    for key in _NAME_KEYS:
        val = event.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    agent = event.get("agent")
    if isinstance(agent, dict):
        for key in _AGENT_OBJ_KEYS:
            val = agent.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return "a teammate"


def main() -> int:
    try:
        event = read_event()
        label = _agent_label(event)
        print(json.dumps(_guard.emit_warn(
            f"{label} has been idle — idle teammates report status or return "
            "their remit to the lead (FR-56 #15)")))
    except Exception as exc:
        print(f"teammate_idle_nudge: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
