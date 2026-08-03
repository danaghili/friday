"""INC-202 AC-202.11 / D3 — the frozen region is genuinely frozen.

The fence is the freeze line: once a proposal's header names its increment,
everything below the fence is frozen. The checker's `frozen-body-edited`
class enforces it mechanically: the baseline is the body at the FIRST
committed version whose header carries the `increment:` field (the D3 freeze
moment), followed through stage renames; the current on-disk body must equal
it byte-for-byte. Header edits never trip it — the compared region is the
body alone. Empty cases per KH-6, all CLEAN skips: no git repo, a proposal
never committed with the field, a proposal with no increment field at all.
"""
import os
import subprocess

import pytest

import proposal_pipeline as pp
import proposal_pipeline_check as ck

BODY_A = "\n## PROP-777 — t\n\nAsk text, version A.\n"
BODY_B = "\n## PROP-777 — t\n\nAsk text, version B — edited after the freeze.\n"


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True)


def _repo(tmp_path):
    os.makedirs(tmp_path, exist_ok=True)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@test")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    for s in pp.STAGES:
        os.makedirs(tmp_path / "proposals" / s)
    return tmp_path


def _write(root, stage, fields, body, name="PROP-777"):
    path = root / "proposals" / stage / f"{name}.md"
    text = "---\n" + "".join(f"{k}: {v}\n" for k, v in fields) + "---" + body
    path.write_text(text, encoding="utf-8")
    return path


def _commit(root, msg):
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", msg)


def _frozen(res):
    return [f for f in res["findings"] if f["class"] == "frozen-body-edited"]


def test_uncommitted_body_edit_after_link_is_caught(tmp_path):
    root = _repo(tmp_path)
    fields = [("status", "02-in-progress"), ("captured", "2026-07-30"),
              ("increment", "INC-9")]
    _write(root, "02-in-progress", fields, BODY_A)
    _commit(root, "queue move writes the increment field")
    _write(root, "02-in-progress", fields, BODY_B)  # disk edit, no commit
    res = ck.check(str(root))
    hits = _frozen(res)
    assert len(hits) == 1
    assert "PROP-777" in hits[0]["detail"]
    assert res["verdict"] == "findings"


def test_committed_body_edit_after_link_is_caught(tmp_path):
    root = _repo(tmp_path)
    fields = [("status", "02-in-progress"), ("captured", "2026-07-30"),
              ("increment", "INC-9")]
    _write(root, "02-in-progress", fields, BODY_A)
    _commit(root, "queue move")
    _write(root, "02-in-progress", fields, BODY_B)
    _commit(root, "a body edit that slipped into some later commit")
    assert len(_frozen(ck.check(str(root)))) == 1


def test_header_only_edit_passes(tmp_path):
    root = _repo(tmp_path)
    fields = [("status", "02-in-progress"), ("captured", "2026-07-30"),
              ("increment", "INC-9")]
    _write(root, "02-in-progress", fields, BODY_A)
    _commit(root, "queue move")
    fields2 = fields + [("note", "paused: waiting on the PM ruling")]
    _write(root, "02-in-progress", fields2, BODY_A)  # header grew, body intact
    assert _frozen(ck.check(str(root))) == []


def test_pre_link_body_edits_are_free(tmp_path):
    root = _repo(tmp_path)
    unlinked = [("status", "01-proposed"), ("captured", "2026-07-30")]
    _write(root, "01-proposed", unlinked, BODY_A)
    _commit(root, "capture")
    _write(root, "01-proposed", unlinked, BODY_B)  # research appended pre-link
    _commit(root, "researched line lands — legal, not yet frozen")
    assert _frozen(ck.check(str(root))) == []
    # the freeze starts at the version that FIRST carries the field: body B
    linked = unlinked + [("increment", "INC-9")]
    _write(root, "01-proposed", linked, BODY_B)
    _commit(root, "link")
    assert _frozen(ck.check(str(root))) == []


def test_follow_across_stage_rename(tmp_path):
    root = _repo(tmp_path)
    fields = [("status", "02-in-progress"), ("captured", "2026-07-30"),
              ("increment", "INC-9")]
    _write(root, "02-in-progress", fields, BODY_A)
    _commit(root, "queue move")
    old = root / "proposals" / "02-in-progress" / "PROP-777.md"
    os.remove(old)
    moved = [("status", "03-pending-validation"), ("captured", "2026-07-30"),
             ("increment", "INC-9")]
    _write(root, "03-pending-validation", moved, BODY_A)
    _commit(root, "close moves it to 03 — header edit + relocation")
    assert _frozen(ck.check(str(root))) == []  # rename + header edit: clean
    _write(root, "03-pending-validation", moved, BODY_B)
    assert len(_frozen(ck.check(str(root)))) == 1  # body edit past the rename


def test_empty_cases_are_clean_skips(tmp_path):
    # (a) no git repo at all — no baseline exists, the class stays silent
    for s in pp.STAGES:
        os.makedirs(tmp_path / "proposals" / s)
    fields = [("status", "02-in-progress"), ("captured", "2026-07-30"),
              ("increment", "INC-9")]
    _write(tmp_path, "02-in-progress", fields, BODY_A)
    assert _frozen(ck.check(str(tmp_path))) == []

    # (b) repo exists but the linked file was never committed — no baseline
    root = _repo(tmp_path / "b")
    _write(root, "02-in-progress", fields, BODY_A)
    assert _frozen(ck.check(str(root))) == []

    # (c) no increment field — not frozen, edit at will
    root2 = _repo(tmp_path / "c")
    unlinked = [("status", "01-proposed"), ("captured", "2026-07-30")]
    _write(root2, "01-proposed", unlinked, BODY_A)
    _commit(root2, "capture")
    _write(root2, "01-proposed", unlinked, BODY_B)
    assert _frozen(ck.check(str(root2))) == []
