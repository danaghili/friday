"""INC-202 FR-202.4 / AC-202.3 / S-202.1 — the mover: both halves or neither.

One tool performs every proposal move: the header status-field edit and the
file relocation as one operation. It validates EVERYTHING before touching
anything — transition legality, evidence for `04-validated`, a reason for
`05-rejected` and for the backwards `03 → 02` loop (D10), the target existing
exactly once — and refuses whole rather than half-completing. The stage
vocabulary is the folder names themselves (D4/D-0155), so every assertion
here compares strings a reader can see in `ls`.
"""
import json
import os

import pytest

import proposal_pipeline as pp


def _mk(root, stage, name="PROP-777", status=None, extra=(), body="## PROP-777 — t\n\nAsk text.\n"):
    d = os.path.join(root, "proposals", stage)
    os.makedirs(d, exist_ok=True)
    fields = [("status", status or stage), ("captured", "2026-07-30")] + list(extra)
    text = "---\n" + "".join(f"{k}: {v}\n" for k, v in fields) + "---\n\n" + body
    path = os.path.join(d, f"{name}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


@pytest.fixture()
def tree(tmp_path):
    for s in pp.STAGES:
        os.makedirs(tmp_path / "proposals" / s)
    (tmp_path / "proposals" / "_research").mkdir()
    return str(tmp_path)


def test_a_legal_move_edits_the_field_and_relocates_in_one_step(tree):
    _mk(tree, "02-in-progress", extra=[("increment", "INC-202")])
    res = pp.move(tree, "PROP-777", "03-pending-validation")
    assert res["verdict"] == "moved"
    new = os.path.join(tree, "proposals", "03-pending-validation", "PROP-777.md")
    assert os.path.isfile(new)
    assert not os.path.exists(os.path.join(tree, "proposals", "02-in-progress", "PROP-777.md"))
    header = pp.read_header(open(new, encoding="utf-8").read())
    assert dict(header["fields"])["status"] == "03-pending-validation"


def test_validation_without_evidence_is_refused_bytes_untouched(tree):
    path = _mk(tree, "03-pending-validation", extra=[("increment", "INC-202")])
    before = open(path, encoding="utf-8").read()
    res = pp.move(tree, "PROP-777", "04-validated")
    assert res["verdict"] == "refused" and "evidence" in res["reason"]
    assert open(path, encoding="utf-8").read() == before
    assert os.path.isfile(path)


def test_validation_with_evidence_writes_the_field_and_moves(tree):
    _mk(tree, "03-pending-validation", extra=[("increment", "INC-202")])
    res = pp.move(tree, "PROP-777", "04-validated",
                  evidence="2026-07-30 — live close run: docs/trails/INC-202.md")
    assert res["verdict"] == "moved"
    text = open(os.path.join(tree, "proposals", "04-validated", "PROP-777.md"),
                encoding="utf-8").read()
    fields = dict(pp.read_header(text)["fields"])
    assert fields["status"] == "04-validated"
    assert fields["validated"].startswith("2026-07-30 — live close run")


def test_the_backwards_loop_requires_a_reason_and_records_it(tree):
    _mk(tree, "03-pending-validation", extra=[("increment", "INC-202")])
    refused = pp.move(tree, "PROP-777", "02-in-progress")
    assert refused["verdict"] == "refused" and "reason" in refused["reason"]
    res = pp.move(tree, "PROP-777", "02-in-progress",
                  reason="validation failed: the target had no real deployment")
    assert res["verdict"] == "moved"
    text = open(os.path.join(tree, "proposals", "02-in-progress", "PROP-777.md"),
                encoding="utf-8").read()
    assert dict(pp.read_header(text)["fields"])["reason"].startswith("validation failed")


def test_a_decline_requires_a_reason(tree):
    _mk(tree, "01-proposed")
    assert pp.move(tree, "PROP-777", "05-rejected")["verdict"] == "refused"
    assert pp.move(tree, "PROP-777", "05-rejected",
                   reason="superseded by PROP-206")["verdict"] == "moved"


def test_queueing_requires_the_increment_link(tree):
    """D2: the 01 → 02 move IS the linking moment — it must carry the
    increment id (argument or already-present field), or refuse."""
    _mk(tree, "01-proposed")
    assert pp.move(tree, "PROP-777", "02-in-progress")["verdict"] == "refused"
    res = pp.move(tree, "PROP-777", "02-in-progress", increment="INC-203")
    assert res["verdict"] == "moved"
    text = open(os.path.join(tree, "proposals", "02-in-progress", "PROP-777.md"),
                encoding="utf-8").read()
    assert dict(pp.read_header(text)["fields"])["increment"] == "INC-203"


def test_terminal_stages_do_not_move_out(tree):
    _mk(tree, "04-validated", extra=[("validated", "2026-07-30 — evidence")])
    assert pp.move(tree, "PROP-777", "02-in-progress",
                   reason="r")["verdict"] == "refused"
    _mk(tree, "05-rejected", name="PROP-778")
    assert pp.move(tree, "PROP-778", "01-proposed")["verdict"] == "refused"


def test_unknown_names_and_duplicates_refuse_loudly(tree):
    assert pp.move(tree, "PROP-999", "02-in-progress",
                   increment="INC-1")["verdict"] == "refused"
    _mk(tree, "01-proposed", name="PROP-800")
    _mk(tree, "03-pending-validation", name="PROP-800")
    res = pp.move(tree, "PROP-800", "05-rejected", reason="r")
    assert res["verdict"] == "refused" and "01-proposed" in res["reason"] \
        and "03-pending-validation" in res["reason"]


def test_a_headerless_file_is_refused_not_guessed(tree):
    d = os.path.join(tree, "proposals", "01-proposed")
    with open(os.path.join(d, "PROP-801.md"), "w", encoding="utf-8") as fh:
        fh.write("## PROP-801 — pre-migration shape, no header\n")
    res = pp.move(tree, "PROP-801", "02-in-progress", increment="INC-1")
    assert res["verdict"] == "refused" and "header" in res["reason"]


def test_cli_emits_the_typed_json_verdict(tree, capsys):
    _mk(tree, "02-in-progress", extra=[("increment", "INC-202")])
    rc = pp.main(["move", "--root", tree, "--name", "PROP-777",
                  "--to", "03-pending-validation", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["verdict"] == "moved" \
        and out["from"] == "02-in-progress" and out["to"] == "03-pending-validation"
