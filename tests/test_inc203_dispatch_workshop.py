"""INC-203 FR-203.7 / AC-203.6 — the orphan-detector sees friday's own workshop.

The measured hole (INC-203 §1): `dispatch_liveness_check.py` walked `agents/`
only, so the two repo-internal workshop agents under `.claude/agents/` were
invisible to the exact checker built to catch orphaned roles — and the record
had demanded a doc-truth run ten times with the wiring never once existing.
D9 (PM-ratified): the checker walks `.claude/agents/` alongside `agents/` and
widens its live-surface search to match (`.claude/skills/` is where the
workshop's real callers live).

Same rule as INC-200 D2 throughout: trigger on the role FILE EXISTING, pass
only on a real dispatch (agent + `model:` on one line) or a typed exception.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import dispatch_liveness_check as dlc  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _workshop_agent(tmp_path, name, body="You are a workshop agent.\n"):
    d = tmp_path / ".claude" / "agents"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.md"
    p.write_text(f"---\nname: {name}\nmodel: opus\n---\n\n{body}",
                 encoding="utf-8")
    return p


def _workshop_skill(tmp_path, slug, text):
    d = tmp_path / ".claude" / "skills" / slug
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_undispatched_workshop_agent_is_seen_and_fails(tmp_path):
    """An orphan under .claude/agents/ must be a valid-fail, not invisible —
    the pre-widening tool passes this tree clean, which is the measured bug."""
    _workshop_agent(tmp_path, "lint-helper")
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail", res
    assert "lint-helper" in res["orphans"]


def test_workshop_agent_dispatched_from_workshop_skill_passes(tmp_path):
    """The workshop's own callers live under .claude/skills/ — a dispatch line
    there (agent + model:, same line) must count, or the widening would orphan
    every workshop agent with a real caller."""
    _workshop_agent(tmp_path, "lint-helper")
    _workshop_skill(tmp_path, "new-surface",
                    "Run the **`lint-helper`** subagent (model: opus) on the "
                    "new file before considering it done.\n")
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass", res
    assert res["orphans"] == []


def test_workshop_agent_dispatched_from_shipped_surface_also_counts(tmp_path):
    """A dispatch is a dispatch wherever the live surface lives — a shipped
    lane skill naming a workshop agent beside its model passes it."""
    _workshop_agent(tmp_path, "truth-checker")
    d = tmp_path / "skills" / "reconcile"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "Spawn the checker (`truth-checker`, model: opus) over the tree.\n",
        encoding="utf-8")
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass", res


def test_mention_without_model_still_orphans_workshop_agent(tmp_path):
    """Prose that merely names the agent is the defect, not a dispatch —
    unchanged from INC-200 D2, now enforced over the workshop too."""
    _workshop_agent(tmp_path, "lint-helper")
    _workshop_skill(tmp_path, "new-surface",
                    "Run the lint-helper subagent on the new file.\n")
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail", res
    assert "lint-helper" in res["orphans"]


def test_shipped_role_mentioned_only_in_workshop_file_still_orphans(tmp_path):
    """AC-203.6's guard on the widening itself: a shipped role whose only
    mention lives under .claude/ (no model beside it) must stay an orphan —
    the wider surface walk must not soften the mention-vs-dispatch line."""
    d = tmp_path / "agents" / "roles"
    d.mkdir(parents=True, exist_ok=True)
    (d / "tester.md").write_text(
        "---\nname: friday-tester\nmodel: sonnet\n---\n\nYou are a role.\n",
        encoding="utf-8")
    _workshop_skill(tmp_path, "new-surface",
                    "The friday-tester role also exists in the roster.\n")
    res = dlc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail", res
    assert "friday-tester" in res["orphans"]


