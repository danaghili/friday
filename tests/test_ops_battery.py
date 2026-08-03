"""INC-102 FR-102.3 — the typed verdict record (tools/ops_battery.py).

One typed line per battery row in a marker-fenced block; the row-key
vocabulary is locked to the contract table (docs/contracts/ops-battery.md);
the empty case is a valid, distinct outcome (AC-102.7, S-102.4); a
non-verdict is structurally impossible to record (KH-5).
"""
import json
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import ops_battery  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONTRACT = os.path.join(REPO, "docs", "contracts", "ops-battery.md")


def _record_path(root):
    return os.path.join(str(root), "docs", "ops", "battery.md")


# --- the vocabulary lock: module and contract state the same row set -----

def test_row_keys_match_the_contract_table():
    """The contract file is the row set's single home (FR-102.1); the module
    carries the operational copy. This test is the lock that keeps the two
    from rotting apart."""
    with open(CONTRACT, encoding="utf-8") as fh:
        text = fh.read()
    rows = re.findall(r"^\|\s*`([a-z][a-z0-9-]*)`\s*\|\s*(drill|inspection|judged)\s*\|",
                      text, re.MULTILINE)
    assert rows, "contract table not found — the lock has nothing to hold"
    assert tuple(rows) == ops_battery.ROWS


# --- recording ------------------------------------------------------------

def test_record_creates_file_and_reads_back(tmp_path):
    res = ops_battery.record(str(tmp_path), "undo", "not-proven",
                             note="drill written, awaiting operator",
                             when="2026-08-03")
    assert res["ok"] is True
    out = ops_battery.read(str(tmp_path))
    assert out["status"] == "recorded"
    row = out["rows"]["undo"]
    assert row["verdict"] == "not-proven"
    assert row["date"] == "2026-08-03"
    assert row["kind"] == "drill"
    assert row["note"] == "drill written, awaiting operator"


def test_record_upserts_one_line_per_row(tmp_path):
    ops_battery.record(str(tmp_path), "undo", "not-proven", when="2026-08-01")
    ops_battery.record(str(tmp_path), "undo", "proven",
                       proves=["deploy.sh", "compose.yml"], when="2026-08-03")
    with open(_record_path(tmp_path), encoding="utf-8") as fh:
        text = fh.read()
    assert text.count("verdict: undo ") == 1
    row = ops_battery.read(str(tmp_path))["rows"]["undo"]
    assert row["verdict"] == "proven"
    assert row["proves"] == ["deploy.sh", "compose.yml"]


def test_rows_keep_contract_order(tmp_path):
    ops_battery.record(str(tmp_path), "monitoring", "judged",
                       note="uptime checks ping a human", when="2026-08-03")
    ops_battery.record(str(tmp_path), "restore", "proven",
                       proves=["backup.sh"], when="2026-08-03")
    with open(_record_path(tmp_path), encoding="utf-8") as fh:
        text = fh.read()
    assert text.index("verdict: restore ") < text.index("verdict: monitoring ")


# --- the grammar refuses what the design refuses ---------------------------

def test_unknown_row_key_refused(tmp_path):
    with pytest.raises(ValueError):
        ops_battery.record(str(tmp_path), "disk-space", "proven",
                           proves=["x"], when="2026-08-03")


def test_unknown_verdict_refused(tmp_path):
    with pytest.raises(ValueError):
        ops_battery.record(str(tmp_path), "undo", "scheduled", when="2026-08-03")


def test_proven_drill_requires_proved_paths(tmp_path):
    """A proven drill line names the paths it proves — that is what the
    expiry reads (FR-102.4). Without them the record cannot expire."""
    with pytest.raises(ValueError):
        ops_battery.record(str(tmp_path), "restart", "proven", when="2026-08-03")


def test_proves_forbidden_off_the_proven_drill_case(tmp_path):
    with pytest.raises(ValueError):
        ops_battery.record(str(tmp_path), "isolation", "proven",
                           proves=["x"], when="2026-08-03")
    with pytest.raises(ValueError):
        ops_battery.record(str(tmp_path), "undo", "not-proven",
                           proves=["x"], when="2026-08-03")


def test_not_applicable_requires_the_reason(tmp_path):
    """FR-102.10: not applicable comes with the reason written down."""
    with pytest.raises(ValueError):
        ops_battery.record(str(tmp_path), "job-list", "not-applicable",
                           when="2026-08-03")
    res = ops_battery.record(str(tmp_path), "job-list", "not-applicable",
                             note="nothing scheduled anywhere", when="2026-08-03")
    assert res["ok"] is True


def test_judged_rows_use_the_judged_token_only(tmp_path):
    """D8: the two judged rows are carried unchanged and labelled as judged —
    the label is literal, and the proof vocabulary never leaks onto them."""
    with pytest.raises(ValueError):
        ops_battery.record(str(tmp_path), "monitoring", "proven",
                           proves=["x"], when="2026-08-03")
    with pytest.raises(ValueError):
        ops_battery.record(str(tmp_path), "monitoring", "judged",
                           when="2026-08-03")  # judgment without substance
    res = ops_battery.record(str(tmp_path), "monitoring", "judged",
                             note="alerts reach the PM's phone", when="2026-08-03")
    assert res["ok"] is True


def test_proof_rows_refuse_the_judged_token(tmp_path):
    with pytest.raises(ValueError):
        ops_battery.record(str(tmp_path), "restore", "judged",
                           note="looks fine", when="2026-08-03")


def test_bad_date_refused(tmp_path):
    with pytest.raises(ValueError):
        ops_battery.record(str(tmp_path), "undo", "not-proven", when="yesterday")


# --- not-applicable ratification (FR-102.10, OQ-102.5) --------------------

def test_not_applicable_ratification_is_structural(tmp_path):
    """The PM's ratification rides the line as `ratified: <date>` so the
    deep clean's accepted-risk aging can read it back mechanically. It is
    its own verb: the role records, the PM ratifies at the close."""
    ops_battery.record(str(tmp_path), "job-list", "not-applicable",
                       note="nothing scheduled anywhere", when="2026-08-03")
    row = ops_battery.read(str(tmp_path))["rows"]["job-list"]
    assert row["ratified"] == ""  # proposed, not yet ratified — distinct
    res = ops_battery.ratify(str(tmp_path), "job-list", when="2026-08-04")
    assert res["ok"] is True
    row = ops_battery.read(str(tmp_path))["rows"]["job-list"]
    assert row["ratified"] == "2026-08-04"


def test_a_fresh_recording_arrives_unratified(tmp_path):
    """Re-recording a ratified row clears the ratification — a new proposal
    needs the PM's fresh ruling, never an inherited one."""
    ops_battery.record(str(tmp_path), "job-list", "not-applicable",
                       note="nothing scheduled anywhere", when="2026-08-03")
    ops_battery.ratify(str(tmp_path), "job-list", when="2026-08-04")
    ops_battery.record(str(tmp_path), "job-list", "not-applicable",
                       note="still nothing scheduled", when="2026-08-05")
    assert ops_battery.read(str(tmp_path))["rows"]["job-list"]["ratified"] == ""


def test_ratified_belongs_only_to_not_applicable(tmp_path):
    ops_battery.record(str(tmp_path), "restore", "proven",
                       proves=["backup.sh"], when="2026-08-03")
    with pytest.raises(ValueError):
        ops_battery.ratify(str(tmp_path), "restore", when="2026-08-04")


def test_ratify_needs_an_existing_row(tmp_path):
    ops_battery.init(str(tmp_path))
    res = ops_battery.ratify(str(tmp_path), "job-list", when="2026-08-04")
    assert res["ok"] is False


def test_ratified_date_validated(tmp_path):
    ops_battery.record(str(tmp_path), "job-list", "not-applicable",
                       note="nothing scheduled", when="2026-08-03")
    with pytest.raises(ValueError):
        ops_battery.ratify(str(tmp_path), "job-list", when="someday")


# --- the empty case is a valid, distinct outcome (AC-102.7, S-102.4) ------

def test_absent_empty_and_recorded_are_three_states(tmp_path):
    assert ops_battery.read(str(tmp_path))["status"] == "absent"
    ops_battery.init(str(tmp_path))
    out = ops_battery.read(str(tmp_path))
    assert out["status"] == "empty"
    assert out["rows"] == {}
    ops_battery.record(str(tmp_path), "undo", "not-proven", when="2026-08-03")
    assert ops_battery.read(str(tmp_path))["status"] == "recorded"


def test_empty_block_reports_nothing_proven_yet(tmp_path):
    ops_battery.init(str(tmp_path))
    with open(_record_path(tmp_path), encoding="utf-8") as fh:
        assert ops_battery.SENTINEL in fh.read()


# --- malformed lines are kept and flagged, never dropped -------------------

def test_malformed_line_kept_and_flagged(tmp_path):
    ops_battery.record(str(tmp_path), "undo", "not-proven", when="2026-08-03")
    path = _record_path(tmp_path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    vandal = "verdict: undo is basically fine I think"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace("<!-- FRIDAY-OPS-BATTERY:END -->",
                              vandal + "\n<!-- FRIDAY-OPS-BATTERY:END -->"))
    out = ops_battery.read(str(tmp_path))
    assert any(vandal in m for m in out["malformed"])
    ops_battery.record(str(tmp_path), "restore", "proven",
                       proves=["backup.sh"], when="2026-08-03")
    with open(path, encoding="utf-8") as fh:
        assert vandal in fh.read()


# --- CLI ------------------------------------------------------------------

def test_cli_record_and_read(tmp_path):
    tool = os.path.join(REPO, "tools", "ops_battery.py")
    rec = subprocess.run(
        [sys.executable, tool, "record", "--root", str(tmp_path),
         "--row", "restart", "--verdict", "proven",
         "--proves", "deploy.sh", "--proves", "systemd/app.service",
         "--note", "PM rebooted the host; came back on the pinned version",
         "--when", "2026-08-03"],
        capture_output=True, text=True)
    assert rec.returncode == 0, rec.stderr
    out = subprocess.run(
        [sys.executable, tool, "read", "--root", str(tmp_path)],
        capture_output=True, text=True)
    assert out.returncode == 0
    data = json.loads(out.stdout)
    assert data["status"] == "recorded"
    assert data["rows"]["restart"]["proves"] == ["deploy.sh", "systemd/app.service"]


def test_cli_refusal_exits_nonzero(tmp_path):
    tool = os.path.join(REPO, "tools", "ops_battery.py")
    rec = subprocess.run(
        [sys.executable, tool, "record", "--root", str(tmp_path),
         "--row", "restart", "--verdict", "proven", "--when", "2026-08-03"],
        capture_output=True, text=True)
    assert rec.returncode == 1
    assert json.loads(rec.stdout)["ok"] is False


# --- drill-row expiry against real history (FR-102.4, AC-102.3) -----------

PRE = "2026-07-01T00:00:00 +0000"
POST = "2026-08-02T00:00:00 +0000"


def _git(repo, *args, date=None):
    env = dict(os.environ)
    if date:
        env["GIT_COMMITTER_DATE"] = date
        env["GIT_AUTHOR_DATE"] = date
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=env,
                   capture_output=True)


def _drill_repo(tmp_path):
    """A real repo whose deploy script predates the drill (drilled
    2026-08-01, script committed 2026-07-01)."""
    root = tmp_path / "proj"
    root.mkdir()
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "deploy.sh").write_text("v1\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "scaffold", date=PRE)
    ops_battery.record(str(root), "restart", "proven",
                       proves=["deploy.sh"], when="2026-08-01")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "record drill", date="2026-08-01T12:00:00 +0000")
    return root


def test_expiry_quiet_when_nothing_moved(tmp_path):
    root = _drill_repo(tmp_path)
    out = ops_battery.check_expiry(str(root))
    (check,) = out["checks"]
    assert check["row"] == "restart"
    assert check["result"] == "stands"
    assert check["killer"] is None


def test_expiry_fires_on_a_change_and_names_the_killer(tmp_path):
    root = _drill_repo(tmp_path)
    (root / "deploy.sh").write_text("v2 — deploy rewritten\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "rewrite deploy to compose", date=POST)
    (check,) = ops_battery.check_expiry(str(root))["checks"]
    assert check["result"] == "expired"
    assert check["killer"]["path"] == "deploy.sh"
    assert "rewrite deploy to compose" in check["killer"]["subject"]
    assert check["killer"]["date"] == "2026-08-02"


def test_expiry_fires_on_an_uncommitted_change(tmp_path):
    root = _drill_repo(tmp_path)
    (root / "deploy.sh").write_text("v2 uncommitted\n", encoding="utf-8")
    (check,) = ops_battery.check_expiry(str(root))["checks"]
    assert check["result"] == "expired"
    assert check["dirty"] == ["deploy.sh"]


def test_expiry_flags_a_path_git_never_saw(tmp_path):
    """A drill claiming to prove a path with no history cannot be verified —
    flagged, never folded into stands (the S-102.4 shape)."""
    root = _drill_repo(tmp_path)
    ops_battery.record(str(root), "undo", "proven",
                       proves=["scripts/rollback.sh"], when="2026-08-01")
    checks = {c["row"]: c for c in ops_battery.check_expiry(str(root))["checks"]}
    assert checks["undo"]["result"] == "unverifiable"
    assert checks["undo"]["unknown"] == ["scripts/rollback.sh"]
    assert checks["restart"]["result"] == "stands"


def test_expiry_checks_only_proven_drill_rows(tmp_path):
    root = _drill_repo(tmp_path)
    ops_battery.record(str(root), "undo", "not-proven", when="2026-08-01")
    ops_battery.record(str(root), "isolation", "proven", when="2026-08-01")
    ops_battery.record(str(root), "monitoring", "judged",
                       note="alerts reach a human", when="2026-08-01")
    rows_checked = [c["row"] for c in ops_battery.check_expiry(str(root))["checks"]]
    assert rows_checked == ["restart"]


def test_expiry_outside_a_repo_is_unverifiable_not_a_pass(tmp_path):
    ops_battery.record(str(tmp_path), "restart", "proven",
                       proves=["deploy.sh"], when="2026-08-01")
    (check,) = ops_battery.check_expiry(str(tmp_path))["checks"]
    assert check["result"] == "unverifiable"


def test_cli_check_reports_and_never_blocks(tmp_path):
    root = _drill_repo(tmp_path)
    (root / "deploy.sh").write_text("v2\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "move deploy", date=POST)
    tool = os.path.join(REPO, "tools", "ops_battery.py")
    out = subprocess.run([sys.executable, tool, "check", "--root", str(root)],
                         capture_output=True, text=True)
    assert out.returncode == 0  # report-only, S-102.2
    data = json.loads(out.stdout)
    assert data["checks"][0]["result"] == "expired"
