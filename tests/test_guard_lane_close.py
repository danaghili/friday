"""Guard #6 through the real hook — the frozen 5-test pattern (AC-13/AC-14)
plus the AC-15 stranger read, the disarm-on-pass path, and the sentinel
edges. Contract: docs/contracts/lane-open.md (arming) +
docs/contracts/change-trail.md (what must pass).

Positive control: an armed lane whose trail is absent → Stop blocked.
Fail-open controls: same armed lane with tools/trail_check.py deleted /
crashing / timing out / emitting an invalid-empty verdict → the Stop is
ALLOWED and the sentinel STAYS ARMED (a later Stop with a working checker
still catches it — the state_stop_gate asymmetry).
"""
import json

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

VALID_TRAIL = """trail: lane=patch id=PATCH-1 date=2026-07-14

## Asked
The parser crashed on empty input.

## Decisions
decisions: none — change fully specified by the ask

## Proof
proof: `python3 -m pytest tests/ -q` → all green

changelog: fixed the empty-input crash
"""


def _proj(tmp_path, *, trail: str | None = None, armed=True, sentinel_body=None):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    (root / "CLAUDE.md").write_text(
        "# proj\n\n<!-- FRIDAY-STATE:BEGIN -->\nstate: build-in-progress\n"
        "<!-- FRIDAY-STATE:END -->\n", encoding="utf-8")
    (root / "docs" / "DECISIONS.md").write_text("# Decisions — proj\n", encoding="utf-8")
    if trail is not None:
        (root / "docs" / "trails").mkdir()
        (root / "docs" / "trails" / "PATCH-1.md").write_text(trail, encoding="utf-8")
    if armed:
        (root / ".friday").mkdir()
        (root / ".friday" / "lane-open").write_text(
            sentinel_body if sentinel_body is not None else json.dumps(
                {"lane": "patch", "id": "PATCH-1", "trail": "docs/trails/PATCH-1.md"}),
            encoding="utf-8")
    return root


def _stop(proj):
    return {"hook_event_name": "Stop", "cwd": str(proj)}


def test_positive_control_trail_less_close_is_blocked(tmp_path):
    proj = _proj(tmp_path)  # armed, no trail file — the seeded lie (AC-23)
    p = run_hook(BUILD_ROOT, "lane_close_gate.py", _stop(proj))
    out = json.loads(p.stdout)
    assert out["decision"] == "block"
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in out["reason"], (part, out["reason"])
    assert (proj / ".friday" / "lane-open").is_file()  # stays armed


def test_malformed_trail_is_also_blocked(tmp_path):
    proj = _proj(tmp_path, trail="trail: lane=patch id=PATCH-1 date=2026-07-14\n\n"
                                 "## Asked\nx\n")  # no Decisions/Proof/changelog
    p = run_hook(BUILD_ROOT, "lane_close_gate.py", _stop(proj))
    assert json.loads(p.stdout)["decision"] == "block"


def test_valid_trail_allows_and_disarms(tmp_path):
    proj = _proj(tmp_path, trail=VALID_TRAIL)
    p = run_hook(BUILD_ROOT, "lane_close_gate.py", _stop(proj))
    assert p.stdout.strip() == ""
    assert not (proj / ".friday" / "lane-open").exists()  # lane closed properly


def test_fail_open_all_four_checker_conditions(tmp_path):
    for mode in FAIL_OPEN_MODES:
        proj = _proj(tmp_path / mode)
        pr = broken_plugin(tmp_path / mode, "tools/trail_check.py", mode)
        p = run_hook(pr, "lane_close_gate.py", _stop(proj),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        assert p.stdout.strip() == "", (mode, p.stdout)          # ALLOW
        assert (proj / ".friday" / "lane-open").is_file(), mode  # stays armed


def test_no_sentinel_is_a_cheap_no_op(tmp_path):
    proj = _proj(tmp_path, armed=False)
    p = run_hook(BUILD_ROOT, "lane_close_gate.py", _stop(proj))
    assert p.stdout.strip() == ""


def test_unreadable_sentinel_fails_open_and_stays(tmp_path):
    proj = _proj(tmp_path, sentinel_body="not json {{{")
    p = run_hook(BUILD_ROOT, "lane_close_gate.py", _stop(proj))
    assert p.stdout.strip() == ""
    assert (proj / ".friday" / "lane-open").is_file()


def test_bug_lanes_are_not_this_guards_business(tmp_path):
    # D-0023 ownership rule: lane=bug belongs wholly to bug_close_gate —
    # even a trail-less bug lane produces no block AND no disarm here.
    proj = _proj(tmp_path, sentinel_body=json.dumps(
        {"lane": "bug", "id": "BUG-9", "trail": "docs/trails/BUG-9.md"}))
    p = run_hook(BUILD_ROOT, "lane_close_gate.py", _stop(proj))
    assert p.stdout.strip() == ""
    assert (proj / ".friday" / "lane-open").is_file()
