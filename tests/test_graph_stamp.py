"""The code-graph freshness stamp (FR-71) — the substrate single-writer that
guard #8 (graph_freshness_check.py) names as its counterpart. The load-bearing
property is the round-trip: what graph_stamp_write() writes, the guard reads
back as CURRENT. Test-first (U6-1).
"""
import json
import os
import subprocess
import sys

import pytest

from guardkit import BUILD_ROOT

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import friday_substrate as fs  # noqa: E402
import graph_freshness_check as gfc  # noqa: E402


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "f.txt").write_text("x", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "c0")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    return root, head


def test_written_stamp_is_read_as_current_by_guard8(tmp_path):
    # The whole contract: writer and reader must agree. Guard #8 sees HEAD-current.
    root, head = _repo(tmp_path)
    fs.graph_stamp_write(str(root), head)
    assert gfc.check(str(root))["verdict"] == "valid-pass"
    assert "current" in gfc.check(str(root))["summary"]


def test_stamp_rejects_a_non_sha(tmp_path):
    # A garbage stamp makes guard #8 no-verdict (fail-open) and silently hides
    # staleness — reject at the write boundary instead.
    root, _ = _repo(tmp_path)
    with pytest.raises(ValueError):
        fs.graph_stamp_write(str(root), "not-a-commit-hash")


def test_stamp_rejects_empty(tmp_path):
    root, _ = _repo(tmp_path)
    with pytest.raises(ValueError):
        fs.graph_stamp_write(str(root), "")


def test_stamp_records_graph_refreshed_event(tmp_path):
    root, head = _repo(tmp_path)
    fs.graph_stamp_write(str(root), head)
    lines = (root / ".friday" / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(ln)["event"] for ln in lines if ln.strip()]
    assert "graph-refreshed" in events


def test_stamp_write_leaves_no_temp_behind(tmp_path):
    # Atomic temp+replace: a reader (guard #8) never observes a torn stamp,
    # and no .graph.stamp.* scratch file is orphaned.
    root, head = _repo(tmp_path)
    fs.graph_stamp_write(str(root), head)
    leftovers = [p.name for p in (root / ".friday").iterdir()
                 if p.name.startswith(".graph.stamp.")]
    assert leftovers == []


def test_graph_refreshed_is_in_the_event_vocabulary(tmp_path):
    # Pin the vocabulary member: an event missing from EVENT_VOCABULARY would
    # be rejected by build_journal_line and the stamp writer's journal line
    # would silently never land.
    assert "graph-refreshed" in fs.EVENT_VOCABULARY
