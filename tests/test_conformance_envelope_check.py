"""INC-105 FR-105.7 — the conformance envelope's checker
(tools/conformance_envelope_check.py).

The sibling envelope: the judge's written answers to rule breaches, closed
answer vocabulary, every answer anchored to the written rule it reasoned
against, no `armed` field to express a block with (D6 structural), the
lying count refused, the count=0 empty case first-class, and the --write
door that validates FIRST. Contract: docs/contracts/conformance-envelope.md.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import conformance_envelope_check as cec  # noqa: E402

GOOD = """conformance-envelope: source=reconcile count=2

## C-1 — no-import-cycles @ tools.receipt ↔ tools.verify_state (answer: not-a-breach)
rule:   modules do not import each other in a cycle at load time
from:   docs/standards/coding-standards.md
reason: both edges are deferred inside function bodies by design, with the relationship documented beside each import

## C-2 — no-env-bypass @ app/jobs/sync.ts:1 (answer: breach)
rule:   every environment variable is read through config.ts
from:   docs/standards/coding-standards.md
reason: the job reads the token around the declared surface; ordinary work under a lane
"""

EMPTY = """conformance-envelope: source=harden count=0

## Checked
every written check and every engaged baseline invariant ran over the tree
"""


def test_good_envelope_passes_with_both_answers():
    out = cec.check_text(GOOD)
    assert out["verdict"] == "valid-pass"
    answers = {f["n"]: f["answer"] for f in out["findings"]}
    assert answers == {"1": "not-a-breach", "2": "breach"}


def test_empty_case_requires_checked_section():
    assert cec.check_text(EMPTY)["verdict"] == "valid-pass"
    bare = "conformance-envelope: source=harden count=0\n"
    out = cec.check_text(bare)
    assert out["verdict"] == "valid-fail"
    assert any("Checked" in e for e in out["errors"])


def test_lying_count_is_refused():
    out = cec.check_text(GOOD.replace("count=2", "count=5"))
    assert out["verdict"] == "valid-fail"
    assert any("lies" in e or "count" in e for e in out["errors"])


def test_armed_field_is_refused_by_design():
    out = cec.check_text(GOOD.replace("count=2", "count=2 armed=true"))
    assert out["verdict"] == "valid-fail"
    assert any("armed" in e and "block" in e for e in out["errors"])


def test_unanchored_answer_is_rejected():
    unanchored = GOOD.replace(
        "rule:   every environment variable is read through config.ts\n", "")
    out = cec.check_text(unanchored)
    assert out["verdict"] == "valid-fail"
    assert any("rule" in e and "unanchored" in e for e in out["errors"])


def test_unknown_answer_and_garbled_heading_are_errors():
    out = cec.check_text(GOOD.replace("(answer: breach)", "(answer: fine)"))
    assert out["verdict"] == "valid-fail"
    garbled = GOOD.replace(
        "## C-2 — no-env-bypass @ app/jobs/sync.ts:1 (answer: breach)",
        "## C-2 no-env-bypass answer breach")
    out2 = cec.check_text(garbled)
    assert out2["verdict"] == "valid-fail"
    assert any("does not parse" in e for e in out2["errors"])


def test_write_door_validates_first_and_lands_at_the_substrate_path(tmp_path):
    repo = os.path.join(os.path.dirname(__file__), "..")
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    tool = os.path.join(repo, "tools", "conformance_envelope_check.py")
    bad = subprocess.run(
        [sys.executable, tool, "--root", str(tmp_path), "--write"],
        input="conformance-envelope: source=nope count=0\n",
        capture_output=True, text=True)
    assert bad.returncode == 1
    assert not os.path.exists(os.path.join(str(tmp_path), ".friday",
                                           "conformance-envelope.md"))
    good = subprocess.run(
        [sys.executable, tool, "--root", str(tmp_path), "--write"],
        input=EMPTY, capture_output=True, text=True)
    assert good.returncode == 0
    landed = json.loads(good.stdout)["path"]
    assert landed.endswith(os.path.join(".friday", "conformance-envelope.md"))
    with open(landed, encoding="utf-8") as fh:
        assert fh.read() == EMPTY


def test_absent_envelope_is_valid_fail_at_consumption(tmp_path):
    result = subprocess.run(
        [sys.executable,
         os.path.join(os.path.dirname(__file__), "..", "tools",
                      "conformance_envelope_check.py"),
         "--file", os.path.join(str(tmp_path), "nope.md")],
        capture_output=True, text=True)
    assert result.returncode == 1
    assert "absent" in result.stdout
