"""BUG-011 regression — guard #7 watched only tests/*.py.

On a TS/Vitest project the committed-test guard never fired: a
committed-first .test.ts could be silently weakened mid-build while every
gate stayed green (docs/BUGS.md BUG-011, D-0186). The rule after the fix:
the watch scope keeps tests/*.py and adds the dotted test-file family — a
basename carrying `.test.` or `.spec.`, any case, any directory.
Deliberately NOT the loose "test anywhere in the name" rule guard #11 uses:
this guard fires unprompted on every edit, and a false block is worse than
a miss by the tool's own doctrine — the ordinary-file pins below hold that
line.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import committed_test_check as ctc  # noqa: E402

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


def _repo(tmp_path):
    root = tmp_path / "proj"
    (root / "tests").mkdir(parents=True)
    (root / "docs").mkdir()
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "CLAUDE.md").write_text("# proj\n\n" + STATE_BLOCK, encoding="utf-8")
    (root / "docs" / "DECISIONS.md").write_text("# Decisions — proj\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "scaffold", date=PRE)
    return root


def _commit_file(root, rel, date=PRE, body="// pinned\n"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    _git(root, "add", str(p))
    _git(root, "commit", "-q", "-m", f"add {rel}", date=date)
    return p


def test_pre_epoch_vitest_test_without_permission_fails(tmp_path):
    root = _repo(tmp_path)
    p = _commit_file(root, "src/app.test.ts")
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-fail", res


def test_pre_epoch_playwright_spec_without_permission_fails(tmp_path):
    root = _repo(tmp_path)
    p = _commit_file(root, "e2e/checkout.spec.ts")
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-fail", res


def test_pre_epoch_vitest_test_with_permission_record_passes(tmp_path):
    root = _repo(tmp_path)
    p = _commit_file(root, "src/app.test.ts")
    (root / "docs" / "DECISIONS.md").write_text(
        "# Decisions — proj\n\n## D-0001 — PM permits the fix\n"
        "- **Decision:** src/app.test.ts may be corrected this build.\n"
        "override-grant: src/app.test.ts\n",
        encoding="utf-8")
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-pass", res


def test_in_build_authored_vitest_test_passes(tmp_path):
    root = _repo(tmp_path)
    p = _commit_file(root, "src/fresh.test.ts", date=POST)
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-pass", res


def test_ordinary_files_with_test_like_words_stay_unwatched(tmp_path):
    # The false-block line: names that merely CONTAIN "test"/"spec" without
    # the dotted convention are not tests and stay out of scope.
    root = _repo(tmp_path)
    for rel in ("docs/latest-notes.md", "src/contest.py", "src/inspect_or.py"):
        p = _commit_file(root, rel)
        res = ctc.check(str(p), repo=str(root))
        assert res["verdict"] == "valid-pass", (rel, res)


def test_python_convention_unchanged(tmp_path):
    root = _repo(tmp_path)
    p = _commit_file(root, "tests/test_old.py", body="def test_x(): pass\n")
    res = ctc.check(str(p), repo=str(root))
    assert res["verdict"] == "valid-fail", res
