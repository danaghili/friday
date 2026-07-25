"""Guard #14 — research-consumer orphans (Stop, WARN tier;
TECHNICAL_SOW_REBUILD FR-56 guard #14, S-4). Checker verdict matrix (tools/
research_orphan_check.py) plus the WARN-tier shape: never blocks, quiet
degradation.
"""
import json

from guardkit import BUILD_ROOT, broken_plugin, run_hook


def _proj(tmp_path):
    root = tmp_path / "proj"
    (root / "docs" / "research").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / "tools" / "widget.py").write_text("x", encoding="utf-8")
    return root


def _stop(root):
    return {"hook_event_name": "Stop", "cwd": str(root)}


# --- checker verdict matrix -----------------------------------------------------

def test_no_research_dir_is_valid_pass(tmp_path):
    from research_orphan_check import check  # noqa
    root = tmp_path / "bare"
    root.mkdir()
    assert check(str(root))["verdict"] == "valid-pass"


def test_consumed_brief_is_valid_pass(tmp_path):
    from research_orphan_check import check  # noqa
    proj = _proj(tmp_path)
    (proj / "docs" / "research" / "foo.md").write_text(
        "consumer: tools/widget.py\n", encoding="utf-8")
    assert check(str(proj))["verdict"] == "valid-pass"


def test_orphaned_brief_is_valid_fail(tmp_path):
    from research_orphan_check import check  # noqa
    proj = _proj(tmp_path)
    (proj / "docs" / "research" / "bar.md").write_text(
        "consumer: nonexistent-widget-xyz\n", encoding="utf-8")
    res = check(str(proj))
    assert res["verdict"] == "valid-fail"
    assert any("bar.md" in o for o in res["orphans"])


def test_exempt_sentinel_is_valid_pass(tmp_path):
    from research_orphan_check import check  # noqa
    proj = _proj(tmp_path)
    (proj / "docs" / "research" / "baz.md").write_text(
        "consumer: rebuild build pass\n", encoding="utf-8")
    assert check(str(proj))["verdict"] == "valid-pass"


def test_missing_consumer_line_is_valid_fail(tmp_path):
    from research_orphan_check import check  # noqa
    proj = _proj(tmp_path)
    (proj / "docs" / "research" / "qux.md").write_text("no tag line here\n", encoding="utf-8")
    res = check(str(proj))
    assert res["verdict"] == "valid-fail"


# --- the hook: WARN shape ------------------------------------------------------

def test_orphan_warns_and_never_blocks(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "research" / "bar.md").write_text(
        "consumer: nonexistent-widget-xyz\n", encoding="utf-8")
    p = run_hook(BUILD_ROOT, "research_orphan_warn.py", _stop(proj))
    out = json.loads(p.stdout)
    assert "orphan" in out["systemMessage"].lower() or "consumer" in out["systemMessage"].lower()
    assert "decision" not in out
    assert "hookSpecificOutput" not in out


def test_consumed_brief_is_silent(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "research" / "foo.md").write_text(
        "consumer: tools/widget.py\n", encoding="utf-8")
    p = run_hook(BUILD_ROOT, "research_orphan_warn.py", _stop(proj))
    assert p.stdout.strip() == ""


def test_no_research_dir_is_a_cheap_no_op(tmp_path):
    root = tmp_path / "bare"
    root.mkdir()
    p = run_hook(BUILD_ROOT, "research_orphan_warn.py", _stop(root))
    assert p.stdout.strip() == ""


def test_broken_checker_stays_quiet(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "research" / "bar.md").write_text(
        "consumer: nonexistent-widget-xyz\n", encoding="utf-8")
    pr = broken_plugin(tmp_path, "tools/research_orphan_check.py", "crash")
    p = run_hook(pr, "research_orphan_warn.py", _stop(proj))
    assert p.stdout.strip() == ""
