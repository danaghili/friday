"""INC-001 hook behavior (contract: docs/contracts/compaction-package.md):
steering prints the spec only in friday projects; filing routes by self-ID
header through the substrate verbs; re-orientation injects the package only
on source=compact and only when a package exists. All three fail open.
"""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import friday_substrate as fs  # noqa: E402

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SID = "sess-hooks-1"


@pytest.fixture()
def proj(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "CLAUDE.md").write_text(
        "# proj\n\n<!-- FRIDAY-CLAIMS:BEGIN -->\nstack: path:python3\n"
        "<!-- FRIDAY-CLAIMS:END -->\n\n<!-- FRIDAY-STATE:BEGIN -->\n"
        "state: build-in-progress\ntsow: docs/TECHNICAL_SOW.md\n"
        "<!-- FRIDAY-STATE:END -->\n", encoding="utf-8")
    return tmp_path


def run_hook(name, event, cwd):
    return subprocess.run(
        ["python3", os.path.join(BUILD_ROOT, "hooks", name), BUILD_ROOT],
        input=json.dumps(event), capture_output=True, text=True, cwd=str(cwd))


def _event(proj, **kw):
    e = {"session_id": SID, "cwd": str(proj), "hook_event_name": kw.pop("name", "")}
    e.update(kw)
    return e


# --- steering (FR-1.1) ---------------------------------------------------------------

def test_steering_prints_the_floor_spec_in_a_friday_project(proj):
    p = run_hook("compaction_steering.py", _event(proj, name="PreCompact", trigger="auto"), proj)
    assert p.returncode == 0
    assert "handoff-of:" in p.stdout and "Tried and ruled out" in p.stdout
    assert "task list" in p.stdout and "re-read your" in p.stdout.lower()


def test_steering_silent_outside_friday_projects(tmp_path):
    p = run_hook("compaction_steering.py",
                 {"session_id": SID, "cwd": str(tmp_path), "trigger": "auto"}, tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


# --- filing (FR-1.2 / FR-1.4) --------------------------------------------------------

def test_filing_attributed_updates_current_and_archive(proj):
    summary = "handoff-of: friday-lead — hook test\n\nCurrent objective: x\n"
    p = run_hook("compaction_filing.py",
                 _event(proj, name="PostCompact", trigger="manual",
                        compact_summary=summary), proj)
    assert p.returncode == 0, p.stderr
    pkg = fs.compaction_read_package(str(proj), session_id=SID, agent="friday-lead")
    assert pkg["current"] == summary and pkg["generations"] == 1


def test_filing_unattributed_archives_only(proj):
    p = run_hook("compaction_filing.py",
                 _event(proj, name="PostCompact", trigger="auto",
                        compact_summary="A plain unguided summary.\n"), proj)
    assert p.returncode == 0, p.stderr
    un = fs.compaction_read_package(str(proj), session_id=SID,
                                    agent=fs.COMPACTION_UNATTRIBUTED)
    assert un["generations"] == 1 and un["current"] is None


def test_filing_without_summary_is_a_noop(proj):
    p = run_hook("compaction_filing.py", _event(proj, name="PostCompact"), proj)
    assert p.returncode == 0
    assert not os.path.isdir(os.path.join(str(proj), ".friday", "compaction"))


# --- re-orientation (FR-1.8 / FR-1.9) ------------------------------------------------

def test_reorient_injects_package_on_compact_source(proj):
    fs.compaction_write_layer(str(proj), session_id=SID, agent="friday-lead",
                              layer="mission", text="MISSION-SENTINEL-77\n")
    fs.compaction_file_summary(str(proj), session_id=SID,
                               summary="handoff-of: friday-lead — t\n\nbody\n")
    p = run_hook("compaction_reorient.py",
                 _event(proj, name="SessionStart", source="compact"), proj)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "MISSION-SENTINEL-77" in ctx and "task list" in ctx


def test_reorient_silent_on_other_sources_and_empty_package(proj):
    p = run_hook("compaction_reorient.py",
                 _event(proj, name="SessionStart", source="startup"), proj)
    assert p.returncode == 0 and p.stdout.strip() == ""
    p = run_hook("compaction_reorient.py",
                 _event(proj, name="SessionStart", source="compact"), proj)
    assert p.returncode == 0 and p.stdout.strip() == ""
