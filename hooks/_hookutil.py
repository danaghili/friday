#!/usr/bin/env python3
"""Shared hook plumbing — plugin-root resolution + the friday_substrate import.

Every hook in this plugin starts with `fs = load_substrate(plugin_root)`.
Per D-0003 the substrate library is imported, not duplicated (ISSUE-006 /
Appendix B: one writer, one root-resolution). A failed import returns None
and the hook degrades to a no-op — hooks ALWAYS exit 0 on their own behalf
("a false block is worse than a miss"); only the Stop gates emit a block
decision, and only from a healthy code path.
"""
from __future__ import annotations

import json
import os
import sys


def plugin_root_from(argv: list[str]) -> str:
    return ((argv[1] if len(argv) > 1 else "")
            or os.environ.get("CLAUDE_PLUGIN_ROOT", "")
            or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_substrate(plugin_root: str):
    """Import tools/friday_substrate.py from the plugin tree; None on failure."""
    tools = os.path.join(plugin_root, "tools")
    try:
        if tools not in sys.path:
            sys.path.insert(0, tools)
        import friday_substrate
        return friday_substrate
    except Exception:
        return None


def read_event() -> dict:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return {}
    return event if isinstance(event, dict) else {}
