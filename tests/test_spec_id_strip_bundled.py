"""spec_id_strip_check.py — the surface-aware bundled-file mode (INC-003
FR-3.3 / S-3.1, the increment's PRIMARY pin). Blessing "a lane may bundle
files" opens a door the ship gate didn't watch: an internal spec-ID tag could
ride to a marketplace stranger by hiding in a bundled reference. The mode
self-enumerates every lane folder (OQ-1: durable-by-construction — no glob for
a future author to forget), never hands the tool a directory, and skips a
binary sibling defensively (KH-1). Test-first.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import spec_id_strip_check as sisc  # noqa: E402

CLEAN_SKILL = """---
name: demo
description: a demonstration lane for the bundled-file ship-gate fixtures here
disable-model-invocation: true
---

You are the lead running the demo lane. Nothing internal survives here.
"""


def _lane(tmp_path, name, files):
    d = tmp_path / "skills" / name
    d.mkdir(parents=True)
    for fname, content in files.items():
        p = d / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
    return str(tmp_path / "skills")


def test_planted_tag_in_bundled_file_is_caught(tmp_path):
    # red-first: the leak this mode exists to close
    sk = _lane(tmp_path, "demo", {
        "SKILL.md": CLEAN_SKILL,
        "references/notes.md": "Remember the FR-99 requirement here.\n"})
    hits = sisc.scan_lane_dir(sk)
    assert len(hits) == 1
    assert hits[0]["tag"] == "FR-99" and hits[0]["line"] == 1
    assert hits[0]["file"].endswith(os.path.join("references", "notes.md"))


def test_tag_in_skill_md_also_caught_through_the_mode(tmp_path):
    sk = _lane(tmp_path, "demo", {"SKILL.md": CLEAN_SKILL + "\nSee AC-42.\n"})
    assert [h["tag"] for h in sisc.scan_lane_dir(sk)] == ["AC-42"]


def test_only_skill_md_scans_clean_exactly_as_today(tmp_path):
    # the defined empty (no-sibling) case = today's behavior
    sk = _lane(tmp_path, "demo", {"SKILL.md": CLEAN_SKILL})
    assert sisc.scan_lane_dir(sk) == []


def test_binary_sibling_never_crashes_the_gate(tmp_path):
    # KH-1: a PNG-shaped sibling is skipped defensively, never a hard error
    sk = _lane(tmp_path, "demo", {
        "SKILL.md": CLEAN_SKILL,
        "logo.png": b"\x89PNG\r\n\x1a\n\xff\xfe\x00binary\x80stuff"})
    assert sisc.scan_lane_dir(sk) == []


def test_no_skills_dir_is_the_defined_empty_case(tmp_path):
    assert sisc.scan_lane_dir(str(tmp_path / "no-such-dir")) == []


def test_cli_skills_dir_mode_exit_codes(tmp_path):
    dirty = _lane(tmp_path, "dirty", {
        "SKILL.md": CLEAN_SKILL,
        "cheat.md": "ships S-7 by accident\n"})
    assert sisc.main(["--skills-dir", dirty]) == 1
    clean = _lane(tmp_path / "c", "clean", {"SKILL.md": CLEAN_SKILL})
    assert sisc.main(["--skills-dir", clean]) == 0


def test_explicit_nonfile_path_still_exits_2(tmp_path):
    # the positional contract is unchanged: a directory path is a bad invocation
    assert sisc.main([str(tmp_path)]) == 2
