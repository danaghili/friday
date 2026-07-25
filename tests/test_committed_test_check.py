"""Guard #7's checker — committed-test edit detection (TECHNICAL_SOW_REBUILD
FR-55 guard #7; §7 pin "Committed-test edit guard"). Production rebuild of
docs/research/rebuild/probe-guard7-prototype.py, test-first: these fixtures
re-pin the probe's seven cases (a–g) plus the documented residual (bonus)
against the real checker.

The mechanical definition (probe-guard7-committed-test.md):
  path not tests/*.py → pass. Epoch from CLAUDE.md FRIDAY-STATE since: (when
  state: build-in-progress), else newest journal state-transition; neither →
  no-verdict. `git log --follow -M100% --format=%cI` — empty → pass; oldest
  > epoch → pass (authored in-build); oldest <= epoch → DECISIONS.md must
  name the literal path (pass) else valid-fail. Any internal error →
  no-verdict. -M100% is load-bearing: default -M50% misattributed unrelated
  boilerplate stubs (false FAIL on new-test authoring — worse than the
  rename bypass it closed).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import committed_test_check as ctc  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO, "tools", "committed_test_check.py")

EPOCH = "2026-07-10T12:00:00Z"
PRE = "2026-07-01T00:00:00 +0000"
POST = "2026-07-12T00:00:00 +0000"

STATE_BLOCK = ("<!-- FRIDAY-STATE:BEGIN -->\n"
               "state: build-in-progress\n"
               f"since: {EPOCH}\n"
               "<!-- FRIDAY-STATE:END -->\n")


def _git(repo, *args, date=None):
    env = dict(os.environ)
    if date:
        env["GIT_COMMITTER_DATE"] = date
        env["GIT_AUTHOR_DATE"] = date
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=env,
                   capture_output=True)


def _repo(tmp_path, *, state_block=True):
    root = tmp_path / "proj"
    (root / "tests").mkdir(parents=True)
    (root / "docs").mkdir()
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "CLAUDE.md").write_text(
        "# proj\n\n" + (STATE_BLOCK if state_block else ""), encoding="utf-8")
    (root / "docs" / "DECISIONS.md").write_text("# Decisions — proj\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "scaffold", date=PRE)
    return root


def _commit_test(root, name="test_old.py", date=PRE, body="def test_x(): assert True\n"):
    p = root / "tests" / name
    p.write_text(body, encoding="utf-8")
    _git(root, "add", str(p))
    _git(root, "commit", "-q", "-m", f"add {name}", date=date)
    return p


# --- the seven pinned fixtures ---------------------------------------------------

def test_a_pre_epoch_test_without_permission_fails(tmp_path):
    root = _repo(tmp_path)
    p = _commit_test(root)
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-fail", res


def test_b_pre_epoch_test_with_permission_record_passes(tmp_path):
    root = _repo(tmp_path)
    p = _commit_test(root)
    (root / "docs" / "DECISIONS.md").write_text(
        "# Decisions — proj\n\n## D-0001 — PM permits the fix\n"
        "- **Decision:** tests/test_old.py may be corrected this build.\n"
        "override-grant: tests/test_old.py\n",
        encoding="utf-8")
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-pass", res


def test_b2_pre_epoch_bare_mention_does_not_pass(tmp_path):
    # A3 (harden): a mention without an override-grant (a rejection here) must NOT permit.
    root = _repo(tmp_path)
    p = _commit_test(root)
    (root / "docs" / "DECISIONS.md").write_text(
        "# Decisions — proj\n\n## D-0001 — rejected\n"
        "- **Decision:** we chose NOT to touch tests/test_old.py.\n",
        encoding="utf-8")
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-fail", res


def test_c_brand_new_untracked_test_passes(tmp_path):
    root = _repo(tmp_path)
    p = root / "tests" / "test_new.py"
    p.write_text("def test_y(): assert True\n", encoding="utf-8")
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-pass", res


def test_d_test_first_committed_after_epoch_passes(tmp_path):
    root = _repo(tmp_path)
    # A near-identical older stub exists — the -M50% trap the probe rejected:
    # default --follow misattributed the new file's history to it.
    _commit_test(root, "test_boiler.py", date=PRE, body="def test_x(): assert True\n")
    p = _commit_test(root, "test_fresh.py", date=POST, body="def test_x(): assert True\n")
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-pass", res


def test_e_non_test_file_passes_immediately(tmp_path):
    root = _repo(tmp_path)
    p = root / "docs" / "notes.md"
    p.write_text("x\n", encoding="utf-8")
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-pass", res


def test_f_no_epoch_resolvable_is_no_verdict(tmp_path):
    root = _repo(tmp_path, state_block=False)
    p = _commit_test(root)
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "no-verdict", res


def test_g_pure_rename_after_epoch_still_caught(tmp_path):
    root = _repo(tmp_path)
    _commit_test(root, "test_old.py", date=PRE)
    _git(root, "mv", "tests/test_old.py", "tests/test_renamed.py")
    _git(root, "commit", "-q", "-m", "mv", date=POST)
    res = ctc.check(str(root / "tests" / "test_renamed.py"), repo=str(root))
    assert res["verdict"] == "valid-fail", res


def test_bonus_rename_plus_edit_same_commit_is_the_accepted_residual(tmp_path):
    # Documented gap, pinned so a future "fix" that changes it is a conscious
    # decision: -M100% cannot see a rename whose content also changed.
    root = _repo(tmp_path)
    _commit_test(root, "test_old.py", date=PRE)
    (root / "tests" / "test_old.py").unlink()
    (root / "tests" / "test_moved.py").write_text(
        "def test_x(): assert True  # edited\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "mv+edit", date=POST)
    res = ctc.check(str(root / "tests" / "test_moved.py"), repo=str(root))
    assert res["verdict"] == "valid-pass", res


# --- epoch fallback + edges ---------------------------------------------------------

def test_journal_state_transition_is_the_epoch_fallback(tmp_path):
    root = _repo(tmp_path, state_block=False)
    (root / ".friday").mkdir()
    (root / ".friday" / "journal.jsonl").write_text(
        json.dumps({"event": "state-transition", "ts": EPOCH}) + "\n", encoding="utf-8")
    p = _commit_test(root)
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-fail", res  # epoch resolved → pre-epoch edit caught


def test_outside_any_git_repo_is_no_verdict(tmp_path):
    p = tmp_path / "tests" / "test_x.py"
    p.parent.mkdir()
    p.write_text("def test_x(): pass\n", encoding="utf-8")
    res = ctc.check(str(p), repo=str(tmp_path))
    assert res["verdict"] == "no-verdict", res


def test_cli_emits_typed_verdict_json(tmp_path):
    root = _repo(tmp_path)
    p = _commit_test(root)
    proc = subprocess.run([sys.executable, CHECKER, "--path", str(p),
                           "--repo", str(root)],
                          capture_output=True, text=True)
    out = json.loads(proc.stdout)
    assert out["verdict"] == "valid-fail"
