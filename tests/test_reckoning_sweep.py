"""INC-104 FR-104.9 — the deep clean's catch-up sweep
(tools/reckoning_sweep.py).

Asks the project's own history which changes landed since the last clean
run and names those that carry no record of having been reconciled —
a hand edit outside any lane is exactly what it exists to catch (D1).
Nothing-outstanding is a distinct outcome from not having run (AC-104.9);
an unanchorable or unverifiable history is reported as exactly that, never
folded into clean (OQ-104.4 takes INC-102 FR-102.4's answer: the record's
own dated stamp against commit dates strictly after it).
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import reckoning  # noqa: E402
import reckoning_sweep  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONTRACT = os.path.join(REPO, "docs", "contracts", "reckoning-record.md")


def test_outcome_vocabulary_matches_the_contract_section():
    """The contract's catch-up section is the outcome set's single home;
    OUTCOMES is the operational copy and every outcome the module emits
    must be in it. This test is the lock that keeps the three in step."""
    with open(CONTRACT, encoding="utf-8") as fh:
        text = fh.read()
    section = text.split("## The catch-up sweep")[1].split("\n## ")[0]
    bullets = re.findall(r"^- \*\*([a-z-]+)\*\* —", section, re.MULTILINE)
    assert tuple(bullets) == reckoning_sweep.OUTCOMES
    with open(reckoning_sweep.__file__, encoding="utf-8") as fh:
        src = fh.read()
    emitted = set(re.findall(
        r'"(findings|nothing-outstanding|could-not-anchor|could-not-verify)"',
        src))
    assert emitted == set(reckoning_sweep.OUTCOMES)


def _git(repo, *args, date=None):
    env = dict(os.environ)
    if date:
        env["GIT_COMMITTER_DATE"] = date
        env["GIT_AUTHOR_DATE"] = date
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, env=env)


def _seed_repo(root, *, stamp="2026-08-01"):
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    with open(os.path.join(str(root), "CLAUDE.md"), "w") as fh:
        fh.write("# proj\n\n<!-- FRIDAY-STATE:BEGIN -->\n"
                 "state: closed\n"
                 f"last-verified: {stamp}\n"
                 "<!-- FRIDAY-STATE:END -->\n")
    with open(os.path.join(str(root), "app.py"), "w") as fh:
        fh.write("x = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "baseline", date="2026-07-30T10:00:00")


def _commit(root, fname, content, message, date):
    with open(os.path.join(str(root), fname), "w") as fh:
        fh.write(content)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message, date=date)


def _short(root, ref="HEAD"):
    out = subprocess.run(["git", "-C", str(root), "rev-parse", "--short",
                          ref], check=True, capture_output=True, text=True)
    return out.stdout.strip()


def test_hand_edit_outside_any_lane_is_named(tmp_path):
    _seed_repo(tmp_path)
    _commit(tmp_path, "deploy.sh", "tag=v2\n", "tweak deploy by hand",
            "2026-08-02T10:00:00")
    sha = _short(tmp_path)
    out = reckoning_sweep.sweep(str(tmp_path))
    assert out["outcome"] == "findings"
    assert out["anchor"] == "2026-08-01"
    (item,) = out["outstanding"]
    assert item["change"] == sha
    assert item["files"] == ["deploy.sh"]
    assert item["subject"] == "tweak deploy by hand"


def test_lane_change_with_a_record_is_reconciled(tmp_path):
    _seed_repo(tmp_path)
    _commit(tmp_path, "deploy.sh", "tag=v2\n", "PATCH-004 deploy tag",
            "2026-08-02T10:00:00")
    reckoning.searched(str(tmp_path), {
        "change": "PATCH-004", "declared": "ran", "name_match": "ran",
        "reading": "ran", "person": "nothing-known", "name": "tag",
        "when": "2026-08-02"})
    out = reckoning_sweep.sweep(str(tmp_path))
    assert out["outcome"] == "nothing-outstanding"
    assert out["outstanding"] == []


def test_lane_id_without_a_record_is_still_outstanding(tmp_path):
    """A lane ran before this machinery existed (or skipped the step) —
    the id in the message is not the record; only the record is."""
    _seed_repo(tmp_path)
    _commit(tmp_path, "deploy.sh", "tag=v2\n", "PATCH-004 deploy tag",
            "2026-08-02T10:00:00")
    out = reckoning_sweep.sweep(str(tmp_path))
    assert out["outcome"] == "findings"
    (item,) = out["outstanding"]
    assert item["change"] == "PATCH-004"


def test_reconciling_by_sha_clears_the_finding(tmp_path):
    _seed_repo(tmp_path)
    _commit(tmp_path, "deploy.sh", "tag=v2\n", "tweak deploy by hand",
            "2026-08-02T10:00:00")
    sha = _short(tmp_path)
    reckoning.searched(str(tmp_path), {
        "change": sha, "declared": "ran", "name_match": "ran",
        "reading": "ran", "person": "answered", "name": "tag",
        "when": "2026-08-03"})
    out = reckoning_sweep.sweep(str(tmp_path))
    assert out["outcome"] == "nothing-outstanding"


def test_commits_at_or_before_the_anchor_are_not_findings(tmp_path):
    """Strictly-after, the same comparison FR-102.4 runs — the anchor day
    itself belongs to the clean run that stamped it."""
    _seed_repo(tmp_path)
    _commit(tmp_path, "a.py", "y = 2\n", "on the anchor day",
            "2026-08-01T09:00:00")
    out = reckoning_sweep.sweep(str(tmp_path))
    assert out["outcome"] == "nothing-outstanding"


def test_record_only_commits_never_feed_the_sweep(tmp_path):
    """Recording the catch-up's own answers must not become the next
    sweep's finding — the record of answers is not a shared thing."""
    _seed_repo(tmp_path)
    os.makedirs(os.path.join(str(tmp_path), "docs"), exist_ok=True)
    _commit(tmp_path, os.path.join("docs", "RECKONINGS.md"),
            "seeded\n", "record reckonings", "2026-08-02T11:00:00")
    out = reckoning_sweep.sweep(str(tmp_path))
    assert out["outcome"] == "nothing-outstanding"


def test_missing_anchor_is_its_own_outcome_never_clean(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    _commit(tmp_path, "app.py", "x = 1\n", "baseline",
            "2026-08-02T10:00:00")
    out = reckoning_sweep.sweep(str(tmp_path))
    assert out["outcome"] == "could-not-anchor"
    assert out["outstanding"] == []


def test_no_git_is_could_not_verify_never_nothing_moved(tmp_path):
    with open(os.path.join(str(tmp_path), "CLAUDE.md"), "w") as fh:
        fh.write("<!-- FRIDAY-STATE:BEGIN -->\nlast-verified: 2026-08-01\n"
                 "<!-- FRIDAY-STATE:END -->\n")
    out = reckoning_sweep.sweep(str(tmp_path))
    assert out["outcome"] == "could-not-verify"


def test_uncommitted_changes_are_reported(tmp_path):
    _seed_repo(tmp_path)
    with open(os.path.join(str(tmp_path), "app.py"), "w") as fh:
        fh.write("x = 3\n")
    out = reckoning_sweep.sweep(str(tmp_path))
    assert "app.py" in out["dirty"]
