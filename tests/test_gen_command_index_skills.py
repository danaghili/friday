"""gen_command_index.py — skill-aware retarget (INC-002 FR-2.3/FR-2.4/S-2.2).
A lane living at skills/<lane>/SKILL.md (frontmatter-first, no line-1 opener —
KH-5) appears in the generated table exactly as a command does; a noticing-skill
(model-invocable offerer) never does; the shadow state (same lane in both homes,
COMMAND WINS) is a detected, self-flagged condition, never a silent one.
Test-first.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import gen_command_index as gci  # noqa: E402


LANE_SKILL = """---
name: feedback
description: the free-form front door for anything the PM noticed
friday-lane: true
disable-model-invocation: true
---

You are the lead running `/friday:feedback` — the free-form front door.
"""

INVOCABLE_LANE_SKILL = """---
name: bug
description: run when the PM reports something known to be broken
friday-lane: true
---

You are the lead running `/friday:bug` — the lane for something known to be broken.
"""

NOTICING_SKILL = """---
name: noticing-something-off
description: Use this when the PM reports something that feels wrong but has not typed a lane command. Offers /friday:feedback and never runs it without an explicit yes.
---

# Noticing something off — recognise the observation, offer the door
"""


def _tree(tmp_path, *, commands=(), skills=()):
    cmds = tmp_path / "commands"
    cmds.mkdir()
    for name, line1 in commands:
        (cmds / f"{name}.md").write_text(line1 + "\n\nbody\n", encoding="utf-8")
    sk = tmp_path / "skills"
    sk.mkdir()
    for name, text in skills:
        d = sk / name
        d.mkdir()
        (d / "SKILL.md").write_text(text, encoding="utf-8")
    return str(cmds), str(sk)


# --- FR-2.3: a lane-skill appears, description read from frontmatter (KH-5) -----

def test_lane_skill_appears_with_frontmatter_description(tmp_path):
    cmds, sk = _tree(tmp_path,
                     commands=[("help", "help — show the index")],
                     skills=[("feedback", LANE_SKILL)])
    entries, shadows = gci.extract_all(cmds, sk)
    assert shadows == []
    names = [e["name"] for e in entries]
    assert names == ["feedback", "help"]  # merged and sorted, one table
    fb = next(e for e in entries if e["name"] == "feedback")
    # KH-5: line 1 of a SKILL.md is `---`; the description MUST come from
    # frontmatter, never from a line-1 em-dash parse
    assert fb["description"] == "the free-form front door for anything the PM noticed"


def test_noticing_skill_never_enters_the_table(tmp_path):
    cmds, sk = _tree(tmp_path, skills=[("noticing-something-off", NOTICING_SKILL),
                                       ("feedback", LANE_SKILL)])
    entries, _ = gci.extract_all(cmds, sk)
    assert [e["name"] for e in entries] == ["feedback"]


# --- INC-007 FR-7.1: the discriminator is `friday-lane: true`, not typed-only ----

def test_invocable_lane_enters_the_table(tmp_path):
    # a lane WITHOUT disable-model-invocation (model-invocable, the new normal)
    # is still a lane — the marker classifies, not the typed-only flag
    cmds, sk = _tree(tmp_path, skills=[("bug", INVOCABLE_LANE_SKILL)])
    entries, _ = gci.extract_all(cmds, sk)
    assert [e["name"] for e in entries] == ["bug"]


def test_typed_only_flag_alone_no_longer_classifies(tmp_path):
    # disable-model-invocation without friday-lane is NOT a lane (the flag now
    # means only "typed-only" — e.g. a repo-internal helper skill)
    old_key_only = LANE_SKILL.replace("friday-lane: true\n", "")
    cmds, sk = _tree(tmp_path, skills=[("feedback", old_key_only)])
    entries, _ = gci.extract_all(cmds, sk)
    assert entries == []


# --- S-2.2: frontmatter description gets the same A8 table escaping -------------

def test_pipe_in_skill_description_escaped(tmp_path):
    evil = LANE_SKILL.replace(
        "description: the free-form front door for anything the PM noticed",
        "description: breaks | the table | badly")
    cmds, sk = _tree(tmp_path, skills=[("feedback", evil)])
    entries, _ = gci.extract_all(cmds, sk)
    row = next(ln for ln in gci.render_table(entries).splitlines() if "feedback" in ln)
    assert row.count("|") - row.count("\\|") == 3, row  # only the 3 real cell borders
    assert "\\|" in row


def test_long_skill_description_capped_like_a_command(tmp_path):
    long = LANE_SKILL.replace(
        "description: the free-form front door for anything the PM noticed",
        "description: " + "x" * 200)
    cmds, sk = _tree(tmp_path, skills=[("feedback", long)])
    entries, _ = gci.extract_all(cmds, sk)
    assert len(entries[0]["description"]) == gci.CAP
    assert entries[0]["description"].endswith("…")


def test_skill_missing_description_self_flags_not_vanishes(tmp_path):
    bare = "---\nname: feedback\nfriday-lane: true\n---\n\nbody\n"
    cmds, sk = _tree(tmp_path, skills=[("feedback", bare)])
    entries, _ = gci.extract_all(cmds, sk)
    assert len(entries) == 1
    assert "non-canonical" in entries[0]["description"]


# --- FR-2.4: shadow and absent are DEFINED, DETECTED conditions ------------------

def test_shadow_is_detected_and_self_flagged(tmp_path):
    cmds, sk = _tree(tmp_path,
                     commands=[("feedback", "feedback — the old command form")],
                     skills=[("feedback", LANE_SKILL)])
    entries, shadows = gci.extract_all(cmds, sk)
    assert shadows == ["feedback"]
    assert len(entries) == 1  # one lane, one row — never two
    assert "SHADOW" in entries[0]["description"]  # probe-proven COMMAND WINS, said out loud


def test_check_mode_fails_on_shadow_passes_clean(tmp_path):
    # README isolation (BUG-003): --check now also compares a README's block;
    # point it at an absent fixture path so this test stays about shadows
    no_readme = str(tmp_path / "no-README.md")
    cmds, sk = _tree(tmp_path,
                     commands=[("feedback", "feedback — the old command form")],
                     skills=[("feedback", LANE_SKILL)])
    assert gci.main(["--commands-dir", cmds, "--skills-dir", sk, "--check",
                     "--write", no_readme]) == 1
    (tmp_path / "clean").mkdir()
    clean_cmds, clean_sk = _tree(tmp_path / "clean",
                                 commands=[("help", "help — show the index")],
                                 skills=[("feedback", LANE_SKILL)])
    assert gci.main(["--commands-dir", clean_cmds, "--skills-dir", clean_sk,
                     "--check", "--write", no_readme]) == 0


# --- FR-3.2 (INC-003 KH-3): bundled siblings are a GUARANTEE, not an accident ----

def test_lane_folder_with_bundled_siblings_lists_identically(tmp_path):
    # tolerance today is accidental (the tool keys on SKILL.md by name); this pin
    # makes it survive a future enumerate-the-folder refactor
    cmds, sk = _tree(tmp_path, skills=[("feedback", LANE_SKILL)])
    lane = tmp_path / "skills" / "feedback"
    (lane / "references").mkdir()
    (lane / "references" / "notes.md").write_text("bundled reference\n", encoding="utf-8")
    (lane / "helper.py").write_text("print('bundled helper')\n", encoding="utf-8")
    entries, shadows = gci.extract_all(cmds, sk)
    assert shadows == []
    assert [e["name"] for e in entries] == ["feedback"]  # one row, no flags
    assert entries[0]["description"] == "the free-form front door for anything the PM noticed"
    assert gci.main(["--commands-dir", cmds, "--skills-dir", sk, "--check",
                     "--write", str(tmp_path / "no-README.md")]) == 0


# --- the empty cases (every grammar defines + tests its empty case) --------------

def test_no_skills_dir_is_the_defined_empty_case(tmp_path):
    cmds = tmp_path / "commands"
    cmds.mkdir()
    (cmds / "help.md").write_text("help — show the index\n", encoding="utf-8")
    entries, shadows = gci.extract_all(str(cmds), str(tmp_path / "no-such-skills"))
    assert [e["name"] for e in entries] == ["help"]
    assert shadows == []


def test_empty_skills_dir_yields_no_skill_entries(tmp_path):
    cmds, sk = _tree(tmp_path, commands=[("help", "help — show the index")])
    assert gci.extract_skills(sk) == []
