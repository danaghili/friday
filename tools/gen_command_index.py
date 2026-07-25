#!/usr/bin/env python3
"""Command-index generator — the single-authoritative-field → generated-index
pattern (preserve-list §3.4): each lane declares its description ONCE and
README's command table regenerates between the `<!-- COMMAND-INDEX:BEGIN/END -->`
markers, never hand-edited. A lane lives in one of two homes (INC-002 FR-2.3):

- `commands/<lane>.md` — line 1 contains an em-dash; the text after the FIRST
  " — " is the description (trimmed to ~90 chars). A file with no em-dash
  opener still appears, self-flagged — it self-flags rather than vanishing.
- `skills/<lane>/SKILL.md` with `friday-lane: true` — a lane-skill (INC-007);
  name + description come from the frontmatter (KH-5: a SKILL.md's line 1 is
  `---`, so the line-1 opener convention never applies). A noticing-skill (no
  discriminator) is a watcher, not a lane, and never enters the table.

Shadow state (FR-2.4): the same lane present in BOTH homes means the command
silently wins (probe-proven, docs/research/probe-plugin-skill-parity.md) — a
defect. The row self-flags, the shadow is reported on stderr, and `--check`
exits 1 on it.

Usage:
  python3 tools/gen_command_index.py [--commands-dir commands] [--skills-dir skills] [--json]
  python3 tools/gen_command_index.py --write README.md
  python3 tools/gen_command_index.py --check
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

BEGIN, END = "<!-- COMMAND-INDEX:BEGIN -->", "<!-- COMMAND-INDEX:END -->"
CAP = 90
# same frontmatter shape skill_standard_check.py parses — one grammar, two readers
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _escape(desc: str) -> str:
    # A8: never break the table columns (applies to BOTH homes — S-2.2)
    return desc.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


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


def extract(commands_dir: str) -> list[dict]:
    out = []
    for name in sorted(os.listdir(commands_dir)):
        if not name.endswith(".md"):
            continue
        try:
            with open(os.path.join(commands_dir, name), encoding="utf-8") as fh:
                first = fh.readline().strip()
        except OSError:
            continue
        if " — " in first:
            desc = first.split(" — ", 1)[1].rstrip(".")
            if len(desc) > CAP:
                desc = desc[:CAP - 1] + "…"
        else:
            desc = "(non-canonical opener — fix line 1 of this command file)"
        out.append({"name": name[:-3], "description": _escape(desc)})
    return out


def extract_skills(skills_dir: str) -> list[dict]:
    """Lane-skills only (`friday-lane: true` — the explicit lane marker,
    INC-007); a noticing-skill is a watcher, never a table row.
    `disable-model-invocation` means only "typed-only" and classifies nothing.
    Empty case: no skills dir, or none of its folders is a lane-skill → []."""
    out = []
    if not os.path.isdir(skills_dir):
        return out
    for name in sorted(os.listdir(skills_dir)):
        path = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                fm = _frontmatter(fh.read())
        except OSError:
            continue
        if fm.get("friday-lane", "").lower() != "true":
            continue
        desc = fm.get("description", "").rstrip(".")
        if desc:
            if len(desc) > CAP:
                desc = desc[:CAP - 1] + "…"
        else:
            desc = "(non-canonical frontmatter — add a description to this SKILL.md)"
        out.append({"name": fm.get("name") or name, "description": _escape(desc)})
    return out


def extract_all(commands_dir: str, skills_dir: str) -> tuple[list[dict], list[str]]:
    """One merged, sorted table over both lane homes, plus the detected shadows.
    A shadowed lane keeps ONE row, self-flagged (COMMAND WINS is a defect state
    that must be visible, never a silent double)."""
    cmds = extract(commands_dir) if os.path.isdir(commands_dir) else []
    skills = extract_skills(skills_dir)
    command_names = {e["name"] for e in cmds}
    shadows = sorted(s["name"] for s in skills if s["name"] in command_names)
    merged = cmds + [s for s in skills if s["name"] not in command_names]
    for e in merged:
        if e["name"] in shadows:
            e["description"] = (f"(SHADOW — commands/{e['name']}.md wins over "
                                f"skills/{e['name']}/SKILL.md; archive the command file)")
    return sorted(merged, key=lambda e: e["name"]), shadows


def render_table(entries: list[dict]) -> str:
    lines = ["| Command | What it does |", "| --- | --- |"]
    lines += [f"| `/friday:{e['name']}` | {e['description']} |" for e in entries]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commands-dir", default="commands")
    ap.add_argument("--skills-dir", default="skills")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", default=None,
                    help="README path to splice the table into; with --check, "
                         "the README to compare against (nothing is written)")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 on a detected shadow OR a stale README table "
                         "(BUG-003: compares the COMMAND-INDEX block of --write, "
                         "default README.md; absent/markerless README → skipped)")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.commands_dir) and not os.path.isdir(args.skills_dir):
        print(f"gen_command_index: neither {args.commands_dir} nor "
              f"{args.skills_dir} exists", file=sys.stderr)
        return 2
    entries, shadows = extract_all(args.commands_dir, args.skills_dir)
    for name in shadows:
        print(f"gen_command_index: SHADOW — commands/{name}.md wins over "
              f"skills/{name}/SKILL.md; archive the command file", file=sys.stderr)
    if args.check:
        # BUG-003: the check owns README-block sync, not just shadows — a
        # stale generated table shipped green because nothing compared it.
        readme = args.write or "README.md"
        stale = False
        note = "no README to compare"
        try:
            with open(readme, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            text = None
        if text is not None:
            i, j = text.find(BEGIN), text.find(END)
            if i < 0 or j < 0 or j < i:
                note = "no COMMAND-INDEX markers to compare"
            else:
                want = "\n" + render_table(entries) + "\n"
                stale = text[i + len(BEGIN):j] != want
                note = (f"README table STALE — run --write {readme}" if stale
                        else "README table in sync")
        bad = bool(shadows) or stale
        print(f"gen_command_index: check {'FAIL' if bad else 'ok'} — "
              f"{len(entries)} lane(s), {len(shadows)} shadow(s), {note}")
        return 1 if bad else 0
    if args.write:
        with open(args.write, encoding="utf-8") as fh:
            text = fh.read()
        i, j = text.find(BEGIN), text.find(END)
        if i < 0 or j < 0 or j < i:
            print(f"gen_command_index: {args.write} lacks the COMMAND-INDEX "
                  "marker pair — refusing to guess a splice point", file=sys.stderr)
            return 2
        new = text[:i + len(BEGIN)] + "\n" + render_table(entries) + "\n" + text[j:]
        with open(args.write, "w", encoding="utf-8") as fh:
            fh.write(new)
        print(f"gen_command_index: spliced {len(entries)} commands into {args.write}")
        return 0
    print(json.dumps(entries) if args.json else render_table(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
