"""Change-trail grammar tests — U1 foundation (TECHNICAL_SOW_REBUILD US-12:
FR-62 one shape three sizes, FR-65 empty case; AC-16 seeded-malformed refusal;
§7 pin "Trail grammar at three sizes").

Contract: docs/contracts/change-trail.md (cited on both sides — the lanes
emit it, tools/trail_check.py + guard #6 consume it).

The grammar in one breath: a trail opens with
`trail: lane=bug|patch|feature id=<token> date=<ISO8601>`, then three
sections in order — ## Asked (non-empty), ## Decisions (either `- D-NNNN —
<title>` references into docs/DECISIONS.md or exactly the empty-case line
`decisions: none — change fully specified by the ask`), ## Proof (at least
one `proof:` line quoting real output; never empty — proof is the point) —
plus exactly one `changelog:` line. Decision references are POINTERS into
the single decision log, never embedded copies (two copies drift).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks"))
import trail_check  # noqa: E402
import _guard  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO, "tools", "trail_check.py")

EMPTY_DECISIONS = "decisions: none — change fully specified by the ask"


def make_trail(*, lane="bug", id_="BUG-001", date="2026-07-14T12:00:00Z",
               asked="The suite crashed on empty input.",
               decisions="- D-0011 — Guard timeout raised to 10s",
               proof="proof: `python3 -m pytest tests/ -q` → 145 passed",
               changelog="changelog: fixed empty-input crash in trail parser") -> str:
    return (f"trail: lane={lane} id={id_} date={date}\n\n"
            f"## Asked\n{asked}\n\n"
            f"## Decisions\n{decisions}\n\n"
            f"## Proof\n{proof}\n\n"
            f"{changelog}\n")


DECISIONS_LOG = """# Decisions — testproj

## D-0011 — Guard timeout raised to 10s
**When:** 2026-07-14T10:00:00Z · **Channel:** model-autonomous · **Weight:** two-way · **Floor:** none
- **Decision:** x
- **Why:** y
- **Rejected:** z
"""


# --- the valid shapes: three lanes, one grammar (§7 pin) -----------------------

def test_valid_trail_passes_each_lane():
    for lane, id_ in (("bug", "BUG-001"), ("patch", "PATCH-003"), ("feature", "INC-002")):
        res = trail_check.check_text(make_trail(lane=lane, id_=id_))
        assert res["verdict"] == "valid-pass", (lane, res)
        assert res["lane"] == lane
        assert res["id"] == id_


def test_empty_decisions_case_is_first_class():
    # FR-65 / AC-16: the grammar's defined empty case — no decisions arose.
    res = trail_check.check_text(make_trail(decisions=EMPTY_DECISIONS))
    assert res["verdict"] == "valid-pass", res


def test_date_only_iso_accepted():
    res = trail_check.check_text(make_trail(date="2026-07-14"))
    assert res["verdict"] == "valid-pass", res


def test_multiple_decision_refs_and_proof_lines_pass():
    res = trail_check.check_text(make_trail(
        decisions="- D-0011 — Guard timeout raised to 10s\n- D-0012 — Second call",
        proof="proof: pytest → 145 passed\nproof: manual run → exit 0"))
    assert res["verdict"] == "valid-pass", res


# --- seeded malformed forms are refused with plain-words reasons (AC-16) -------

def _fails(text, needle, **kw):
    res = trail_check.check_text(text, **kw)
    assert res["verdict"] == "valid-fail", res
    joined = " ".join(res["errors"]).lower()
    assert needle in joined, (needle, res["errors"])
    return res


def test_missing_trail_header_fails():
    _fails("## Asked\nx\n\n## Decisions\n" + EMPTY_DECISIONS +
           "\n\n## Proof\nproof: ok\n\nchangelog: y\n", "trail:")


def test_bad_lane_fails():
    _fails(make_trail(lane="hotfix"), "lane")


def test_bad_date_fails():
    _fails(make_trail(date="last tuesday"), "date")


def test_missing_asked_content_fails():
    _fails(make_trail(asked=""), "asked")


def test_missing_proof_section_fails():
    text = (f"trail: lane=bug id=B-1 date=2026-07-14\n\n"
            f"## Asked\nx\n\n## Decisions\n{EMPTY_DECISIONS}\n\nchangelog: y\n")
    _fails(text, "proof")


def test_empty_proof_fails_proof_is_the_point():
    _fails(make_trail(proof=""), "proof")


def test_prose_only_proof_fails():
    # A Proof section with prose but no `proof:` tag line is not proof.
    _fails(make_trail(proof="it works, trust me"), "proof")


def test_missing_changelog_fails():
    _fails(make_trail(changelog=""), "changelog")


def test_two_changelog_lines_fail():
    _fails(make_trail(changelog="changelog: a\nchangelog: b"), "changelog")


def test_decisions_section_with_junk_fails():
    _fails(make_trail(decisions="we decided some stuff informally"), "decision")


def test_sentinel_coexisting_with_refs_fails():
    _fails(make_trail(decisions=EMPTY_DECISIONS + "\n- D-0011 — Guard timeout raised to 10s"),
           "decision")


def test_sections_out_of_order_fail():
    text = (f"trail: lane=bug id=B-1 date=2026-07-14\n\n"
            f"## Decisions\n{EMPTY_DECISIONS}\n\n## Asked\nx\n\n"
            f"## Proof\nproof: ok\n\nchangelog: y\n")
    _fails(text, "order")


def test_errors_are_plain_words():
    # NFR-1: a stranger must be able to act on the message — every error
    # names the part of the trail it's about.
    res = trail_check.check_text("not a trail at all")
    assert res["verdict"] == "valid-fail"
    assert res["errors"], res
    for err in res["errors"]:
        assert not err.startswith("Traceback"), err


# --- decision-log cross-check (--decisions-log): lie vs unreadable -------------

def test_referenced_decision_found_in_log_passes():
    res = trail_check.check_text(make_trail(), decisions_text=DECISIONS_LOG)
    assert res["verdict"] == "valid-pass", res


def test_referenced_decision_absent_from_readable_log_is_a_lie():
    res = trail_check.check_text(
        make_trail(decisions="- D-9999 — Never happened"),
        decisions_text=DECISIONS_LOG)
    assert res["verdict"] == "valid-fail"
    assert any("D-9999" in e for e in res["errors"]), res["errors"]


def test_unreadable_log_degrades_to_structural_only():
    # Fail-open doctrine: an unreadable log is not a provable lie — the
    # checker notes the degradation instead of manufacturing a block.
    res = trail_check.check_text(make_trail(), decisions_text=None,
                                 decisions_log_error="no such file")
    assert res["verdict"] == "valid-pass"
    assert "not cross-checked" in res["summary"], res


# --- CLI + skeleton integration: the verdict rides the frozen shape ------------

def test_cli_valid_pass(tmp_path):
    p = tmp_path / "trail.md"
    p.write_text(make_trail(), encoding="utf-8")
    proc = subprocess.run([sys.executable, CHECKER, "--file", str(p)],
                          capture_output=True, text=True)
    out = json.loads(proc.stdout)
    assert out["verdict"] == "valid-pass"
    assert proc.returncode == 0


def test_cli_missing_file_is_valid_fail_not_crash(tmp_path):
    # Guard #6's whole point: a close without its trail. The absent file IS
    # the provable failure, not a checker malfunction.
    proc = subprocess.run([sys.executable, CHECKER, "--file", str(tmp_path / "nope.md")],
                          capture_output=True, text=True)
    out = json.loads(proc.stdout)
    assert out["verdict"] == "valid-fail"
    assert proc.returncode == 1


def test_cli_cross_check_flag(tmp_path):
    trail = tmp_path / "trail.md"
    trail.write_text(make_trail(decisions="- D-9999 — Never happened"), encoding="utf-8")
    log = tmp_path / "DECISIONS.md"
    log.write_text(DECISIONS_LOG, encoding="utf-8")
    proc = subprocess.run([sys.executable, CHECKER, "--file", str(trail),
                           "--decisions-log", str(log)],
                          capture_output=True, text=True)
    out = json.loads(proc.stdout)
    assert out["verdict"] == "valid-fail"


def test_bad_invocation_exits_2_with_no_verdict():
    proc = subprocess.run([sys.executable, CHECKER], capture_output=True, text=True)
    assert proc.returncode == 2
    assert not proc.stdout.strip()  # no verdict on stdout → guard sees no-verdict


def test_skeleton_consumes_the_checker(tmp_path):
    # End-to-end through the frozen skeleton: run_checker() must accept the
    # verdict shape, and decide() must block a block-tier guard on it.
    good = tmp_path / "good.md"
    good.write_text(make_trail(), encoding="utf-8")
    v = _guard.run_checker([sys.executable, CHECKER, "--file", str(good)])
    assert v["verdict"] == "valid-pass"
    assert _guard.decide(v, "block", "x").kind == "allow"

    v = _guard.run_checker([sys.executable, CHECKER, "--file", str(tmp_path / "absent.md")])
    assert v["verdict"] == "valid-fail"
    action = _guard.decide(v, "block", _guard.block_message(
        "closing this change without its trail",
        "every change leaves a three-part record; none was found",
        "write the trail (see docs/contracts/change-trail.md) and close again",
        "record a decision via tools/decisions_append.py explaining why no trail applies"))
    assert action.kind == "block"
