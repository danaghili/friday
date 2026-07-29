"""tools/capture_integrity.py — the §6.6 retro-fabrication smell detector (task #14).

Reconcile's temporal-honesty check: model-autonomous decision entries all
stamped within one narrow window look like a log reconstructed at the end —
a rationalization, not a record. Warn-level by design (a smell, never proof),
with `back-filled: true` as the first-class honest exemption. Entries are
planted through the real writer (`decisions.append_entry` with controlled
`when` stamps) so the parse side stays real too.
"""
import json
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_BASE, "tools"))
import capture_integrity as ci  # noqa: E402
import decisions  # noqa: E402


def _proj(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".friday").mkdir()
    return str(root)


def _plant(root, when, *, back_filled=False, n=1):
    decisions.append_entry(root, title=f"call {n} at {when}", decision="x",
                           why="y", rejected="z", when=when,
                           back_filled=back_filled)


def test_an_organic_spread_is_clean(tmp_path):
    root = _proj(tmp_path)
    for n, when in enumerate(("2026-07-29T09:00:00Z", "2026-07-29T11:30:00Z",
                              "2026-07-29T14:00:00Z", "2026-07-29T16:45:00Z")):
        _plant(root, when, n=n)
    res = ci.check(root)
    assert res["ok"] and res["findings"] == []
    assert res["live"] == 4 and res["back_filled"] == 0
    assert "organic" in res["summary"]


def test_end_clustered_entries_are_the_smell(tmp_path):
    """Four live entries inside fifteen minutes: the exact shape of a log
    written in one sitting at the end of the build."""
    root = _proj(tmp_path)
    for n, when in enumerate(("2026-07-29T16:00:00Z", "2026-07-29T16:03:00Z",
                              "2026-07-29T16:07:00Z", "2026-07-29T16:11:00Z")):
        _plant(root, when, n=n)
    res = ci.check(root)
    assert res["ok"]                                   # a smell, not a failure
    (finding,) = res["findings"]
    assert finding["severity"] == "warn"
    assert "retro-fabrication" in finding["detail"]


def test_back_filled_entries_are_exempt_by_design(tmp_path):
    """The tag exists precisely so an honest back-fill session (A.4) is never
    misread as fabrication — clustered stamps with back-filled: true raise
    nothing."""
    root = _proj(tmp_path)
    for n, when in enumerate(("2026-07-29T16:00:00Z", "2026-07-29T16:03:00Z",
                              "2026-07-29T16:07:00Z", "2026-07-29T16:11:00Z")):
        _plant(root, when, back_filled=True, n=n)
    res = ci.check(root)
    assert res["ok"] and res["findings"] == []
    assert res["live"] == 0 and res["back_filled"] == 4


def test_below_the_entry_floor_never_smells(tmp_path):
    """Three clustered entries is a normal burst of related calls, not a
    reconstruction — the detector needs volume before it speaks."""
    root = _proj(tmp_path)
    for n, when in enumerate(("2026-07-29T16:00:00Z", "2026-07-29T16:01:00Z",
                              "2026-07-29T16:02:00Z")):
        _plant(root, when, n=n)
    assert ci.check(root)["findings"] == []


def test_an_unparseable_timestamp_is_surfaced_not_dropped(tmp_path):
    """A stamp that won't parse silently shrinking the live set would hide
    exactly the entries most worth a look — it becomes its own warn."""
    root = _proj(tmp_path)
    for n, when in enumerate(("2026-07-29T09:00:00Z", "2026-07-29T12:00:00Z")):
        _plant(root, when, n=n)
    log = os.path.join(root, decisions.DEFAULT_PATH)
    text = open(log, encoding="utf-8").read()
    with open(log, "w", encoding="utf-8") as fh:
        fh.write(text.replace("2026-07-29T12:00:00Z", "sometime thursday"))
    res = ci.check(root)
    assert any("unparseable" in f["detail"] for f in res["findings"])


def test_a_malformed_log_is_blocking_and_exits_nonzero(tmp_path, capsys):
    root = _proj(tmp_path)
    path = os.path.join(root, decisions.DEFAULT_PATH)
    os.makedirs(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("## D-x — this is not the grammar\n")
    assert ci.main(["--root", root, "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert not out["ok"]
    assert out["findings"][0]["severity"] == "blocking"


def test_the_zero_decision_form_is_a_clean_pass_but_a_missing_log_is_not(tmp_path):
    """The grammar's empty case vs the absent case, kept distinct on purpose:
    the A.2 zero-decision form has nothing to smell (clean pass), while a log
    that does not EXIST means the record is gone — the check refuses to vouch
    for integrity it cannot read (the same doctrine as consuming an absent
    envelope: the absence IS the finding)."""
    root = _proj(tmp_path)
    res_no_file = ci.check(root)
    assert not res_no_file["ok"]
    assert res_no_file["findings"][0]["severity"] == "blocking"
    path = os.path.join(root, decisions.DEFAULT_PATH)
    os.makedirs(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(decisions.empty_form("proj"))
    res = ci.check(root)
    assert res["ok"] and res["findings"] == [] and res["entries"] == 0
