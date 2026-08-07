"""INC-105 FR-105.2/FR-105.3 — the written conformance check
(tools/conformance_checks.py).

A declared convention's check is a typed line in the FRIDAY-CONFORMANCE
block beside the project's measured bars (docs/standards/coding-standards.md
for friday itself): it names the rule it came from, where the rule is
written, and what it looks for — exact search or a graph walk, never a
similarity judgement (OQ-105.1). found-not-checked is a first-class kind,
never an absence; a check whose rule vanished from its document is orphaned;
a territory-shaped exception is refused by name at read time with the check
still running (FR-105.9, AC-105.10); every check carries a content
fingerprint so the report can show which version ran (AC-105.6, KH-4).
Contract: docs/contracts/conformance-envelope.md § The check grammar.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import conformance_checks as cc  # noqa: E402


def _standards(root, body):
    path = os.path.join(str(root), "docs", "standards")
    os.makedirs(path, exist_ok=True)
    full = os.path.join(path, "coding-standards.md")
    with open(full, "w", encoding="utf-8") as fh:
        fh.write("# standards\n\n<!-- FRIDAY-CONFORMANCE:BEGIN -->\n"
                 + body + ("\n" if body else "")
                 + "<!-- FRIDAY-CONFORMANCE:END -->\n")
    return full


FORBID = ("conformance: no-hand-built-substrate-paths forbid · rule: nothing "
          "hand-builds a path into the shared substrate directory · from: "
          "CLAUDE.md · anchor: Nothing hand-builds a `.friday/` path · "
          "pattern: [\"']\\.friday[/\"'] · except: tools/friday_substrate.py")
REQUIRE = ("conformance: actions-validate require · rule: every action module "
           "validates its input at the boundary · from: docs/standards/"
           "coding-standards.md · scope: app/actions/*.ts · pattern: "
           "validate\\(")
CYCLE = ("conformance: no-import-cycles cycle · rule: modules do not import "
         "each other in a cycle · from: docs/standards/coding-standards.md")
UNCHECKED = ("conformance: handlers-stay-thin unchecked · rule: handlers stay "
             "thin and delegate to the domain layer · from: docs/architecture/"
             "01-overview.md")


# --- the grammar: four kinds, round-trip, closed vocabulary ------------------

def test_all_four_kinds_parse_and_round_trip(tmp_path):
    _standards(tmp_path, "\n".join([FORBID, REQUIRE, CYCLE, UNCHECKED]))
    out = cc.read(str(tmp_path))
    assert out["status"] == "recorded"
    kinds = {c["id"]: c["kind"] for c in out["checks"]}
    assert kinds == {"no-hand-built-substrate-paths": "forbid",
                     "actions-validate": "require",
                     "no-import-cycles": "cycle",
                     "handlers-stay-thin": "unchecked"}
    forbid = next(c for c in out["checks"]
                  if c["id"] == "no-hand-built-substrate-paths")
    assert forbid["pattern"] == "[\"']\\.friday[/\"']"
    assert forbid["excepts"] == ["tools/friday_substrate.py"]
    assert forbid["from"] == "CLAUDE.md"
    assert forbid["anchor"] == "Nothing hand-builds a `.friday/` path"
    for c in out["checks"]:
        assert cc.format_check(c) in (FORBID, REQUIRE, CYCLE, UNCHECKED)


def test_unknown_kind_is_flagged_never_dropped(tmp_path):
    _standards(tmp_path, "conformance: fuzzy similarity · rule: r · from: f")
    out = cc.read(str(tmp_path))
    assert out["checks"] == []
    assert len(out["malformed"]) == 1
    assert "similarity" in out["malformed"][0]


def test_kind_segment_rules_are_enforced(tmp_path):
    """require without scope, unchecked with a pattern, cycle with a scope —
    each is invalid WITH ITS REASON, kept and reported, never silently run
    and never silently dropped."""
    bad = "\n".join([
        "conformance: r1 require · rule: r · from: f · pattern: x",
        "conformance: u1 unchecked · rule: r · from: f · pattern: x",
        "conformance: c1 cycle · rule: r · from: f · scope: tools/*.py",
    ])
    _standards(tmp_path, bad)
    out = cc.read(str(tmp_path))
    assert len(out["checks"]) == 3
    for c in out["checks"]:
        assert c["invalid"], f"{c['id']} should be invalid"
    reasons = {c["id"]: c["invalid"] for c in out["checks"]}
    assert "scope" in reasons["r1"]
    assert "unchecked" in reasons["u1"]
    assert "cycle" in reasons["c1"]


def test_duplicate_id_is_flagged(tmp_path):
    _standards(tmp_path, CYCLE + "\n" + CYCLE)
    out = cc.read(str(tmp_path))
    assert len(out["checks"]) == 1
    assert len(out["malformed"]) == 1
    assert "duplicate" in out["malformed"][0]


# --- FR-105.9 / AC-105.10: pattern-shaped exceptions, refused territory -----

def test_territory_shaped_exception_is_refused_by_name(tmp_path):
    """A whole-tree carve-out (the audit's own disease) is refused with a
    message naming what is required; the check still runs, minus the
    refused exception — never silently honoured, never silently dropped."""
    line = ("conformance: cfg forbid · rule: r · from: f · pattern: x · "
            "except: scripts/**")
    _standards(tmp_path, line)
    (check,) = cc.read(str(tmp_path))["checks"]
    assert check["excepts"] == []
    assert len(check["refused_excepts"]) == 1
    refusal = check["refused_excepts"][0]
    assert "scripts/**" in refusal["value"]
    assert "pattern" in refusal["reason"]
    assert not check["invalid"]


def test_pattern_shaped_exceptions_are_accepted(tmp_path):
    line = ("conformance: cfg forbid · rule: r · from: f · pattern: x · "
            "except: **/conftest.py,tools/friday_substrate.py,*.test.ts")
    _standards(tmp_path, line)
    (check,) = cc.read(str(tmp_path))["checks"]
    assert check["excepts"] == ["**/conftest.py", "tools/friday_substrate.py",
                                "*.test.ts"]
    assert check["refused_excepts"] == []


def test_bare_directory_and_star_basename_are_territory(tmp_path):
    for terr in ("scripts/", "scripts/*", "app/legacy/**"):
        line = (f"conformance: t forbid · rule: r · from: f · pattern: x · "
                f"except: {terr}")
        _standards(tmp_path, line)
        (check,) = cc.read(str(tmp_path))["checks"]
        assert check["excepts"] == [], f"{terr} should be refused"
        assert check["refused_excepts"], f"{terr} should be refused by name"


# --- AC-105.6 / KH-4: the fingerprint shows which version ran ----------------

def test_fingerprint_changes_when_the_check_is_edited(tmp_path):
    _standards(tmp_path, FORBID)
    (before,) = cc.read(str(tmp_path))["checks"]
    edited = FORBID.replace("[\"']\\.friday[/\"']", "\\.friday/")
    _standards(tmp_path, edited)
    (after,) = cc.read(str(tmp_path))["checks"]
    assert before["fingerprint"] != after["fingerprint"]
    assert len(before["fingerprint"]) == 8


# --- FR-105.3, the orphan half: the check's rule left its document ----------

def test_orphaned_when_the_from_document_is_gone(tmp_path):
    _standards(tmp_path, ("conformance: gone forbid · rule: r · from: "
                          "docs/vanished.md · pattern: x"))
    (check,) = cc.read(str(tmp_path))["checks"]
    assert check["orphaned"] == "docs/vanished.md does not exist"


def test_orphaned_when_the_anchor_phrase_left_the_document(tmp_path):
    _standards(tmp_path, ("conformance: drifted forbid · rule: r · from: "
                          "docs/standards/coding-standards.md · anchor: a "
                          "sentence that is not there · pattern: x"))
    (check,) = cc.read(str(tmp_path))["checks"]
    assert check["orphaned"]
    assert "anchor" in check["orphaned"]


def test_not_orphaned_when_path_and_anchor_hold(tmp_path):
    full = _standards(tmp_path, "")
    with open(full, "a", encoding="utf-8") as fh:
        fh.write("\nEvery action module validates its input.\n")
    _standards(tmp_path, "")  # rewrite block empty, then append line + rule
    with open(full, "w", encoding="utf-8") as fh:
        fh.write("# standards\n\nEvery action module validates its input.\n\n"
                 "<!-- FRIDAY-CONFORMANCE:BEGIN -->\n"
                 "conformance: ok forbid · rule: r · from: "
                 "docs/standards/coding-standards.md · anchor: Every action "
                 "module validates its input · pattern: x\n"
                 "<!-- FRIDAY-CONFORMANCE:END -->\n")
    (check,) = cc.read(str(tmp_path))["checks"]
    assert check["orphaned"] is None


# --- the empty case and the add door -----------------------------------------

def test_absent_empty_and_recorded_are_three_states(tmp_path):
    out = cc.read(str(tmp_path))
    assert out["status"] == "absent"
    cc.init(str(tmp_path))
    out = cc.read(str(tmp_path))
    assert out["status"] == "empty"
    assert out["checks"] == []
    res = cc.add(str(tmp_path), {
        "id": "no-import-cycles", "kind": "cycle",
        "rule": "modules do not import each other in a cycle",
        "from": "docs/standards/coding-standards.md"})
    assert res["ok"] is True
    assert cc.read(str(tmp_path))["status"] == "recorded"


def test_add_refuses_bad_vocabulary_and_duplicate_ids(tmp_path):
    cc.init(str(tmp_path))
    assert cc.add(str(tmp_path), {"id": "x", "kind": "similarity",
                                  "rule": "r", "from": "f"})["ok"] is False
    cc.add(str(tmp_path), {"id": "x", "kind": "cycle", "rule": "r",
                           "from": "f"})
    res = cc.add(str(tmp_path), {"id": "x", "kind": "cycle", "rule": "r",
                                 "from": "f"})
    assert res["ok"] is False
    assert "duplicate" in res["reason"] or "already" in res["reason"]


def test_hand_edited_lines_survive_the_add_door(tmp_path):
    """A person can edit the block directly (D1); the module's own writes
    never rewrite or normalize the lines a person owns."""
    _standards(tmp_path, FORBID)
    cc.add(str(tmp_path), {"id": "added", "kind": "cycle", "rule": "r",
                           "from": "f"})
    with open(os.path.join(str(tmp_path), "docs", "standards",
                           "coding-standards.md"), encoding="utf-8") as fh:
        text = fh.read()
    assert FORBID in text
    assert "conformance: added cycle" in text
