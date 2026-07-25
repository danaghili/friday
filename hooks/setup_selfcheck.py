#!/usr/bin/env python3
"""Guard #19 — install self-check (Setup, SILENT tier; TECHNICAL_SOW_REBUILD
FR-57 guard #19: "install self-check at setup"). A doc-only harness event
per probe-hook-events.md (no CLI trigger surface found in this version) —
fine if it never fires.

Checks: hooks/hooks.json parses as JSON; every hooks/*.py file its commands
reference actually exists; python3 is present (trivially true — this very
script is executing under it). Journals "install-self-check" with ok:
true|false and the missing list — never prints to stdout, so a broken
install is visible in the record, not in the PM's face.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_HOOK_CMD_RE = re.compile(r"hooks/([A-Za-z0-9_]+\.py)")


def _referenced_hook_files(hooks_config: dict) -> set[str]:
    files: set[str] = set()
    for entries in (hooks_config.get("hooks") or {}).values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            for h in (entry.get("hooks") or []) if isinstance(entry, dict) else []:
                cmd = h.get("command", "") if isinstance(h, dict) else ""
                files.update(_HOOK_CMD_RE.findall(cmd))
    return files


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        if not fs.should_engage(cwd):
            return 0
        missing: list[str] = []
        hooks_json_path = os.path.join(plugin_root, "hooks", "hooks.json")
        try:
            with open(hooks_json_path, encoding="utf-8") as fh:
                config = json.load(fh)
        except Exception as exc:
            missing.append(f"hooks.json invalid: {exc}")
            config = None

        if config is not None:
            for fn in sorted(_referenced_hook_files(config)):
                if not os.path.isfile(os.path.join(plugin_root, "hooks", fn)):
                    missing.append(fn)

        ok = not missing
        fs.append_journal_line(cwd, fs.build_journal_line(
            "install-self-check", "session", by="session",
            data={"ok": ok, "missing": missing}))
    except Exception as exc:
        print(f"setup_selfcheck: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
