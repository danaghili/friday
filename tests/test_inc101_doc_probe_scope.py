"""INC-101 FR-101.3 / FR-101.4 / AC-101.3 / AC-101.4 — the record set is derived,
sized against the project's own bar, and nothing skipped is ever silent.

The scope tool is the mechanical half of the probe: it derives the record set
from the roles' own declared outputs plus the project front page (D2 — a list
carried in prose is exactly the rot this increment treats), reads the size bar
from the project's declared-bar home, and splits members into within-bar and
over-bar so the probe can read the first and NAME the second (S-101.4).
"""
import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "doc_probe_scope.py"


def run(root, roles_dir=None, extra=None):
    cmd = [sys.executable, str(TOOL), "--root", str(root), "--json"]
    if roles_dir:
        cmd += ["--roles-dir", str(roles_dir)]
    cmd += extra or []
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def project(tmp_path, standards=None, readme="# Front page\n"):
    root = tmp_path / "proj"
    root.mkdir()
    if readme is not None:
        (root / "README.md").write_text(readme)
    if standards is not None:
        std = root / "docs" / "standards"
        std.mkdir(parents=True)
        (std / "coding-standards.md").write_text(standards)
    return root


def roles(tmp_path, *outputs_lines):
    d = tmp_path / "agents" / "roles"
    d.mkdir(parents=True)
    for i, line in enumerate(outputs_lines):
        (d / f"role{i}.md").write_text(
            f"---\nname: friday-role{i}\ndescription: t\ntools: Read\nmodel: opus\n{line}\n---\nbody\n"
        )
    return tmp_path / "agents"


def test_outputs_are_parsed_with_annotations_and_joined_with_the_front_page(tmp_path):
    root = project(tmp_path)
    (root / "docs" / "ops").mkdir(parents=True)
    (root / "docs" / "ops" / "runbook.md").write_text("x")
    (root / "CLAUDE.md").write_text("x")
    agents = roles(
        tmp_path,
        "outputs: docs/ops/runbook.md, CLAUDE.md (`## Environments` maintenance)",
    )
    out = run(root, agents)
    paths = {m["path"] for m in out["members"]}
    assert paths == {"README.md", "docs/ops/runbook.md", "CLAUDE.md"}


def test_a_directory_output_expands_to_its_markdown_documents(tmp_path):
    root = project(tmp_path)
    std = root / "docs" / "standards"
    std.mkdir(parents=True)
    (std / "a.md").write_text("a")
    (std / "sub").mkdir()
    (std / "sub" / "b.md").write_text("b")
    (std / "notes.txt").write_text("not a document")
    agents = roles(tmp_path, "outputs: docs/standards/")
    out = run(root, agents)
    paths = {m["path"] for m in out["members"]}
    assert "docs/standards/a.md" in paths
    assert "docs/standards/sub/b.md" in paths
    assert "docs/standards/notes.txt" not in paths


def test_a_missing_output_is_named_missing_and_never_dropped(tmp_path):
    root = project(tmp_path)
    agents = roles(tmp_path, "outputs: docs/never-written.md")
    out = run(root, agents)
    assert out["missing"] == ["docs/never-written.md"]
    assert all(m["path"] != "docs/never-written.md" for m in out["members"])


def test_a_templated_output_is_named_patterned_not_missing(tmp_path):
    root = project(tmp_path)
    agents = roles(
        tmp_path, "outputs: docs/increments/INC-<n>.md, tests/test_bug_<id>_*.py"
    )
    out = run(root, agents)
    assert out["patterned"] == [
        "docs/increments/INC-<n>.md",
        "tests/test_bug_<id>_*.py",
    ]
    assert out["missing"] == []


def test_an_out_of_tree_output_is_named_as_such_not_missing(tmp_path):
    root = project(tmp_path)
    agents = roles(tmp_path, "outputs: ~/.claude/CLAUDE.md")
    out = run(root, agents)
    assert out["out_of_tree"] == ["~/.claude/CLAUDE.md"]
    assert out["missing"] == []


def test_a_missing_front_page_is_named_not_silently_absent(tmp_path):
    root = project(tmp_path, readme=None)
    agents = roles(tmp_path, "outputs:")
    out = run(root, agents)
    assert "README.md" in out["missing"]


def test_the_declared_bar_splits_within_from_over_and_the_front_page_reads_first(tmp_path):
    bar_block = (
        "<!-- FRIDAY-DOC-PROBE:BEGIN -->\ndoc-probe: read-kb <= 1\n<!-- FRIDAY-DOC-PROBE:END -->\n"
    )
    root = project(tmp_path, standards=bar_block, readme="r" * 512)
    (root / "big.md").write_text("b" * 2048)
    agents = roles(tmp_path, "outputs: big.md")
    out = run(root, agents)
    assert out["bar"] == {"read_kb": 1, "source": "declared"}
    within = [m["path"] for m in out["within_bar"]]
    over = [m["path"] for m in out["over_bar"]]
    assert within == ["README.md"]
    assert over == ["big.md"]


def test_no_bar_line_means_the_declared_default_and_says_so(tmp_path):
    root = project(tmp_path)
    agents = roles(tmp_path, "outputs:")
    out = run(root, agents)
    assert out["bar"]["source"] == "default"
    assert out["bar"]["read_kb"] > 0


def test_a_malformed_bar_line_is_surfaced_never_silently_defaulted(tmp_path):
    bar_block = (
        "<!-- FRIDAY-DOC-PROBE:BEGIN -->\ndoc-probe: read-kb <= banana\n<!-- FRIDAY-DOC-PROBE:END -->\n"
    )
    root = project(tmp_path, standards=bar_block)
    agents = roles(tmp_path, "outputs:")
    out = run(root, agents)
    assert out["bar"]["source"] == "default"
    assert "banana" in out["bar_error"]


def test_an_unreadable_member_is_named_unreadable_never_absorbed(tmp_path):
    import os

    root = project(tmp_path)
    locked = root / "locked.md"
    locked.write_text("cannot be read")
    os.chmod(locked, 0)
    try:
        agents = roles(tmp_path, "outputs: locked.md")
        out = run(root, agents)
        assert out["unreadable"] == ["locked.md"]
        assert all(m["path"] != "locked.md" for m in out["within_bar"])
    finally:
        os.chmod(locked, 0o644)


def test_the_empty_case_is_first_class(tmp_path):
    root = tmp_path / "bare"
    root.mkdir()
    agents = tmp_path / "agents"
    agents.mkdir()
    out = run(root, agents)
    assert out["members"] == []
    assert out["missing"] == ["README.md"]
    assert out["within_bar"] == []
    assert out["over_bar"] == []


def test_scope_widens_when_a_role_declares_a_new_output_with_no_tool_edit(tmp_path):
    root = project(tmp_path)
    (root / "new-doc.md").write_text("fresh")
    agents = roles(tmp_path, "outputs:")
    before = {m["path"] for m in run(root, agents)["members"]}
    assert "new-doc.md" not in before
    extra = tmp_path / "agents" / "roles" / "late.md"
    extra.write_text(
        "---\nname: friday-late\ndescription: t\ntools: Read\nmodel: opus\noutputs: new-doc.md\n---\nbody\n"
    )
    after = {m["path"] for m in run(root, agents)["members"]}
    assert "new-doc.md" in after
