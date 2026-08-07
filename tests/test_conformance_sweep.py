"""INC-105 FR-105.5/FR-105.8/FR-105.9 — the conformance sweep
(tools/conformance_sweep.py).

Mechanical full recall over the written checks and the switched-on baseline
invariants; counts and never judges; three silences named as themselves and
never absorbed into a clean line (found-not-checked, switched-off-here,
out-of-reach); an unreadable file surfaces as unread; findings carry the
rule and the location and never the line's value (S-105.4, KH-5); exit 0
whatever it finds (S-105.1). A sibling of the maintainability measurer,
never an extension of it (D9; INC-207 D12 governs).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import conformance_sweep as sweep_mod  # noqa: E402


def _project(root, files, checks_body):
    for rel, content in files.items():
        full = os.path.join(str(root), rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
    std = os.path.join(str(root), "docs", "standards")
    os.makedirs(std, exist_ok=True)
    with open(os.path.join(std, "coding-standards.md"), "w",
              encoding="utf-8") as fh:
        fh.write("# s\n\n<!-- FRIDAY-CONFORMANCE:BEGIN -->\n"
                 + checks_body + ("\n" if checks_body else "")
                 + "<!-- FRIDAY-CONFORMANCE:END -->\n")


def _baseline(root, body):
    path = os.path.join(str(root), "baseline.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# b\n\n<!-- FRIDAY-BASELINE:BEGIN -->\n" + body
                 + ("\n" if body else "") + "<!-- FRIDAY-BASELINE:END -->\n")
    return path


FORBID = ("conformance: no-env-bypass forbid · rule: every environment "
          "variable is read through config.ts · from: docs/standards/"
          "coding-standards.md · scope: app/** · pattern: process\\.env\\. · "
          "except: app/config.ts")


# --- forbid: full recall, value-blind, exceptions -----------------------------

def test_forbid_reports_every_location_with_path_and_line(tmp_path):
    _project(tmp_path, {
        "app/config.ts": "export const A = process.env.A\n",
        "app/jobs/sync.ts": "const t = process.env.TOKEN\nok()\n",
        "app/actions/save.ts": "x()\nconst d = process.env.DB\n",
    }, FORBID)
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    hits = {(f["path"], f["line"]) for f in out["findings"]}
    assert hits == {("app/jobs/sync.ts", 1), ("app/actions/save.ts", 2)}
    assert out["verdict"] == "not-clean"


def test_findings_never_carry_the_matched_lines_value(tmp_path):
    """KH-5: the search reads the line a token sits on; the report never
    reproduces it."""
    planted = "sk-live-PLANTED4732SECRET"
    _project(tmp_path, {
        "app/deploy.sh": f"export TOKEN={planted} # process.env.TOKEN\n",
    }, ("conformance: c forbid · rule: r · from: docs/standards/"
        "coding-standards.md · pattern: TOKEN"))
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    assert out["findings"]
    assert planted not in json.dumps(out)


def test_pattern_except_honored_territory_refusal_named_and_not_honored(tmp_path):
    _project(tmp_path, {
        "app/config.ts": "process.env.A\n",
        "scripts/run.sh": "process.env.B\n",
    }, ("conformance: c forbid · rule: r · from: docs/standards/"
        "coding-standards.md · pattern: process\\.env\\. · "
        "except: app/config.ts,scripts/**"))
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    paths = {f["path"] for f in out["findings"]}
    assert "app/config.ts" not in paths
    assert "scripts/run.sh" in paths
    assert any("scripts/**" in r["value"] for r in out["refused_excepts"])


# --- require + the distinct clean outcome (AC-105.2 shape) --------------------

def test_require_flags_scope_files_lacking_the_pattern(tmp_path):
    _project(tmp_path, {
        "app/actions/save.ts": "validate(input)\nsave()\n",
        "app/actions/del.ts": "del()\n",
    }, ("conformance: av require · rule: r · from: docs/standards/"
        "coding-standards.md · scope: app/actions/* · pattern: validate\\("))
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    (finding,) = out["findings"]
    assert finding["path"] == "app/actions/del.ts"
    assert finding.get("line") is None


def test_clean_check_is_a_distinct_outcome_not_silence(tmp_path):
    _project(tmp_path, {
        "app/actions/save.ts": "validate(input)\n",
    }, ("conformance: av require · rule: r · from: docs/standards/"
        "coding-standards.md · scope: app/actions/* · pattern: validate\\("))
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    assert out["findings"] == []
    (clean,) = out["clean_checks"]
    assert clean["id"] == "av"
    assert clean["files_checked"] == 1
    assert len(clean["fingerprint"]) == 8
    assert out["verdict"] == "clean"


# --- the three silences (FR-105.8, S-105.2, KH-2) ----------------------------

def test_found_not_checked_is_named_and_dirties_the_verdict(tmp_path):
    _project(tmp_path, {}, ("conformance: thin unchecked · rule: handlers "
                            "stay thin · from: docs/standards/"
                            "coding-standards.md"))
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    (fnc,) = out["found_not_checked"]
    assert fnc["id"] == "thin"
    assert out["verdict"] == "not-clean"


def test_switched_off_invariant_is_named_every_time_but_not_a_stain(tmp_path):
    """D5/FR-105.8: a self-switched-off rule is named in the report every
    time; correct non-engagement is not a silence about something owed, so
    it does not by itself dirty the verdict (KH-2's fixture goes not-clean
    on the other classes)."""
    _project(tmp_path, {"app/a.py": "x = 1\n"}, "")
    baseline = _baseline(tmp_path, (
        "baseline: outbound-timeouts forbid · rule: every outbound call "
        "carries a time limit · when: found: requests\\.|urllib|fetch\\( · "
        "provenance: scarred — the audit's scalability segment · "
        "pattern: requests\\.(get|post)\\((?![^)]*timeout)"))
    out = sweep_mod.sweep(str(tmp_path), baseline_path=baseline)
    (off,) = out["switched_off"]
    assert off["id"] == "outbound-timeouts"
    assert "condition" in off
    assert out["verdict"] == "clean"


def test_engaged_invariant_runs_and_finds(tmp_path):
    _project(tmp_path, {"app/a.py": "import requests\n"
                                    "requests.get(url)\n"}, "")
    baseline = _baseline(tmp_path, (
        "baseline: outbound-timeouts forbid · rule: every outbound call "
        "carries a time limit · when: found: requests\\. · provenance: "
        "scarred — the audit's scalability segment · pattern: "
        "requests\\.get\\((?![^)]*timeout)"))
    out = sweep_mod.sweep(str(tmp_path), baseline_path=baseline)
    (finding,) = out["findings"]
    assert finding["check"] == "outbound-timeouts"
    assert finding["source"] == "baseline"
    assert finding["provenance"].startswith("scarred")


def test_cycle_out_of_reach_is_named_never_clean(tmp_path):
    _project(tmp_path, {}, ("conformance: nc cycle · rule: no cycles · "
                            "from: docs/standards/coding-standards.md"))
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    (oor,) = out["out_of_reach"]
    assert oor["id"] == "nc"
    assert out["verdict"] == "not-clean"


def test_cycle_check_reports_cycles_from_the_ir(tmp_path):
    _project(tmp_path, {}, ("conformance: nc cycle · rule: no cycles · "
                            "from: docs/standards/coding-standards.md"))
    gen = os.path.join(str(tmp_path), "docs", "architecture", "generated")
    os.makedirs(gen)
    with open(os.path.join(gen, "architecture-ir.json"), "w") as fh:
        json.dump({"modules": [{"id": "a", "path": "a.py", "loc": 1},
                               {"id": "b", "path": "b.py", "loc": 1}],
                   "edges": [{"from": "a", "to": "b", "line": 1,
                              "deferred": True},
                             {"from": "b", "to": "a", "line": 2,
                              "deferred": True}]}, fh)
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    (finding,) = out["findings"]
    assert finding["cycle"]["modules"] == ["a", "b"]
    assert all(e["deferred"] for e in finding["cycle"]["edges"])


def test_in_file_exception_is_refused_by_name_and_still_a_finding(tmp_path):
    """OQ-105.6, resolved refuse-side: exceptions live on the check line,
    their single home — a `conformance-except` token beside the violation
    changes nothing about the count and is named in the report."""
    _project(tmp_path, {
        "app/a.py": "boom()  # conformance-except: c — legacy, leave it\n",
    }, ("conformance: c forbid · rule: r · from: docs/standards/"
        "coding-standards.md · pattern: boom"))
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    (finding,) = out["findings"]
    assert (finding["path"], finding["line"]) == ("app/a.py", 1)
    (refusal,) = [r for r in out["refused_excepts"]
                  if "conformance-except" in r["value"]]
    assert "app/a.py:1" in refusal["value"]
    assert "single home" in refusal["reason"] or "check line" in refusal["reason"]


# --- honesty residue: unreadable, orphaned, malformed, invalid ---------------

def test_unreadable_file_is_unread_never_absorbed(tmp_path):
    _project(tmp_path, {"app/ok.py": "x\n"},
             ("conformance: c forbid · rule: r · from: docs/standards/"
              "coding-standards.md · pattern: x · scope: app/**"))
    bad = os.path.join(str(tmp_path), "app", "locked.py")
    with open(bad, "w") as fh:
        fh.write("x\n")
    os.chmod(bad, 0)
    try:
        out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
        assert any("locked.py" in u for u in out["unread"])
        assert out["verdict"] == "not-clean"
    finally:
        os.chmod(bad, 0o644)


def test_orphaned_check_still_runs_and_is_named(tmp_path):
    _project(tmp_path, {"app/a.py": "boom\n"},
             ("conformance: c forbid · rule: r · from: docs/gone.md · "
              "pattern: boom"))
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    assert out["findings"]
    (orphan,) = out["orphaned"]
    assert orphan["id"] == "c"
    assert out["verdict"] == "not-clean"


def test_invalid_and_malformed_are_could_not_run(tmp_path):
    _project(tmp_path, {},
             "conformance: r1 require · rule: r · from: f · pattern: x\n"
             "conformance: broken beyond parse")
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    assert len(out["could_not_run"]) == 2
    assert out["verdict"] == "not-clean"


def test_absent_block_is_its_own_state_never_clean_silence(tmp_path):
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    assert out["checks_home"] == "absent"
    assert out["verdict"] == "not-clean"


# --- scope: what the project itself excludes stays out (2026-08-05 reconcile,
# --- PM-directed; the D-1075 pattern applied to this instrument) ------------

def test_gitignored_paths_leave_the_sweep(tmp_path):
    import subprocess
    _project(tmp_path, {
        ".gitignore": "app/scratch/\n",
        "app/scratch/gen.ts": "const t = process.env.TOKEN\n",
        "app/jobs/sync.ts": "const t = process.env.TOKEN\n",
    }, FORBID)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    hits = {(f["path"], f["line"]) for f in out["findings"]}
    assert hits == {("app/jobs/sync.ts", 1)}


def test_docs_archive_is_not_swept(tmp_path):
    check = ("conformance: no-env anywhere-forbid · rule: r · from: f · "
             "scope: ** · pattern: process\\.env\\.")
    check = check.replace("anywhere-forbid", "forbid")
    _project(tmp_path, {
        "docs/archive/old-era.md": "    process.env.TOKEN\n",
        "docs/live.md": "    process.env.TOKEN\n",
    }, check)
    out = sweep_mod.sweep(str(tmp_path), baseline_path=None)
    paths = {f["path"] for f in out["findings"]}
    assert "docs/live.md" in paths
    assert not any(p.startswith("docs/archive/") for p in paths)
