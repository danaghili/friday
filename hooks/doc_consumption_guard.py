#!/usr/bin/env python3
"""Guard #9 — document-consumption gate (PreToolUse Read, BLOCK tier;
TECHNICAL_SOW_REBUILD FR-55/FR-64 guard #9; D-0018 event mapping).

Thin per the skeleton doctrine: read event → run_checker → decide → emit.
No new checker — tools/doc_gate.py IS the judgment, dispatched by path:
`docs/TECHNICAL_SOW*.md` → --kind spec; `docs/increments/*.md` → --kind
increment --parent <wroot>/docs/TECHNICAL_SOW.md; `docs/reviews/
findings-*.md` → --kind findings-brief; `docs/intake-brief.md` or
`docs/briefs/intake-*.md` → --kind intake-brief. Any other path is
untouched.

Spec kind ARMED 2026-07-14 (D-0023): the PM provenance amendment landed —
both in-repo oracles now carry `provenance: born-from-discovery`, so the
false-block class that kept this kind disarmed (D-0018) is gone. New specs
are already forced to carry provenance at WRITE time by guard #2.
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
_FINDINGS_GLOB = os.path.join("docs", "reviews", "findings-*.md")
_INTAKE_GLOBS = (os.path.join("docs", "intake-brief.md"),
                 os.path.join("docs", "briefs", "intake-*.md"))


def _kind_for(rel: str) -> str | None:
    if fnmatch.fnmatch(rel, _SPEC_GLOB):
        return "spec"
    if fnmatch.fnmatch(rel, _INCREMENT_GLOB):
        return "increment"
    if fnmatch.fnmatch(rel, _FINDINGS_GLOB):
        return "findings-brief"
    if any(fnmatch.fnmatch(rel, g) for g in _INTAKE_GLOBS):
        return "intake-brief"
    return None


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        tool_input = event.get("tool_input") or {}
        path = tool_input.get("file_path")
        if not isinstance(path, str) or not path.strip():
            return 0
        wroot = fs.resolve_worktree_root(cwd)
        rel = os.path.relpath(os.path.abspath(path), wroot)
        kind = _kind_for(rel)
        if kind is None:
            return 0

        checker = os.path.join(plugin_root, "tools", "doc_gate.py")
        argv = [sys.executable, checker, "--kind", kind, "--file", path]
        if kind == "increment":
            argv += ["--parent", os.path.join(wroot, "docs", "TECHNICAL_SOW.md")]
        research = os.path.join(wroot, "docs", "research")
        if os.path.isdir(research):  # S-4's blocking half rides this gate
            argv += ["--research-dir", research]

        timeout = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S",
                                       _guard.DEFAULT_TIMEOUT_S))
        verdict = _guard.run_checker(argv, timeout_s=timeout)
        action = _guard.decide(verdict, "block", _guard.block_message(
            f"reading {path} — a {kind} document that fails its own gate",
            (verdict.get("summary") or "the document is missing load-bearing "
             "fields") + ". A build-feeding document is validated at "
            "consumption time so a malformed one is caught before its "
            "content is trusted, not after.",
            "fix the document so it parses (see the checker's errors above), "
            "then read it again",
            "there is no override — a malformed document is never wired "
            "around; fix the document itself"))
        if action.kind == "block":
            print(json.dumps(_guard.emit_block("PreToolUse", action.reason)))
        elif action.detail:
            print(f"doc_consumption_guard: no verdict, failing open: {action.detail}",
                  file=sys.stderr)
    except Exception as exc:
        print(f"doc_consumption_guard: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
