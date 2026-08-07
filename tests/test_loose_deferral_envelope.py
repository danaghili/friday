"""INC-107 FR-107.10 — the loose-deferral envelope checker.

A sibling of the maintainability envelope, by that contract's own reasoning
(D10): the findings brief carries a severity axis, the maintainability
envelope a disposition axis; this seam's axis is whether a decision has a
route back, and the answer comes from the PM, not a judge. Same structural
pattern, same tagline grammar, its own contract.

What the tests insist on (the pattern's proven teeth, re-applied):
- the tag line is first and its count is TRUE — a header that lies is refused;
- a heading that looks like a candidate but does not parse is an ERROR, never
  tolerated prose (a dropped candidate is the silent miss, S-107.2);
- every candidate carries every required field, and the home answer is one of
  the three ruled words with its evidence attached (FR-107.4);
- the empty case is first-class: count=0 requires a non-empty `## Scanned`
  section — a run that reached nothing must not read as a run that found
  nothing (FR-107.8);
- what the scan could not reach is named: declared unread/unparsed counts
  require the matching `## Unreached` lines;
- the producer writes THROUGH the checker to the substrate-resolved path —
  a malformed envelope bounces and touches nothing.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import loose_deferral_envelope_check as chk  # noqa: E402


def _envelope(findings=None, extra="", **counts):
    c = {"count": 2, "remainder": 3, "recognized": 5, "unread": 0,
         "unparsed": 0, **counts}
    head = (f"loose-deferral-envelope: source=deep-clean count={c['count']} "
            f"remainder={c['remainder']} recognized={c['recognized']} "
            f"unread={c['unread']} unparsed={c['unparsed']}\n")
    if findings is None:
        findings = [
            "## LD-1 — src/app/health/route.ts:1-12 (recommend: capture)\n"
            "id:      0a1b2c3d4e5f\n"
            "text:    INTENTIONALLY MINIMAL health check — liveness only, no DB ping\n"
            "reading: a real deferral: the block records a accepted trade-off with revisit conditions\n"
            "home:    homeless — 3-architecture.md 'When to revisit' explains the trade and schedules nothing\n",
            "## LD-2 — src/lib/webhook.ts:40-41 (recommend: leave-standing)\n"
            "id:      ffee00112233\n"
            "text:    TODO (F063): stuck-sending recovery is manual SQL surgery\n"
            "reading: a real deferral: manual recovery is a decision awaiting tooling\n"
            "home:    homed — F063 is open in the project's FEATURES.md tracker\n",
        ]
    return head + "\n" + "\n".join(findings) + extra


def test_valid_envelope_passes_and_extracts():
    res = chk.check_text(_envelope())
    assert res["verdict"] == "valid-pass", res["errors"]
    assert res["count"] == 2 and res["remainder"] == 3 and res["recognized"] == 5
    assert res["findings"][0]["recommend"] == "capture"
    assert res["findings"][0]["home"].startswith("homeless")


def test_header_count_lie_is_refused():
    res = chk.check_text(_envelope(count=5))
    assert res["verdict"] == "valid-fail"
    assert any("true count" in e for e in res["errors"])


def test_malformed_candidate_heading_is_an_error_never_dropped():
    res = chk.check_text(_envelope(count=1, findings=[
        "## LD-1 — src/x.ts lines twelve-ish (recommend: capture)\n"
        "id:      0a1b2c3d4e5f\ntext: t\nreading: r\nhome: homed — x\n"]))
    assert res["verdict"] == "valid-fail"
    assert any("does not parse" in e for e in res["errors"])


def test_unknown_recommendation_is_refused():
    res = chk.check_text(_envelope(count=1, findings=[
        "## LD-1 — src/x.ts:1-2 (recommend: shrug)\n"
        "id:      0a1b2c3d4e5f\ntext: t\nreading: r\nhome: homed — x\n"]))
    assert res["verdict"] == "valid-fail"


def test_missing_required_field_is_refused():
    res = chk.check_text(_envelope(count=1, findings=[
        "## LD-1 — src/x.ts:1-2 (recommend: dismiss)\n"
        "id:      0a1b2c3d4e5f\ntext: t\nhome: homed — x\n"]))
    assert res["verdict"] == "valid-fail"
    assert any("reading" in e for e in res["errors"])


def test_home_answer_must_be_ruled_word_plus_evidence():
    for bad in ("home: probably fine\n", "home: homed\n"):
        res = chk.check_text(_envelope(count=1, findings=[
            "## LD-1 — src/x.ts:1-2 (recommend: dismiss)\n"
            "id:      0a1b2c3d4e5f\ntext: t\nreading: r\n" + bad]))
        assert res["verdict"] == "valid-fail", bad


def test_duplicate_candidate_numbers_are_refused():
    f = ("## LD-1 — src/x.ts:1-2 (recommend: dismiss)\n"
         "id:      0a1b2c3d4e5f\ntext: t\nreading: r\nhome: homed — x\n")
    res = chk.check_text(_envelope(count=2, findings=[f, f]))
    assert res["verdict"] == "valid-fail"
    assert any("unique" in e for e in res["errors"])


def test_empty_case_requires_scanned_section():
    bare = ("loose-deferral-envelope: source=deep-clean count=0 remainder=0 "
            "recognized=4 unread=0 unparsed=0\n")
    res = chk.check_text(bare)
    assert res["verdict"] == "valid-fail"
    ok = chk.check_text(bare + "\n## Scanned\n212 files scanned, 4 candidates "
                               "all previously answered and passed over.\n")
    assert ok["verdict"] == "valid-pass", ok["errors"]


def test_declared_unread_requires_matching_unreached_lines():
    res = chk.check_text(_envelope(unread=1))
    assert res["verdict"] == "valid-fail"
    ok = chk.check_text(_envelope(unread=1, unparsed=1, extra=(
        "\n## Unreached\nunread: secrets/locked.env\nunparsed: native/lib.zig\n")))
    assert ok["verdict"] == "valid-pass", ok["errors"]


def test_write_lands_only_a_valid_envelope(tmp_path, capsys):
    rc = chk.main(["--write", "--root", str(tmp_path)],
                  stdin_text=_envelope())
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["verdict"] == "valid-pass"
    assert os.path.isfile(out["path"])

    rc = chk.main(["--write", "--root", str(tmp_path)],
                  stdin_text=_envelope(count=9))
    out2 = json.loads(capsys.readouterr().out)
    assert rc == 1 and out2["verdict"] == "valid-fail"
    # the malformed body touched nothing: the valid one is still on disk
    assert "count=2" in open(out["path"], encoding="utf-8").read()


def test_missing_file_is_valid_fail_not_a_crash(tmp_path, capsys):
    rc = chk.main(["--file", str(tmp_path / "nope.md")])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1 and out["verdict"] == "valid-fail"
