"""INC-101 FR-101.7 / AC-101.6 / KH-3 — the handover's reconcile gate cannot be
satisfied without the read.

The one refusal this increment adds: attesting the reconcile gate confirmed
with no note is refused (a bare confirmation is not a read record), and the
refusal names BOTH real answers (OQ-101.4 — a refusal naming only one teaches
the PM the wrong route): a deep clean whose run included the document-truth
probe, or the PM's recorded decision to hand over with findings outstanding.
The restore gate's evidence refusal is the model.
"""
import handoff_attest
import handoff_gate as hg


def _friday_project(tmp_path):
    (tmp_path / ".friday").mkdir()
    return str(tmp_path)


def test_bare_reconcile_confirmation_is_refused_and_names_both_answers(tmp_path, capsys):
    root = _friday_project(tmp_path)
    rc = handoff_attest.main(
        ["--gate", "reconcile", "--status", "confirmed", "--by", "pm", "--cwd", root]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "document-truth probe" in err
    assert "findings outstanding" in err
    assert hg.read_gate_status(root) == {}


def test_a_probe_carrying_deep_clean_note_is_accepted(tmp_path):
    root = _friday_project(tmp_path)
    rc = handoff_attest.main(
        ["--gate", "reconcile", "--status", "confirmed", "--by", "pm", "--cwd", root,
         "--note", "deep clean 2026-08-03, document-truth probe ran, verdict clean"]
    )
    assert rc == 0
    assert hg.read_gate_status(root) == {"reconcile": "confirmed"}


def test_the_pms_recorded_hand_over_anyway_decision_is_accepted(tmp_path):
    root = _friday_project(tmp_path)
    rc = handoff_attest.main(
        ["--gate", "reconcile", "--status", "confirmed", "--by", "pm", "--cwd", root,
         "--note", "PM decision D-0201: hand over with findings outstanding"]
    )
    assert rc == 0
    assert hg.read_gate_status(root) == {"reconcile": "confirmed"}
