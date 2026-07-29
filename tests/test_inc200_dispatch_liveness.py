"""INC-200 FR-200.1 / FR-200.2 / FR-200.3 / FR-200.15 — the dispatch-liveness
checker, test-first.

The rule (D2, PM-ratified): trigger on the role FILE EXISTING, never on the
role being mentioned — measured, because fourteen of fifteen roles are named
somewhere and `friday-architect` in none, so a mention-triggered rule would
give a clean pass to the most orphaned role in the roster. A role passes by
being dispatched somewhere (a spawn naming BOTH the agent and its `model:`)
or by carrying the typed declared-exception line.

Hard failure by design: this checks friday's OWN source in friday's own suite
and ship gate, never a PM's project, so it is a sibling of the spec-ID strip
gate — the warn-first / fail-open doctrine (which governs hooks gating a PM's
work) does not apply here (D2, S-200.5).
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import dispatch_liveness_check as dlc  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _role(tmp_path, name, body="You are a role.\n"):
    d = tmp_path / "agents" / "roles"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name.replace('friday-', '')}.md"
    p.write_text(f"---\nname: {name}\nmodel: sonnet\n---\n\n{body}",
                 encoding="utf-8")
    return p


def _surface(tmp_path, fname, text):
    d = tmp_path / "skills" / fname
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    p.write_text(text, encoding="utf-8")
    return p


# --- FR-200.1: the role side ---------------------------------------------------------

def test_dispatched_role_passes(tmp_path):
    _role(tmp_path, "friday-tester")
    _surface(tmp_path, "harden",
             "Spawn the tester (`friday-tester`, model: **sonnet**) over the diff.\n")
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass", res
    assert res["orphans"] == []


def test_undispatched_role_is_a_hard_failure(tmp_path):
    _role(tmp_path, "friday-architect")
    _surface(tmp_path, "build", "The lead wears the architect hat itself.\n")
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail", res
    assert "friday-architect" in res["orphans"]
    # the report says what would fix it
    assert "declared-exception" in res["summary"] or "dispatch" in res["summary"]


def test_mention_without_a_model_is_not_a_dispatch(tmp_path):
    """The defect shape itself: prose routes to a role, nothing spawns it."""
    _role(tmp_path, "friday-operations")
    _surface(tmp_path, "security",
             "L6 ops-readiness gaps route to `friday-operations` to own and fill.\n")
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail"
    assert "friday-operations" in res["orphans"]


def test_lane_names_are_never_flagged(tmp_path):
    """Precision-first: `/friday:research` is a lane the PM types, not a role.
    Nine of eleven live 'route to' phrases are this shape."""
    _role(tmp_path, "friday-tester")
    _surface(tmp_path, "harden",
             "Spawn (`friday-tester`, model: sonnet).\n"
             "An open risk routes to `/friday:research` before any build.\n")
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass", res


def test_empty_case_no_roles(tmp_path):
    """FR-200.1's empty case: no roster is a pass, not a crash."""
    (tmp_path / "skills").mkdir(parents=True)
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass"
    assert res["roles_checked"] == 0


def test_empty_case_every_role_dispatched(tmp_path):
    _role(tmp_path, "friday-tester")
    _role(tmp_path, "friday-closer")
    _surface(tmp_path, "harden",
             "(`friday-tester`, model: sonnet) then (`friday-closer`, model: haiku)\n")
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass"
    assert res["roles_checked"] == 2 and res["orphans"] == []


# --- FR-200.2: the declared exception --------------------------------------------------

def test_declared_exception_passes_and_removal_fails(tmp_path):
    """AC-200.2, both directions."""
    p = _role(tmp_path, "friday-architect",
              "dispatch-exception: no lane dispatches this role — the build lead "
              "wears the architect hat in-context (continuity over decomposition)\n")
    (tmp_path / "skills").mkdir(parents=True, exist_ok=True)
    assert dlc.check(root=str(tmp_path))["verdict"] == "valid-pass"

    p.write_text(p.read_text(encoding="utf-8").replace(
        "dispatch-exception: no lane dispatches this role — the build lead "
        "wears the architect hat in-context (continuity over decomposition)", ""),
        encoding="utf-8")
    assert dlc.check(root=str(tmp_path))["verdict"] == "valid-fail"


def test_exception_without_a_reason_is_refused(tmp_path):
    """The grammar's empty case: a bare exception is a silent loosening."""
    _role(tmp_path, "friday-architect", "dispatch-exception:\n")
    (tmp_path / "skills").mkdir(parents=True, exist_ok=True)
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail", res


# --- FR-200.3: the contract-path existence check ---------------------------------------

def test_phantom_contract_path_is_a_hard_failure(tmp_path):
    """AC-200.3 — the class that already bit: compaction-package.md claimed a
    seam-handoff contract that never existed (D-0117)."""
    (tmp_path / "docs" / "contracts").mkdir(parents=True)
    (tmp_path / "docs" / "contracts" / "real-thing.md").write_text("# real\n",
                                                                   encoding="utf-8")
    _surface(tmp_path, "build",
             "Contract: docs/contracts/real-thing.md and docs/contracts/ghost.md\n")
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail", res
    assert any("ghost" in m for m in res["missing_contracts"])
    assert not any("real-thing" in m for m in res["missing_contracts"])


def test_no_contract_mentions_is_a_pass(tmp_path):
    (tmp_path / "skills").mkdir(parents=True)
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass"
    assert res["missing_contracts"] == []


# --- FR-200.15: the checker polices this increment's own wiring -------------------------

def test_frydays_own_tree_is_clean():
    """FR-200.15 / AC-200.14: it gates from the first pass, and the increment's
    own build is that first run. RED until every orphan is dispositioned —
    which is the point (KH-3: the rule is never narrowed to fit the tree)."""
    res = dlc.check(root=REPO)
    assert res["verdict"] == "valid-pass", (
        f"orphan roles: {res['orphans']}; missing contracts: "
        f"{res['missing_contracts']}")
