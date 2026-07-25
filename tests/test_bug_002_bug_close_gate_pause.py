"""BUG-002 regression — the bug lane arms AFTER the diagnosis gate
(docs/BUGS.md BUG-002; trail docs/trails/BUG-002.md; D-0069 Option a).

The Stop-tier bug-close guard enforces the full close bar at every turn-end
while the sentinel exists, and the lane's Phase-4 PM gate REQUIRES a
turn-end — so arming before diagnosis made every in-context bug run trip the
guard at its own designed pause. The fix moves the arm point to fix-start
(post-confirmation); the declaration beat lives in the docs/BUGS.md entry at
intake. These tests pin the ordering, the intake declaration, the guard
behavior that must survive (an armed-but-unfinished lane still blocks), and
the two doc-truth side-findings.
"""
import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "tools"))
import bug_close_check  # noqa: E402


def _bug_md() -> str:
    # the bug lane lives at skills/bug/SKILL.md since the INC-2 sweep (D-0081)
    with open(os.path.join(_REPO, "skills", "bug", "SKILL.md"), encoding="utf-8") as fh:
        return fh.read()


# --- the fix: process ordering ------------------------------------------------------

def test_arm_command_follows_the_diagnosis_gate():
    text = _bug_md()
    gate = text.lower().index("show-your-diagnosis")
    arm = text.index("open --lane bug")
    assert arm > gate, ("the lane-arming command appears before the PM "
                        "diagnosis gate — the guard would fire on the lane's "
                        "own designed pause (BUG-002)")


def test_intake_declares_the_paths_before_any_arming():
    text = _bug_md()
    gate = text.lower().index("show-your-diagnosis")
    assert "declared in the `docs/BUGS.md` entry at intake" in text[:gate], (
        "declaration-before-action must live in the intake beat once arming "
        "moves post-gate — otherwise the declared test path is elicited "
        "nowhere before work starts")


# --- guard behavior that must survive the fix --------------------------------------

def _sentinel(tmp_path, **overrides):
    root = tmp_path / "proj"
    root.mkdir(exist_ok=True)
    data = {"lane": "bug", "id": "BUG-XXX",
            "trail": "docs/trails/BUG-XXX.md",
            "regression-test": "tests/test_bug_xxx.py"}
    data.update(overrides)
    p = tmp_path / "lane-open"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(root), str(p)


def test_armed_but_unfinished_lane_still_fails_the_close_bar(tmp_path):
    root, sentinel = _sentinel(tmp_path)
    res = bug_close_check.check(root, sentinel)
    assert res["verdict"] == "valid-fail", res
    assert "tests/test_bug_xxx.py" in res["summary"], res


def test_full_close_bar_still_passes(tmp_path):
    root, sentinel = _sentinel(tmp_path)
    os.makedirs(os.path.join(root, "tests"), exist_ok=True)
    os.makedirs(os.path.join(root, "docs", "trails"), exist_ok=True)
    open(os.path.join(root, "tests", "test_bug_xxx.py"), "w").close()
    with open(os.path.join(root, "docs", "trails", "BUG-XXX.md"), "w",
              encoding="utf-8") as fh:
        fh.write("trail: lane=bug id=BUG-XXX date=2026-07-15\n\n"
                 "## Asked\nFixture close.\n\n## Decisions\n"
                 "decisions: none — change fully specified by the ask\n\n"
                 "## Proof\nproof: 1 passed\n\nchangelog: fixture\n")
    res = bug_close_check.check(root, sentinel)
    assert res["verdict"] == "valid-pass", res


# --- doc-truth side-findings ---------------------------------------------------------

def test_checker_docstring_carries_no_stale_disarm_claim():
    # The owning hook disarms on pass (D-0023); the checker saying otherwise
    # is drift inside the guard's own documentation.
    assert "does NOT disarm" not in (bug_close_check.__doc__ or "")


def test_missing_test_summary_claims_existence_not_committedness(tmp_path):
    # The check is os.path.isfile — asserting "committed" overclaims what was
    # mechanically verified.
    root, sentinel = _sentinel(tmp_path)
    res = bug_close_check.check(root, sentinel)
    assert "committed" not in res["summary"], res
