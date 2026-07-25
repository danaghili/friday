"""Hook-level tests: TEST-08 (SubagentStop identity landmine, ISSUE-007),
Channel-A capture gating, stop-gate block/clear, mirror/cleanup smoke,
review-format R-checks."""
import json
import os
import subprocess

import pytest

import decisions
import verify_review_format as vrf

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLAIMS = ("<!-- FRIDAY-CLAIMS:BEGIN -->\nstack: path:python3\n"
          "<!-- FRIDAY-CLAIMS:END -->")


def _claude_md(state):
    return ("# proj\n\n" + CLAIMS + "\n\n<!-- FRIDAY-STATE:BEGIN -->\n"
            f"state: {state}\ntsow: docs/TECHNICAL_SOW.md\n"
            "<!-- FRIDAY-STATE:END -->\n")


@pytest.fixture()
def proj(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "docs" / "reviews").mkdir(parents=True)
    (tmp_path / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    # `closed` with no close artifacts = a BROKEN record (K2/K3/K5 fire).
    (tmp_path / "CLAUDE.md").write_text(_claude_md("closed"), encoding="utf-8")
    return tmp_path


def run_hook(name, event, cwd):
    return subprocess.run(
        ["python3", os.path.join(BUILD_ROOT, "hooks", name), BUILD_ROOT],
        input=json.dumps(event), capture_output=True, text=True, cwd=str(cwd))


def _sentinel(proj):
    return proj / ".friday" / "state-inconsistent"


# --- TEST-08: the identity landmine --------------------------------------------------

def _stop_event(proj, agent_type=None):
    e = {"hook_event_name": "SubagentStop", "cwd": str(proj), "session_id": "s1"}
    if agent_type is not None:
        e["agent_type"] = agent_type
    return e


def test_a_correct_type_arms_on_broken_record(proj):
    p = run_hook("state_sentinel.py", _stop_event(proj, "friday-closer"), proj)
    assert p.returncode == 0
    assert _sentinel(proj).is_file()


def test_b_foreign_type_never_arms(proj):
    p = run_hook("state_sentinel.py", _stop_event(proj, "friday-strategist"), proj)
    assert p.returncode == 0
    assert not _sentinel(proj).exists()


def test_b2_foreign_type_never_clears_an_armed_gate(proj):
    """Reproduce the 2026-07-10 incident shape: an armed gate + a FOREIGN
    agent's idle event over a now-clean record must NOT release the gate."""
    (proj / "CLAUDE.md").write_text(_claude_md("build-in-progress"), encoding="utf-8")
    _sentinel(proj).parent.mkdir(exist_ok=True)
    _sentinel(proj).write_text("armed\n", encoding="utf-8")
    p = run_hook("state_sentinel.py", _stop_event(proj, "friday-strategist"), proj)
    assert p.returncode == 0
    assert _sentinel(proj).is_file(), "a foreign event must never clear an armed gate"


def test_c_typeless_proceeds_per_declared_posture(proj):
    """Typeless events proceed (verify-first: K-rules are precision-first on
    partial state, established by the TEST-07 corpus)."""
    p = run_hook("state_sentinel.py", _stop_event(proj, None), proj)
    assert p.returncode == 0
    assert _sentinel(proj).is_file()   # broken record + typeless → verifies + arms
    (proj / "CLAUDE.md").write_text(_claude_md("build-in-progress"), encoding="utf-8")
    p2 = run_hook("state_sentinel.py", _stop_event(proj, None), proj)
    assert p2.returncode == 0
    assert not _sentinel(proj).exists()  # verified-clean typeless run may self-clear


def test_stop_gate_blocks_then_releases(proj):
    run_hook("state_sentinel.py", _stop_event(proj, "friday-closer"), proj)
    assert _sentinel(proj).is_file()
    p = run_hook("state_stop_gate.py", {"hook_event_name": "Stop", "cwd": str(proj)}, proj)
    out = json.loads(p.stdout)
    assert out["decision"] == "block" and "INCONSISTENT" in out["reason"]
    (proj / "CLAUDE.md").write_text(_claude_md("build-in-progress"), encoding="utf-8")
    p2 = run_hook("state_stop_gate.py", {"hook_event_name": "Stop", "cwd": str(proj)}, proj)
    assert p2.stdout.strip() == "" and not _sentinel(proj).exists()


# --- Channel A: decision_capture gating -------------------------------------------------

def _ask_event(proj, question, response=None):
    return {"hook_event_name": "PostToolUse", "cwd": str(proj),
            "tool_name": "AskUserQuestion", "session_id": "s1",
            "tool_input": {"questions": [{
                "question": question, "header": "Decision",
                "options": [{"label": "redis"}, {"label": "in-memory dict"}]}]},
            "tool_response": response or {"answer": "redis"}}


DECISION_ASK = ("[FRIDAY-DECISION] Session store choice\n"
                "decision: which session store the API uses\n"
                "why: survives restarts; already in stack\n"
                "rejected: in-memory dict (loses sessions)\n"
                "floor: schema-data\nweight: two-way\n")


def test_decision_ask_shape_fires_the_write(proj):
    p = run_hook("decision_capture.py", _ask_event(proj, DECISION_ASK), proj)
    assert p.returncode == 0, p.stderr
    parsed = decisions.parse_file(str(proj / "docs" / "DECISIONS.md"))
    assert parsed["ok"], parsed["errors"]
    [e] = parsed["entries"]
    assert e["channel"] == "pm-ratified"
    assert e["floor"] == "schema-data" and e["weight"] == "one-way"  # floor override
    assert "redis" in e["decision"]
    assert "in-memory dict" in e["rejected"]


def test_ordinary_question_never_captures(proj):
    p = run_hook("decision_capture.py",
                 _ask_event(proj, "Should I also update the README?"), proj)
    assert p.returncode == 0
    assert not (proj / "docs" / "DECISIONS.md").exists()


# --- ask mirror / cleanup smoke -----------------------------------------------------------

def test_mirror_then_cleanup_roundtrip(proj):
    pre = {"hook_event_name": "PreToolUse", "cwd": str(proj),
           "tool_name": "AskUserQuestion", "session_id": "sX",
           "tool_input": {"questions": [{"question": "Pick one", "header": "Q",
                                         "options": [{"label": "a"}]}]}}
    run_hook("substrate_ask_mirror.py", pre, proj)
    asks = list((proj / ".friday" / "asks").glob("ask-*-request.md"))
    assert len(asks) == 1
    post = {"hook_event_name": "PostToolUse", "cwd": str(proj),
            "tool_name": "AskUserQuestion", "session_id": "sX"}
    run_hook("substrate_ask_cleanup.py", post, proj)
    assert not list((proj / ".friday" / "asks").glob("ask-*-request.md"))
    journal = (proj / ".friday" / "journal.jsonl").read_text(encoding="utf-8")
    assert "question-answered" in journal


# --- review-format checks -------------------------------------------------------------------

GOOD_REVIEW = """# review

<!-- FRIDAY-REVIEW:BEGIN -->
reviewer: friday-reviewer
iteration: 1
verdict: changes-required
spec-compliance: meets-spec
finding: 🔴 1 src/x.py:9 — broken thing
<!-- FRIDAY-REVIEW:END -->

## 🔴-1 broken thing

detail.
"""


def test_review_format_good_and_empty_case(tmp_path):
    p = tmp_path / "r.md"
    p.write_text(GOOD_REVIEW, encoding="utf-8")
    assert vrf.verify_file(str(p))["ok"]
    p.write_text(GOOD_REVIEW.replace("changes-required", "approved")
                 .replace("finding: 🔴 1 src/x.py:9 — broken thing\n", "")
                 .replace("## 🔴-1 broken thing\n\ndetail.\n", ""), encoding="utf-8")
    assert vrf.verify_file(str(p))["ok"]   # zero findings + approving = valid empty case


def test_review_format_red_under_approved_is_R5(tmp_path):
    p = tmp_path / "r.md"
    p.write_text(GOOD_REVIEW.replace("changes-required", "approved"), encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert not res["ok"]
    assert any(f["check"] == "R5" for f in res["failures"])


def test_review_format_missing_spec_compliance_is_R3(tmp_path):
    p = tmp_path / "r.md"
    p.write_text(GOOD_REVIEW.replace("spec-compliance: meets-spec\n", ""), encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert any(f["check"] == "R3" and "spec-compliance" in f["detail"]
               for f in res["failures"])


def test_review_sentinel_bounces_and_gate_blocks(proj):
    bad = proj / "docs" / "reviews" / "post-build-review.md"
    bad.write_text(GOOD_REVIEW.replace("changes-required", "approved"), encoding="utf-8")
    event = {"hook_event_name": "PostToolUse", "cwd": str(proj), "tool_name": "Write",
             "tool_input": {"file_path": str(bad), "content": "x"}}
    p = run_hook("review_format_sentinel.py", event, proj)
    assert json.loads(p.stdout)["decision"] == "block"
    assert (proj / ".friday" / "review-format-invalid").is_file()
    p2 = run_hook("review_format_stop_gate.py",
                  {"hook_event_name": "Stop", "cwd": str(proj)}, proj)
    assert json.loads(p2.stdout)["decision"] == "block"
    bad.write_text(GOOD_REVIEW, encoding="utf-8")   # fix it
    p3 = run_hook("review_format_stop_gate.py",
                  {"hook_event_name": "Stop", "cwd": str(proj)}, proj)
    assert p3.stdout.strip() == ""
    assert not (proj / ".friday" / "review-format-invalid").exists()


# --- DF-015: envelope-dispatching verifier (release-gate / dispositions / contract) ---------

# FRIDAY-RELEASE-GATE — the tester's release verdict (agents/roles/tester.md, harden.md
# Step 3). suite/build/migration each present exactly once with a closed value.
GOOD_GATE = """# release gate

<!-- FRIDAY-RELEASE-GATE:BEGIN -->
reviewer: friday-tester
suite: pass
build: pass
migration: n/a
<!-- FRIDAY-RELEASE-GATE:END -->

full suite: 214 passed.
"""

# FRIDAY-DISPOSITIONS — the coverage ledger (one disposition line per TSOW ID). Line-shape
# only here; set-closure against the TSOW is verify_coverage.py's job.
GOOD_DISPO = """# coverage

<!-- FRIDAY-DISPOSITIONS:BEGIN -->
disposition: FR-1 implemented — src/x.py:9
disposition: NFR-2 deferred — out of scope this cut
<!-- FRIDAY-DISPOSITIONS:END -->
"""


def test_release_gate_good_and_empty_case(tmp_path):
    p = tmp_path / "release-gate.md"
    p.write_text(GOOD_GATE, encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert res["ok"] and not res["failures"], res   # dispatched to the gate grammar, clean
    # empty block: the defined empty case is INVALID — the gate must carry a verdict.
    p.write_text("# release gate\n\n<!-- FRIDAY-RELEASE-GATE:BEGIN -->\n"
                 "<!-- FRIDAY-RELEASE-GATE:END -->\n", encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert not res["ok"]
    assert sum(f["check"] == "G3" for f in res["failures"]) == 3  # suite/build/migration


def test_release_gate_bad_value_is_G3(tmp_path):
    p = tmp_path / "release-gate.md"
    p.write_text(GOOD_GATE.replace("suite: pass", "suite: maybe"), encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert not res["ok"]
    assert any(f["check"] == "G3" and "suite" in f["detail"] for f in res["failures"])


def test_release_gate_unknown_key_is_G2(tmp_path):
    p = tmp_path / "release-gate.md"
    p.write_text(GOOD_GATE.replace("suite: pass\n", "suite: pass\nbogus: x\n"),
                 encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert not res["ok"]
    assert any(f["check"] == "G2" for f in res["failures"])


def test_release_gate_duplicate_required_key_is_G3(tmp_path):
    p = tmp_path / "release-gate.md"
    p.write_text(GOOD_GATE.replace("suite: pass\n", "suite: pass\nsuite: fail\n"),
                 encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert not res["ok"]
    assert any(f["check"] == "G3" and "exactly once" in f["detail"]
               for f in res["failures"])


def test_dispositions_good_and_empty_case(tmp_path):
    p = tmp_path / "coverage.md"
    p.write_text(GOOD_DISPO, encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert res["ok"] and not res["failures"], res
    # empty block: the defined empty case is VALID — nothing to cover (taglines convention,
    # verify_coverage.py). A present-but-empty ledger is not malformed.
    p.write_text("# coverage\n\n<!-- FRIDAY-DISPOSITIONS:BEGIN -->\n"
                 "<!-- FRIDAY-DISPOSITIONS:END -->\n", encoding="utf-8")
    assert vrf.verify_file(str(p))["ok"]


def test_dispositions_dotted_increment_ids_parse(tmp_path):
    # increment IDs are dotted (FR-1.1, AC-1.7 — INC-001); the grammar here
    # must stay in lockstep with verify_coverage.py's, which closes over
    # TSOW + increments
    p = tmp_path / "coverage.md"
    p.write_text(GOOD_DISPO.replace(
        "disposition: FR-1 implemented — src/x.py:9",
        "disposition: FR-1.1 implemented — hooks/x.py steering spec\n"
        "disposition: AC-1.7 implemented — fixture run evidence\n"
        "disposition: S-1.3 deferred — rides the live run (D-0075)"),
        encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert res["ok"] and not res["failures"], res


def test_dispositions_malformed_line_is_D2(tmp_path):
    p = tmp_path / "coverage.md"
    # bad state token ("done" is not implemented|deferred)
    p.write_text(GOOD_DISPO.replace("FR-1 implemented", "FR-1 done"), encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert not res["ok"] and any(f["check"] == "D2" for f in res["failures"])
    # a non-disposition typed line inside the block is also D2
    p.write_text(GOOD_DISPO.replace("disposition: FR-1 implemented — src/x.py:9\n",
                                    "note: not a disposition\n"), encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert not res["ok"] and any(f["check"] == "D2" for f in res["failures"])


def test_no_known_envelope_warns_sweep_blocks_strict(tmp_path):
    p = tmp_path / "fix-round-ledger.md"
    p.write_text("# fix round 1\n\nreloc notes, no verdict envelope here.\n",
                 encoding="utf-8")
    sweep = vrf.verify_file(str(p))                       # sweep (Edit): warn, not blocking
    assert sweep["ok"]
    warn = [f for f in sweep["failures"] if f["check"] == "R1"]
    assert warn and warn[0]["severity"] == "warn"
    assert "docs/hardening/" in warn[0]["detail"] and "typed verdict" in warn[0]["detail"]
    strict = vrf.verify_file(str(p), strict_missing=True)  # Write: blocking
    assert not strict["ok"]
    block = [f for f in strict["failures"] if f["check"] == "R1"]
    assert block and block[0]["severity"] == "blocking"
    assert "docs/hardening/" in block[0]["detail"]


def test_combined_families_validate_each_grammar(tmp_path):
    # Field shape (dogfood-tether coverage.md / release-gate.md): a FRIDAY-REVIEW
    # verdict envelope preceding a typed data block is coherent, NOT ambiguous —
    # each declared family is validated against its own grammar.
    p = tmp_path / "coverage.md"
    p.write_text(GOOD_REVIEW + "\n" + GOOD_DISPO, encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert res["ok"] and not res["failures"], res   # both families pass, clean
    # A bad value in one family fails with THAT family's check (here G3), never an
    # ambiguity error — the other family is unaffected.
    p.write_text(GOOD_REVIEW + "\n" + GOOD_GATE.replace("suite: pass", "suite: maybe"),
                 encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert not res["ok"]
    assert any(f["check"] == "G3" for f in res["failures"])
    assert not any("ambiguous" in f["detail"] for f in res["failures"])


def test_duplicate_same_family_still_blocks(tmp_path):
    # Two REVIEW envelopes + one DISPOSITIONS block: the duplicated family blocks on
    # its own one-pair check (R1) even with another family's markers present, while
    # that other family still validates independently.
    p = tmp_path / "coverage.md"
    p.write_text(GOOD_REVIEW + "\n" + GOOD_REVIEW + "\n" + GOOD_DISPO, encoding="utf-8")
    res = vrf.verify_file(str(p))
    assert not res["ok"]
    assert any(f["check"] == "R1" and "BEGIN/END pair" in f["detail"]
               for f in res["failures"])
