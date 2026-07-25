"""session_lifecycle journals the SessionStart `source` label — the trap for
the auto-compact label (docs/research/inc001-live-validation.md: the reorient
hook's `compact` matcher never engaged at a live auto-compaction, so the label
an automatic compaction actually carries is unknown). The key is ALWAYS
present — null when the event carried none — so absence is itself evidence.
"""
import json
import os
import subprocess
import sys

import pytest

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SID = "sess-lifecycle-1"

# pid above any plausible pid_max: resolves via the test override, and the
# spawned heartbeat sees a dead pid and exits at once instead of lingering.
DEAD_PID = "999999999"


@pytest.fixture()
def proj(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "CLAUDE.md").write_text(
        "# proj\n\n<!-- FRIDAY-CLAIMS:BEGIN -->\nstack: path:python3\n"
        "<!-- FRIDAY-CLAIMS:END -->\n\n<!-- FRIDAY-STATE:BEGIN -->\n"
        "state: build-in-progress\ntsow: docs/TECHNICAL_SOW.md\n"
        "<!-- FRIDAY-STATE:END -->\n", encoding="utf-8")
    return tmp_path


def run_lifecycle(event, cwd):
    env = dict(os.environ)
    env["FRIDAY_TEST_SESSION_PID"] = DEAD_PID
    env["FRIDAY_TEST_SESSION_CMDLINE"] = "claude"
    return subprocess.run(
        [sys.executable, os.path.join(BUILD_ROOT, "hooks", "session_lifecycle.py"),
         BUILD_ROOT],
        input=json.dumps(event), capture_output=True, text=True,
        cwd=str(cwd), env=env)


def _last_session_start(proj):
    lines = (proj / ".friday" / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    starts = [json.loads(x) for x in lines if json.loads(x)["event"] == "session-start"]
    assert starts, "no session-start journal line written"
    return starts[-1]


def test_session_start_journals_the_source_label(proj):
    p = run_lifecycle({"session_id": SID, "cwd": str(proj),
                       "hook_event_name": "SessionStart", "source": "compact"}, proj)
    assert p.returncode == 0, p.stderr
    rec = _last_session_start(proj)
    assert rec["data"]["source"] == "compact"


def test_session_start_records_null_when_source_absent(proj):
    p = run_lifecycle({"session_id": SID, "cwd": str(proj),
                       "hook_event_name": "SessionStart"}, proj)
    assert p.returncode == 0, p.stderr
    rec = _last_session_start(proj)
    assert "source" in rec["data"] and rec["data"]["source"] is None
