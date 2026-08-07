"""INC-109 — the due signal's second arm: mutating closes counted from the
project's own committed change trails.

The clock measures elapsed calendar; what makes a record wrong is change, and
at AI-assisted pace the two came apart (PROP-120 — the PM's own drill-1
design). The count is a filter over records every mutating close already
commits: each trail's first line carries lane, id and date (grammar:
docs/contracts/change-trail.md, cited never restated), and a trail counts
when its date is STRICTLY later than `last-verified:` (D11 — the boundary
day is not counted; the no-nagging ruling breaks the tie). The journal is
NOT the source, on D1's three grounds — the disqualifying one being that it
is per-checkout scratch a fresh clone reads as zero (KH-1/KH-2).

What the tests insist on:

- **Could-not-count is never zero** (S-109.2, FR-109.11, AC-109.9): an
  unreadable trail directory, a malformed first line, an unparseable date —
  each named as itself, never folded into a clean total or a silent calm.
- **The empty cases are silence** (FR-109.5): no trails dir, no trail newer
  than the record, no event bar — the time arm's behaviour untouched.
- **Both arms, one message** (D8, KH-5, AC-109.4): the judgement's existing
  assembly carries both facts; two greetings is the nagging the ruling
  forbids.
- **Malformed per arm** (D9, FR-109.7): a broken event bar is surfaced in
  words and skips only its own arm, both directions.
- **First line and nothing else** (S-109.3, AC-109.10): trail bodies quote
  real terminal output and the counter has no business in them.
- **Closed projects only** (D6): mid-build silence no matter the volume.
- **Nothing written** (S-109.5).
"""
import hashlib
import json
import os
import stat
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
          due=None, closes_bar=None, handoff=True):
    root = tmp_path / "proj"
    root.mkdir(exist_ok=True)
    extra = ""
    if last_verified is not None:
        extra += f"last-verified: {last_verified}\nrecord-status: verified\n"
    if due is not None:
        extra += f"reconcile-due: {due}\n"
    if closes_bar is not None:
        extra += f"reconcile-due-closes: {closes_bar}\n"
    (root / "CLAUDE.md").write_text(RECORD.format(state=state, extra=extra),
                                    encoding="utf-8")
    if handoff:
        (root / "docs" / "handoff").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "handoff" / "README.md").write_text(
            "# Start here\n", encoding="utf-8")
    return str(root)


def _trail(root, name, *, lane="feature", date="2026-08-01",
           first_line=None, body="proof: `pytest` → green\n"):
    d = os.path.join(root, "docs", "trails")
    os.makedirs(d, exist_ok=True)
    first = first_line if first_line is not None else (
        f"trail: lane={lane} id={name} date={date}")
    with open(os.path.join(d, f"{name}.md"), "w", encoding="utf-8") as fh:
        fh.write(first + "\n\n" + body)


def _due(root, today="2026-08-04"):
    return sac.check_due(root, today=today)


# --- the arm fires on volume (AC-109.1) --------------------------------------------------

def test_the_arm_fires_on_volume_and_names_the_count(tmp_path):
    root = _proj(tmp_path, closes_bar="10")
    for i in range(11):
        _trail(root, f"INC-{i}", date="2026-07-3" + str(i % 2), lane="feature")
    for i in range(11):  # rewrite with valid distinct dates after the bar
        _trail(root, f"INC-{i}", date=f"2026-07-{21 + (i % 9):02d}")
    out = _due(root)
    assert out["verdict"] == "valid-fail"
    assert "11" in out["summary"]
    assert "finished changes" in out["summary"]


def test_the_same_fixture_with_trails_removed_is_quiet(tmp_path):
    root = _proj(tmp_path, closes_bar="10")
    out = _due(root)
    assert out["verdict"] == "valid-pass"


def test_under_the_bar_is_quiet(tmp_path):
    root = _proj(tmp_path, closes_bar="10")
    for i in range(3):
        _trail(root, f"INC-{i}", date="2026-08-01")
    out = _due(root)
    assert out["verdict"] == "valid-pass"


# --- the boundary day (D11, KH-6) ---------------------------------------------------------

def test_a_close_on_the_verification_day_is_not_counted(tmp_path):
    """Strictly-later, chosen on the no-nagging ground: the arm may be late
    by one close, never early — a boundary-day trail cannot tip the bar."""
    root = _proj(tmp_path, last_verified="2026-07-20 (close)", closes_bar="2")
    _trail(root, "INC-1", date="2026-07-20")
    _trail(root, "INC-2", date="2026-07-20")
    _trail(root, "INC-3", date="2026-07-21")
    out = _due(root)
    assert out["verdict"] == "valid-pass"
    _trail(root, "INC-4", date="2026-07-22")
    _trail(root, "INC-5", date="2026-07-23")
    out2 = _due(root)
    assert out2["verdict"] == "valid-fail" and "3" in out2["summary"]


# --- every lane counts one, breakdown honest (FR-109.3, AC-109.8) -------------------------

def test_every_lane_counts_one_and_the_breakdown_matches(tmp_path):
    root = _proj(tmp_path, closes_bar="3")
    _trail(root, "BUG-1", lane="bug", date="2026-07-25")
    _trail(root, "PATCH-1", lane="patch", date="2026-07-26")
    _trail(root, "INC-1", lane="feature", date="2026-07-27")
    _trail(root, "INC-2", lane="feature", date="2026-07-28")
    out = _due(root)
    assert out["verdict"] == "valid-fail"
    assert "4" in out["summary"]
    assert "1 bug" in out["summary"] and "1 patch" in out["summary"] \
        and "2 feature" in out["summary"]


def test_an_unrecognised_lane_is_named_not_counted_not_dropped(tmp_path):
    root = _proj(tmp_path, closes_bar="10")
    _trail(root, "X-1", first_line="trail: lane=cowboy id=X-1 date=2026-08-01")
    out = _due(root)
    assert out["verdict"] == "valid-fail"
    assert "cowboy" in out["summary"] or "X-1" in out["summary"]


# --- could-not-count is never zero (AC-109.9, S-109.2, KH-1) ------------------------------

def test_an_unreadable_trail_directory_is_could_not_count_never_zero(tmp_path):
    root = _proj(tmp_path, closes_bar="10")
    d = os.path.join(root, "docs", "trails")
    os.makedirs(d)
    os.chmod(d, 0)
    try:
        out = _due(root)
        assert out["verdict"] == "valid-fail"
        assert "could not" in out["summary"].lower()
    finally:
        os.chmod(d, stat.S_IRWXU)


def test_a_trail_with_a_malformed_first_line_is_named(tmp_path):
    root = _proj(tmp_path, closes_bar="10")
    _trail(root, "INC-good", date="2026-08-01")
    _trail(root, "broken", first_line="## not a tag line at all")
    out = _due(root)
    assert out["verdict"] == "valid-fail"
    assert "broken" in out["summary"]


def test_a_trail_whose_date_wont_parse_is_named(tmp_path):
    root = _proj(tmp_path, closes_bar="10")
    _trail(root, "INC-odd",
           first_line="trail: lane=feature id=INC-odd date=yesterday")
    out = _due(root)
    assert out["verdict"] == "valid-fail"
    assert "INC-odd" in out["summary"]


# --- the bar line (FR-109.4, D2/D3) --------------------------------------------------------

def test_the_projects_own_bar_overrides_the_default(tmp_path):
    root = _proj(tmp_path, closes_bar="3")
    for i in range(4):
        _trail(root, f"INC-{i}", date="2026-08-01")
    out = _due(root)
    assert out["verdict"] == "valid-fail" and "3-close" in out["summary"]


def test_without_its_own_line_the_default_of_ten_applies(tmp_path):
    root = _proj(tmp_path)
    for i in range(11):
        _trail(root, f"INC-{i}", date="2026-08-01")
    out = _due(root)
    assert out["verdict"] == "valid-fail"
    assert "11" in out["summary"] and "10-close" in out["summary"]


# --- malformed per arm (FR-109.7, D9, AC-109.5) --------------------------------------------

def test_a_malformed_event_bar_is_surfaced_and_the_time_arm_still_judges(tmp_path):
    root = _proj(tmp_path, last_verified="2026-06-01 (close)", due="30d",
                 closes_bar="lots")
    for i in range(20):
        _trail(root, f"INC-{i}", date="2026-07-01")
    out = _due(root)
    assert out["verdict"] == "valid-fail"
    assert "reconcile-due-closes: lots" in out["summary"]
    assert "days ago" in out["summary"]
    assert "20" not in out["summary"]  # the broken arm contributes no count


def test_a_malformed_time_bar_leaves_the_event_arm_working(tmp_path):
    root = _proj(tmp_path, due="fortnight", closes_bar="3")
    for i in range(4):
        _trail(root, f"INC-{i}", date="2026-08-01")
    out = _due(root)
    assert out["verdict"] == "valid-fail"
    assert "reconcile-due: fortnight" in out["summary"]
    assert "4" in out["summary"] and "finished changes" in out["summary"]


# --- both arms, one message (AC-109.4, D8, KH-5) -------------------------------------------

def test_both_arms_trip_as_one_message_carrying_both_facts(tmp_path):
    root = _proj(tmp_path, last_verified="2026-06-01 (close)", due="30d",
                 closes_bar="3")
    for i in range(4):
        _trail(root, f"INC-{i}", date="2026-07-15")
    out = _due(root)
    assert out["verdict"] == "valid-fail"
    assert "days ago" in out["summary"]
    assert "finished changes" in out["summary"]
    assert isinstance(out["summary"], str)  # one assembled message, not two


# --- scope, blindness, and writes (D6, S-109.3, S-109.5) -----------------------------------

def test_a_mid_build_project_is_silent_whatever_the_volume(tmp_path):
    root = _proj(tmp_path, state="build-in-progress", last_verified=None,
                 handoff=False)
    for i in range(30):
        _trail(root, f"INC-{i}", date="2026-08-01")
    out = _due(root)
    assert out["verdict"] == "valid-pass"


def test_trail_bodies_are_never_read(tmp_path):
    root = _proj(tmp_path, closes_bar="1")
    _trail(root, "INC-1", date="2026-08-01",
           body="proof: PLANTED-BODY-TOKEN-zz93 leaked terminal output\n")
    _trail(root, "INC-2", date="2026-08-02")
    out = _due(root)
    assert out["verdict"] == "valid-fail"
    assert "PLANTED-BODY-TOKEN-zz93" not in json.dumps(out)


def test_the_counter_writes_nothing(tmp_path):
    root = _proj(tmp_path, closes_bar="1")
    for i in range(3):
        _trail(root, f"INC-{i}", date="2026-08-01")
    def treehash(p):
        h = hashlib.sha256()
        for dp, dn, fn in sorted(os.walk(p)):
            for f in sorted(fn):
                fp = os.path.join(dp, f)
                h.update(fp.encode()); h.update(open(fp, "rb").read())
        return h.hexdigest()
    before = treehash(root)
    _due(root)
    assert treehash(root) == before
