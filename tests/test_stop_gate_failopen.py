"""Regression tests for the fail-OPEN fix on the two Stop-gates.

The panel found both gates fail-CLOSED on a broken re-verifier — a false-block
path that stalls a working session, contradicting the gates' own "a false block
is worse than a miss" doctrine. These pin the corrected behavior: a gate blocks
ONLY on a fresh, valid verdict of FAIL; a missing or crashing verifier (which
emits no valid verdict) ALLOWS the Stop and leaves the sentinel armed for a
later, runnable re-check. A positive control proves the gate still blocks a
genuine inconsistency (i.e. the fix didn't just defang it).
"""
import json
import os
import shutil
import subprocess

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _proj(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "docs" / "reviews").mkdir(parents=True)
    (root / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    # `closed` with no close artifacts = a genuinely BROKEN record.
    (root / "CLAUDE.md").write_text(
        "# proj\n\n<!-- FRIDAY-CLAIMS:BEGIN -->\nstack: path:python3\n"
        "<!-- FRIDAY-CLAIMS:END -->\n\n<!-- FRIDAY-STATE:BEGIN -->\n"
        "state: closed\ntsow: docs/TECHNICAL_SOW.md\n<!-- FRIDAY-STATE:END -->\n",
        encoding="utf-8")
    return root


def _arm(proj, name, body="armed: a prior inconsistency\n"):
    d = proj / ".friday"
    d.mkdir(exist_ok=True)
    (d / name).write_text(body, encoding="utf-8")


def _plugin_with_broken_verifier(tmp_path, verifier_rel, mode):
    pr = tmp_path / "plugin"
    shutil.copytree(os.path.join(BUILD_ROOT, "hooks"), pr / "hooks",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(BUILD_ROOT, "tools"), pr / "tools",
                    ignore=shutil.ignore_patterns("__pycache__"))
    v = pr / verifier_rel
    if mode == "missing":
        v.unlink()
    else:  # "crash": exits non-zero with a traceback to stderr, no verdict on stdout
        v.write_text("import sys\nsys.stderr.write('boom\\n')\nraise SystemExit(3)\n",
                     encoding="utf-8")
    return str(pr)


def _run(plugin_root, hook, proj):
    return subprocess.run(
        ["python3", os.path.join(plugin_root, "hooks", hook), plugin_root],
        input=json.dumps({"hook_event_name": "Stop", "cwd": str(proj)}),
        capture_output=True, text=True, cwd=str(proj))


# --- state_stop_gate --------------------------------------------------------

def test_state_gate_positive_control_still_blocks(tmp_path):
    proj = _proj(tmp_path)
    _arm(proj, "state-inconsistent")
    p = _run(BUILD_ROOT, "state_stop_gate.py", proj)  # real, working verifier
    assert json.loads(p.stdout)["decision"] == "block"


def test_state_gate_fails_open_on_missing_verifier(tmp_path):
    proj = _proj(tmp_path)
    _arm(proj, "state-inconsistent")
    pr = _plugin_with_broken_verifier(tmp_path, "tools/verify_state.py", "missing")
    p = _run(pr, "state_stop_gate.py", proj)
    assert p.stdout.strip() == ""                                   # ALLOW, not block
    assert (proj / ".friday" / "state-inconsistent").is_file()      # stays armed


def test_state_gate_fails_open_on_crashing_verifier(tmp_path):
    proj = _proj(tmp_path)
    _arm(proj, "state-inconsistent")
    pr = _plugin_with_broken_verifier(tmp_path, "tools/verify_state.py", "crash")
    p = _run(pr, "state_stop_gate.py", proj)
    assert p.stdout.strip() == ""                                   # ALLOW despite armed
    assert (proj / ".friday" / "state-inconsistent").is_file()


# --- review_format_stop_gate ------------------------------------------------

def test_review_gate_fails_open_on_crashing_verifier(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "reviews" / "BUILD-001-review.md").write_text("bad\n", encoding="utf-8")
    # sentinel format: line1=rel_path, line2=mode, rest=armed summary
    _arm(proj, "review-format-invalid",
         "docs/reviews/BUILD-001-review.md\nsweep\narmed summary\n")
    pr = _plugin_with_broken_verifier(tmp_path, "tools/verify_review_format.py", "crash")
    p = _run(pr, "review_format_stop_gate.py", proj)
    assert p.stdout.strip() == ""                                   # ALLOW
    assert (proj / ".friday" / "review-format-invalid").is_file()   # stays armed
