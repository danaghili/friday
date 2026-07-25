"""The lane-open substrate helpers — U3's payment of the D-0023 deferral:
every `.friday/` write goes through friday_substrate (the single-writer house
rule), so the lane doors built this unit open lanes via `lane_open()` and
never hand-write the sentinel. Contract: docs/contracts/lane-open.md.

The guards' disarm (`os.remove` in lane_close_gate / bug_close_gate) stays
theirs — one owner per lane, removal-on-pass is the guard's act; these
helpers cover the PRODUCER side plus an explicit `lane_clear()` — its `by=pm`
escalation default and the `by=lead` a door passes on an honest re-route/close.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import friday_substrate as fs  # noqa: E402


def _proj(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "CLAUDE.md").write_text(
        "# p\n\n<!-- FRIDAY-STATE:BEGIN -->\nstate: build-in-progress\n"
        "<!-- FRIDAY-STATE:END -->\n", encoding="utf-8")
    return str(root)


def test_lane_open_writes_the_contract_shape(tmp_path):
    root = _proj(tmp_path)
    path = fs.lane_open(root, lane="bug", id="BUG-3",
                        trail="docs/trails/BUG-3.md",
                        regression_test="tests/test_bug_3_crash.py")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data == {"lane": "bug", "id": "BUG-3",
                    "trail": "docs/trails/BUG-3.md",
                    "regression-test": "tests/test_bug_3_crash.py"}
    assert os.path.dirname(path) == fs.friday_dir(root)


def test_lane_open_patch_carries_blast_radius(tmp_path):
    root = _proj(tmp_path)
    path = fs.lane_open(root, lane="patch", id="PATCH-1",
                        trail="docs/trails/PATCH-1.md",
                        blast_radius=["docs/help.md", "tests/"])
    data = json.load(open(path, encoding="utf-8"))
    assert data["blast-radius"] == ["docs/help.md", "tests/"]
    assert "regression-test" not in data


def test_lane_open_refuses_a_second_open_lane(tmp_path):
    # One lane at a time: an open lane is a stalled question, not a stack.
    root = _proj(tmp_path)
    fs.lane_open(root, lane="bug", id="BUG-1", trail="docs/trails/BUG-1.md",
                 regression_test="tests/test_bug_1_x.py")
    try:
        fs.lane_open(root, lane="patch", id="P-2", trail="t.md",
                     blast_radius=["x"])
        assert False, "second open must raise"
    except ValueError as exc:
        assert "BUG-1" in str(exc)


def test_lane_open_enforces_the_contract_required_fields(tmp_path):
    root = _proj(tmp_path)
    for bad in (dict(lane="bug", id="B", trail="t.md"),               # no regression test
                dict(lane="patch", id="P", trail="t.md"),             # no blast radius
                dict(lane="hotfix", id="H", trail="t.md")):           # bad lane
        try:
            fs.lane_open(root, **bad)
            assert False, f"must raise: {bad}"
        except ValueError:
            pass
    assert not os.path.isfile(os.path.join(fs.friday_dir(root), "lane-open"))


def test_lane_events_actually_reach_the_journal(tmp_path):
    # The append is best-effort (swallowed exceptions), so an event name
    # missing from EVENT_VOCABULARY would silently never land — pin it.
    root = _proj(tmp_path)
    fs.lane_open(root, lane="feature", id="INC-1", trail="docs/trails/INC-1.md")
    fs.lane_clear(root)
    journal = open(os.path.join(fs.friday_dir(root), "journal.jsonl"),
                   encoding="utf-8").read()
    assert '"lane-opened"' in journal and '"lane-cleared"' in journal


def test_lane_clear_is_the_escalation_path(tmp_path):
    root = _proj(tmp_path)
    fs.lane_open(root, lane="feature", id="INC-2", trail="docs/trails/INC-2.md")
    assert fs.lane_clear(root) is True
    assert not os.path.isfile(os.path.join(fs.friday_dir(root), "lane-open"))
    assert fs.lane_clear(root) is False  # the tested empty case: nothing open


def test_lane_clear_records_who_actually_cleared(tmp_path):
    # A clear has two real callers: the PM's conscious escalation (by=pm, the
    # default) and a door's own honest re-route/close (by=lead) — e.g. patch
    # growing past its radius, or a bug closing unpindownable. The journal must
    # name the real actor, not stamp every clear as a PM escalation.
    root = _proj(tmp_path)
    fs.lane_open(root, lane="patch", id="PATCH-5",
                 trail="docs/trails/PATCH-5.md", blast_radius=["docs/x.md"])
    assert fs.lane_clear(root, by="lead") is True
    fs.lane_open(root, lane="feature", id="INC-3", trail="docs/trails/INC-3.md")
    assert fs.lane_clear(root) is True  # default → pm
    cleared = [json.loads(ln) for ln in
               open(os.path.join(fs.friday_dir(root), "journal.jsonl"),
                    encoding="utf-8") if '"lane-cleared"' in ln]
    assert [c["by"] for c in cleared] == ["lead", "pm"]


def test_lane_clear_rejects_an_unknown_actor(tmp_path):
    # by= is a provenance field: a bogus value would silently pollute the
    # record, so it fails fast rather than journaling a lie.
    root = _proj(tmp_path)
    fs.lane_open(root, lane="feature", id="INC-4", trail="docs/trails/INC-4.md")
    try:
        fs.lane_clear(root, by="somebody")
        assert False, "unknown by= must raise"
    except ValueError:
        pass
    # the lane is untouched — a rejected clear does not remove the sentinel
    assert os.path.isfile(os.path.join(fs.friday_dir(root), "lane-open"))


def test_guards_still_consume_the_helper_written_sentinel(tmp_path):
    # End-to-end: a helper-opened bug lane with no regression test on disk
    # is blocked by the real bug_close_gate over a real Stop event.
    import subprocess
    root = _proj(tmp_path)
    (tmp_path / "proj" / "docs").mkdir()
    (tmp_path / "proj" / "docs" / "DECISIONS.md").write_text("# Decisions\n", encoding="utf-8")
    fs.lane_open(root, lane="bug", id="BUG-9", trail="docs/trails/BUG-9.md",
                 regression_test="tests/test_bug_9_x.py")
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proc = subprocess.run(
        [sys.executable, os.path.join(repo, "hooks", "bug_close_gate.py"), repo],
        input=json.dumps({"hook_event_name": "Stop", "cwd": root}),
        capture_output=True, text=True, cwd=root)
    assert json.loads(proc.stdout)["decision"] == "block"
