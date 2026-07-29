"""Logic-core #5 — the K-rule verifier, driven by the TEST-07 mandated
adversarial corpus (not 'should work')."""
import subprocess

import pytest

import decisions
import verify_state as vst

TSOW = """# TSOW
- **FR-1** does the thing.
- **AC-1** it works.
- **S-1** no secrets in logs.
"""

CLAIMS = """<!-- FRIDAY-CLAIMS:BEGIN -->
stack: path:python3
non-goal: multi-user auth
<!-- FRIDAY-CLAIMS:END -->"""


def _state_block(state, extra=""):
    return ("<!-- FRIDAY-STATE:BEGIN -->\n"
            f"state: {state}\n"
            "tsow: docs/TECHNICAL_SOW.md\n"
            f"since: 2026-07-12T16:00:00Z\n{extra}"
            "<!-- FRIDAY-STATE:END -->")


REVIEW = """# Post-build review

<!-- FRIDAY-REVIEW:BEGIN -->
reviewer: friday-reviewer
iteration: 1
verdict: approved
spec-compliance: meets-spec
<!-- FRIDAY-REVIEW:END -->
"""

RELEASE_GATE = """# Release gate

<!-- FRIDAY-RELEASE-GATE:BEGIN -->
reviewer: friday-tester
suite: pass
build: pass
migration: n/a
<!-- FRIDAY-RELEASE-GATE:END -->
"""

COVERAGE = """# Requirement coverage vs TSOW

<!-- FRIDAY-DISPOSITIONS:BEGIN -->
disposition: FR-1 implemented — app/web.py
disposition: AC-1 implemented — tests/test_app.py
disposition: S-1 deferred — no log sink in v1; revisit with ops runbook (deferred per D-0001)
<!-- FRIDAY-DISPOSITIONS:END -->
"""


@pytest.fixture()
def proj(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "reviews").mkdir()
    (tmp_path / "docs" / "TECHNICAL_SOW.md").write_text(TSOW, encoding="utf-8")
    return tmp_path


def _write_claude(proj, state, extra=""):
    (proj / "CLAUDE.md").write_text(
        "# proj\n\n" + CLAIMS + "\n\n" + _state_block(state, extra), encoding="utf-8")


def _close_artifacts(proj):
    (proj / "docs" / "reviews" / "post-build-review.md").write_text(REVIEW, encoding="utf-8")
    (proj / "docs" / "reviews" / "release-gate.md").write_text(RELEASE_GATE, encoding="utf-8")
    (proj / "docs" / "reviews" / "coverage.md").write_text(COVERAGE, encoding="utf-8")


# (a) clean closed build — every K-rule satisfied, verdict ok.
def test_corpus_a_clean_close(proj):
    _write_claude(proj, "closed",
                  "last-verified: 2026-07-12 (close)\nrecord-status: verified\n")
    _close_artifacts(proj)
    decisions.append_entry(str(proj), title="t", decision="d", why="w", rejected="r")
    res = vst.verify_state(str(proj))
    assert res["ok"], res["failures"]
    assert res["state"] == "closed"


# (b) mid-build crash/compaction leaving build-in-progress — precision-first:
# an in-flight trail violates NOTHING blocking (K6 may warn).
def test_corpus_b_midbuild_crash_is_not_blocking(proj):
    _write_claude(proj, "build-in-progress")
    res = vst.verify_state(str(proj))
    assert res["ok"], res["failures"]
    assert all(f["severity"] != "blocking" for f in res["failures"])


# (c) capture-integrity: build-in-progress with ZERO decisions — K6 warns,
# never blocks (the floor-omission itself is the §6.7 diff's job, not K's).
def test_corpus_c_zero_decisions_warns_K6(proj):
    _write_claude(proj, "build-in-progress")
    res = vst.verify_state(str(proj))
    assert any(f["check"] == "K6" and f["severity"] == "warn" for f in res["failures"])
    decisions.append_entry(str(proj), title="t", decision="d", why="w", rejected="r")
    res2 = vst.verify_state(str(proj))
    assert not any(f["check"] == "K6" for f in res2["failures"])


# Close-state K-rules fire exactly on their intended gap and no other.
def test_close_without_review_fails_K2_only_there(proj):
    _write_claude(proj, "closed",
                  "last-verified: 2026-07-12 (close)\nrecord-status: verified\n")
    _close_artifacts(proj)
    (proj / "docs" / "reviews" / "post-build-review.md").unlink()
    res = vst.verify_state(str(proj))
    assert not res["ok"]
    assert {f["check"] for f in res["failures"] if f["severity"] == "blocking"} == {"K2"}


def test_close_without_release_gate_fails_K3(proj):
    _write_claude(proj, "closed",
                  "last-verified: 2026-07-12 (close)\nrecord-status: verified\n")
    _close_artifacts(proj)
    (proj / "docs" / "reviews" / "release-gate.md").unlink()
    res = vst.verify_state(str(proj))
    assert {f["check"] for f in res["failures"] if f["severity"] == "blocking"} == {"K3"}


def test_close_without_dirty_bit_fails_K5(proj):
    _write_claude(proj, "closed")
    _close_artifacts(proj)
    res = vst.verify_state(str(proj))
    assert "K5" in {f["check"] for f in res["failures"]}


def test_uncovered_requirement_fails_K7(proj):
    _write_claude(proj, "closed",
                  "last-verified: 2026-07-12 (close)\nrecord-status: verified\n")
    _close_artifacts(proj)
    (proj / "docs" / "reviews" / "coverage.md").write_text(
        COVERAGE.replace("disposition: S-1 deferred — no log sink in v1; revisit with ops runbook (deferred per D-0001)\n", ""),
        encoding="utf-8")
    res = vst.verify_state(str(proj))
    assert any(f["check"] == "K7" and "S-1" in f["detail"] for f in res["failures"])


# K4 — closed vocabulary; no invented status strings, ever.
def test_invented_state_fails_K4(proj):
    _write_claude(proj, "basically-done")
    res = vst.verify_state(str(proj))
    assert any(f["check"] == "K4" and f["severity"] == "blocking" for f in res["failures"])


# K0 — the init/TSOW-substrate gate content (surviving Strategist checks).
def test_missing_tsow_fails_K0(proj):
    _write_claude(proj, "build-in-progress")
    (proj / "docs" / "TECHNICAL_SOW.md").unlink()
    res = vst.verify_state(str(proj))
    assert any(f["check"] == "K0" and f["severity"] == "blocking" for f in res["failures"])


# No FRIDAY-STATE block at all — not engaged; never a false block.
def test_no_state_block_is_skipped(proj):
    (proj / "CLAUDE.md").write_text("# proj\n\n" + CLAIMS + "\n", encoding="utf-8")
    res = vst.verify_state(str(proj))
    assert res["ok"] and res.get("skipped")


# tsow-approved (D-0105 wired the producer): the bootstrap crash window. A
# stub CLAUDE.md holding ONLY the state block is the expected shape here —
# FRIDAY-CLAIMS arrives later with the Strategist, so K0 must not demand it.
def test_tsow_approved_stub_claude_md_passes(proj):
    (proj / "CLAUDE.md").write_text(
        "# proj\n\n" + _state_block("tsow-approved"), encoding="utf-8")
    res = vst.verify_state(str(proj))
    assert res["ok"], res["failures"]
    assert res["state"] == "tsow-approved"


def test_tsow_approved_without_tsow_file_fails_K0(proj):
    (proj / "CLAUDE.md").write_text(
        "# proj\n\n" + _state_block("tsow-approved"), encoding="utf-8")
    (proj / "docs" / "TECHNICAL_SOW.md").unlink()
    res = vst.verify_state(str(proj))
    assert any(f["check"] == "K0" and f["severity"] == "blocking"
               for f in res["failures"])
