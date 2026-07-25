"""BUG-003 — README-table sync is guarded by nobody: `--check` never read the
README, and the no-arg hook invocation wrote nothing. The fix makes `--check`
compare the README's COMMAND-INDEX block against the rendered table (README
named by --write, defaulting to README.md; nothing is written in check mode).
Regression-first: these pins were red on the pre-fix tool.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import gen_command_index as gci  # noqa: E402


LANE = """---
name: demo
description: the NEW description after an edit — long enough for the lane floor
friday-lane: true
---

body
"""


def _tree(tmp_path):
    (tmp_path / "commands").mkdir(exist_ok=True)
    lane = tmp_path / "skills" / "demo"
    lane.mkdir(parents=True, exist_ok=True)
    (lane / "SKILL.md").write_text(LANE, encoding="utf-8")
    return str(tmp_path / "commands"), str(tmp_path / "skills")


def _args(tmp_path, readme=None):
    cmds, sk = _tree(tmp_path)
    out = ["--commands-dir", cmds, "--skills-dir", sk, "--check"]
    if readme is not None:
        out += ["--write", str(readme)]
    return out


def test_stale_readme_block_fails_check(tmp_path, capsys):
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# fixture\n\n{gci.BEGIN}\n| Command | What it does |\n| --- | --- |\n"
        f"| `/friday:demo` | the STALE description from before the edit |\n{gci.END}\n",
        encoding="utf-8")
    assert gci.main(_args(tmp_path, readme)) == 1
    assert "STALE" in capsys.readouterr().out
    # check mode never writes — the stale block is untouched
    assert "STALE description" in readme.read_text(encoding="utf-8")


def test_fresh_readme_block_passes_check(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(f"# fixture\n\n{gci.BEGIN}\nplaceholder\n{gci.END}\n",
                      encoding="utf-8")
    cmds, sk = _tree(tmp_path)
    assert gci.main(["--commands-dir", cmds, "--skills-dir", sk,
                     "--write", str(readme)]) == 0  # splice for real
    assert gci.main(_args(tmp_path, readme)) == 0   # then the check agrees


def test_absent_readme_is_the_defined_empty_case(tmp_path):
    # no README to compare → shadow-only check, clean pass (the test-tree case)
    assert gci.main(_args(tmp_path, tmp_path / "no-such-README.md")) == 0


def test_markerless_readme_skips_comparison(tmp_path):
    # a README with no marker pair holds no generated block — nothing can drift
    readme = tmp_path / "README.md"
    readme.write_text("# no markers here\n", encoding="utf-8")
    assert gci.main(_args(tmp_path, readme)) == 0


def test_shadow_still_fails_even_with_fresh_readme(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(f"{gci.BEGIN}\nx\n{gci.END}\n", encoding="utf-8")
    cmds, sk = _tree(tmp_path)
    gci.main(["--commands-dir", cmds, "--skills-dir", sk, "--write", str(readme)])
    (tmp_path / "commands" / "demo.md").write_text(
        "demo — the shadow form\n", encoding="utf-8")
    assert gci.main(["--commands-dir", cmds, "--skills-dir", sk,
                     "--check", "--write", str(readme)]) == 1
