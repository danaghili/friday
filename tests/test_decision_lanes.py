"""Decision-id lane enforcement (D-0152, mechanism added 2026-07-30).

The lane rule predates this module: one development clone mints below
D-1000, the other from D-1000 up. Pre-merge that held "by construction"
because each machine's log only contained its own entries and allocation is
highest-seen + 1. The 2026-07-29 lab-line merge put both lanes into ONE
shared log, so the construction silently died: the first post-merge mint ran
on the low-lane clone and came out D-1007 — inside the other clone's
lane — and the substrate counter was poisoned to 1007 with it. These tests
pin the repaired contract: allocation counts only ids inside the lane
`git config friday.decision-id-base` selects (unset = the low lane), an
empty lane starts at its base (the D-0113 shape), an exhausted lane fails
loudly writing nothing, and the monotonic counter still guards — but only
within its own lane.
"""
import os
import subprocess

import pytest

import decisions


def _seed_entry(n: int) -> str:
    return decisions.format_entry(
        id_num=n, title=f"seed {n}", when="2026-07-29T00:00:00Z",
        channel="pm-ratified", weight="two-way", floor="none",
        back_filled=False, decision="d", why="w", rejected="r",
        override_grant=None)


def _seed_log(tmp_path, ids):
    header = "\n".join(
        ln for ln in decisions.empty_form().splitlines()
        if ln.strip() != decisions.EMPTY_SENTINEL).rstrip()
    text = header + "".join("\n\n" + _seed_entry(n) for n in ids) + "\n"
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "DECISIONS.md").write_text(text, encoding="utf-8")
    parsed = decisions.parse(text)
    assert parsed["ok"], f"seed log must parse clean: {parsed['errors']}"


@pytest.fixture()
def merged_repo(tmp_path):
    """A repo whose log holds BOTH machines' lanes — the post-merge reality."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    _seed_log(tmp_path, [152, 1006])
    return tmp_path


def _set_base(repo, value: int) -> None:
    subprocess.run(["git", "-C", str(repo), "config",
                    "friday.decision-id-base", str(value)], check=True)


def _write_counter(repo, value: int) -> None:
    os.makedirs(decisions.fs.friday_dir(str(repo)), exist_ok=True)
    decisions._write_counter(str(repo), value)


def test_low_lane_machine_ignores_high_lane_entries_and_poisoned_counter(merged_repo):
    """The live incident: merged log holds D-0152 and D-1006, the counter says
    1007, and a machine with no configured base (= the low lane) must still
    mint D-0153 — never continue the high lane's sequence."""
    _write_counter(merged_repo, 1007)
    id1, _ = decisions.append_entry(str(merged_repo), title="t", decision="d",
                                    why="w", rejected="r")
    assert id1 == "D-0153"


def test_high_lane_machine_continues_its_own_lane(merged_repo):
    """A machine configured with base 1000 sees the same merged log and mints
    D-1007 — its lane's next id, blind to the low lane's D-0152."""
    _set_base(merged_repo, 1000)
    id1, _ = decisions.append_entry(str(merged_repo), title="t", decision="d",
                                    why="w", rejected="r")
    assert id1 == "D-1007"


def test_empty_lane_starts_at_its_base(tmp_path):
    """A machine whose lane holds no entries yet mints exactly its base —
    the same empty-range rule as INC/PROP allocation (D-0113)."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    _seed_log(tmp_path, [152])
    _set_base(tmp_path, 1000)
    id1, _ = decisions.append_entry(str(tmp_path), title="t", decision="d",
                                    why="w", rejected="r")
    assert id1 == "D-1000"


def test_exhausted_lane_fails_loudly_and_writes_nothing(tmp_path):
    """A full lane must refuse — never spill into the neighbour's range. The
    refusal is a raise before any write: log bytes and counter unchanged."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    _seed_log(tmp_path, [999])
    log = tmp_path / "docs" / "DECISIONS.md"
    before = log.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="lane"):
        decisions.append_entry(str(tmp_path), title="t", decision="d",
                               why="w", rejected="r")
    assert log.read_text(encoding="utf-8") == before
    assert decisions._read_counter(str(tmp_path)) in (0, 999)


def test_counter_still_guards_monotonicity_within_its_lane(tmp_path):
    """The counter's original job survives the fix: if in-lane entries were
    deleted or archived, the counter stops id reuse — an in-lane counter above
    the surviving entries wins."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    _seed_log(tmp_path, [152])
    _write_counter(tmp_path, 500)
    id1, _ = decisions.append_entry(str(tmp_path), title="t", decision="d",
                                    why="w", rejected="r")
    assert id1 == "D-0501"
