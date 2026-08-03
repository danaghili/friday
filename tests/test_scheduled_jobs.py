"""INC-102 FR-102.7 — the scheduled-job list (tools/scheduled_jobs.py).

Photograph -> confirm -> diff (D6), value-blind at the write (S-102.3,
KH-4, AC-102.6): the one place this increment writes is the one place a
live machine keeps credentials in the clear, and no value may reach disk.
"""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import scheduled_jobs  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOL = os.path.join(REPO, "tools", "scheduled_jobs.py")

PLANTED_TOKEN = "ghp_16C7e42F292c6912E7710c838347Ae178B4a"
PLANTED_URL = "postgres://backup:S3cr3tPa55w0rd@db.internal/prod"


def _list_path(root):
    return os.path.join(str(root), "docs", "ops", "scheduled-jobs.md")


def _file_text(root):
    with open(_list_path(root), encoding="utf-8") as fh:
        return fh.read()


# --- photograph (D6: copied off the machine, ratifies nothing) -------------

def test_photograph_writes_a_pending_entry_and_says_so(tmp_path):
    res = scheduled_jobs.photograph(str(tmp_path), name="nightly-backup",
                                    schedule="0 3 * * *", source="crontab",
                                    purpose="dumps the database to /backups")
    assert res["ok"] is True
    text = _file_text(tmp_path)
    assert "job: nightly-backup" in text
    assert "confirmed: pending" in text
    assert "ratif" in text  # the in-file statement that a photograph ratifies nothing
    out = scheduled_jobs.read(str(tmp_path))
    assert out["status"] == "recorded"
    assert out["jobs"]["nightly-backup"]["confirmed"] == "pending"


def test_photograph_upserts_by_name(tmp_path):
    scheduled_jobs.photograph(str(tmp_path), name="ping", schedule="* * * * *",
                              source="crontab", purpose="old")
    scheduled_jobs.photograph(str(tmp_path), name="ping", schedule="*/5 * * * *",
                              source="crontab", purpose="pings the health endpoint")
    assert _file_text(tmp_path).count("job: ping ") == 1
    assert scheduled_jobs.read(str(tmp_path))["jobs"]["ping"]["schedule"] == "*/5 * * * *"


# --- the value-blind write (S-102.3, KH-4, AC-102.6) -----------------------

def test_a_planted_token_is_refused_in_every_field(tmp_path):
    for field in ("name", "schedule", "source", "purpose"):
        kwargs = {"name": "job-a", "schedule": "0 3 * * *",
                  "source": "crontab", "purpose": "backs things up"}
        kwargs[field] = f"x {PLANTED_TOKEN}" if field == "purpose" else PLANTED_TOKEN
        with pytest.raises(ValueError):
            scheduled_jobs.photograph(str(tmp_path), **kwargs)
    assert not os.path.exists(_list_path(tmp_path))


def test_a_url_credential_is_refused(tmp_path):
    with pytest.raises(ValueError):
        scheduled_jobs.photograph(str(tmp_path), name="backup",
                                  schedule="0 3 * * *", source="crontab",
                                  purpose=f"pg_dump {PLANTED_URL} nightly")


def test_an_inline_assignment_is_refused(tmp_path):
    with pytest.raises(ValueError):
        scheduled_jobs.photograph(str(tmp_path), name="sync",
                                  schedule="0 4 * * *", source="crontab",
                                  purpose="runs sync with API_KEY=abc123def456 inline")


def test_the_entry_lands_without_the_value_and_no_value_reaches_disk(tmp_path):
    """AC-102.6's shape: the job is recordable — name, schedule, purpose —
    and the planted value reaches nothing."""
    with pytest.raises(ValueError):
        scheduled_jobs.photograph(str(tmp_path), name="health-ping",
                                  schedule="*/5 * * * *", source="crontab",
                                  purpose=f"curl -H 'Authorization: Bearer {PLANTED_TOKEN}' https://x")
    res = scheduled_jobs.photograph(str(tmp_path), name="health-ping",
                                    schedule="*/5 * * * *", source="crontab",
                                    purpose="pings the health endpoint and alerts on failure")
    assert res["ok"] is True
    assert PLANTED_TOKEN not in _file_text(tmp_path)


def test_confirm_scans_the_updated_purpose_too(tmp_path):
    scheduled_jobs.photograph(str(tmp_path), name="ping", schedule="* * * * *",
                              source="crontab", purpose="tbd")
    with pytest.raises(ValueError):
        scheduled_jobs.confirm(str(tmp_path), "ping",
                               purpose=f"pings with {PLANTED_TOKEN}",
                               when="2026-08-03")


# --- confirm (D6: once per job, on the PM's word, dated) --------------------

def test_confirm_marks_the_job_with_date_and_purpose(tmp_path):
    scheduled_jobs.photograph(str(tmp_path), name="ping", schedule="*/5 * * * *",
                              source="crontab", purpose="tbd")
    res = scheduled_jobs.confirm(str(tmp_path), "ping",
                                 purpose="pings the health endpoint",
                                 when="2026-08-03")
    assert res["ok"] is True
    job = scheduled_jobs.read(str(tmp_path))["jobs"]["ping"]
    assert job["confirmed"] == "2026-08-03"
    assert job["purpose"] == "pings the health endpoint"


def test_confirm_unknown_job_refused(tmp_path):
    scheduled_jobs.photograph(str(tmp_path), name="ping", schedule="* * * * *",
                              source="crontab", purpose="x")
    res = scheduled_jobs.confirm(str(tmp_path), "ghost", when="2026-08-03")
    assert res["ok"] is False


# --- diff (AC-102.10: pending baseline vs findings, both directions) --------

def _confirmed_list(tmp_path):
    scheduled_jobs.photograph(str(tmp_path), name="backup", schedule="0 3 * * *",
                              source="crontab", purpose="dumps the db")
    scheduled_jobs.photograph(str(tmp_path), name="ping", schedule="*/5 * * * *",
                              source="crontab", purpose="health checks")
    scheduled_jobs.confirm(str(tmp_path), "backup", when="2026-08-03")
    scheduled_jobs.confirm(str(tmp_path), "ping", when="2026-08-03")


def test_diff_before_confirmation_is_a_pending_baseline_not_drift(tmp_path):
    scheduled_jobs.photograph(str(tmp_path), name="backup", schedule="0 3 * * *",
                              source="crontab", purpose="dumps the db")
    out = scheduled_jobs.diff(str(tmp_path),
                              installed=[("backup", "0 3 * * *"),
                                         ("mystery", "1 1 * * *")])
    assert out["baseline"] == "pending"
    assert out["findings"] == []
    assert any("mystery" in p for p in out["pending"])


def test_diff_after_confirmation_names_the_added_job(tmp_path):
    _confirmed_list(tmp_path)
    out = scheduled_jobs.diff(str(tmp_path),
                              installed=[("backup", "0 3 * * *"),
                                         ("ping", "*/5 * * * *"),
                                         ("left-behind", "0 0 * * 0")])
    assert out["baseline"] == "confirmed"
    assert any("left-behind" in f for f in out["findings"])


def test_diff_after_confirmation_names_the_vanished_job_and_the_moved_schedule(tmp_path):
    _confirmed_list(tmp_path)
    out = scheduled_jobs.diff(str(tmp_path),
                              installed=[("backup", "0 5 * * *")])
    assert any("ping" in f and "not installed" in f for f in out["findings"])
    assert any("backup" in f and "0 5 * * *" in f for f in out["findings"])


def test_diff_clean_when_machine_matches_the_confirmed_list(tmp_path):
    _confirmed_list(tmp_path)
    out = scheduled_jobs.diff(str(tmp_path),
                              installed=[("backup", "0 3 * * *"),
                                         ("ping", "*/5 * * * *")])
    assert out["findings"] == []
    assert out["pending"] == []


# --- empty case -------------------------------------------------------------

def test_absent_and_empty_are_distinct(tmp_path):
    assert scheduled_jobs.read(str(tmp_path))["status"] == "absent"
    scheduled_jobs.init(str(tmp_path))
    assert scheduled_jobs.read(str(tmp_path))["status"] == "empty"


# --- CLI ---------------------------------------------------------------------

def test_cli_roundtrip_and_report_only_diff(tmp_path):
    ph = subprocess.run(
        [sys.executable, TOOL, "photograph", "--root", str(tmp_path),
         "--name", "backup", "--schedule", "0 3 * * *", "--source", "crontab",
         "--purpose", "dumps the db"],
        capture_output=True, text=True)
    assert ph.returncode == 0, ph.stderr
    cf = subprocess.run(
        [sys.executable, TOOL, "confirm", "--root", str(tmp_path),
         "--name", "backup", "--when", "2026-08-03"],
        capture_output=True, text=True)
    assert cf.returncode == 0
    df = subprocess.run(
        [sys.executable, TOOL, "diff", "--root", str(tmp_path),
         "--installed", "backup@0 3 * * *", "--installed", "stray@1 1 * * *"],
        capture_output=True, text=True)
    assert df.returncode == 0  # report-only, S-102.2
    data = json.loads(df.stdout)
    assert any("stray" in f for f in data["findings"])


def test_cli_refuses_a_planted_value(tmp_path):
    ph = subprocess.run(
        [sys.executable, TOOL, "photograph", "--root", str(tmp_path),
         "--name", "sync", "--schedule", "0 4 * * *", "--source", "crontab",
         "--purpose", f"syncs via {PLANTED_URL}"],
        capture_output=True, text=True)
    assert ph.returncode == 1
    assert json.loads(ph.stdout)["ok"] is False
    # the refusal names the field and never echoes the value back
    assert "S3cr3tPa55w0rd" not in ph.stdout + ph.stderr
    assert not os.path.exists(_list_path(tmp_path))
