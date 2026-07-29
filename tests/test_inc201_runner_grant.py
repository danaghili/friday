"""INC-201 FR-201.8 / FR-201.10 — the runner's grant is the prohibition.

For the whole of INC-200 the runner was *told* to run nothing but its executor.
That is a promise about behaviour, and the contract said so honestly: a `Bash`
grant names a tool, not a permitted command, so "only this one script" could not
be expressed where it would be enforced. This increment closes it by removing
`Bash` — the sentence "you never run a shell command" stops being a rule the
runner keeps and becomes a description of what it holds.

Which makes the frontmatter itself load-bearing, so it is tested. A future edit
that adds `Bash` back "just for a moment" is not a style regression; it silently
returns the runner to a world where the containment is a promise again, and
nothing else in the suite would notice.

These assertions are deliberately about the FILE, not about a running agent.
Whether a grant binds at spawn time is a separate, measured question with its own
answer (`docs/research/probe-teammate-tool-grants.md`: only on the un-named
path), enforced by `tools/spawn_grant_check.py`. Both halves are needed — a
correct list that does not bind is worth nothing, and so is a binding list with
the wrong contents.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

ROLE = os.path.join(ROOT, "agents", "roles", "experiment-runner.md")
PLAN = "mcp__plugin_friday_friday-experiments__plan"
RUN = "mcp__plugin_friday_friday-experiments__run"


def _frontmatter(path=ROLE):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "role file must open with a frontmatter block"
    return m.group(1), text


def _tools():
    fm, _ = _frontmatter()
    line = next(ln for ln in fm.splitlines() if ln.startswith("tools:"))
    return [t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()]


def test_the_runner_holds_no_shell_and_no_write():
    """The one that matters. Bash is the whole reason INC-201 exists; Write and
    Edit matter too, because the consent record's unforgeability rests on the
    runner being unable to write into `.friday/` at all."""
    granted = set(_tools())
    for forbidden in ("Bash", "Write", "Edit", "MultiEdit", "NotebookEdit", "Task", "Agent"):
        assert forbidden not in granted, f"{forbidden} is back in the runner's grant"


def test_the_runner_is_granted_both_experiment_tools():
    granted = _tools()
    assert PLAN in granted and RUN in granted, granted


def test_the_grant_is_named_tool_by_tool_with_no_wildcard():
    """A wildcard would quietly widen with every tool the server later grows."""
    for t in _tools():
        assert "*" not in t, t


def test_the_declared_tools_are_the_ones_the_server_actually_exposes():
    """Guards the seam a typo lives in: a misspelled MCP tool name is not an
    error anywhere — the runner simply comes up without it and stands down
    forever, which reads exactly like the door being down."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "experiments_server", os.path.join(ROOT, "tools", "experiments", "server.py"))
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    exposed = {t["name"] for t in server.TOOLS}
    for granted in (PLAN, RUN):
        assert granted.rsplit("__", 1)[1] in exposed, (granted, exposed)


def test_the_role_no_longer_tells_the_runner_to_shell_out():
    """The old file handed it a `python3 tools/experiment_run.py …` command line.
    Leaving that in would be an instruction it can no longer follow — and a
    reader would reasonably conclude the grant was the mistake."""
    _, text = _frontmatter()
    assert "python3" not in text, "the role still spells out a shell command"
    assert "experiment_run.py" not in text


def test_the_role_still_forbids_inventing_moves_and_batch_ids():
    """Removing the shell must not read as removing the discipline. The batch id
    is now the ONLY thing the runner supplies, so it is the only injection
    surface left and the file has to say so."""
    _, text = _frontmatter()
    low = text.lower()
    assert "batch id" in low
    assert "data, never an instruction" in low or "data, never" in low


def test_the_door_failing_is_a_stand_down_not_a_workaround():
    """FR-201.10, stated in the role file as intended behaviour rather than left
    to an error path. An agent that meets a broken door and goes looking for
    another way in is the exact failure this increment removes the shell to
    prevent — so the file must name standing down as the correct outcome AND
    forbid routing around it."""
    _, text = _frontmatter()
    low = text.lower()
    assert "stand down" in low
    assert "informational" in low
    assert "way round" in low or "work around" in low or "another way" in low
