#!/usr/bin/env python3
"""Guard #2 — spec-write gate (PostToolUse Write|Edit|MultiEdit, BLOCK tier;
TECHNICAL_SOW_REBUILD FR-55 guard #2; D-0018 event mapping).

Thin per the skeleton doctrine: read event → run_checker → decide → emit.
No new checker — tools/doc_gate.py IS the judgment, dispatched by path:
`docs/TECHNICAL_SOW*.md` → --kind spec; `docs/increments/*.md` → --kind
increment --parent <wroot>/docs/TECHNICAL_SOW.md (increments always mint
against the MAIN oracle, per skills/feature/SKILL.md — never the rebuild
oracle). Any other path is untouched — this guard does not re-derive what
counts as a spec, doc_gate already owns that.

Fires AFTER the write (PostToolUse), so the document already exists on disk
at the reported path; doc_gate reads it directly. Engages only in a friday
project (fs.is_friday_project). Always exits 0; a block rides the JSON.
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_SPEC_GLOB = os.path.join("docs", "TECHNICAL_SOW*.md")
_INCREMENT_GLOB = os.path.join("docs", "increments", "*.md")


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        if not fs.is_friday_project(cwd):
            return 0
        tool_input = event.get("tool_input") or {}
        path = tool_input.get("file_path")
        if not isinstance(path, str) or not path.strip():
            return 0

        wroot = fs.resolve_worktree_root(cwd)
        rel = os.path.relpath(os.path.abspath(path), wroot)

        checker = os.path.join(plugin_root, "tools", "doc_gate.py")
        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        if fnmatch.fnmatch(rel, _SPEC_GLOB):
            argv = [sys.executable, checker, "--kind", "spec", "--file", path]
            what = f"this write to {path} — a spec document"
        elif fnmatch.fnmatch(rel, _INCREMENT_GLOB):
            parent = os.path.join(wroot, "docs", "TECHNICAL_SOW.md")
            argv = [sys.executable, checker, "--kind", "increment",
                    "--file", path, "--parent", parent]
            what = f"this write to {path} — an increment document"
        else:
            return 0

        verdict = _guard.run_checker(argv, timeout_s=timeout)
        action = _guard.decide(verdict, "block", _guard.block_message(
            what,
            (verdict.get("summary") or "the document does not carry the "
             "load-bearing fields a build feeds from") + ". A build-feeding "
            "document that fails its own gate quietly poisons everything "
            "downstream that consumes it.",
            "fix the document so it parses (see the checker's errors above), "
            "then save it again",
            "there is no override — a malformed spec/increment is never "
            "wired around; fix the document itself"))
        if action.kind == "block":
            print(json.dumps(_guard.emit_block("PostToolUse", action.reason)))
        elif action.detail:
            print(f"spec_write_guard: no verdict, failing open: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"spec_write_guard: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
