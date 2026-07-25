#!/usr/bin/env python3
"""Spawn-telemetry coverage check (A.5 #8b) — the anti-ISSUE-006 verifier.

Mechanical rule: any lane surface whose body mentions dispatching agents
(the tokens below) MUST cite `spawn_telemetry.py`; a spawning surface with no
citation is exactly the "reactive flow forgot to instrument" split ISSUE-006
documents. String-mechanical, precision-first: files that never dispatch are
never flagged.

Covers both lane homes (INC-2 sweep, D-0081): `commands/*.md` and lane-skills
at `skills/<lane>/SKILL.md` (frontmatter `friday-lane: true` — the same
discriminator gen_command_index and skill_standard_check key on; INC-007).
A noticing-skill is a watcher, never a dispatch surface, and is out of scope.

Usage:
  python3 tools/verify_spawn_coverage.py [--commands-dir commands] [--skills-dir skills] [--json]

Exit codes: 0 all spawning surfaces instrumented · 1 gaps · 2 bad invocation.
Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# A file "dispatches" when it names the dispatch surface. Deliberately narrow
# tokens (precision-first): prose like "no dispatching here" must not trip it.
_DISPATCH_RE = re.compile(
    r"\b(Agent tool|Task tool|subagent(?:_type)?s?|SendMessage|spawn(?:s|ed|ing)?\b)",
    re.IGNORECASE)
_CITATION = "spawn_telemetry.py"
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _is_lane_skill(text: str) -> bool:
    m = _FRONTMATTER.match(text)
    if not m:
        return False
    for line in m.group(1).splitlines():
        key, _, val = line.partition(":")
        if key.strip() == "friday-lane":
            return val.strip().lower() == "true"
    return False


def check_commands(commands_dir: str) -> dict:
    failures: list[dict] = []
    checked = 0
    try:
        names = sorted(os.listdir(commands_dir))
    except OSError as exc:
        return {"ok": False, "checked": 0,
                "failures": [{"file": commands_dir, "detail": f"unreadable: {exc}"}],
                "summary": f"cannot list {commands_dir}"}
    for name in names:
        if not name.endswith(".md"):
            continue
        path = os.path.join(commands_dir, name)
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        checked += 1
        if _DISPATCH_RE.search(text) and _CITATION not in text:
            failures.append({
                "file": name, "check": "SPAWN-COV", "severity": "blocking",
                "owner": "lead",
                "detail": ("mentions agent dispatch but never cites "
                           f"{_CITATION} — every spawning surface calls the one "
                           "shared telemetry primitive (ISSUE-006)")})
    ok = not failures
    return {"ok": ok, "checked": checked, "failures": failures,
            "summary": ("spawn-telemetry coverage: all spawning surfaces instrumented"
                        if ok else
                        f"spawn-telemetry coverage: {len(failures)} uninstrumented "
                        f"spawning surface(s): "
                        + ", ".join(f["file"] for f in failures))}


def check_skills(skills_dir: str) -> dict:
    """Lane-skills only; the empty case (no dir / no lane-skills) is a clean
    zero-checked result."""
    failures: list[dict] = []
    checked = 0
    if not os.path.isdir(skills_dir):
        return {"ok": True, "checked": 0, "failures": []}
    for name in sorted(os.listdir(skills_dir)):
        path = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        if not _is_lane_skill(text):
            continue
        checked += 1
        if _DISPATCH_RE.search(text) and _CITATION not in text:
            failures.append({
                "file": f"skills/{name}/SKILL.md", "check": "SPAWN-COV",
                "severity": "blocking", "owner": "lead",
                "detail": ("mentions agent dispatch but never cites "
                           f"{_CITATION} — every spawning surface calls the one "
                           "shared telemetry primitive (ISSUE-006)")})
    return {"ok": not failures, "checked": checked, "failures": failures}


def check_all(commands_dir: str, skills_dir: str) -> dict:
    cmds = (check_commands(commands_dir) if os.path.isdir(commands_dir)
            else {"ok": True, "checked": 0, "failures": []})
    skills = check_skills(skills_dir)
    failures = cmds["failures"] + skills["failures"]
    checked = cmds["checked"] + skills["checked"]
    ok = not failures
    return {"ok": ok, "checked": checked, "failures": failures,
            "summary": ("spawn-telemetry coverage: all spawning surfaces instrumented"
                        if ok else
                        f"spawn-telemetry coverage: {len(failures)} uninstrumented "
                        f"spawning surface(s): "
                        + ", ".join(f["file"] for f in failures))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commands-dir", default="commands")
    ap.add_argument("--skills-dir", default="skills")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.commands_dir) and not os.path.isdir(args.skills_dir):
        print(f"verify_spawn_coverage: neither {args.commands_dir} nor "
              f"{args.skills_dir} exists", file=sys.stderr)
        return 2
    res = check_all(args.commands_dir, args.skills_dir)
    print(json.dumps(res) if args.json else res["summary"])
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
