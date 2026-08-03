"""INC-204 FR-204.2 / FR-204.3 — the secret-store declaration grammar and the
value-blind posture checker, test-first.

The make-or-break (KH-1): a checker built to inspect secret hygiene must be
INCAPABLE of opening a value file, not merely careful — it classifies dotenv
files by filename through tools/secret_names.py's existing allowlist and asks
git what is tracked. AC-204.2 proves the incapacity by behaviour (an unreadable
value file changes nothing) and by the open-set (no opened path is a
value-carrying filename).

S-204.3: an absent declaration and a recorded decline are distinguishable —
"accepting the risk" means somebody accepted it, by name, with a reason.
"""
import builtins
import json
import os
import stat
import subprocess
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import secret_posture_check as spc  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DECLARED = (
    "# proj\n\n<!-- FRIDAY-SECRET-STORE:BEGIN -->\n"
    "secret-store: homeassistant secrets.yaml (values via !secret includes)\n"
    "<!-- FRIDAY-SECRET-STORE:END -->\n")
DECLINED = (
    "# proj\n\n<!-- FRIDAY-SECRET-STORE:BEGIN -->\n"
    "secret-store: accepted-risk — solo throwaway prototype, PM keeps values in local .env only\n"
    "<!-- FRIDAY-SECRET-STORE:END -->\n")


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _repo(tmp_path, claude_md=DECLARED, files=(), track=()):
    _git(tmp_path, "init", "-q")
    (tmp_path / "CLAUDE.md").write_text(claude_md, encoding="utf-8")
    for name, content in files:
        (tmp_path / name).write_text(content, encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".env\n.env.*\n!.env.example\n",
                                         encoding="utf-8")
    _git(tmp_path, "add", "CLAUDE.md", ".gitignore")
    for name in track:
        _git(tmp_path, "add", "-f", name)
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "seed")
    return tmp_path


# --- the declaration grammar (FR-204.2, OQ-204.2) ------------------------------------

def test_grammar_declared_store():
    d = spc.parse_declaration(DECLARED)
    assert d == {"kind": "store",
                 "store": "homeassistant secrets.yaml (values via !secret includes)"}


def test_grammar_accepted_risk_carries_reason():
    d = spc.parse_declaration(DECLINED)
    assert d["kind"] == "accepted-risk"
    assert "throwaway prototype" in d["reason"]


def test_grammar_empty_cases_absent_vs_empty_block():
    """The defined empty case: no block, or a block with no secret-store line,
    both parse to None — 'never declared', distinct from a decline (S-204.3)."""
    assert spc.parse_declaration("# proj\nno block here\n") is None
    empty_block = ("<!-- FRIDAY-SECRET-STORE:BEGIN -->\n"
                   "<!-- FRIDAY-SECRET-STORE:END -->\n")
    assert spc.parse_declaration(empty_block) is None


def test_grammar_reasonless_decline_is_malformed_not_accepted():
    """`accepted-risk —` with nothing after it is NOT an accepted risk — a risk
    nobody gave a reason for was not accepted by anybody."""
    bad = ("<!-- FRIDAY-SECRET-STORE:BEGIN -->\n"
           "secret-store: accepted-risk —\n"
           "<!-- FRIDAY-SECRET-STORE:END -->\n")
    d = spc.parse_declaration(bad)
    assert d["kind"] == "malformed"


# --- the four verdict states (AC-204.3) ----------------------------------------------

def test_declared_and_clean_passes(tmp_path):
    _repo(tmp_path)
    res = spc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass", res


def test_tracked_value_file_reported_by_path_never_content(tmp_path):
    secret_line = "API_KEY=sk-live-actual-value-9911\n"
    _repo(tmp_path, files=[(".env", secret_line)], track=[".env"])
    res = spc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail"
    assert any(f["kind"] == "tracked-value-file" and f["path"] == ".env"
               for f in res["findings"])
    assert "sk-live-actual-value-9911" not in json.dumps(res)


def test_no_declaration_is_the_gap(tmp_path):
    _repo(tmp_path, claude_md="# proj\nnothing declared\n")
    res = spc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail"
    assert any(f["kind"] == "no-declaration" for f in res["findings"])


def test_recorded_decline_passes_and_is_named(tmp_path):
    _repo(tmp_path, claude_md=DECLINED)
    res = spc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass", res
    assert "accepted-risk" in res["summary"]


def test_decline_downgrades_tracked_file_to_note_the_bite_condition(tmp_path):
    """FR-204.5's bite is (tracked value files AND no accepted-risk record) —
    with the record, the checker reports the file as a note, not a failure."""
    _repo(tmp_path, claude_md=DECLINED,
          files=[(".env", "X=1\n")], track=[".env"])
    res = spc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass", res
    assert any(n["kind"] == "tracked-value-file" for n in res["notes"])


# --- KH-1 / AC-204.2: value-blind by construction ------------------------------------

def test_unreadable_value_file_changes_nothing(tmp_path):
    """The checker never needed the contents: a value file it cannot read is
    indistinguishable from one it could."""
    _repo(tmp_path, files=[(".env", "X=1\n")])  # present, untracked, ignored
    os.chmod(tmp_path / ".env", 0)
    try:
        res = spc.check(root=str(tmp_path))
        assert res["verdict"] == "valid-pass", res
    finally:
        os.chmod(tmp_path / ".env", stat.S_IRUSR | stat.S_IWUSR)


def test_open_set_contains_no_value_filename(tmp_path, monkeypatch):
    """AC-204.2's direct form: record every open() during a check and assert no
    opened basename is a value-carrying dotenv name."""
    import secret_names
    _repo(tmp_path, files=[(".env", "X=1\n"), (".env.example", "X=\n")])
    opened = []
    real_open = builtins.open

    def tracking_open(file, *a, **k):
        opened.append(os.path.basename(str(file)))
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", tracking_open)
    spc.check(root=str(tmp_path))
    assert not [b for b in opened if secret_names.is_value_env_file(b)], opened


def test_example_file_still_classified_example():
    """Both directions of AC-204.2: the allowlist still reads examples."""
    import secret_names
    assert secret_names.is_example_env_file(".env.example")
    assert not secret_names.is_value_env_file(".env.example")
    assert secret_names.is_value_env_file(".env.production")
