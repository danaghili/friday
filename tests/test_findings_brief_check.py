"""Findings-brief grammar tests — U1 foundation (TECHNICAL_SOW_REBUILD US-12:
FR-63, FR-65; AC-16; the FR-42 structural PoC cap via the §7 pin
"PoC-or-informational discipline").

Contract: docs/contracts/findings-brief.md (cited on both sides — harden /
security / redteam / adopt / the tester's failure-path pass emit it;
tools/findings_brief_check.py + the document gate consume it).

The grammar in one breath: header tag
`findings-brief: source=harden|security|redteam|adopt|failure-path count=N`;
each finding
`## F-n — <title> (severity: act-now|before-growth|track|informational)`
with non-empty `evidence:` / `explained:` / `fixed-when:` lines; count must
equal the number of findings; the empty case (count=0) requires a non-empty
`## Checked` section saying what was examined. The PoC cap is structural:
`evidence: none — <reason>` is legal ONLY at severity informational; for
source=security|redteam, anything above informational must point at real
evidence — no PoC, nothing above informational.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks"))
import findings_brief_check  # noqa: E402
import _guard  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO, "tools", "findings_brief_check.py")


def make_finding(n=1, title="Session cookie missing HttpOnly", severity="act-now",
                 evidence="evidence: hooks/session.py:42 — PoC at docs/poc/f1.md",
                 explained="explained: anyone who can run script in the page can steal the login",
                 fixed_when="fixed-when: the cookie is set HttpOnly and the PoC no longer works") -> str:
    return (f"## F-{n} — {title} (severity: {severity})\n"
            f"{evidence}\n{explained}\n{fixed_when}\n")


def make_brief(*, source="security", findings=None, checked=None) -> str:
    findings = [make_finding()] if findings is None else findings
    text = f"findings-brief: source={source} count={len(findings)}\n\n"
    text += "\n".join(findings)
    if checked is not None:
        text += f"\n## Checked\n{checked}\n"
    return text


# --- valid shapes ---------------------------------------------------------------

def test_valid_brief_passes_every_source():
    for source in ("harden", "security", "redteam", "adopt", "failure-path"):
        res = findings_brief_check.check_text(make_brief(source=source))
        assert res["verdict"] == "valid-pass", (source, res)
        assert res["source"] == source
        assert res["count"] == 1


def test_empty_case_count_zero_with_checked_section():
    # FR-65 / FR-63: "no findings, here's what was checked" is first-class.
    res = findings_brief_check.check_text(make_brief(
        findings=[], checked="- every hook in hooks/ against the fail-open matrix\n- all tag-line parsers"))
    assert res["verdict"] == "valid-pass", res


def test_multiple_findings_pass():
    res = findings_brief_check.check_text(make_brief(
        findings=[make_finding(1), make_finding(2, severity="track"),
                  make_finding(3, severity="before-growth")]))
    assert res["verdict"] == "valid-pass", res
    assert res["count"] == 3


def test_informational_may_carry_evidence_none_with_reason():
    res = findings_brief_check.check_text(make_brief(findings=[make_finding(
        severity="informational",
        evidence="evidence: none — could not reproduce; pattern noted for the next pass")]))
    assert res["verdict"] == "valid-pass", res


# --- seeded malformed forms (AC-16) ----------------------------------------------

def _fails(text, needle):
    res = findings_brief_check.check_text(text)
    assert res["verdict"] == "valid-fail", res
    joined = " ".join(res["errors"]).lower()
    assert needle in joined, (needle, res["errors"])
    return res


def test_missing_header_fails():
    _fails(make_finding(), "findings-brief")


def test_unknown_source_fails():
    _fails(make_brief(source="vibes"), "source")


def test_count_mismatch_is_a_lie():
    text = "findings-brief: source=harden count=3\n\n" + make_finding()
    _fails(text, "count")


def test_empty_case_without_checked_section_fails():
    _fails(make_brief(findings=[]), "checked")


def test_empty_case_with_empty_checked_section_fails():
    _fails(make_brief(findings=[], checked=""), "checked")


def test_bad_severity_fails():
    _fails(make_brief(findings=[make_finding(severity="urgent")]), "f-1")


def test_missing_explained_fails():
    _fails(make_brief(findings=[make_finding(explained="")]), "explained")


def test_missing_fixed_when_fails():
    _fails(make_brief(findings=[make_finding(fixed_when="")]), "fixed-when")


def test_duplicate_finding_ids_fail():
    _fails(make_brief(findings=[make_finding(1), make_finding(1)]), "f-1")


def test_malformed_f_heading_never_slips_through():
    # An H2 that starts like a finding but doesn't parse is an error, not
    # tolerated prose — otherwise a bad heading silently drops a finding.
    text = ("findings-brief: source=harden count=1\n\n"
            "## F-1 — Broken thing\n"
            "evidence: x\nexplained: y\nfixed-when: z\n")
    _fails(text, "f-1")


# --- the structural PoC cap (FR-42 / §7 pin) --------------------------------------

def test_security_above_informational_without_evidence_fails():
    for source in ("security", "redteam"):
        res = findings_brief_check.check_text(make_brief(
            source=source, findings=[make_finding(evidence="evidence:")]))
        assert res["verdict"] == "valid-fail", (source, res)


def test_security_above_informational_with_evidence_none_fails():
    # The plausible-but-false finding: graded act-now, points at nothing.
    res = findings_brief_check.check_text(make_brief(
        source="redteam",
        findings=[make_finding(evidence="evidence: none — it just feels exploitable")]))
    assert res["verdict"] == "valid-fail"
    assert any("informational" in e.lower() for e in res["errors"]), res["errors"]


def test_security_informational_with_evidence_none_passes():
    res = findings_brief_check.check_text(make_brief(
        source="security",
        findings=[make_finding(severity="informational",
                               evidence="evidence: none — not reproducible this pass")]))
    assert res["verdict"] == "valid-pass", res


def test_harden_above_informational_still_needs_real_evidence():
    # FR-63 says every finding is evidenced; the none-form is an
    # informational-only concession for every source.
    res = findings_brief_check.check_text(make_brief(
        source="harden",
        findings=[make_finding(evidence="evidence: none — general unease")]))
    assert res["verdict"] == "valid-fail", res


# --- CLI + skeleton integration ---------------------------------------------------

def test_cli_valid_pass(tmp_path):
    p = tmp_path / "brief.md"
    p.write_text(make_brief(), encoding="utf-8")
    proc = subprocess.run([sys.executable, CHECKER, "--file", str(p)],
                          capture_output=True, text=True)
    out = json.loads(proc.stdout)
    assert out["verdict"] == "valid-pass"
    assert proc.returncode == 0


def test_cli_missing_file_is_valid_fail(tmp_path):
    proc = subprocess.run([sys.executable, CHECKER, "--file", str(tmp_path / "no.md")],
                          capture_output=True, text=True)
    out = json.loads(proc.stdout)
    assert out["verdict"] == "valid-fail"
    assert proc.returncode == 1


def test_bad_invocation_exits_2_with_no_verdict():
    proc = subprocess.run([sys.executable, CHECKER], capture_output=True, text=True)
    assert proc.returncode == 2
    assert not proc.stdout.strip()


def test_skeleton_consumes_the_checker(tmp_path):
    p = tmp_path / "brief.md"
    p.write_text(make_brief(findings=[make_finding(evidence="evidence:")]), encoding="utf-8")
    v = _guard.run_checker([sys.executable, CHECKER, "--file", str(p)])
    assert v["verdict"] == "valid-fail"
    assert _guard.decide(v, "block", "reason").kind == "block"
