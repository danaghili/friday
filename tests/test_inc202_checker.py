"""INC-202 FR-202.6 / FR-202.9 / AC-202.4 / AC-202.8 — the pipeline checker.

Four finding classes, every one grounded in a failure this repo has actually
had: (a) folder-vs-status-field disagreement (PROP-105/PROP-107's shape) plus
its sibling, an unparseable header where one is required; (b) a proposal in
`02-in-progress` whose named increment has closed — the PROP-200 class, with
"closed" read mechanically from the increment's trail existing; (c) a live
surface writing a folder-bearing proposal path — the INC-007/INC-008 dead
pointers' class, what makes D1 a rule instead of a habit; (d) a retired
folder name existing at all — the invisible-merge-resurrection class (KH-5).
Empty cases per KH-6: a tree with no proposals dir, empty stages, and a
`01-proposed` resident with no increment field are all CLEAN, never errors.
`tests/` is excluded from class (c) by design: test fixtures construct
violation specimens on purpose; the suite is not a pointer surface.
"""
import json
import os

import pytest

import proposal_pipeline as pp
import proposal_pipeline_check as ck


def _mk(root, stage, name="PROP-777", status=None, extra=()):
    d = os.path.join(root, "proposals", stage)
    os.makedirs(d, exist_ok=True)
    fields = [("status", status or stage), ("captured", "2026-07-30")] + list(extra)
    text = "---\n" + "".join(f"{k}: {v}\n" for k, v in fields) + "---\n\n## x\n"
    with open(os.path.join(d, f"{name}.md"), "w", encoding="utf-8") as fh:
        fh.write(text)


@pytest.fixture()
def tree(tmp_path):
    for s in pp.STAGES:
        os.makedirs(tmp_path / "proposals" / s)
    return str(tmp_path)


def _classes(res):
    return sorted({f["class"] for f in res["findings"]})


def test_a_healthy_tree_is_clean(tree):
    _mk(tree, "01-proposed")
    _mk(tree, "03-pending-validation", name="PROP-778",
        extra=[("increment", "INC-9")])
    res = ck.check(tree)
    assert res["verdict"] == "clean" and res["findings"] == []


def test_no_proposals_dir_at_all_is_a_valid_empty_case(tmp_path):
    res = ck.check(str(tmp_path))
    assert res["verdict"] == "clean"


def test_folder_field_disagreement_is_caught(tree):
    """PROP-105's shape replayed: the file sits in one stage, its own header
    claims another."""
    _mk(tree, "04-validated", status="02-in-progress")
    res = ck.check(tree)
    assert "folder-field-disagreement" in _classes(res)
    finding = [f for f in res["findings"]
               if f["class"] == "folder-field-disagreement"][0]
    assert "04-validated" in finding["detail"] and "02-in-progress" in finding["detail"]


def test_an_unparseable_header_is_a_finding_not_a_crash(tree):
    d = os.path.join(tree, "proposals", "01-proposed")
    with open(os.path.join(d, "PROP-800.md"), "w", encoding="utf-8") as fh:
        fh.write("## PROP-800 — no header at all\n")
    res = ck.check(tree)
    assert "unparseable-header" in _classes(res)


def test_the_prop200_class_a_closed_increment_still_in_progress(tree):
    """The failure that started all this, replayed mechanically: the
    increment's trail exists (the close's own artifact), the proposal still
    says in-progress."""
    _mk(tree, "02-in-progress", extra=[("increment", "INC-9")])
    os.makedirs(os.path.join(tree, "docs", "trails"))
    with open(os.path.join(tree, "docs", "trails", "INC-009.md"), "w",
              encoding="utf-8") as fh:
        fh.write("# trail\n")
    res = ck.check(tree)
    assert "closed-increment-still-in-progress" in _classes(res)


def test_an_open_increment_in_progress_is_clean(tree):
    _mk(tree, "02-in-progress", extra=[("increment", "INC-9")])
    assert ck.check(tree)["verdict"] == "clean"


def test_a_01_resident_with_no_increment_is_clean(tree):
    """KH-6: a proposal with no increment is a defined, valid state — ideas
    sit in 01-proposed unlinked by design."""
    _mk(tree, "01-proposed")
    assert ck.check(tree)["verdict"] == "clean"


def test_a_live_surface_writing_a_folder_bearing_path_is_caught(tree):
    os.makedirs(os.path.join(tree, "skills", "demo"))
    with open(os.path.join(tree, "skills", "demo", "SKILL.md"), "w",
              encoding="utf-8") as fh:
        fh.write("See " + "proposals/open/PROP-107.md" + " for details.\n")
    res = ck.check(tree)
    hits = [f for f in res["findings"] if f["class"] == "folder-bearing-path"]
    assert len(hits) == 1 and "SKILL.md" in hits[0]["file"]


def test_new_stage_names_in_paths_are_caught_too(tree):
    os.makedirs(os.path.join(tree, "skills"))
    with open(os.path.join(tree, "skills", "x.md"), "w", encoding="utf-8") as fh:
        fh.write("read " + "proposals/03-pending-validation/PROP-101.md" + "\n")
    res = ck.check(tree)
    assert "folder-bearing-path" in _classes(res)


def test_derived_artifact_output_is_outside_the_scan_boundary(tree):
    """graphify-out/ is gitignored derived state, regenerated from the tree by
    the graphify pipeline — nobody's live surface, so a stale pre-pipeline
    proposal path frozen inside its cache is not a D1 finding (the class that
    fired for real on 2026-07-31: a months-old graph snapshot carrying
    proposals/open/ paths tripped the INC-101 queue move)."""
    os.makedirs(os.path.join(tree, "graphify-out", "cache"))
    with open(os.path.join(tree, "graphify-out", "cache", "stat-index.json"),
              "w", encoding="utf-8") as fh:
        fh.write('{"path": "proposals/open/PROP-107.md"}\n')
    assert ck.check(tree)["verdict"] == "clean"


def test_append_only_records_keep_old_paths_unflagged(tree):
    """History is history: trails, the decision log, coverage and archives
    keep old path names by doctrine (FR-202.11) and must not be findings."""
    os.makedirs(os.path.join(tree, "docs", "trails"))
    with open(os.path.join(tree, "docs", "trails", "INC-007.md"), "w",
              encoding="utf-8") as fh:
        fh.write("moved " + "proposals/open/PROP-107.md" + " historically\n")
    with open(os.path.join(tree, "docs", "DECISIONS.md"), "w",
              encoding="utf-8") as fh:
        fh.write("cited " + "proposals/shipped/PROP-102.md" + " once\n")
    assert ck.check(tree)["verdict"] == "clean"


def test_a_resurrected_retired_folder_is_caught_even_empty(tree):
    """KH-5/AC-202.8: the invisible failure made loud — a retired name
    existing AT ALL is the finding; it need not contain anything."""
    os.makedirs(os.path.join(tree, "proposals", "open"))
    res = ck.check(tree)
    hits = [f for f in res["findings"] if f["class"] == "retired-folder"]
    assert len(hits) == 1 and "open" in hits[0]["detail"]


def test_cli_exit_codes_and_json(tree, capsys):
    _mk(tree, "01-proposed")
    rc = ck.main(["--root", tree, "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["verdict"] == "clean"
    _mk(tree, "04-validated", name="PROP-801", status="02-in-progress")
    rc = ck.main(["--root", tree, "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1 and out["verdict"] == "findings"
