"""MCP advisory index — the sync-on-query core (tools/doc-index/registry.py).

The index was shipped untested; these pin its load-bearing advisory contract:
stat-compare re-sync is incremental, vanished docs are pruned, and the
cross-document rollups return structured results (never raw exceptions) — while
the reader triad (tested in test_server.py) never depends on any of it.
"""
import os
import subprocess

import registry


def _git_project(tmp_path):
    """registry resolves .friday via friday_substrate (git-common-dir), so the
    fixture is a real git repo with the docs/ tree the index walks."""
    root = str(tmp_path)
    subprocess.run(["git", "init", "-q", root], check=True)
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    with open(os.path.join(root, "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write("# project\n")
    return root


def test_connect_creates_schema(tmp_path):
    conn = registry.connect(_git_project(tmp_path))
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"documents", "decisions", "actions"} <= tables


def test_ensure_fresh_indexes_then_short_circuits(tmp_path):
    root = _git_project(tmp_path)
    with open(os.path.join(root, "docs", "note.md"), "w", encoding="utf-8") as fh:
        fh.write("# Note\n\nbody\n")
    conn = registry.connect(root)
    first = registry.ensure_fresh(conn, root)
    assert "docs/note.md" in first["resynced"] and first["stale_possible"] is False
    # unchanged file -> stat-compare short-circuits, nothing re-synced next cycle
    assert registry.ensure_fresh(conn, root)["resynced"] == []
    assert conn.execute(
        "SELECT 1 FROM documents WHERE path='docs/note.md'").fetchone() is not None


def test_ensure_fresh_prunes_vanished_doc(tmp_path):
    root = _git_project(tmp_path)
    note = os.path.join(root, "docs", "gone.md")
    with open(note, "w", encoding="utf-8") as fh:
        fh.write("# Gone\n")
    conn = registry.connect(root)
    registry.ensure_fresh(conn, root)
    os.remove(note)
    registry.ensure_fresh(conn, root)
    assert conn.execute(
        "SELECT 1 FROM documents WHERE path='docs/gone.md'").fetchone() is None


def test_status_and_resolve_are_structured(tmp_path):
    root = _git_project(tmp_path)
    conn = registry.connect(root)
    registry.ensure_fresh(conn, root)
    st = registry.status(conn, root, "decisions")
    assert st["ok"] is True and "decision_count" in st
    miss = registry.resolve(conn, root, "D-9999")
    assert miss["ok"] is False and miss["error"] == "unknown_id"
    shape = registry.resolve(conn, root, "not-an-id")
    assert shape["ok"] is False and shape["error"] == "unknown_id_shape"
