"""INC-008 FR-8.4 / AC-8.4 / Pin #1 — the agent judge's typed envelope + checker.

Test-first. The judge emits a strict, machine-checkable envelope — one verdict
per finding {location, metric+amount, justified|unjustified, standard-cited,
reason, floor}. It is a SIBLING of the findings-brief (a disposition axis, not a
severity axis), built on the same structural pattern and REUSING the tagline
grammar (Pin #1). Like the findings brief it: states its own count (a header
that lies is refused), makes the count=0 empty case first-class (a `## Checked`
section is required), and never silently drops a malformed finding.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import maintainability_envelope_check as ec  # noqa: E402


def _env(count, *findings, armed="false", source="harden", checked=None):
    head = f"maintainability-envelope: source={source} count={count} armed={armed}\n\n"
    body = "\n\n".join(findings)
    tail = f"\n\n## Checked\n{checked}\n" if checked else "\n"
    return head + body + tail


_JUSTIFIED = (
    "## M-1 — complexity 37 > 15 @ tools/trail_check.py:102:check_text "
    "(disposition: justified)\n"
    "standard: coding-standards.md §Complexity — verifier scripts are inherently branchy\n"
    "reason: a single-pass token checker; splitting would scatter one cohesive scan\n"
    "floor: none"
)
_UNJUSTIFIED = (
    "## M-2 — param-count 14 > 6 @ tools/decisions.py:265:append_entry "
    "(disposition: unjustified)\n"
    "standard: coding-standards.md §Size — parameter count <= 6\n"
    "reason: collapse the 14 keyword args into a dataclass; no reason to exceed the bar\n"
    "floor: none"
)


def _v(text):
    return ec.check_text(text)["verdict"]


def test_valid_envelope_passes():
    assert _v(_env(2, _JUSTIFIED, _UNJUSTIFIED)) == "valid-pass"


def test_empty_case_needs_checked_section():
    assert _v(_env(0, checked="measured tools/ + hooks/ against all six bars")) == "valid-pass"
    assert _v(_env(0)) == "valid-fail"          # count=0 but no Checked section


def test_count_must_be_truthful():
    assert _v(_env(5, _JUSTIFIED, _UNJUSTIFIED)) == "valid-fail"   # says 5, holds 2


def test_missing_field_fails():
    no_reason = (
        "## M-1 — complexity 37 > 15 @ f.py:1:x (disposition: justified)\n"
        "standard: coding-standards.md §Complexity — reason omitted on purpose\n"
        "floor: none"
    )
    assert _v(_env(1, no_reason)) == "valid-fail"


def test_bad_disposition_fails():
    bad = (
        "## M-1 — complexity 37 > 15 @ f.py:1:x (disposition: maybe)\n"
        "standard: s\nreason: r\nfloor: none"
    )
    assert _v(_env(1, bad)) == "valid-fail"


def test_bad_floor_category_fails():
    bad = (
        "## M-1 — complexity 37 > 15 @ f.py:1:x (disposition: justified)\n"
        "standard: s\nreason: r\nfloor: kinda-sensitive"
    )
    assert _v(_env(1, bad)) == "valid-fail"


def test_unknown_metric_fails():
    bad = (
        "## M-1 — cyclomatic 37 > 15 @ f.py:1:x (disposition: justified)\n"
        "standard: s\nreason: r\nfloor: none"
    )
    assert _v(_env(1, bad)) == "valid-fail"


def test_malformed_finding_is_not_silently_dropped():
    # A heading that looks like a finding but does not parse must be an ERROR,
    # never skipped (that would let a finding vanish and the count still "match").
    broken = "## M-1 — this is not a real finding heading"
    res = ec.check_text(_env(1, broken))
    assert res["verdict"] == "valid-fail" and res["errors"]


def test_duplicate_finding_number_fails():
    dupe = _JUSTIFIED.replace("M-1", "M-3") + "\n\n" + _UNJUSTIFIED.replace("M-2", "M-3")
    assert _v(_env(2, dupe)) == "valid-fail"


def test_missing_header_fails():
    assert _v("## M-1 — complexity 37 > 15 @ f.py:1:x (disposition: justified)\n"
              "standard: s\nreason: r\nfloor: none\n") == "valid-fail"


def test_dangerous_floor_is_a_valid_category():
    danger = (
        "## M-1 — complexity 20 > 15 @ src/auth/login.py:40:verify (disposition: unjustified)\n"
        "standard: coding-standards.md §Complexity\n"
        "reason: over the bar in the auth path — must be simplified\n"
        "floor: auth-security"
    )
    res = ec.check_text(_env(1, danger))
    assert res["verdict"] == "valid-pass"
    # the checker exposes the floor so the hook can enforce the one-way rule (S-8.3)
    assert any(f.get("floor") == "auth-security" for f in res["findings"])


# --- task #9: one path authority — the tool writes, the substrate resolves ------------

def _git_proj(tmp_path):
    import subprocess
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def test_write_lands_exactly_where_the_substrate_resolves(tmp_path, capsys):
    """The seam that used to be two hands: the judge writes where it was told,
    the gate reads where the substrate points. Now the WRITE goes through the
    tool, the tool asks the substrate, and — run from a project SUBDIRECTORY,
    the exact shape that used to silently split the two — the envelope still
    lands at the worktree root's shared .friday/."""
    import friday_substrate as fs
    root = _git_proj(tmp_path)
    body = _env(1, _JUSTIFIED, armed="true", checked="the tree")
    rc = ec.main(["--write", "--root", str(root / "src")], stdin_text=body)
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["verdict"] == "valid-pass"
    expected = fs.envelope_path(str(root / "src"))
    assert out["path"] == expected
    assert os.path.dirname(expected) == os.path.join(str(root), ".friday")
    assert open(expected, encoding="utf-8").read() == body


def test_write_bounces_a_malformed_envelope_without_writing(tmp_path, capsys):
    """Validate-then-write: a malformed envelope can no longer LAND at all —
    the bounce happens before the filesystem, so the gate never meets a
    document the checker would refuse."""
    import friday_substrate as fs
    root = _git_proj(tmp_path)
    bad = _env(2, _JUSTIFIED, checked="the tree")  # header lies about its count
    rc = ec.main(["--write", "--root", str(root)], stdin_text=bad)
    out = json.loads(capsys.readouterr().out)
    assert rc == 1 and out["verdict"] == "valid-fail"
    assert not os.path.exists(fs.envelope_path(str(root)))


def test_file_mode_is_unchanged(tmp_path, capsys):
    """--file validation stays exactly as it was — the gate's consumption-time
    check and every existing caller keep their interface."""
    p = tmp_path / "env.md"
    p.write_text(_env(1, _JUSTIFIED, checked="the tree"), encoding="utf-8")
    rc = ec.main(["--file", str(p)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["verdict"] == "valid-pass"
