"""INC-004 PRIMARY pin (FR-4.2 / AC-4.2 / S-4.3 / KH-1): the batch editor
validates the whole batch before writing anything — a zero-match, multi-match,
or missing-file edit refuses the ENTIRE batch and leaves every file
byte-identical. Partial application is the failure mode the tool exists to
prevent; these pins prove nothing is written on any refusal path.
"""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import batch_edit  # noqa: E402

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(BUILD_ROOT, "tools", "batch_edit.py")


@pytest.fixture()
def tree(tmp_path):
    (tmp_path / "a.md").write_text("alpha ONE beta\ngamma\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("delta TWO epsilon TWO\n", encoding="utf-8")
    (tmp_path / "c.py").write_text("x = 'THREE'\n", encoding="utf-8")
    return tmp_path


def snapshot(tree):
    return {p.name: p.read_text(encoding="utf-8") for p in tree.iterdir() if p.is_file()}


def run_cli(edits, cwd, *args, raw=None):
    payload = raw if raw is not None else json.dumps(edits)
    return subprocess.run([sys.executable, CLI, *args], input=payload,
                          capture_output=True, text=True, cwd=str(cwd))


# --- success paths --------------------------------------------------------------------

def test_valid_multi_file_batch_applies_all(tree):
    p = run_cli([{"file": "a.md", "old": "ONE", "new": "1"},
                 {"file": "c.py", "old": "'THREE'", "new": "'3'"}], tree)
    assert p.returncode == 0, p.stderr
    assert (tree / "a.md").read_text(encoding="utf-8") == "alpha 1 beta\ngamma\n"
    assert (tree / "c.py").read_text(encoding="utf-8") == "x = '3'\n"
    assert "2" in p.stdout  # applied count reported

def test_empty_edit_list_is_a_clean_noop(tree):
    before = snapshot(tree)
    p = run_cli([], tree)
    assert p.returncode == 0
    assert snapshot(tree) == before

def test_same_file_sequential_edits_validate_against_current_text(tree):
    # second edit's `old` only exists after the first is applied in memory
    p = run_cli([{"file": "a.md", "old": "ONE", "new": "UNO"},
                 {"file": "a.md", "old": "UNO beta", "new": "UNO BETA"}], tree)
    assert p.returncode == 0, p.stderr
    assert (tree / "a.md").read_text(encoding="utf-8") == "alpha UNO BETA\ngamma\n"

def test_dry_run_reports_but_writes_nothing(tree):
    before = snapshot(tree)
    p = run_cli([{"file": "a.md", "old": "ONE", "new": "1"}], tree, "--dry-run")
    assert p.returncode == 0, p.stderr
    assert snapshot(tree) == before
    assert "a.md" in p.stdout


# --- refusal paths: the whole batch dies, nothing is written --------------------------

def test_multi_match_refuses_entire_batch(tree):
    before = snapshot(tree)
    p = run_cli([{"file": "a.md", "old": "ONE", "new": "1"},      # valid on its own
                 {"file": "b.md", "old": "TWO", "new": "2"}], tree)  # matches twice
    assert p.returncode == 1
    assert snapshot(tree) == before  # the VALID edit was not applied either
    assert "b.md" in (p.stdout + p.stderr) and "2" in (p.stdout + p.stderr)

def test_zero_match_refuses_entire_batch(tree):
    before = snapshot(tree)
    p = run_cli([{"file": "a.md", "old": "NOPE", "new": "x"},
                 {"file": "c.py", "old": "'THREE'", "new": "'3'"}], tree)
    assert p.returncode == 1
    assert snapshot(tree) == before
    assert "a.md" in (p.stdout + p.stderr) and "0" in (p.stdout + p.stderr)

def test_missing_file_refuses_entire_batch(tree):
    before = snapshot(tree)
    p = run_cli([{"file": "ghost.md", "old": "x", "new": "y"},
                 {"file": "a.md", "old": "ONE", "new": "1"}], tree)
    assert p.returncode == 1
    assert snapshot(tree) == before
    assert "ghost.md" in (p.stdout + p.stderr)

def test_dry_run_on_invalid_batch_reports_failure_exit(tree):
    p = run_cli([{"file": "b.md", "old": "TWO", "new": "2"}], tree, "--dry-run")
    assert p.returncode == 1
    assert "b.md" in (p.stdout + p.stderr)


# --- input contract -------------------------------------------------------------------

def test_malformed_json_is_usage_error(tree):
    before = snapshot(tree)
    p = run_cli(None, tree, raw="not json [")
    assert p.returncode == 2
    assert snapshot(tree) == before

def test_empty_old_is_rejected(tree):
    # an empty `old` "matches" everywhere; it can never be exactly-once
    before = snapshot(tree)
    p = run_cli([{"file": "a.md", "old": "", "new": "x"}], tree)
    assert p.returncode in (1, 2)
    assert snapshot(tree) == before

def test_module_run_batch_returns_structured_verdicts(tree):
    ok, results = batch_edit.run_batch(
        [{"file": "b.md", "old": "TWO", "new": "2"}], root=str(tree), dry_run=True)
    assert ok is False
    assert results and results[0]["count"] == 2 and results[0]["ok"] is False
