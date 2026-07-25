"""handoff_gate tests — FR-85: the four operator-attested completion bars.
The empty case (no attestations -> all outstanding, not complete) is tested
(hard-won lesson #6). The one attestation representation is the JSON journal
event written by handoff_attest.py — there is no second (text) grammar."""
import json

import handoff_gate as hg


def test_gates_vocabulary():
    assert hg.GATES == ("reconcile", "keys", "restore", "receiver")


def test_empty_case_all_outstanding():
    r = hg.evaluate({})
    assert r["complete"] is False
    assert set(r["outstanding"]) == set(hg.GATES)
    assert r["confirmed"] == []


def test_partial_outstanding():
    r = hg.evaluate({"reconcile": "confirmed", "keys": "confirmed"})
    assert r["complete"] is False
    assert set(r["outstanding"]) == {"restore", "receiver"}
    assert set(r["confirmed"]) == {"reconcile", "keys"}


def test_all_confirmed_complete():
    r = hg.evaluate({g: "confirmed" for g in hg.GATES})
    assert r["complete"] is True
    assert r["outstanding"] == []
    assert set(r["confirmed"]) == set(hg.GATES)


def test_non_confirmed_status_is_outstanding():
    status = {g: "confirmed" for g in hg.GATES}
    status["restore"] = "pending"          # a non-'confirmed' status does NOT satisfy the bar
    r = hg.evaluate(status)
    assert r["complete"] is False
    assert r["outstanding"] == ["restore"]


def test_unknown_gate_ignored():
    r = hg.evaluate({"reconcile": "confirmed", "bogus": "confirmed"})
    assert "bogus" not in r["confirmed"]
    assert r["complete"] is False


def test_gates_from_events_latest_wins():
    events = [
        {"event": "handoff-attest", "by": "pm", "data": {"gate": "keys", "status": "pending"}},
        {"event": "spawn", "data": {"agent": "x"}},                      # unrelated events ignored
        {"event": "handoff-attest", "by": "pm", "data": {"gate": "keys", "status": "confirmed"}},
        {"event": "handoff-attest", "by": "pm", "data": {"gate": "reconcile", "status": "confirmed"}},
    ]
    status = hg.gates_from_events(events)
    assert status == {"keys": "confirmed", "reconcile": "confirmed"}     # later 'confirmed' wins
    assert hg.evaluate(status)["complete"] is False


def test_confirmed_then_blocked_regression():
    events = [
        {"event": "handoff-attest", "by": "pm", "data": {"gate": "keys", "status": "confirmed"}},
        {"event": "handoff-attest", "by": "pm", "data": {"gate": "keys", "status": "blocked"}},
    ]
    status = hg.gates_from_events(events)
    assert status == {"keys": "blocked"}   # a later regression un-confirms the gate
    assert "keys" in hg.evaluate(status)["outstanding"]


def test_gates_from_events_skips_non_dict_entries():
    events = [
        42, None, "x", [1, 2],                                            # corrupt entries skipped
        {"event": "handoff-attest", "data": [1, 2]},                      # non-dict data skipped
        {"event": "handoff-attest", "by": "pm", "data": {"gate": "keys", "status": "confirmed"}},
    ]
    assert hg.gates_from_events(events) == {"keys": "confirmed"}


def test_read_gate_status_from_journal(tmp_path):
    fdir = tmp_path / ".friday"
    fdir.mkdir()
    lines = [
        {"ts": "t1", "phase": "handoff", "event": "handoff-attest", "by": "pm",
         "data": {"gate": g, "status": "confirmed",
                  **({"note": "restored 1200 rows, verified"} if g == "restore" else {})}}
        for g in hg.GATES
    ]
    (fdir / "journal.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    status = hg.read_gate_status(str(tmp_path))
    assert hg.evaluate(status)["complete"] is True


def test_read_gate_status_skips_corrupt_lines(tmp_path):
    # Valid-JSON non-objects and non-JSON garbage are skipped, never a crash —
    # and a crash could only ever fail SAFE (outstanding), but skip is the contract.
    fdir = tmp_path / ".friday"
    fdir.mkdir()
    good = json.dumps({"ts": "t", "phase": "handoff", "event": "handoff-attest",
                       "by": "pm", "data": {"gate": "keys", "status": "confirmed"}})
    (fdir / "journal.jsonl").write_text(
        '42\n"hello"\n[1,2,3]\nnull\ntrue\nnot json at all\n' + good + "\n",
        encoding="utf-8")
    assert hg.read_gate_status(str(tmp_path)) == {"keys": "confirmed"}


def test_read_gate_status_missing_journal(tmp_path):
    assert hg.read_gate_status(str(tmp_path)) == {}
