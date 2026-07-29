"""PROP-028 / D-0106 — the dirty bit gets a writer.

`/friday:reconcile` has always cleared `record-status: stale` back to `verified`.
Nothing ever SET it. So the promise "closed never means frozen — any later
mutation flips the record stale" was one half of a mechanism: reconcile
faithfully cleared a flag that could not arrive, and record drift after close was
invisible. Found independently twice (NF3, and the state-matrix audit), ratified
as D-0106, and this is the missing half.

Two properties decide whether this is worth having:

**It edits one line and nothing else.** The obvious implementation — read the
block, rebuild it with `taglines.format_block` — would reorder fields, drop
comments, and quietly rewrite a record that several gates read. A tool that
corrupts the state record while marking it stale is worse than no tool. So the
byte-preservation test below is the real one; the rest are bookkeeping.

**It is silent where the bit does not exist.** `record-status:` lives on a CLOSED
project's record only. Every lane will call this on every run, including the
hundreds of runs against projects that are mid-build or have no state block at
all, so "not applicable" has to be an ordinary, quiet, tested outcome — not an
error, and never a lazily-created field.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import state_record  # noqa: E402

CLOSED = """# proj

Some prose a human wrote.

<!-- FRIDAY-STATE:BEGIN -->
stack: path:python3
non-goal: third-party runtime dependencies
state: closed
tsow: docs/TECHNICAL_SOW.md
since: 2026-07-12T16:20:00Z
last-verified: 2026-07-20
record-status: {status}
<!-- FRIDAY-STATE:END -->

## Conventions

- more prose below the block.
"""

BUILDING = CLOSED.replace("state: closed", "state: build-in-progress")


def _proj(tmp_path, text):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "CLAUDE.md").write_text(text, encoding="utf-8")
    return str(root)


def _claude(root):
    return open(os.path.join(root, "CLAUDE.md"), encoding="utf-8").read()


# --- the empty cases: quiet, and never a lazily-created field ------------------------

def test_a_project_with_no_state_block_is_a_quiet_no_op(tmp_path):
    root = _proj(tmp_path, "# proj\n\nNo state block here.\n")
    before = _claude(root)
    res = state_record.mark_stale(root)
    assert res["ok"] is True and res["changed"] is False
    assert _claude(root) == before


def test_an_open_project_is_a_quiet_no_op(tmp_path):
    """The bit only exists on a closed record. Mid-build there is nothing to
    dirty — the whole project is in motion by definition."""
    root = _proj(tmp_path, BUILDING.format(status="verified"))
    before = _claude(root)
    res = state_record.mark_stale(root)
    assert res["ok"] is True and res["changed"] is False
    assert "closed" in res["detail"]
    assert _claude(root) == before


def test_a_missing_project_is_not_a_crash(tmp_path):
    res = state_record.mark_stale(str(tmp_path / "nope"))
    assert res["ok"] is True and res["changed"] is False


# --- setting the bit (the half that never existed) -----------------------------------

def test_landing_changes_on_a_closed_project_marks_the_record_stale(tmp_path):
    root = _proj(tmp_path, CLOSED.format(status="verified"))
    res = state_record.mark_stale(root)
    assert res["ok"] is True and res["changed"] is True
    assert "record-status: stale" in _claude(root)


def test_marking_stale_leaves_last_verified_alone(tmp_path):
    """`last-verified:` records WHEN the record was last confirmed true. Moving
    it while marking the record stale would erase the very gap reconcile exists
    to notice."""
    root = _proj(tmp_path, CLOSED.format(status="verified"))
    state_record.mark_stale(root)
    assert "last-verified: 2026-07-20" in _claude(root)


def test_marking_stale_is_idempotent(tmp_path):
    """Three lanes may each land changes before one reconcile. The second call
    must be a no-op, not a second flip or a duplicated field."""
    root = _proj(tmp_path, CLOSED.format(status="verified"))
    state_record.mark_stale(root)
    once = _claude(root)
    res = state_record.mark_stale(root)
    assert res["changed"] is False
    assert _claude(root) == once
    assert once.count("record-status:") == 1


# --- clearing it: reconcile's exclusive -----------------------------------------------

def test_reconcile_clears_the_bit_and_refreshes_last_verified(tmp_path):
    root = _proj(tmp_path, CLOSED.format(status="stale"))
    res = state_record.mark_verified(root, when="2026-07-29")
    assert res["ok"] is True and res["changed"] is True
    text = _claude(root)
    assert "record-status: verified" in text
    assert "last-verified: 2026-07-29" in text
    assert "2026-07-20" not in text


def test_reconcile_re_dates_a_record_that_was_already_verified(tmp_path):
    """A clean reconcile run IS a fresh confirmation, so the date moves even
    when the status does not. Otherwise `last-verified:` ages forever on a
    healthy project and eventually reads as neglect — the opposite of true."""
    root = _proj(tmp_path, CLOSED.format(status="verified"))
    assert state_record.mark_verified(root, when="2026-07-29")["changed"] is True
    assert "last-verified: 2026-07-29" in _claude(root)


def test_reconcile_drops_the_close_annotation_it_is_no_longer_true(tmp_path):
    """The real closer writes `last-verified: <date> (close)` — the shape this
    tool actually meets in the wild (agents/roles/closer.md step 5). Once
    reconcile re-dates it the stamp is a reconcile, not a close, so carrying the
    `(close)` annotation forward would be a false claim about its own origin.
    K5 requires the field to be PRESENT, not annotated, so dropping it keeps a
    closed record verifiable — checked here because reconcile breaking the
    record it just certified would be the worst possible failure of this tool."""
    root = _proj(tmp_path, CLOSED.format(status="stale").replace(
        "last-verified: 2026-07-20", "last-verified: 2026-07-20 (close)"))
    assert state_record.mark_verified(root, when="2026-07-29")["changed"] is True
    text = _claude(root)
    assert "last-verified: 2026-07-29" in text
    assert "(close)" not in text


def test_marking_stale_preserves_the_close_annotation(tmp_path):
    """The mirror: marking stale must not touch that line at all, annotation
    included. Only the clear re-dates."""
    root = _proj(tmp_path, CLOSED.format(status="verified").replace(
        "last-verified: 2026-07-20", "last-verified: 2026-07-20 (close)"))
    state_record.mark_stale(root)
    assert "last-verified: 2026-07-20 (close)" in _claude(root)


def test_a_second_reconcile_on_the_same_day_changes_nothing(tmp_path):
    """The genuine no-op: same status, same date, so there is nothing to say."""
    root = _proj(tmp_path, CLOSED.format(status="verified"))
    state_record.mark_verified(root, when="2026-07-29")
    once = _claude(root)
    assert state_record.mark_verified(root, when="2026-07-29")["changed"] is False
    assert _claude(root) == once


# --- the one that matters: it edits a line, not the record --------------------------

def test_only_the_status_line_changes_and_the_file_is_otherwise_byte_identical(tmp_path):
    """Several gates read this block. Rebuilding it from parsed fields would
    reorder them, drop the comment markers' neighbours, and rewrite a record the
    closer, the foundation gate and the epoch resolver all depend on."""
    root = _proj(tmp_path, CLOSED.format(status="verified"))
    before = _claude(root).split("\n")
    state_record.mark_stale(root)
    after = _claude(root).split("\n")
    assert len(before) == len(after)
    differing = [(b, a) for b, a in zip(before, after) if b != a]
    assert differing == [("record-status: verified", "record-status: stale")], differing


def test_a_closed_record_missing_the_field_refuses_rather_than_inventing_it(tmp_path):
    """verify_state's K5 blocks a close without this field, so a closed record
    that lacks it is already broken. Silently adding one would paper over that
    and backdate a claim nobody made."""
    text = CLOSED.format(status="verified").replace("record-status: verified\n", "")
    root = _proj(tmp_path, text)
    before = _claude(root)
    res = state_record.mark_stale(root)
    assert res["ok"] is False and res["changed"] is False
    assert "record-status" in res["detail"]
    assert _claude(root) == before


# --- the shape the lanes consume ------------------------------------------------------

def test_the_cli_reports_its_outcome_and_exits_zero_when_not_applicable(tmp_path, capsys):
    root = _proj(tmp_path, BUILDING.format(status="verified"))
    assert state_record.main(["--mark", "stale", "--root", root]) == 0
    assert "changed" in capsys.readouterr().out


def test_the_cli_exits_nonzero_when_it_could_not_do_what_was_asked(tmp_path):
    text = CLOSED.format(status="verified").replace("record-status: verified\n", "")
    root = _proj(tmp_path, text)
    assert state_record.main(["--mark", "stale", "--root", root]) == 1
