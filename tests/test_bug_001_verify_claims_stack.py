"""BUG-001 regression — stack claims: evidence location is explicit, matching
is bounded (docs/BUGS.md BUG-001; trail docs/trails/BUG-001.md).

Option B (PM-ratified): the claim grammar names WHERE evidence lives —
bare/`manifest:` = project-declared (manifest or PEP 723 inline, parsed match,
no PATH fallback), `path:` = on PATH, `files:` = repo file/dir evidence,
`harness:`/`external:` = honestly unverifiable. The parenthetical is an
annotation, never a rule switch. Every facet D1-D8 of the original report is
pinned here so no future "simplification" can reintroduce substring matching.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import verify_claims as vc  # noqa: E402


def _proj_a(tmp_path):
    """The report's fixture: manifest holds ONLY pyyaml plus a comment
    documenting redis as REMOVED; repo holds only an empty push.py."""
    a = tmp_path / "a"
    a.mkdir()
    (a / "requirements.txt").write_text(
        "pyyaml\n# we ripped out redis last year, do not reinstall\n",
        encoding="utf-8")
    (a / "push.py").write_text("", encoding="utf-8")
    return str(a)


def _proj_pep723(tmp_path):
    """PEP 723 project: no manifest file at all; deps live inline."""
    b = tmp_path / "b"
    b.mkdir()
    (b / "tool.py").write_text(
        '# /// script\n# requires-python = ">=3.11"\n'
        '# dependencies = ["pyyaml"]\n# ///\nimport yaml\n',
        encoding="utf-8")
    return str(b)


def _proj_named_paths(tmp_path):
    """Well-named directory + hyphen/underscore-mismatched file."""
    c = tmp_path / "c"
    (c / "sync" / "ha_sync").mkdir(parents=True)
    (c / "sync" / "ha_sync" / "__init__.py").write_text("", encoding="utf-8")
    (c / "home_assistant_mcp.py").write_text("", encoding="utf-8")
    return str(c)


# --- D1: manifest matching is bounded and comment-blind ---------------------------

def test_d1_substring_of_another_package_is_drift(tmp_path):
    v, ev = vc._check_stack(_proj_a(tmp_path), "yaml")
    assert v == "drift", (v, ev)


def test_d1_dependency_documented_as_removed_is_drift(tmp_path):
    v, ev = vc._check_stack(_proj_a(tmp_path), "redis")
    assert v == "drift", (v, ev)


def test_d1_true_manifest_dependency_passes_and_names_its_evidence(tmp_path):
    v, ev = vc._check_stack(_proj_a(tmp_path), "pyyaml")
    assert v == "pass" and "requirements.txt" in ev, (v, ev)


# --- D2: files: matches whole stems and directory segments, never substrings ------

def test_d2_filename_substring_is_drift(tmp_path):
    v, ev = vc._check_stack(_proj_a(tmp_path), "files:us")
    assert v == "drift", (v, ev)


def test_d2_directory_segment_counts_as_file_evidence(tmp_path):
    v, ev = vc._check_stack(_proj_named_paths(tmp_path), "files:ha_sync")
    assert v == "pass", (v, ev)


def test_d2_stem_match_normalizes_hyphen_underscore(tmp_path):
    v, ev = vc._check_stack(_proj_named_paths(tmp_path), "files:home-assistant-mcp")
    assert v == "pass", (v, ev)


# --- D3: the parenthetical is an annotation, never a rule switch ------------------

def test_d3_annotation_does_not_change_what_is_tested(tmp_path):
    a = _proj_a(tmp_path)
    bare = vc._check_stack(a, "pyyaml")
    annotated = vc._check_stack(a, "pyyaml (yaml parsing)")
    assert annotated[0] == bare[0] == "pass", (bare, annotated)


# --- D4: harness/external locations are sayable, and honestly unverifiable --------

def test_d4_harness_claim_is_unverifiable_not_drift(tmp_path):
    v, ev = vc._check_stack(_proj_a(tmp_path),
                            "harness:home-assistant-mcp (audit-time exploration)")
    assert v == "unverifiable", (v, ev)


def test_d4_external_claim_is_unverifiable_not_drift(tmp_path):
    v, ev = vc._check_stack(_proj_a(tmp_path),
                            "external:ha-rest-config-api (data source)")
    assert v == "unverifiable", (v, ev)


def test_d4_unverifiable_does_not_count_as_drift_in_check_all(tmp_path):
    root = tmp_path / "d4"
    root.mkdir()
    (root / "CLAUDE.md").write_text(
        "# p\n\n<!-- FRIDAY-CLAIMS:BEGIN -->\n"
        "stack: harness:some-mcp (exploration)\n"
        "<!-- FRIDAY-CLAIMS:END -->\n", encoding="utf-8")
    res = vc.check_all(str(root))
    assert res["ok"] and res["drift_count"] == 0, res


# --- D5: PEP 723 inline dependencies are project-declared evidence ----------------

def test_d5_pep723_inline_dependency_passes(tmp_path):
    v, ev = vc._check_stack(_proj_pep723(tmp_path), "pyyaml")
    assert v == "pass", (v, ev)


# --- D6: bare names never fall back to machine state; path: is explicit -----------

def test_d6_bare_name_does_not_pass_on_machine_path(tmp_path):
    empty = tmp_path / "e"
    empty.mkdir()
    # python3 is certainly on PATH on the machine running this suite;
    # the claim is about the PROJECT, so it must drift.
    v, ev = vc._check_stack(str(empty), "python3")
    assert v == "drift", (v, ev)


def test_d6_explicit_path_location_passes_and_says_so(tmp_path):
    empty = tmp_path / "e2"
    empty.mkdir()
    v, ev = vc._check_stack(str(empty), "path:python3")
    assert v == "pass" and "PATH" in ev, (v, ev)


# --- D7: version constraints parse -------------------------------------------------

def test_d7_natural_constraint_spelling_parses(tmp_path):
    empty = tmp_path / "e3"
    empty.mkdir()
    v, ev = vc._check_stack(str(empty), "python>=3.11")
    assert "does not parse" not in ev, (v, ev)


def test_d7_requires_python_satisfies_python_constraint(tmp_path):
    v, ev = vc._check_stack(_proj_pep723(tmp_path), "python>=3.11")
    assert v == "pass", (v, ev)


# --- D8: version pins behave consistently per declared location -------------------

def test_d8_manifest_major_pin_still_verifies(tmp_path):
    a2 = tmp_path / "a2"
    a2.mkdir()
    (a2 / "requirements.txt").write_text("pyyaml==6.0.1\n", encoding="utf-8")
    assert vc._check_stack(str(a2), "pyyaml@6")[0] == "pass"
    assert vc._check_stack(str(a2), "pyyaml@5")[0] == "drift"


def test_d8_path_location_with_pin_is_defined_and_scoped(tmp_path):
    empty = tmp_path / "e4"
    empty.mkdir()
    v, ev = vc._check_stack(str(empty), "path:python3@99")
    # Presence on PATH is provable; the pin is not version-checked there —
    # the evidence must say so rather than silently overclaiming.
    assert v == "pass" and "not" in ev.lower(), (v, ev)


# --- the headline: the report's false-claims block must count 3 drifts ------------

def test_headline_false_claims_block_drifts(tmp_path):
    a = _proj_a(tmp_path)
    with open(os.path.join(a, "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write("# p\n\n<!-- FRIDAY-CLAIMS:BEGIN -->\n"
                 "stack: yaml\n"
                 "stack: redis\n"
                 "stack: files:us (substring of push.py)\n"
                 "<!-- FRIDAY-CLAIMS:END -->\n")
    res = vc.check_all(a)
    assert not res["ok"] and res["drift_count"] == 3, res


# --- grammar hygiene ----------------------------------------------------------------

def test_unknown_location_prefix_is_drift_with_a_named_reason(tmp_path):
    empty = tmp_path / "e5"
    empty.mkdir()
    v, ev = vc._check_stack(str(empty), "bogus:thing")
    assert v == "drift", (v, ev)
