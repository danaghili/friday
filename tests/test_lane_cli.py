"""tools/lane.py — the door-facing CLI over friday_substrate's lane helpers
(U3; contract: docs/contracts/lane-open.md). Thin by design: the rules live
in fs.lane_open/lane_clear (tests/test_lane_open_helper.py); these tests pin
the CLI surface the command doors actually call.
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(REPO, "tools", "lane.py")


def _proj(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "CLAUDE.md").write_text(
        "# p\n\n<!-- FRIDAY-STATE:BEGIN -->\nstate: build-in-progress\n"
        "<!-- FRIDAY-STATE:END -->\n", encoding="utf-8")
    return str(root)


def _run(*args):
    return subprocess.run([sys.executable, CLI, *args],
                          capture_output=True, text=True)


def test_open_status_clear_round_trip(tmp_path):
    root = _proj(tmp_path)
    p = _run("open", "--root", root, "--lane", "bug", "--id", "BUG-7",
             "--trail", "docs/trails/BUG-7.md",
             "--regression-test", "tests/test_bug_7_x.py")
    assert p.returncode == 0, p.stderr
    assert "lane-open" in p.stdout

    s = _run("status", "--root", root)
    assert json.loads(s.stdout)["id"] == "BUG-7"

    c = _run("clear", "--root", root)
    assert c.returncode == 0 and "cleared" in c.stdout
    s2 = _run("status", "--root", root)
    assert "no lane open" in s2.stdout


def test_patch_open_takes_repeated_blast_radius(tmp_path):
    root = _proj(tmp_path)
    p = _run("open", "--root", root, "--lane", "patch", "--id", "PATCH-2",
             "--trail", "docs/trails/PATCH-2.md",
             "--blast-radius", "docs/help.md", "--blast-radius", "README.md")
    assert p.returncode == 0, p.stderr
    s = json.loads(_run("status", "--root", root).stdout)
    # the trail path rides along by construction (NF12 — see lane_open)
    assert s["blast-radius"] == ["docs/help.md", "README.md",
                                 "docs/trails/PATCH-2.md"]


def test_clear_records_who_via_by_flag(tmp_path):
    root = _proj(tmp_path)
    _run("open", "--root", root, "--lane", "patch", "--id", "PATCH-9",
         "--trail", "docs/trails/PATCH-9.md", "--blast-radius", "docs/x.md")
    c = _run("clear", "--root", root, "--by", "lead")
    assert c.returncode == 0 and "cleared" in c.stdout
    lines = open(os.path.join(root, ".friday", "journal.jsonl"),
                 encoding="utf-8").read().splitlines()
    cleared = [json.loads(ln) for ln in lines if '"lane-cleared"' in ln]
    assert cleared[-1]["by"] == "lead"


def test_contract_violations_exit_2_with_plain_words(tmp_path):
    root = _proj(tmp_path)
    p = _run("open", "--root", root, "--lane", "bug", "--id", "B",
             "--trail", "t.md")  # no regression test
    assert p.returncode == 2
    assert "regression-test" in p.stderr
    assert not os.path.isfile(os.path.join(root, ".friday", "lane-open"))
