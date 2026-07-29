"""INC-200 C5 (task #27, D-0111) — due-signals for the standing-care lanes.

Five care lanes have zero due logic, and the most damaging silence is the
terminal seam: nothing anywhere ever says a finished project's handover is due
(NF10). D-0111 rules the cure MINIMAL — warn-tier signals at natural moments
only, no cron, no nagging. Exactly two signals, both scoped to a CLOSED project,
both delivered once at session start:

- **The handover that never happened**: the project is closed and no package
  exists at `docs/handoff/` (the contract's "start here" README is the marker).
- **The reconcile that is overdue**: `last-verified:` has aged past a
  threshold. This leans on task #22's work deliberately — a clean reconcile now
  re-dates that field even when nothing was dirty (D-0141), precisely so its
  age is an honest staleness signal rather than a stuck clock.

The threshold is the project's own typed line (`reconcile-due: <N>d`, optional,
FRIDAY-STATE) with a 30-day default — recorded where the record lives, not
buried in the checker. A malformed threshold is surfaced, never silently
replaced by the default (the guard-that-quietly-stops-guarding fault again).

Everything else is silence, and the silences are the contract: mid-build
projects, non-friday directories, a closed record with no `last-verified:` at
all (that is K5's breach to report, not this signal's to double-count).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import state_advisory_check as sac  # noqa: E402

RECORD = """# proj

<!-- FRIDAY-STATE:BEGIN -->
stack: path:python3
state: {state}
tsow: docs/TECHNICAL_SOW.md
since: 2026-07-12T16:20:00Z
{extra}<!-- FRIDAY-STATE:END -->
"""


def _proj(tmp_path, *, state="closed", last_verified="2026-07-20 (close)",
          due=None, handoff=False):
    root = tmp_path / "proj"
    root.mkdir(exist_ok=True)
    extra = ""
    if last_verified is not None:
        extra += f"last-verified: {last_verified}\nrecord-status: verified\n"
    if due is not None:
        extra += f"reconcile-due: {due}\n"
    (root / "CLAUDE.md").write_text(RECORD.format(state=state, extra=extra),
                                    encoding="utf-8")
    if handoff:
        (root / "docs" / "handoff").mkdir(parents=True)
        (root / "docs" / "handoff" / "README.md").write_text(
            "# Start here\n", encoding="utf-8")
    return str(root)


# --- the silences (the common case, and the contract) ---------------------------------

def test_a_mid_build_project_is_silent(tmp_path):
    root = _proj(tmp_path, state="build-in-progress", last_verified=None)
    res = sac.check_due(root, today="2026-07-29")
    assert res["verdict"] == "valid-pass"


def test_a_non_friday_directory_is_silent(tmp_path):
    root = tmp_path / "plain"
    root.mkdir()
    assert sac.check_due(str(root), today="2026-07-29")["verdict"] == "valid-pass"


def test_a_closed_project_with_package_and_fresh_record_is_silent(tmp_path):
    root = _proj(tmp_path, handoff=True, last_verified="2026-07-20 (close)")
    res = sac.check_due(root, today="2026-07-29")
    assert res["verdict"] == "valid-pass"


def test_a_closed_record_with_no_last_verified_is_k5s_problem_not_ours(tmp_path):
    """That record is already in breach of the close rules; a second voice
    saying so here would be double-reporting, not a due-signal."""
    root = _proj(tmp_path, last_verified=None, handoff=True)
    assert sac.check_due(root, today="2026-09-01")["verdict"] == "valid-pass"


# --- signal one: the handover that never happened ---------------------------------------

def test_a_closed_project_with_no_handoff_package_warns(tmp_path):
    root = _proj(tmp_path, handoff=False)
    res = sac.check_due(root, today="2026-07-29")
    assert res["verdict"] == "valid-fail"
    assert "handover" in res["summary"] or "handoff" in res["summary"]


def test_an_empty_handoff_directory_is_not_a_package(tmp_path):
    """The contract's marker is the 'start here' README, not a bare folder."""
    root = _proj(tmp_path, handoff=False)
    (tmp_path / "proj" / "docs" / "handoff").mkdir(parents=True)
    res = sac.check_due(root, today="2026-07-29")
    assert res["verdict"] == "valid-fail"


# --- signal two: the reconcile that is overdue --------------------------------------------

def test_a_record_older_than_the_default_thirty_days_warns_with_its_age(tmp_path):
    root = _proj(tmp_path, handoff=True, last_verified="2026-06-01 (close)")
    res = sac.check_due(root, today="2026-07-29")
    assert res["verdict"] == "valid-fail"
    assert "58" in res["summary"] and "30" in res["summary"]


def test_the_projects_own_threshold_line_overrides_the_default(tmp_path):
    root = _proj(tmp_path, handoff=True, last_verified="2026-06-01 (close)",
                 due="90d")
    assert sac.check_due(root, today="2026-07-29")["verdict"] == "valid-pass"


def test_a_tighter_threshold_also_binds(tmp_path):
    root = _proj(tmp_path, handoff=True, last_verified="2026-07-20 (close)",
                 due="7d")
    res = sac.check_due(root, today="2026-07-29")
    assert res["verdict"] == "valid-fail" and "7" in res["summary"]


def test_the_close_annotation_on_the_date_still_parses(tmp_path):
    """The closer writes `<date> (close)`; a reconcile writes the bare date.
    Both shapes must read as dates, or the signal dies on real records."""
    root = _proj(tmp_path, handoff=True, last_verified="2026-07-28")
    assert sac.check_due(root, today="2026-07-29")["verdict"] == "valid-pass"


def test_a_malformed_threshold_is_surfaced_never_silently_defaulted(tmp_path):
    """`reconcile-due: soonish` must not quietly become 30d — a project that
    thinks it set a policy deserves to hear the policy did not parse."""
    root = _proj(tmp_path, handoff=True, due="soonish")
    res = sac.check_due(root, today="2026-07-29")
    assert res["verdict"] == "valid-fail"
    assert "soonish" in res["summary"]


def test_an_unparseable_last_verified_date_is_surfaced_not_treated_as_fresh(tmp_path):
    root = _proj(tmp_path, handoff=True, last_verified="sometime in June")
    res = sac.check_due(root, today="2026-07-29")
    assert res["verdict"] == "valid-fail"
    assert "last-verified" in res["summary"]


# --- both at once, and the tier ------------------------------------------------------------

def test_both_signals_fire_as_one_message_naming_both(tmp_path):
    root = _proj(tmp_path, handoff=False, last_verified="2026-06-01 (close)")
    res = sac.check_due(root, today="2026-07-29")
    assert res["verdict"] == "valid-fail"
    assert ("handover" in res["summary"] or "handoff" in res["summary"])
    assert "58" in res["summary"]


def test_due_signals_are_warn_tier_and_cannot_express_a_block(tmp_path):
    for setup in (dict(handoff=False), dict(handoff=True, due="soonish")):
        res = sac.check_due(_proj(tmp_path, **setup), today="2026-07-29")
        assert res["tier"] == "warn"
        assert "permissionDecision" not in res and "decision" not in res


def test_the_cli_mode_exists_and_always_exits_zero(tmp_path, capsys):
    root = _proj(tmp_path, handoff=False)
    rc = sac.main(["--root", root, "--mode", "due", "--today", "2026-07-29"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["verdict"] == "valid-fail"
