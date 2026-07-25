"""Foundation substrate tests (A.5 #6, #8 + Appendix B wiring).

#6  SubagentStop in-hook identity check (ISSUE-007).
#8  spawn-telemetry: the single journal primitive + its coverage check.
B   every writer resolves .friday/ via git --git-common-dir (worktrees share it).
"""
import json
import os
import subprocess

import pytest

import friday_substrate as fs


# --- Appendix B: root resolution ------------------------------------------------

@pytest.fixture()
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    (tmp_path / "seed.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c",
                    "user.name=t", "commit", "-qm", "seed"], check=True)
    return tmp_path


def test_root_resolves_to_repo_from_subdir(repo):
    sub = repo / "docs"
    assert fs.resolve_project_root(str(sub)) == str(repo)


def test_root_resolves_to_MAIN_repo_from_linked_worktree(repo):
    wt = repo.parent / (repo.name + "-wt")
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", str(wt)], check=True)
    assert fs.resolve_project_root(str(wt)) == str(repo)
    # ... and the journal written FROM the worktree lands in the MAIN .friday/
    fs.append_journal_line(str(wt), fs.build_journal_line("spawn", "build:tester", by="lead"))
    assert (repo / ".friday" / "journal.jsonl").is_file()
    assert not (wt / ".friday").exists()


def test_non_git_dir_falls_back_to_cwd(tmp_path):
    d = tmp_path / "loose"
    d.mkdir()
    assert fs.resolve_project_root(str(d)) == str(d)


# --- journal primitive -----------------------------------------------------------

def test_journal_line_validation(repo):
    with pytest.raises(ValueError):
        fs.build_journal_line("", "phase")
    with pytest.raises(ValueError):
        fs.build_journal_line("spawn", "p", by="hacker")
    with pytest.raises(ValueError):
        fs.build_journal_line("spawn", "p", data="not-a-dict")
    line = fs.build_journal_line("spawn", "build:tester", data={"agent": "friday-tester"})
    fs.append_journal_line(str(repo), line)
    raw = (repo / ".friday" / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(raw[-1])["event"] == "spawn"


def test_journal_rejects_oversized_line(repo):
    line = fs.build_journal_line("spawn", "p", data={"blob": "x" * 5000})
    with pytest.raises(ValueError):
        fs.append_journal_line(str(repo), line)


# --- per-session locks (Appendix B.3) --------------------------------------------

def test_session_locks_are_per_session(repo):
    fs.write_session_lock(str(repo), "sess-a", {"pid": 1})
    fs.write_session_lock(str(repo), "sess-b", {"pid": 2})
    locks = fs.read_session_locks(str(repo))
    assert set(locks) == {"sess-a", "sess-b"}
    fs.remove_session_lock(str(repo), "sess-a")
    assert set(fs.read_session_locks(str(repo))) == {"sess-b"}


# --- ISSUE-007 identity check (#6) ------------------------------------------------

def test_identity_match_foreign_typeless():
    assert fs.event_matches_agent({"agent_type": "friday-closer"}, "closer") == "match"
    assert fs.event_matches_agent({"agent_type": "friday-strategist"}, "closer") == "foreign"
    assert fs.event_matches_agent({}, "closer") == "typeless"
    assert fs.event_matches_agent({"agent_type": ""}, "closer") == "typeless"
    # nested + alternate key spellings observed in the wild (#27755)
    assert fs.event_matches_agent({"agent": {"type": "friday-closer"}}, "closer") == "match"
    assert fs.event_matches_agent({"subagentType": "friday-tester"}, "closer") == "foreign"


# --- spawn telemetry CLI (#8) ------------------------------------------------------

def _run(args, cwd):
    tools = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
    return subprocess.run(
        ["python3", os.path.join(tools, "spawn_telemetry.py"), *args],
        capture_output=True, text=True, cwd=cwd)


def test_spawn_telemetry_writes_envelope_events(repo):
    for evt in ("spawn", "accept", "done"):
        p = _run(["--emit", evt, "--agent", "friday-tester", "--phase", "build:test"], str(repo))
        assert p.returncode == 0, p.stderr
    lines = [json.loads(x) for x in
             (repo / ".friday" / "journal.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [x["event"] for x in lines] == ["spawn", "accept", "done"]
    assert all(x["data"]["agent"] == "friday-tester" for x in lines)


def test_spawn_telemetry_rejects_unknown_event(repo):
    p = _run(["--emit", "launched", "--agent", "x", "--phase", "p"], str(repo))
    assert p.returncode == 2


def test_spawn_telemetry_refuses_non_friday_dir(tmp_path):
    loose = tmp_path / "loose"
    loose.mkdir()
    p = _run(["--emit", "spawn", "--agent", "x", "--phase", "p"], str(loose))
    assert p.returncode == 2 and not (loose / ".friday").exists()


# --- spawn-coverage check (#8b) ----------------------------------------------------

def test_verify_spawn_coverage_flags_uninstrumented_command(tmp_path):
    import verify_spawn_coverage as vsc
    cmds = tmp_path / "commands"
    cmds.mkdir()
    (cmds / "good.md").write_text(
        "Dispatch the tester subagent via the Agent tool.\n"
        "Emit telemetry: `spawn_telemetry.py --emit spawn ...` then `--emit done`.\n",
        encoding="utf-8")
    (cmds / "bad.md").write_text(
        "Spawn a subagent via the Agent tool and wait for it.\n", encoding="utf-8")
    (cmds / "quiet.md").write_text("Just edits files. No dispatching.\n", encoding="utf-8")
    res = vsc.check_commands(str(cmds))
    assert not res["ok"]
    flagged = [f["file"] for f in res["failures"]]
    assert "bad.md" in flagged and "good.md" not in flagged and "quiet.md" not in flagged


def _skill(text, *, lane=True):
    fm = "---\nname: x\ndescription: a lane playbook for the coverage test fixtures here\n"
    if lane:
        fm += "friday-lane: true\n"
    return fm + "---\n\n" + text


def test_verify_spawn_coverage_covers_lane_skills(tmp_path):
    # INC-2 sweep (D-0081): lanes that spawn now live in skills/ — the checker
    # follows them; a noticing-skill is a watcher, not a dispatch surface.
    import verify_spawn_coverage as vsc
    cmds = tmp_path / "commands"
    cmds.mkdir()
    sk = tmp_path / "skills"
    for name, text in [
            ("badlane", _skill("Spawn a subagent via the Agent tool.\n")),
            ("goodlane", _skill("Spawn via the Agent tool.\nCite `spawn_telemetry.py`.\n")),
            ("watcher", _skill("Never spawn a subagent yourself — offer the door.\n",
                               lane=False))]:
        d = sk / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(text, encoding="utf-8")
    res = vsc.check_all(str(cmds), str(sk))
    flagged = [f["file"] for f in res["failures"]]
    assert flagged == ["skills/badlane/SKILL.md"]
    assert res["checked"] == 2  # the two lane-skills; the watcher is out of scope


def test_verify_spawn_coverage_skills_empty_case(tmp_path):
    # no skills dir → the commands-only behavior, unchanged
    import verify_spawn_coverage as vsc
    cmds = tmp_path / "commands"
    cmds.mkdir()
    (cmds / "quiet.md").write_text("No dispatching.\n", encoding="utf-8")
    res = vsc.check_all(str(cmds), str(tmp_path / "no-skills"))
    assert res["ok"] and res["checked"] == 1
