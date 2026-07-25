"""Guard #15 — idle-teammate nudge (TeammateIdle, WARN tier;
TECHNICAL_SOW_REBUILD FR-56 guard #15). A doc-only harness event
(probe-hook-events.md); this drives the hook's stdin directly rather than
via a real trigger. No checker — always warns, never blocks.
"""
import json
import subprocess
import sys

from guardkit import BUILD_ROOT


def _run(event):
    return subprocess.run(
        [sys.executable, f"{BUILD_ROOT}/hooks/teammate_idle_nudge.py", BUILD_ROOT],
        input=json.dumps(event), capture_output=True, text=True)


def test_named_agent_appears_in_the_nudge():
    p = _run({"hook_event_name": "TeammateIdle", "agent_type": "friday-tester"})
    assert p.returncode == 0
    out = json.loads(p.stdout)
    assert "friday-tester" in out["systemMessage"]
    assert "decision" not in out
    assert "hookSpecificOutput" not in out


def test_no_agent_name_still_warns_with_a_generic_label():
    p = _run({"hook_event_name": "TeammateIdle"})
    assert p.returncode == 0
    out = json.loads(p.stdout)
    assert "teammate" in out["systemMessage"].lower()
    assert "decision" not in out
    assert "hookSpecificOutput" not in out


def test_agent_object_shape_is_also_read():
    p = _run({"hook_event_name": "TeammateIdle", "agent": {"name": "friday-security-reviewer"}})
    out = json.loads(p.stdout)
    assert "friday-security-reviewer" in out["systemMessage"]


def test_malformed_stdin_never_crashes():
    p = subprocess.run(
        [sys.executable, f"{BUILD_ROOT}/hooks/teammate_idle_nudge.py", BUILD_ROOT],
        input="not json", capture_output=True, text=True)
    assert p.returncode == 0
