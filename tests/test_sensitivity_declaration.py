"""INC-108 FR-108.1/2/3/5/8 — the sensitivity declaration record.

The specimen this answers is not an unasked question: the audited project
classified its health data correctly, in the right file, and the label
changed nothing because no run-moment reads a source comment, and its two
honest records about deletion and backups never met. So the record here is
one something actually OPENS (the deep clean's read-back, the handover),
and the treatment answers are a closed set where silence is not in the
vocabulary (D1, FR-108.2).

What the tests insist on:

- **A blank treatment is a finding; an explicit not-applicable with a reason
  is clean; prose that considers without answering is a blank** (AC-108.3
  red-first, all three — the softened-back-into-a-question death of §3).
- **The floor behaves as a floor** (D2, AC-108.5): a project-named class
  outside the listed members declares like any listed one; unclassified is
  not an outcome.
- **A shared copy is answered once** (D7, KH-4, AC-108.6): project-level
  copy artefacts carry the lifetimes; a store cites `project-copies`; a
  store-level answer restating a project artefact's name is REFUSED — two
  stores behind one dump can never hold two different answers about it.
- **The empty case is declared, dated, and distinct from absent** (D12):
  a project with no sensitive store writes that down; a missing record
  means never-asked, never clean.
- **A malformed line is kept and flagged, never dropped.**
- **Nothing here reads data** (S-108.3): the tool takes names, shapes and
  postures as arguments and opens nothing but its own record file.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import sensitivity_declaration as sd  # noqa: E402


def _root(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    return str(root)


def _record(root):
    return open(os.path.join(root, "docs", "SENSITIVITY.md"),
                encoding="utf-8").read()


ANSWERS = {
    "at-rest": "R2 server-side encryption, verified against the bucket config",
    "copies": "cites project-copies",
    "deletion": "consent withdrawal wipes the live row; dump residue lives the full window",
    "reach": "admin role and the profile owner only",
    "basis": "explicit consent, ADR-0044",
    "told": "privacy page retention table names the backup window",
}


# --- declaring -------------------------------------------------------------------------

def test_declare_creates_the_record_and_round_trips(tmp_path):
    root = _root(tmp_path)
    res = sd.declare(root, store="subscriber_profiles", store_class="health",
                     answers=ANSWERS, requirements=["FR-9.1", "S-9.2"],
                     when="2026-08-04")
    assert res["ok"] is True
    (entry,) = sd.entries(root)
    assert entry["store"] == "subscriber_profiles"
    assert entry["class"] == "health"
    assert entry["date"] == "2026-08-04"
    assert entry["requirements"] == ["FR-9.1", "S-9.2"]
    assert entry["answers"]["at-rest"].startswith("R2 server-side")
    assert entry["malformed"] is False


def test_floor_class_outside_the_list_declares_like_any_other(tmp_path):
    """D2/AC-108.5: the floor is a floor — the project's own class counts
    exactly as much as a listed one, and unclassified is not an outcome."""
    root = _root(tmp_path)
    res = sd.declare(root, store="biometric_templates",
                     store_class="biometric-gait-signature",
                     answers=ANSWERS, requirements=[], when="2026-08-04")
    assert res["ok"] is True
    (entry,) = sd.entries(root)
    assert entry["class"] == "biometric-gait-signature"


def test_redeclaring_a_store_updates_the_same_store(tmp_path):
    """OQ-108.4: the declaration is a LIVING record keyed by the store's own
    name — a changed answer updates the store, it does not mint a sibling
    (the read-back would otherwise meet two declarations for one store)."""
    root = _root(tmp_path)
    sd.declare(root, store="subscriber_profiles", store_class="health",
               answers=ANSWERS, requirements=["FR-9.1"], when="2026-08-04")
    updated = dict(ANSWERS, reach="admin, owner, and the new export job")
    sd.declare(root, store="subscriber_profiles", store_class="health",
               answers=updated, requirements=["FR-9.1", "FR-9.3"],
               when="2026-08-05")
    (entry,) = sd.entries(root)
    assert entry["date"] == "2026-08-05"
    assert "export job" in entry["answers"]["reach"]
    assert entry["requirements"] == ["FR-9.1", "FR-9.3"]


# --- silence is not in the vocabulary (FR-108.2 / AC-108.3) ---------------------------

def test_a_blank_treatment_is_a_finding_not_clean(tmp_path):
    """declare() refuses a blank up front, so the blank check() guards
    against is the hand-edit AFTER a valid declare — the record is a
    committed file anyone can touch, and a deleted answer line must surface
    as a finding, never read as clean."""
    root = _root(tmp_path)
    sd.declare(root, store="s", store_class="health", answers=ANSWERS,
               requirements=[], when="2026-08-04")
    path = os.path.join(root, "docs", "SENSITIVITY.md")
    text = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(
        text.replace("deletion: " + ANSWERS["deletion"] + "\n", ""))
    out = sd.check(root)
    assert out["clean"] is False
    assert any(f.get("treatment") == "deletion" and f.get("store") == "s"
               for f in out["findings"])


def test_explicit_not_applicable_with_reason_is_clean(tmp_path):
    root = _root(tmp_path)
    answers = dict(ANSWERS,
                   deletion="not-applicable — the store holds no per-person rows")
    sd.declare(root, store="s", store_class="credentials", answers=answers,
               requirements=[], when="2026-08-04")
    out = sd.check(root)
    assert out["clean"] is True, out["findings"]


def test_not_applicable_without_a_reason_is_a_blank(tmp_path):
    root = _root(tmp_path)
    answers = dict(ANSWERS, deletion="not-applicable")
    res = sd.declare(root, store="s", store_class="health", answers=answers,
                     requirements=[], when="2026-08-04")
    assert res["ok"] is False
    assert "reason" in res["detail"]


def test_an_empty_answer_is_refused_at_declare_time(tmp_path):
    root = _root(tmp_path)
    answers = dict(ANSWERS, basis="  ")
    res = sd.declare(root, store="s", store_class="health", answers=answers,
                     requirements=[], when="2026-08-04")
    assert res["ok"] is False and "basis" in res["detail"]


def test_a_missing_treatment_key_is_refused_at_declare_time(tmp_path):
    """The closed set is closed both ways: every treatment present, and an
    unknown treatment name refused rather than absorbed."""
    root = _root(tmp_path)
    partial = {k: v for k, v in ANSWERS.items() if k != "told"}
    res = sd.declare(root, store="s", store_class="health", answers=partial,
                     requirements=[], when="2026-08-04")
    assert res["ok"] is False and "told" in res["detail"]
    extra = dict(ANSWERS, sparkle="yes")
    res2 = sd.declare(root, store="s", store_class="health", answers=extra,
                      requirements=[], when="2026-08-04")
    assert res2["ok"] is False and "sparkle" in res2["detail"]


# --- the shared-copy rule (D7 / KH-4 / AC-108.6) --------------------------------------

def test_project_copies_answered_once_and_cited_by_both_stores(tmp_path):
    root = _root(tmp_path)
    sd.set_project_copies(root, [
        {"artefact": "nightly-full-dump", "lifetime": "14 daily + 4 weekly + 12 monthly"},
    ], when="2026-08-04")
    for store in ("subscriber_profiles", "payment_tokens"):
        res = sd.declare(root, store=store, store_class="health",
                         answers=ANSWERS, requirements=[], when="2026-08-04")
        assert res["ok"] is True, res
    out = sd.check(root)
    assert out["clean"] is True, out["findings"]
    text = _record(root)
    assert text.count("14 daily + 4 weekly + 12 monthly") == 1


def test_a_store_restating_a_project_artefact_is_refused(tmp_path):
    """Two stores behind one dump can never hold two answers about it: a
    store-level copies answer that NAMES a project-level artefact is a
    restatement that can drift, refused at declare time."""
    root = _root(tmp_path)
    sd.set_project_copies(root, [
        {"artefact": "nightly-full-dump", "lifetime": "12 monthly"},
    ], when="2026-08-04")
    answers = dict(ANSWERS, copies="nightly-full-dump kept 6 monthly")
    res = sd.declare(root, store="s", store_class="health", answers=answers,
                     requirements=[], when="2026-08-04")
    assert res["ok"] is False
    assert "nightly-full-dump" in res["detail"] and "cite" in res["detail"].lower()


def test_store_specific_copies_are_answered_on_the_store(tmp_path):
    root = _root(tmp_path)
    sd.set_project_copies(root, [
        {"artefact": "nightly-full-dump", "lifetime": "12 monthly"},
    ], when="2026-08-04")
    answers = dict(ANSWERS,
                   copies="cites project-copies; plus the per-store CSV export "
                          "kept 30 days on the operator laptop")
    res = sd.declare(root, store="s", store_class="health", answers=answers,
                     requirements=[], when="2026-08-04")
    assert res["ok"] is True
    (entry,) = sd.entries(root)
    assert "CSV export" in entry["answers"]["copies"]


# --- the empty case (D12) ---------------------------------------------------------------

def test_declare_none_is_dated_distinct_and_clean(tmp_path):
    root = _root(tmp_path)
    res = sd.declare_none(root, reason="no data store of any kind — stdlib "
                          "tooling, no database, by recorded non-goal",
                          when="2026-08-04")
    assert res["ok"] is True
    assert sd.entries(root) == []
    out = sd.check(root)
    assert out["clean"] is True and out["empty"] is True
    assert "no data store" in _record(root)


def test_absent_record_is_never_asked_never_clean(tmp_path):
    root = _root(tmp_path)
    out = sd.check(root)
    assert out["clean"] is False and out["empty"] is False
    assert any(f.get("kind") == "never-declared" for f in out["findings"])


# --- hostile text ------------------------------------------------------------------------

def test_a_malformed_line_is_kept_and_flagged_never_dropped(tmp_path):
    root = _root(tmp_path)
    sd.declare(root, store="s", store_class="health", answers=ANSWERS,
               requirements=[], when="2026-08-04")
    path = os.path.join(root, "docs", "SENSITIVITY.md")
    text = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(text.replace(
        "<!-- FRIDAY-SENSITIVITY:END -->",
        "sensitive-store: broken-line-no-fields\n<!-- FRIDAY-SENSITIVITY:END -->"))
    all_entries = sd.entries(root)
    assert len(all_entries) == 2
    bad = [e for e in all_entries if e["malformed"]]
    assert len(bad) == 1 and "broken-line-no-fields" in bad[0]["raw"]
    out = sd.check(root)
    assert out["clean"] is False


def test_free_prose_in_answers_round_trips_the_grammar_glyphs(tmp_path):
    root = _root(tmp_path)
    tricky = "wiped on withdrawal — dump residue: 12 monthly · see ADR-0044"
    answers = dict(ANSWERS, deletion=tricky)
    sd.declare(root, store="s", store_class="health", answers=answers,
               requirements=[], when="2026-08-04")
    (entry,) = sd.entries(root)
    assert entry["answers"]["deletion"] == tricky


# --- CLI --------------------------------------------------------------------------------

def test_cli_check_emits_json_and_exit_reflects_findings(tmp_path, capsys):
    root = _root(tmp_path)
    rc = sd.main(["check", "--root", root, "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1 and out["clean"] is False
    sd.declare_none(root, reason="fixture", when="2026-08-04")
    rc2 = sd.main(["check", "--root", root, "--json"])
    out2 = json.loads(capsys.readouterr().out)
    assert rc2 == 0 and out2["clean"] is True


def test_a_malformed_project_copy_line_is_a_finding(tmp_path):
    """FR-108.13's third class with mechanical support: a copy artefact the
    record carries but the parser cannot enumerate is named, never silently
    ignored — surfaced by the INC-108 coverage tester's close note."""
    root = _root(tmp_path)
    sd.set_project_copies(root, [
        {"artefact": "nightly-dump", "lifetime": "30 days"},
    ], when="2026-08-04")
    sd.declare(root, store="s", store_class="health", answers=ANSWERS,
               requirements=[], when="2026-08-04")
    path = os.path.join(root, "docs", "SENSITIVITY.md")
    text = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(text.replace(
        "<!-- FRIDAY-SENSITIVITY-COPIES:END -->",
        "copy: broken-copy-line-no-fields\n<!-- FRIDAY-SENSITIVITY-COPIES:END -->"))
    out = sd.check(root)
    assert out["clean"] is False
    assert any(f.get("kind") == "malformed-copy" and
               "broken-copy-line-no-fields" in f["detail"]
               for f in out["findings"])
