"""handoff_attest tests — the attestation writer rides the single substrate
writer for real (no hand-rolled journal write), and its event kind is pinned in
EVENT_VOCABULARY (an event missing from the vocabulary would silently never
land — same pin as test_graph_stamp)."""
import friday_substrate as fs
import handoff_attest
import handoff_gate as hg


def test_event_kind_pinned_in_vocabulary():
    assert "handoff-attest" in fs.EVENT_VOCABULARY


def _friday_project(tmp_path):
    (tmp_path / ".friday").mkdir()          # an existing substrate is engagement enough
    return str(tmp_path)


def test_roundtrip_through_the_real_writer(tmp_path, capsys):
    root = _friday_project(tmp_path)
    rc = handoff_attest.main(["--gate", "keys", "--status", "confirmed",
                              "--by", "pm", "--note", "moved in Infisical", "--cwd", root])
    assert rc == 0
    assert '"handoff-attest"' in capsys.readouterr().out
    status = hg.read_gate_status(root)      # read back through the real reader
    assert status == {"keys": "confirmed"}


def test_all_four_gates_roundtrip_to_complete(tmp_path):
    root = _friday_project(tmp_path)
    for g in hg.GATES:
        args = ["--gate", g, "--status", "confirmed", "--by", "pm", "--cwd", root]
        if g == "restore":                       # A1: restore requires evidence
            args += ["--note", "restored from backup 2026-07-14, verified 1200 rows"]
        assert handoff_attest.main(args) == 0
    assert hg.evaluate(hg.read_gate_status(root))["complete"] is True


def test_restore_gate_refuses_without_evidence(tmp_path):
    root = _friday_project(tmp_path)
    assert handoff_attest.main(["--gate", "restore", "--status", "confirmed",
                                "--by", "pm", "--cwd", root]) == 2   # A1: no evidence
    assert hg.read_gate_status(root) == {}


def test_rejects_bad_gate_and_status(tmp_path, capsys):
    root = _friday_project(tmp_path)
    assert handoff_attest.main(["--gate", "bogus", "--cwd", root]) == 2
    assert handoff_attest.main(["--gate", "keys", "--status", "maybe", "--cwd", root]) == 2
    capsys.readouterr()
    assert hg.read_gate_status(root) == {}  # nothing was written


def test_refuses_outside_a_friday_project(tmp_path):
    # No .friday/, no markers — must refuse rather than lazy-create a stray journal.
    assert handoff_attest.main(["--gate", "keys", "--cwd", str(tmp_path)]) == 2
    assert not (tmp_path / ".friday").exists()
