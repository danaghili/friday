"""The brief carve-outs in review_format_sentinel.

Interim (DF-021 / D-0009): `docs/reviews/interim-*.md` files are interim
findings-brief artifacts — the seam plan mandates both the path and the
grammar — so the sentinel validates them with tools/findings_brief_check.py
instead of the FRIDAY-REVIEW envelope, bounces on a malformed brief, and
NEVER arms the Stop-gate sentinel for them (their consumer is the
disposition step, not the session close).

Failure-path (INC-106 S-106.1 / D-1061): `docs/reviews/findings-*.md` is the
failure-path pass's contract-mandated landing name (the consumption rule,
docs/contracts/findings-brief.md), and before the carve-out a fresh Write of
it bounced off the envelope check with decision:block — a hook standing
exactly where S-106.1 promises none. Same class, same treatment as interim.

Non-brief review files keep the envelope check unchanged.
"""
import json
import os
import subprocess
import sys

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VALID_BRIEF = """findings-brief: source=harden count=1

## F-1 — Loose bolt (severity: track)
evidence: hooks/x.py:3
explained: the bolt is loose
fixed-when: the bolt is tight
"""


def _proj(tmp_path):
    root = tmp_path / "proj"
    (root / "docs" / "reviews").mkdir(parents=True)
    (root / "CLAUDE.md").write_text(
        "# proj\n\n<!-- FRIDAY-STATE:BEGIN -->\nstate: build-in-progress\n"
        "<!-- FRIDAY-STATE:END -->\n", encoding="utf-8")
    return root


def _write_event(proj, rel, text):
    p = proj / rel
    p.write_text(text, encoding="utf-8")
    return {"hook_event_name": "PostToolUse", "tool_name": "Write",
            "cwd": str(proj), "tool_input": {"file_path": str(p)}}


def _run(proj, event):
    proc = subprocess.run(
        [sys.executable, os.path.join(BUILD_ROOT, "hooks", "review_format_sentinel.py"),
         BUILD_ROOT],
        input=json.dumps(event), capture_output=True, text=True, cwd=str(proj))
    assert proc.returncode == 0
    return proc


def test_valid_interim_brief_passes_silently_and_never_arms(tmp_path):
    proj = _proj(tmp_path)
    p = _run(proj, _write_event(proj, "docs/reviews/interim-u1-gate.md", VALID_BRIEF))
    assert p.stdout.strip() == ""
    assert not (proj / ".friday" / "review-format-invalid").exists()


def test_malformed_interim_brief_bounces_but_never_arms(tmp_path):
    proj = _proj(tmp_path)
    p = _run(proj, _write_event(proj, "docs/reviews/interim-u1-review.md",
                                "just some prose, no header\n"))
    out = json.loads(p.stdout)
    assert out["decision"] == "block"
    assert "findings-brief" in out["reason"]
    assert not (proj / ".friday" / "review-format-invalid").exists()


def test_interim_pass_disarms_a_stale_arming_for_the_same_file(tmp_path):
    proj = _proj(tmp_path)
    (proj / ".friday").mkdir()
    (proj / ".friday" / "review-format-invalid").write_text(
        "docs/reviews/interim-u1-gate.md\nstrict\nstale arming\n", encoding="utf-8")
    _run(proj, _write_event(proj, "docs/reviews/interim-u1-gate.md", VALID_BRIEF))
    assert not (proj / ".friday" / "review-format-invalid").exists()


def test_valid_failure_path_brief_passes_silently_and_never_arms(tmp_path):
    proj = _proj(tmp_path)
    brief = VALID_BRIEF.replace("source=harden", "source=failure-path")
    p = _run(proj, _write_event(proj, "docs/reviews/findings-failure-path.md", brief))
    assert p.stdout.strip() == ""
    assert not (proj / ".friday" / "review-format-invalid").exists()


def test_malformed_failure_path_brief_bounces_but_never_arms(tmp_path):
    proj = _proj(tmp_path)
    p = _run(proj, _write_event(proj, "docs/reviews/findings-failure-path.md",
                                "just some prose, no header\n"))
    out = json.loads(p.stdout)
    assert out["decision"] == "block"
    assert "findings-brief" in out["reason"]
    assert not (proj / ".friday" / "review-format-invalid").exists()


def test_non_interim_review_file_still_gets_the_envelope_check(tmp_path):
    proj = _proj(tmp_path)
    p = _run(proj, _write_event(proj, "docs/reviews/BUILD-9-review.md", "bad\n"))
    out = json.loads(p.stdout)
    assert out["decision"] == "block"
    assert "FRIDAY-REVIEW" in out["reason"]
    assert (proj / ".friday" / "review-format-invalid").is_file()  # unchanged path
