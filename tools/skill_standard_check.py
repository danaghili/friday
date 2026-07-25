#!/usr/bin/env python3
"""The mechanical floor under FR-81 — verifies a SKILL.md carries the STRUCTURE
its KIND demands. Two kinds since INC-002 (FR-2.5):

- **noticing-skill** — a watcher (offer-only, never a doer). Held to the full
  skill-authoring standard (docs/research/rebuild/skill-authoring-standard.md):
  iron law, anti-scope, counted triggers, scripted dialogue, quick-reference,
  Excuse|Reality table, named terminal state.
- **lane-skill** — a `/friday:<lane>` playbook, marked `friday-lane: true`
  (typed-invocable always; model-invocable unless it carries the typed-only
  tag). Held to the lighter structural floor: `name` + a substantial
  `description`. A playbook has no iron law to demand (the KH-3 genre
  collision).

Discriminator: frontmatter `friday-lane: true` marks a lane-skill (INC-007,
the explicit marker INC-002 OQ-2 reserved). `disable-model-invocation: true`
means only "typed-only" — an opt-out of model-firing — and classifies nothing.

It checks presence, not quality: whether the writing is "at least as good as
the exemplars" stays the harden close-bar's human judgement (FR-81). Every
element a floor names becomes one named check, so a dropped element is a
specific, fixable finding — never a vague "doesn't feel right".

Verdict rides stdout as JSON. Exit 0 all-pass · 1 any-fail · 2 bad invocation.
Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Scripted dialogue is a sentence the skill instructs you to SAY — a speech cue
# followed, on the same line, by a quoted phrase of real length. Anchoring on the
# cue distinguishes it from the (also-quoted) quips in the Excuse|Reality table
# and the quoted trigger phrases, which carry no such cue.
_SCRIPTED = re.compile(
    r'(say|ask|tell|verbatim|scripted|the move|in this shape)[^"\n]{0,40}"[^"]{25,}"',
    re.IGNORECASE)
DESC_MIN = 40


def _has_scripted_dialogue(text: str) -> bool:
    body = _FRONTMATTER.sub("", text, count=1)
    return bool(_SCRIPTED.search(body))


def _frontmatter(text: str) -> dict:
    m = _FRONTMATTER.match(text)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip()
    return out


def classify_skill(text: str) -> str:
    """'lane' when frontmatter carries `friday-lane: true` (the explicit lane
    marker, INC-007), else 'noticing' (a watcher). The typed-only flag never
    classifies. Empty text has no frontmatter and is therefore the noticing
    kind's empty case."""
    fm = _frontmatter(text)
    return "lane" if fm.get("friday-lane", "").lower() == "true" else "noticing"


def check_lane_skill(text: str) -> dict:
    """The lane-skill floor (FR-2.5): valid frontmatter with `name` and a
    substantial `description` — nothing of the watcher authoring style is
    demanded of a playbook. Empty case: only the discriminator present →
    missing name + description, nothing crashes."""
    fm = _frontmatter(text)
    missing: list[str] = []
    if not fm.get("name"):
        missing.append("name")
    if len(fm.get("description", "")) < DESC_MIN:
        missing.append("description")
    return {"ok": not missing, "missing": missing, "kind": "lane"}


def check(text: str) -> dict:
    """Classify, then hold the skill to its own kind's floor."""
    if classify_skill(text) == "lane":
        return check_lane_skill(text)
    res = check_skill(text)
    res["kind"] = "noticing"
    return res


def check_skill(text: str) -> dict:
    """The noticing-skill (strict) floor. Return {"ok": bool, "missing":
    [element, ...]}. `missing` names every required element absent from `text`;
    empty text reports them all (the defined empty case)."""
    fm = _frontmatter(text)
    low = text.lower()
    missing: list[str] = []

    if not fm.get("name"):
        missing.append("name")
    # matcher-written description (standard #1): present and substantial, not a
    # one-word summary a matcher can't fire on.
    if len(fm.get("description", "")) < DESC_MIN:
        missing.append("description")
    # one quotable iron law (standard #2)
    if "iron law" not in low:
        missing.append("iron-law")
    # anti-scope stated head-on (standard #3)
    if "anti-scope" not in low:
        missing.append("anti-scope")
    # counted triggers, never vibes (standard #5)
    if "trigger" not in low:
        missing.append("triggers")
    # scripted dialogue — at least one quoted sentence to say (standard #7)
    if not _has_scripted_dialogue(text):
        missing.append("scripted-dialogue")
    # per-phase criteria + quick-reference table (standard #6)
    has_phase_table = ("phase" in low and ("success" in low or "criterion" in low))
    if not (has_phase_table or "quick reference" in low):
        missing.append("quick-reference")
    # rationalization table Excuse | Reality (standard #4)
    if not ("excuse" in low and "reality" in low):
        missing.append("excuse-reality")
    # named terminal state, everything else forbidden (standard #10)
    if "terminal state" not in low:
        missing.append("terminal-state")

    return {"ok": not missing, "missing": missing}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="FR-81/FR-2.5 SKILL.md structural floor")
    ap.add_argument("paths", nargs="+", help="SKILL.md file(s) to check")
    args = ap.parse_args(argv)
    results = []
    all_ok = True
    for path in args.paths:
        try:
            with open(path, encoding="utf-8") as fh:
                res = check(fh.read())
        except OSError as exc:
            res = {"ok": False, "missing": ["unreadable"], "error": str(exc)}
        res["file"] = path
        all_ok = all_ok and res["ok"]
        results.append(res)
    print(json.dumps({"ok": all_ok, "results": results}))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
