"""Logic-core tests (A.5 #2, #4, #7) — written BEFORE tools/decisions.py exists.

#2  DECISIONS.md schema parser/serializer incl. the A.2 empty form.
#4  three-part-test + floor-category classifier's mechanical checks.
#7  D-NNNN monotonic-ID assignment — including under concurrency (Appendix B.2).
"""
import concurrent.futures
import os
import subprocess

import pytest

import decisions


# --- A.2 empty form -----------------------------------------------------------

def test_empty_form_roundtrip():
    text = decisions.empty_form()
    assert text.startswith("# Decisions")
    assert decisions.EMPTY_SENTINEL in text
    res = decisions.parse(text)
    assert res["ok"] and res["empty"] and res["entries"] == [] and res["errors"] == []


def test_zero_byte_and_missing_H1_are_not_valid_empty_forms():
    assert not decisions.parse("")["ok"]                       # zero-byte file
    assert not decisions.parse("# Decisions — x\n")["ok"]      # bare heading, no sentinel


def test_sentinel_plus_entries_is_malformed():
    text = decisions.empty_form() + "\n" + _entry(1)
    res = decisions.parse(text)
    assert not res["ok"]  # sentinel must be REPLACED by the first entry, never coexist


# --- schema parse/serialize ---------------------------------------------------

def _entry(n, channel="model-autonomous", weight="two-way", floor="none",
           back_filled=False, when="2026-07-12T16:00:00Z"):
    return decisions.format_entry(
        id_num=n, title=f"choice {n}", when=when, channel=channel,
        weight=weight, floor=floor, back_filled=back_filled,
        decision="what", why="because", rejected="the other thing")


def test_parse_roundtrip_single_entry():
    text = decisions.empty_form().replace(decisions.EMPTY_SENTINEL, "").rstrip() + "\n\n" + _entry(1)
    res = decisions.parse(text)
    assert res["ok"] and not res["empty"]
    [e] = res["entries"]
    assert e["id"] == 1 and e["id_str"] == "D-0001"
    assert e["channel"] == "model-autonomous" and e["weight"] == "two-way"
    assert e["floor"] == "none" and e["back_filled"] is False
    assert e["decision"] == "what" and e["why"] == "because" and e["rejected"] == "the other thing"


def test_parse_flags_missing_mandatory_bullets():
    bad = _entry(1).replace("- **Why:** because\n", "")
    res = decisions.parse("# Decisions — x\n\n" + bad)
    assert not res["ok"]
    assert any("Why" in err for err in res["errors"])


def test_parse_back_filled_marker():
    text = "# Decisions — x\n\n" + _entry(1, back_filled=True)
    [e] = decisions.parse(text)["entries"]
    assert e["back_filled"] is True


# --- classifier mechanical checks (#4) -----------------------------------------

def test_floor_vocabulary_is_closed():
    assert decisions.validate_fields("model-autonomous", "one-way", "schema-data") == []
    errs = decisions.validate_fields("model-autonomous", "one-way", "performance")
    assert errs and "floor" in errs[0]


def test_floor_category_forces_one_way():
    """PROP-044 categorical override: anything touching a floor category is
    one-way regardless of the three-part conclusion."""
    errs = decisions.validate_fields("pm-ratified", "two-way", "auth-security")
    assert errs and "one-way" in errs[0]


def test_channel_vocabulary_is_closed():
    assert decisions.validate_fields("pm-ratified", "two-way", "none") == []
    assert decisions.validate_fields("somebody", "two-way", "none")


# --- decision-ask shape (Channel A contract) -----------------------------------

ASK = """[FRIDAY-DECISION] Session store choice
decision: which session store the API uses
why: redis is already in the stack and survives restarts
rejected: in-memory dict (loses sessions on deploy); postgres table (extra migration)
floor: schema-data
weight: one-way
"""


def test_parse_decision_ask_shape():
    d = decisions.parse_decision_ask(ASK)
    assert d["title"] == "Session store choice"
    assert d["floor"] == "schema-data" and d["weight"] == "one-way"
    assert "redis" in d["why"]


def test_ordinary_question_is_not_a_decision_ask():
    assert decisions.parse_decision_ask("Should I also update the README?") is None


# --- D-NNNN monotonicity (#7), incl. concurrency --------------------------------

@pytest.fixture()
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "DECISIONS.md").write_text(decisions.empty_form(), encoding="utf-8")
    return tmp_path


def test_append_replaces_sentinel_and_assigns_ids(repo):
    id1, _ = decisions.append_entry(str(repo), title="a", decision="d", why="w", rejected="r")
    id2, _ = decisions.append_entry(str(repo), title="b", decision="d", why="w", rejected="r")
    assert (id1, id2) == ("D-0001", "D-0002")
    text = (repo / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    assert decisions.EMPTY_SENTINEL not in text
    res = decisions.parse(text)
    assert res["ok"] and [e["id"] for e in res["entries"]] == [1, 2]


def test_concurrent_appends_never_collide(repo):
    """Appendix B.2: the monotonic id is allocated under an advisory lock so
    concurrent writers cannot collide or reuse an id."""
    def one(i):
        return decisions.append_entry(str(repo), title=f"t{i}", decision="d",
                                      why="w", rejected="r")[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        ids = list(ex.map(one, range(24)))
    assert len(set(ids)) == 24
    res = decisions.parse((repo / "docs" / "DECISIONS.md").read_text(encoding="utf-8"))
    assert res["ok"]
    got = sorted(e["id"] for e in res["entries"])
    assert got == list(range(1, 25))


def test_counter_survives_worktree_split(repo):
    """Appendix B: two worktrees share one .friday/, so IDs allocated from a
    linked worktree continue the main repo's sequence."""
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c",
                    "user.name=t", "commit", "-qm", "seed"], check=True)
    wt = repo.parent / (repo.name + "-wt")
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", str(wt)], check=True)
    id1, _ = decisions.append_entry(str(repo), title="main", decision="d", why="w", rejected="r")
    id2, _ = decisions.append_entry(str(wt), title="wt", decision="d", why="w", rejected="r")
    assert id1 == "D-0001" and id2 == "D-0002"          # one shared counter
    assert (repo / ".friday").is_dir()
    assert not (wt / ".friday").exists()                 # substrate never fragments


def test_archive_discipline(repo):
    for i in range(12):
        decisions.append_entry(str(repo), title=f"t{i}", decision="d", why="w",
                               rejected="r", cap=10)
    main = decisions.parse((repo / "docs" / "DECISIONS.md").read_text(encoding="utf-8"))
    assert main["ok"] and len(main["entries"]) <= 10
    archives = list((repo / "docs" / "decisions").glob("archive-*.md"))
    assert archives, "cap exceeded must MOVE oldest entries to an archive file"
    arch = decisions.parse(archives[0].read_text(encoding="utf-8"))
    assert arch["ok"] and arch["entries"], "archived entries stay schema-valid"


# --- override-grant lines survive the round trip (the rotation-strip bug) ------
#
# Found live: the archiver re-renders every entry it touches through the
# parser, and the parser never carried the typed `override-grant:` line — so
# the rotation that trims the log also silently destroyed every structured
# authorization in it, live file and archive both. The grant is the one line
# the frozen-artifact guards trust; a record type whose maintenance pass
# strips authorizations is worse than no maintenance pass.

def test_parse_carries_the_override_grant_line():
    granted = decisions.format_entry(
        id_num=7, title="grant carrier", when="2026-08-04T10:00:00Z",
        channel="pm-ratified", weight="two-way", floor="none", back_filled=False,
        decision="d", why="w", rejected="r",
        override_grant="docs/contracts/parked-ledger.md (test reason)")
    [e] = decisions.parse("# Decisions — x\n\n" + granted)["entries"]
    assert e["override_grant"] == "docs/contracts/parked-ledger.md (test reason)"


def test_rotation_preserves_override_grants_in_live_and_archive(repo):
    """cap=10, 12 appends → the oldest half rotates out. A grant on an entry
    that gets ARCHIVED must survive in the archive; a grant on an entry that
    stays LIVE must survive the live file's re-render. Both were stripped."""
    for i in range(12):
        grant = None
        if i == 1:
            grant = "docs/contracts/archived-target.md (rotates out)"
        if i == 8:
            grant = "docs/contracts/live-target.md (stays live)"
        decisions.append_entry(str(repo), title=f"t{i}", decision="d", why="w",
                               rejected="r", cap=10, override_grant=grant)
    live = (repo / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    assert decisions.has_override_grant(live, "docs/contracts/live-target.md")
    [archive] = (repo / "docs" / "decisions").glob("archive-*.md")
    arch = archive.read_text(encoding="utf-8")
    assert "override-grant: docs/contracts/archived-target.md (rotates out)" in arch
    assert decisions.parse(arch)["ok"], "archive stays schema-valid with grants"
