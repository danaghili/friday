"""INC-204 FR-204.5 / D4 — the single bite: the handoff keys gate does not
attest while value-carrying files are tracked and no accepted-risk record
exists. A precondition on a gate that already refuses to report done with
anything outstanding — no new gate, no new hook (S-204.2). Everywhere else the
posture checker reports and blocks nothing (that half is AC-204.4's reconcile
run, proven at the AC pass).
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import handoff_attest  # noqa: E402
import handoff_gate as hg  # noqa: E402

DECLINED = (
    "# proj\n\n<!-- FRIDAY-SECRET-STORE:BEGIN -->\n"
    "secret-store: accepted-risk — PM keeps a tracked env for this demo repo, accepted 2026-07-30\n"
    "<!-- FRIDAY-SECRET-STORE:END -->\n")


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _project(tmp_path, claude_md="# proj\n", tracked_env=False):
    (tmp_path / ".friday").mkdir()
    _git(tmp_path, "init", "-q")
    (tmp_path / "CLAUDE.md").write_text(claude_md, encoding="utf-8")
    _git(tmp_path, "add", "CLAUDE.md")
    if tracked_env:
        (tmp_path / ".env").write_text("KEY=value\n", encoding="utf-8")
        _git(tmp_path, "add", "-f", ".env")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "seed")
    return str(tmp_path)


def test_keys_gate_refuses_on_tracked_value_file(tmp_path, capsys):
    root = _project(tmp_path, tracked_env=True)
    rc = handoff_attest.main(["--gate", "keys", "--status", "confirmed",
                              "--by", "pm", "--cwd", root])
    assert rc == 2
    err = capsys.readouterr().err
    assert ".env" in err and "accepted-risk" in err  # plain words: what and what next
    assert hg.read_gate_status(root) == {}           # nothing was written


def test_keys_gate_proceeds_with_accepted_risk_record(tmp_path):
    root = _project(tmp_path, claude_md=DECLINED, tracked_env=True)
    rc = handoff_attest.main(["--gate", "keys", "--status", "confirmed",
                              "--by", "pm", "--note", "moved in the client vault",
                              "--cwd", root])
    assert rc == 0
    assert hg.read_gate_status(root) == {"keys": "confirmed"}


def test_other_gates_unaffected_by_posture(tmp_path):
    """The bite bites at keys and only there (AC-204.4's 'only there' half).
    The reconcile note satisfies that gate's own rule (INC-101 FR-101.7,
    D-1023) — what this test proves is that the keys POSTURE played no part."""
    root = _project(tmp_path, tracked_env=True)
    rc = handoff_attest.main(["--gate", "reconcile", "--status", "confirmed",
                              "--by", "pm", "--cwd", root,
                              "--note", "deep clean ran with the document-truth probe, verdict clean"])
    assert rc == 0


def test_keys_gate_clean_tree_unaffected(tmp_path):
    """No tracked value file → the precondition is silent even with no
    declaration at all — the bite condition is D4's, not the checker's whole
    verdict."""
    root = _project(tmp_path)
    rc = handoff_attest.main(["--gate", "keys", "--status", "confirmed",
                              "--by", "pm", "--cwd", root])
    assert rc == 0
