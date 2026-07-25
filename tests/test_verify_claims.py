"""FRIDAY-CLAIMS vocabulary tests — the U1 claims extensions
(TECHNICAL_SOW_REBUILD US-13: FR-66 world=greenfield|brownfield, FR-67
provenance=), plus the standing rule they ride on: an ABSENT claim is a
declared gap readers tolerate — only doc_gate's spec kind requires
provenance (tested in tests/test_doc_gate.py).

The closed value vocabularies live in ONE home — tools/taglines.py (the
grammar authority) — imported by verify_claims and doc_gate alike.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import taglines  # noqa: E402
import verify_claims  # noqa: E402


def _claude_md(*claim_lines: str) -> str:
    body = "\n".join(claim_lines)
    return ("# testproj\n\n<!-- FRIDAY-CLAIMS:BEGIN -->\n"
            f"{body}\n<!-- FRIDAY-CLAIMS:END -->\n")


def _run(tmp_path, *claim_lines: str) -> dict:
    (tmp_path / "CLAUDE.md").write_text(_claude_md(*claim_lines), encoding="utf-8")
    return verify_claims.check_all(str(tmp_path))


# --- the single-home vocabularies ------------------------------------------------

def test_vocabularies_live_in_taglines():
    assert taglines.PROVENANCE_VALUES == ("born-from-discovery", "recovered-from-code")
    assert taglines.WORLD_VALUES == ("greenfield", "brownfield")


# --- world= (FR-66) ---------------------------------------------------------------

def test_world_claim_valid_values_are_not_drift(tmp_path):
    for value in taglines.WORLD_VALUES:
        res = _run(tmp_path, "stack: path:python3", f"world: {value}")
        assert res["ok"], (value, res)
        world = [r for r in res["results"] if r["claim"].startswith("world:")]
        assert world and world[0]["verdict"] == "semantic_only", world


def test_world_claim_unknown_value_is_drift(tmp_path):
    res = _run(tmp_path, "stack: path:python3", "world: swamp")
    assert not res["ok"], res
    world = [r for r in res["results"] if r["claim"].startswith("world:")]
    assert world[0]["verdict"] == "drift", world


# --- provenance= (FR-67) ------------------------------------------------------------

def test_provenance_claim_valid_values_are_not_drift(tmp_path):
    for value in taglines.PROVENANCE_VALUES:
        res = _run(tmp_path, "stack: path:python3", f"provenance: {value}")
        assert res["ok"], (value, res)


def test_provenance_claim_unknown_value_is_drift(tmp_path):
    res = _run(tmp_path, "stack: path:python3", "provenance: found-in-a-drawer")
    assert not res["ok"], res


# --- absence is a declared gap, not an error ------------------------------------------

def test_absent_world_and_provenance_claims_are_tolerated(tmp_path):
    # FR-66/FR-67 extend the vocabulary; they do not make the claims
    # mandatory here. (The one consumer that REQUIRES provenance is
    # doc_gate's spec kind — tests/test_doc_gate.py.)
    res = _run(tmp_path, "stack: path:python3")
    assert res["ok"], res
    ok, errs = verify_claims.well_formed(_claude_md("stack: path:python3"))
    assert ok, errs


def test_new_types_parse_as_known_claims():
    ok, errs = verify_claims.well_formed(_claude_md(
        "world: brownfield", "provenance: recovered-from-code"))
    assert ok, errs
