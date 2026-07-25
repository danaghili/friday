"""skill_standard_check.py — the mechanical floor under FR-81
(docs/research/rebuild/skill-authoring-standard.md). It verifies a SKILL.md
carries the STRUCTURE the standard demands — matcher description, one iron law,
anti-scope, a counted trigger list, scripted dialogue, a quick-reference/phase
table, an Excuse|Reality table, and a named terminal state. It cannot judge
QUALITY ("at least as good as the exemplars" stays the harden close-bar's human
call); it catches the skill that silently dropped an element. Test-first (U6-3).
"""
import os
import sys

from guardkit import BUILD_ROOT

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import skill_standard_check as ssc  # noqa: E402


COMPLIANT = """---
name: starting-a-project
description: Use this when the PM expresses intent to build something new — "I want to build", "I have an idea for", "let's make" — idea-shaped intent that has not entered a friday project yet. Offers /friday:init; never runs it without a yes.
---

# Starting a project — recognise the intent, offer the door

> **Iron law: OFFER, NEVER ENTER. Nothing runs without the PM's explicit yes.**

## Anti-scope — what this skill is NOT
It does not start the project or run discovery. It recognises intent and offers.

## Triggers (counted, not vibes)
- "I want to build / make / create …"
- "I have an idea for …"
- "let's build / start …"

## The move (scripted)
Say: **"This sounds like the start of a new project — want me to run /friday:init?"** Then wait.

## Quick reference
| Phase | Key activity | Success criterion |
|---|---|---|
| Recognise | Match idea-shaped intent | A trigger matched, or silence |
| Offer | Surface the one-line offer | Door named, not opened |
| Confirm | Wait for an explicit yes | Nothing runs without it |

## Excuse | Reality
| Excuse | Reality |
|---|---|
| "They obviously want to build." | A wrong auto-entry is worse than one question. |

## Terminal state
The PM confirms and /friday:init runs, or declines and nothing happens.
"""


def test_a_compliant_skill_passes_clean():
    res = ssc.check_skill(COMPLIANT)
    assert res["ok"] is True, res["missing"]
    assert res["missing"] == []


def test_empty_file_fails_with_everything_missing():
    res = ssc.check_skill("")
    assert res["ok"] is False
    # the defined empty case: every required element is reported, nothing crashes
    assert set(res["missing"]) >= {
        "name", "description", "iron-law", "anti-scope", "triggers",
        "scripted-dialogue", "quick-reference", "excuse-reality", "terminal-state"}


def _drop(marker):
    return "\n".join(ln for ln in COMPLIANT.splitlines() if marker not in ln)


def test_missing_iron_law_is_caught():
    res = ssc.check_skill(_drop("Iron law"))
    assert res["ok"] is False and "iron-law" in res["missing"]


def test_missing_anti_scope_is_caught():
    res = ssc.check_skill(_drop("Anti-scope"))
    assert res["ok"] is False and "anti-scope" in res["missing"]


def test_missing_excuse_reality_table_is_caught():
    res = ssc.check_skill(_drop("Excuse | Reality"))
    assert res["ok"] is False and "excuse-reality" in res["missing"]


def test_missing_terminal_state_is_caught():
    res = ssc.check_skill(_drop("Terminal state"))
    assert res["ok"] is False and "terminal-state" in res["missing"]


def test_missing_scripted_dialogue_is_caught():
    # strip the one quoted sentence
    stripped = COMPLIANT.replace(
        '**"This sounds like the start of a new project — want me to run /friday:init?"**',
        "offer the init door")
    res = ssc.check_skill(stripped)
    assert res["ok"] is False and "scripted-dialogue" in res["missing"]


def test_frontmatter_description_must_be_substantial():
    thin = COMPLIANT.replace(COMPLIANT.split("description:")[1].split("\n")[0],
                             " use it")
    res = ssc.check_skill(thin)
    assert res["ok"] is False and "description" in res["missing"]


# --- INC-002 FR-2.5: two kinds of skill, each held to its own floor -------------
# Discriminator (INC-007): `friday-lane: true` marks a lane-skill; a watcher (a
# noticing-skill) never carries it. `disable-model-invocation: true` now means
# only "typed-only" — an opt-out of model-firing, present on some lanes and on
# repo-internal helpers, and it classifies NOTHING.

LANE = """---
name: feedback
description: the free-form front door for anything the PM noticed about a friday-managed project
friday-lane: true
disable-model-invocation: true
---

You are the lead running `/friday:feedback` — the free-form front door.
"""

INVOCABLE_LANE = LANE.replace("disable-model-invocation: true\n", "")


def test_classify_lane_vs_noticing():
    assert ssc.classify_skill(LANE) == "lane"            # both tags (typed-only lane)
    assert ssc.classify_skill(INVOCABLE_LANE) == "lane"  # marker alone (invocable lane)
    assert ssc.classify_skill(COMPLIANT) == "noticing"


def test_typed_only_flag_alone_is_not_a_lane():
    # the old key stripped of the marker: e.g. a repo-internal typed-only helper
    old_key_only = LANE.replace("friday-lane: true\n", "")
    assert ssc.classify_skill(old_key_only) == "noticing"


def test_lane_skill_passes_the_lighter_floor():
    # a lane playbook has no iron law / excuse-reality / terminal state — and
    # must NOT be asked for them (the KH-3 genre collision)
    res = ssc.check(LANE)
    assert res["kind"] == "lane"
    assert res["ok"] is True, res["missing"]


def test_lane_skill_thin_description_fails_its_floor():
    thin = LANE.replace(
        "description: the free-form front door for anything the PM noticed"
        " about a friday-managed project",
        "description: feedback door")
    res = ssc.check(thin)
    assert res["kind"] == "lane"
    assert res["ok"] is False and "description" in res["missing"]


def test_lane_empty_case_reports_its_own_floor_only():
    # the lane grammar's defined empty case: discriminator present, nothing else
    bare = "---\nfriday-lane: true\n---\n"
    res = ssc.check(bare)
    assert res["kind"] == "lane"
    assert set(res["missing"]) == {"name", "description"}


def test_noticing_skill_still_routes_to_the_strict_floor():
    res = ssc.check(COMPLIANT)
    assert res["kind"] == "noticing"
    assert res["ok"] is True, res["missing"]


def test_empty_text_is_the_noticing_empty_case():
    # no frontmatter, no discriminator → strict floor, everything missing
    res = ssc.check("")
    assert res["kind"] == "noticing"
    assert res["ok"] is False


# --- FR-3.2 (INC-003 KH-3): a bundled sibling never affects the SKILL.md check --

def test_skill_md_check_unaffected_by_bundled_siblings(tmp_path):
    lane = tmp_path / "skills" / "demo"
    (lane / "references").mkdir(parents=True)
    (lane / "SKILL.md").write_text(LANE, encoding="utf-8")
    (lane / "references" / "notes.md").write_text(
        "no iron law here, and none demanded\n", encoding="utf-8")
    assert ssc.main([str(lane / "SKILL.md")]) == 0


# --- the shipped skills must pass their own kind's bar (FR-81 + FR-2.5) ---------

def test_all_shipped_skills_pass_their_own_floor():
    skills_dir = os.path.join(BUILD_ROOT, "skills")
    kinds = {"lane": [], "noticing": []}
    for name in sorted(os.listdir(skills_dir)):
        path = os.path.join(skills_dir, name, "SKILL.md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                res = ssc.check(fh.read())
            kinds[res["kind"]].append(name)
            assert res["ok"] is True, f"{name} SKILL.md fails its {res['kind']} floor: {res['missing']}"
    # the three watcher families of US-16 all ship, on the STRICT floor
    assert len(kinds["noticing"]) >= 3
