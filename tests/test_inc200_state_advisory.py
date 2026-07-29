"""INC-200 C1 (task #21, D-0107) — the warn-tier state advisory, both halves.

Two questions, one tier, one owner. Both are "the record and what is actually
happening disagree", and D-0107 ruled the answer is **always a warning the PM
sees, never a block** — a false block is worse than a miss, and enforcement here
was prose-only at every stage boundary (NF1), so the PM never saw the
contradiction at all.

**Half one — the lane-start advisory (D-0107 as ruled).** A lane doing something
the project's current state says it should not: re-seeding a project that is
mid-build, packaging a handover for work that is not finished. This rides
PreToolUse deliberately. PostToolUse fires *after* the write, by which point
init has already overwritten `build-in-progress` with `substrate-seeded` and the
contradiction it was supposed to notice is gone from the disk. PreToolUse sees
the project as it still is, plus the change being proposed — the only moment
both halves of the disagreement exist at once.

**Half two — the PROP-028 dirty-bit backstop (D-0106/D-0141, folded in here by
the PM 2026-07-29).** Task #22 gave the dirty bit a writer and told feature,
patch and bug to call it. An instruction can be skipped, and the obvious
mechanical home does not work: patch and bug pass through a lane-close gate but
**feature arms no lane at all**, so a lane-close hook would cover two of three
while looking complete. This backstop keys on *the tree having moved* rather
than on which lane moved it, so all three are covered equally. It mirrors guard
#8's proven shape — stamp the commit, warn "N commits behind", never block.

The empty cases matter more than the findings here: this runs on every write in
every project, and almost every one of them is a project with no state block, no
rules, or nothing to say. Silence has to be the cheap, ordinary, tested outcome.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import state_advisory_check as sac  # noqa: E402
import state_record  # noqa: E402

CONTRACT = """# Contract: the project state record

prose the parser must ignore.

<!-- FRIDAY-LANE-LEGALITY:BEGIN -->
illegal: reseed-state when tsow-approved,substrate-seeded,build-in-progress,post-build-review-recorded,closed — re-seeding a project that is already under way
illegal: handoff-package when tsow-approved,substrate-seeded,build-in-progress,post-build-review-recorded — packaging a handover for work that is not finished
<!-- FRIDAY-LANE-LEGALITY:END -->

more prose.
"""

RECORD = """# proj

<!-- FRIDAY-STATE:BEGIN -->
stack: path:python3
state: {state}
tsow: docs/TECHNICAL_SOW.md
since: 2026-07-12T16:20:00Z
{extra}<!-- FRIDAY-STATE:END -->
"""


def _closed(status="verified"):
    return RECORD.format(state="closed",
                         extra=f"last-verified: 2026-07-20 (close)\n"
                               f"record-status: {status}\n")


def _proj(tmp_path, text, *, git=False):
    root = tmp_path / "proj"
    root.mkdir(exist_ok=True)
    (root / "CLAUDE.md").write_text(text, encoding="utf-8")
    if git:
        _git(root, "init", "-q", ".")
        _git(root, "config", "user.email", "t@example.com")
        _git(root, "config", "user.name", "t")
        _commit(root, "first")
    return str(root)


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, check=False)


def _commit(root, msg):
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", msg)
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def _contract(tmp_path, text=CONTRACT):
    p = tmp_path / "state-record.md"
    p.write_text(text, encoding="utf-8")
    return str(p)


# --- the rules table: a grammar, therefore an empty case ------------------------------

def test_a_contract_with_no_legality_block_yields_no_rules(tmp_path):
    """Not every friday version ships the block. An absent block is zero rules
    and total silence — never a crash, and never an invented default rule."""
    assert sac.load_rules(_contract(tmp_path, "# contract\n\nno block here.\n")) == []


def test_a_present_but_empty_block_is_valid_with_zero_rules(tmp_path):
    """THE empty case: the block exists and declares nothing. Valid, and
    distinguishable from an absent block only in that someone wrote it down."""
    text = ("# c\n<!-- FRIDAY-LANE-LEGALITY:BEGIN -->\n"
            "<!-- FRIDAY-LANE-LEGALITY:END -->\n")
    assert sac.load_rules(_contract(tmp_path, text)) == []


def test_a_rule_parses_into_its_action_its_states_and_its_plain_english_reason(tmp_path):
    rules = sac.load_rules(_contract(tmp_path))
    assert len(rules) == 2
    reseed = [r for r in rules if r["action"] == "reseed-state"][0]
    assert "build-in-progress" in reseed["states"]
    assert "closed" in reseed["states"]
    assert reseed["why"].startswith("re-seeding a project")


def test_a_malformed_rule_is_surfaced_not_silently_dropped(tmp_path):
    """A rule that does not parse must not vanish. A silently-dropped rule is a
    guard that quietly stops guarding — the exact fault task #10 fixed in the
    maintainability gate, and it is not being reintroduced here."""
    text = ("# c\n<!-- FRIDAY-LANE-LEGALITY:BEGIN -->\n"
            "illegal: reseed-state when halfway-done — a state that does not exist\n"
            "<!-- FRIDAY-LANE-LEGALITY:END -->\n")
    rules = sac.load_rules(_contract(tmp_path, text))
    # `halfway-done` is not in the lifecycle, so this rule could never match any
    # real project — policy that reads as enforced and guards nothing.
    assert len(rules) == 1 and rules[0]["malformed"] is True
    assert rules[0]["unknown_states"] == ("halfway-done",)
    res = sac.check_lane_start(_proj(tmp_path, RECORD.format(
        state="build-in-progress", extra="")), "CLAUDE.md", "",
        contract=_contract(tmp_path, text))
    assert "malformed" in res["summary"].lower()


# --- half one: the lane-start advisory ------------------------------------------------

def test_re_seeding_a_project_that_is_mid_build_warns(tmp_path):
    """D-0107's own worked example: /friday:init run again over a live build."""
    root = _proj(tmp_path, RECORD.format(state="build-in-progress", extra=""))
    proposed = RECORD.format(state="substrate-seeded", extra="")
    res = sac.check_lane_start(root, "CLAUDE.md", proposed,
                               contract=_contract(tmp_path))
    assert res["verdict"] == "valid-fail"
    assert "build-in-progress" in res["summary"]


def test_the_warning_says_what_it_saw_in_plain_words(tmp_path):
    """The PM reads this, not a developer. It must name the state the project is
    actually in and why the action contradicts it — never a rule id alone."""
    root = _proj(tmp_path, RECORD.format(state="build-in-progress", extra=""))
    res = sac.check_lane_start(root, "CLAUDE.md",
                               RECORD.format(state="substrate-seeded", extra=""),
                               contract=_contract(tmp_path))
    assert "re-seeding a project that is already under way" in res["summary"]


def test_a_write_that_does_not_move_the_state_backwards_is_silent(tmp_path):
    """Ordinary build-time edits to CLAUDE.md must not warn, or the advisory
    becomes noise and stops being read."""
    root = _proj(tmp_path, RECORD.format(state="build-in-progress", extra=""))
    same = RECORD.format(state="build-in-progress", extra="") + "\nnew prose.\n"
    res = sac.check_lane_start(root, "CLAUDE.md", same,
                               contract=_contract(tmp_path))
    assert res["verdict"] == "valid-pass"


def test_seeding_a_project_that_has_no_state_yet_is_silent(tmp_path):
    """The greenfield path — the common, correct case. A project with no record
    cannot contradict its record."""
    root = _proj(tmp_path, "# proj\n\nnothing yet.\n")
    res = sac.check_lane_start(root, "CLAUDE.md",
                               RECORD.format(state="substrate-seeded", extra=""),
                               contract=_contract(tmp_path))
    assert res["verdict"] == "valid-pass"


def test_packaging_a_handover_for_unfinished_work_warns(tmp_path):
    root = _proj(tmp_path, RECORD.format(state="build-in-progress", extra=""))
    res = sac.check_lane_start(root, "docs/handoff/package.md", "# handover\n",
                               contract=_contract(tmp_path))
    assert res["verdict"] == "valid-fail"
    assert "handover" in res["summary"]


def test_packaging_a_handover_for_a_finished_project_is_silent(tmp_path):
    """The legal case, which is the whole point of the lane."""
    root = _proj(tmp_path, _closed())
    res = sac.check_lane_start(root, "docs/handoff/package.md", "# handover\n",
                               contract=_contract(tmp_path))
    assert res["verdict"] == "valid-pass"


def test_a_write_matching_no_rule_at_all_is_silent(tmp_path):
    """Every write in every friday project reaches this. The overwhelmingly
    common answer is 'nothing to say', and it must be cheap."""
    root = _proj(tmp_path, RECORD.format(state="build-in-progress", extra=""))
    res = sac.check_lane_start(root, "src/thing.py", "print(1)\n",
                               contract=_contract(tmp_path))
    assert res["verdict"] == "valid-pass"


# --- half two: the dirty-bit backstop -------------------------------------------------

def test_a_closed_record_whose_tree_has_not_moved_is_silent(tmp_path):
    root = _proj(tmp_path, _closed(), git=True)
    state_record.mark_verified(root, when="2026-07-29")
    assert sac.check_liveness(root)["verdict"] == "valid-pass"


def test_a_closed_record_still_claiming_verified_after_the_tree_moved_warns(tmp_path):
    """The backstop's whole reason to exist: a lane landed changes and did not
    mark the record stale, so the record now claims something untrue."""
    root = _proj(tmp_path, _closed(), git=True)
    state_record.mark_verified(root, when="2026-07-29")
    (tmp_path / "proj" / "feature.py").write_text("print(1)\n", encoding="utf-8")
    _commit(tmp_path / "proj", "a lane landed changes")
    res = sac.check_liveness(root)
    assert res["verdict"] == "valid-fail"
    assert "stale" in res["summary"]


def test_uncommitted_changes_count_as_the_tree_having_moved(tmp_path):
    """A lane that has not committed yet has still changed the project."""
    root = _proj(tmp_path, _closed(), git=True)
    state_record.mark_verified(root, when="2026-07-29")
    (tmp_path / "proj" / "feature.py").write_text("print(1)\n", encoding="utf-8")
    assert sac.check_liveness(root)["verdict"] == "valid-fail"


def test_a_record_already_marked_stale_does_not_warn(tmp_path):
    """The lane did its job. Warning here would train the PM to ignore this."""
    root = _proj(tmp_path, _closed(), git=True)
    state_record.mark_verified(root, when="2026-07-29")
    (tmp_path / "proj" / "feature.py").write_text("print(1)\n", encoding="utf-8")
    _commit(tmp_path / "proj", "landed")
    state_record.mark_stale(root)
    assert sac.check_liveness(root)["verdict"] == "valid-pass"


def test_a_project_that_is_not_closed_is_silent(tmp_path):
    """Mid-build the whole project is in motion by definition."""
    root = _proj(tmp_path, RECORD.format(state="build-in-progress", extra=""),
                 git=True)
    assert sac.check_liveness(root)["verdict"] == "valid-pass"


def test_a_closed_record_never_verified_through_the_tool_is_silent(tmp_path):
    """THE backstop's empty case. Every project closed before this existed has
    no stamp, and inventing a baseline would fire a false alarm at every one of
    them on their next session — the fastest way to get a warning ignored."""
    root = _proj(tmp_path, _closed(), git=True)
    (tmp_path / "proj" / "feature.py").write_text("print(1)\n", encoding="utf-8")
    res = sac.check_liveness(root)
    assert res["verdict"] == "valid-pass"
    assert "never" in res["summary"] or "no stamp" in res["summary"]


def test_a_project_that_is_not_a_git_repo_is_silent(tmp_path):
    """friday does not require git. No history means no way to tell the tree
    moved, and a guess is worse than silence."""
    root = _proj(tmp_path, _closed())
    state_record.mark_verified(root, when="2026-07-29")
    assert sac.check_liveness(root)["verdict"] == "valid-pass"


def test_marking_verified_stamps_the_commit_and_marking_stale_does_not(tmp_path):
    """The stamp is the clear's companion. Marking stale must not touch it, or
    the backstop would forget where 'verified' was and go quiet forever."""
    root = _proj(tmp_path, _closed(), git=True)
    state_record.mark_verified(root, when="2026-07-29")
    stamp = sac.read_stamp(root)
    assert stamp and len(stamp) >= 7
    state_record.mark_stale(root)
    assert sac.read_stamp(root) == stamp


# --- the tier, asserted rather than assumed -------------------------------------------

def test_no_outcome_of_either_half_is_ever_a_block(tmp_path):
    """D-0107 ruled warn-only. This asserts the checker cannot express a block
    at all, so the tier is a property of the code and not of the caller."""
    root = _proj(tmp_path, RECORD.format(state="build-in-progress", extra=""))
    outcomes = [
        sac.check_lane_start(root, "CLAUDE.md",
                             RECORD.format(state="substrate-seeded", extra=""),
                             contract=_contract(tmp_path)),
        sac.check_lane_start(root, "src/x.py", "", contract=_contract(tmp_path)),
        sac.check_liveness(root),
    ]
    for res in outcomes:
        # The checker has no vocabulary for blocking: the only verdicts it can
        # return are the two warn-tier ones, and it never emits the harness's
        # deny shape. The tier is a property of this code, not of its caller.
        assert res["verdict"] in ("valid-pass", "valid-fail")
        assert res["tier"] == "warn"
        assert "permissionDecision" not in res and "decision" not in res


def test_the_cli_emits_one_json_verdict_and_exits_zero_either_way(tmp_path, capsys):
    """An advisory that crashes a lane is worse than the drift it reports."""
    root = _proj(tmp_path, RECORD.format(state="build-in-progress", extra=""))
    rc = sac.main(["--root", root, "--mode", "liveness"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["verdict"] in ("valid-pass", "valid-fail")
