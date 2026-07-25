"""Guard #1 — profile validity after profile writes (PostToolUse, BLOCK tier;
TECHNICAL_SOW_REBUILD FR-55 guard #1). Checker verdict matrix (tools/
profile_check.py) plus the frozen 5-test hook pattern (AC-13/AC-14) and the
AC-15 stranger read. Ground truth for the required shape came from reading
the real ~/.claude/CLAUDE.md profile (READ ONLY) — all fixtures below are
built fresh under tmp_path, never against the real file.

Arms ONLY on a write to the user-global profile (normalized path ends with
`/.claude/CLAUDE.md`, a `.claude` DIRECTORY component) — a project's own
root CLAUDE.md must never match, regardless of content.
"""
import json
import sys

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

sys.path.insert(0, f"{BUILD_ROOT}/tools")
import profile_check as pc  # noqa: E402

REQUIRED_SUBSECTIONS = (
    "Communication", "Code comments", "Error handling", "Test discipline",
    "Review pickiness", "Refactor stance", "Audience", "Learning preference",
    "Awareness (decision teach-back)", "Formatting defaults",
)

GOOD_PROFILE = """<!-- FRIDAY-PROFILE:BEGIN -->
## Collaboration Preferences

_Last updated: 2026-07-10 by Friday Profiler._

### Communication
- **Verbosity:** Explanatory — walks through reasoning
- **On uncertainty:** Ask first

### Code comments
- **Style:** WHY-only

### Error handling
- **Validation:** Minimal
- **On unexpected state:** Fail fast

### Test discipline
- **Approach:** Test after
- **Isolation:** Heavy mocking

### Review pickiness
- **Strictness:** Block on every issue

### Refactor stance
- **Default:** Note but don't change

### Audience
- **General experience:** Non-technical

### Learning preference
- **Mode:** Just execute

### Awareness (decision teach-back)
- **Intensity:** Every decision-bearing close

### Formatting defaults
- **Quotes (when ambiguous):** Single quotes
- **File naming (when ambiguous):** camelCase
<!-- FRIDAY-PROFILE:END -->
"""

# Seeded lie: the whole Formatting defaults subsection is gone.
MISSING_SUBSECTION_PROFILE = GOOD_PROFILE.replace(
    "\n### Formatting defaults\n- **Quotes (when ambiguous):** Single quotes\n"
    "- **File naming (when ambiguous):** camelCase\n", "\n")

# The heading survives but carries no bullet content at all.
EMPTY_SUBSECTION_PROFILE = GOOD_PROFILE.replace(
    "- **Quotes (when ambiguous):** Single quotes\n"
    "- **File naming (when ambiguous):** camelCase\n", "")

NO_HEADING_PROFILE = "# Some other file\n\nJust prose, no profile heading here.\n"


def _global_profile_path(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    return home / ".claude" / "CLAUDE.md"


def _project_claude_md_path(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    return proj / "CLAUDE.md"


def _event(path):
    return {"hook_event_name": "PostToolUse", "tool_name": "Write",
            "cwd": str(path.parent), "tool_input": {"file_path": str(path)}}


# --- checker verdict matrix -----------------------------------------------------

def test_no_heading_is_valid_pass():
    res = pc.check_text(NO_HEADING_PROFILE)
    assert res["verdict"] == "valid-pass"


def test_well_formed_profile_is_valid_pass():
    res = pc.check_text(GOOD_PROFILE)
    assert res["verdict"] == "valid-pass"


def test_missing_subsection_is_valid_fail():
    res = pc.check_text(MISSING_SUBSECTION_PROFILE)
    assert res["verdict"] == "valid-fail"
    assert any("Formatting defaults" in p for p in res["problems"])


def test_empty_subsection_is_valid_fail():
    res = pc.check_text(EMPTY_SUBSECTION_PROFILE)
    assert res["verdict"] == "valid-fail"
    assert any("Formatting defaults" in p for p in res["problems"])


def test_all_required_subsections_are_checked():
    for name in REQUIRED_SUBSECTIONS:
        mangled = GOOD_PROFILE.replace(f"### {name}\n", f"### {name} (renamed)\n")
        res = pc.check_text(mangled)
        assert res["verdict"] == "valid-fail", name
        assert any(name in p for p in res["problems"]), name


# --- the hook: 5-test blocking pattern ------------------------------------------

def test_positive_control_missing_subsection_is_blocked(tmp_path):
    path = _global_profile_path(tmp_path)
    path.write_text(MISSING_SUBSECTION_PROFILE, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "profile_guard.py", _event(path))
    out = json.loads(p.stdout)
    assert out["decision"] == "block"
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in out["reason"], (part, out["reason"])


def test_fail_open_all_four_checker_conditions(tmp_path):
    path = _global_profile_path(tmp_path)
    path.write_text(MISSING_SUBSECTION_PROFILE, encoding="utf-8")
    for mode in FAIL_OPEN_MODES:
        pr = broken_plugin(tmp_path, "tools/profile_check.py", mode)
        p = run_hook(pr, "profile_guard.py", _event(path),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        assert p.stdout.strip() == "", (mode, p.stdout)


def test_well_formed_profile_write_is_allowed(tmp_path):
    path = _global_profile_path(tmp_path)
    path.write_text(GOOD_PROFILE, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "profile_guard.py", _event(path))
    assert p.stdout.strip() == ""


def test_project_root_claude_md_never_matches(tmp_path):
    path = _project_claude_md_path(tmp_path)
    path.write_text(MISSING_SUBSECTION_PROFILE, encoding="utf-8")  # same seeded lie
    p = run_hook(BUILD_ROOT, "profile_guard.py", _event(path))
    assert p.stdout.strip() == ""


def test_event_without_a_path_is_untouched(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    event = {"hook_event_name": "PostToolUse", "tool_name": "Write",
             "cwd": str(home), "tool_input": {}}
    p = run_hook(BUILD_ROOT, "profile_guard.py", event)
    assert p.stdout.strip() == ""
