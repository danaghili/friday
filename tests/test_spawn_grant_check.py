"""The spawn-grant checker, test-first.

**The measured fact this exists to defend** (`docs/research/probe-teammate-tool-grants.md`,
Claude Code v2.1.220): passing a `name` when spawning a role overwrites the
recorded `agentType` with that name, so the role's definition file can no
longer be resolved, so the spawn code falls through to its no-definition
branch and grants **every** tool in the session. friday's security reviewer —
declared `Read, Grep, Glob` plus three docs tools — came up holding a shell,
the user's mail, chat, files, calendar and a browser, and ran a shell command.
Spawned WITHOUT a name, the identical role file delivered exactly its six
declared tools.

So a role file's tool list is a real constraint on one spawn path and pure
decoration on the other, and nothing in the source says which path a lane
takes. That is this house's recurring failure class — a promise that reads as
enforced and is not — and a sentence in a lane file asking the lead to
remember is not a mechanism.

The rule: a role opts in by carrying a typed `grant-binding: <reason>` line,
meaning "my declared tool grant is load-bearing; spawn me unnamed or it
evaporates". Every live surface that dispatches such a role must carry the
typed `spawn-unnamed: <role>` marker. Trigger is the role file's own
declaration, never a mention — the same existence-triggered choice
`dispatch_liveness_check.py` makes, and for the same measured reason.

Hard failure by design: this checks friday's OWN source in friday's own suite
and ship gate, never a PM's project (S-200.5).
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import spawn_grant_check as sgc  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _role(tmp_path, name, *, binding=None, tools="Read, Grep, Glob"):
    """A role file. `binding` writes the typed opt-in line into its body."""
    d = tmp_path / "agents" / "roles"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name.replace('friday-', '')}.md"
    body = "You are a role.\n"
    if binding is not None:
        body += f"\ngrant-binding: {binding}\n"
    p.write_text(f"---\nname: {name}\ntools: {tools}\nmodel: sonnet\n---\n\n{body}",
                 encoding="utf-8")
    return p


def _surface(tmp_path, fname, text):
    d = tmp_path / "skills" / fname
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    p.write_text(text, encoding="utf-8")
    return p


# --- the empty case, defined and tested (house rule) ---------------------------------

def test_empty_tree_is_a_clean_pass(tmp_path):
    """No roles at all is a pass, not a crash and not a vacuous failure."""
    (tmp_path / "agents").mkdir()
    (tmp_path / "skills").mkdir()
    res = sgc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass", res
    assert res["roles_checked"] == 0
    assert res["unguarded"] == []


def test_role_without_the_opt_in_is_not_checked(tmp_path):
    """Most roles do not declare their grant load-bearing; they are out of scope
    entirely, so an un-marked dispatch of one is fine."""
    _role(tmp_path, "friday-tester", tools="Read, Write, Edit, Bash")
    _surface(tmp_path, "harden",
             "Spawn the tester (`friday-tester`, model: **sonnet**) over the diff.\n")
    res = sgc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass", res
    assert res["roles_checked"] == 0


# --- the rule itself -----------------------------------------------------------------

def test_guarded_dispatch_passes(tmp_path):
    _role(tmp_path, "friday-security-reviewer",
          binding="read-only sandbox; a named spawn grants every session tool")
    _surface(tmp_path, "security",
             "Spawn `friday-security-reviewer` (model: **opus**) over the mirror.\n"
             "spawn-unnamed: friday-security-reviewer\n")
    res = sgc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass", res
    assert res["unguarded"] == []
    assert res["roles_checked"] == 1


def test_unguarded_dispatch_is_a_hard_failure(tmp_path):
    """The whole point: a dispatch with no un-named marker silently hands the
    role every tool in the session."""
    _role(tmp_path, "friday-security-reviewer",
          binding="read-only sandbox; a named spawn grants every session tool")
    _surface(tmp_path, "security",
             "Spawn `friday-security-reviewer` (model: **opus**) over the mirror.\n")
    res = sgc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail", res
    assert any("friday-security-reviewer" in u for u in res["unguarded"]), res
    # the report must name the file to fix, not just the role
    assert any("skills/security/SKILL.md" in u.replace(os.sep, "/")
               for u in res["unguarded"]), res
    # and it must say what would fix it
    assert "spawn-unnamed:" in res["summary"]


def test_marker_for_a_different_role_does_not_satisfy_this_one(tmp_path):
    """A marker naming some other role must not launder this dispatch through."""
    _role(tmp_path, "friday-security-reviewer", binding="read-only sandbox")
    _role(tmp_path, "friday-redteam-reviewer", binding="read-only sandbox")
    _surface(tmp_path, "security",
             "Spawn `friday-security-reviewer` (model: **opus**) over the mirror.\n"
             "spawn-unnamed: friday-redteam-reviewer\n")
    res = sgc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail", res
    assert any("friday-security-reviewer" in u for u in res["unguarded"]), res


def test_every_dispatching_surface_needs_its_own_marker(tmp_path):
    """Two lanes spawn the role; marking one does not cover the other."""
    _role(tmp_path, "friday-experiment-runner", binding="no shell beyond its executor")
    _surface(tmp_path, "harden",
             "Spawn `friday-experiment-runner` (model: **sonnet**) on the batch.\n"
             "spawn-unnamed: friday-experiment-runner\n")
    _surface(tmp_path, "security",
             "Spawn `friday-experiment-runner` (model: **sonnet**) on the batch.\n")
    res = sgc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail", res
    assert len(res["unguarded"]) == 1
    assert "skills/security" in res["unguarded"][0].replace(os.sep, "/")


def test_bare_declaration_with_no_reason_is_refused(tmp_path):
    """Same discipline as `dispatch-exception:` — a typed line with no reason is
    a silent loosening of the rule, so it is a failure, not a pass."""
    _role(tmp_path, "friday-security-reviewer", binding="   ")
    _surface(tmp_path, "security",
             "Spawn `friday-security-reviewer` (model: **opus**) over the mirror.\n"
             "spawn-unnamed: friday-security-reviewer\n")
    res = sgc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail", res
    assert res["bare_declarations"] == ["friday-security-reviewer"], res


def test_role_declaring_but_dispatched_nowhere_is_not_our_failure(tmp_path):
    """Orphan roles are `dispatch_liveness_check.py`'s job. Two checkers must not
    both claim the same defect, or a fix silences one and not the other."""
    _role(tmp_path, "friday-security-reviewer", binding="read-only sandbox")
    _surface(tmp_path, "build", "The lead reviews security itself here.\n")
    res = sgc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-pass", res


def test_the_role_file_may_carry_the_marker_for_a_sibling(tmp_path):
    """A role file that dispatches another role is a live surface like any
    other, but its OWN `grant-binding:` reason must never self-satisfy."""
    _role(tmp_path, "friday-security-reviewer", binding="spawn-unnamed: friday-security-reviewer")
    _surface(tmp_path, "security",
             "Spawn `friday-security-reviewer` (model: **opus**) over the mirror.\n")
    res = sgc.check(root=str(tmp_path))
    assert res["verdict"] == "valid-fail", res


# --- the real tree ------------------------------------------------------------------

def test_this_repository_is_clean():
    res = sgc.check(root=REPO)
    assert res["verdict"] == "valid-pass", res["summary"]


def test_cli_exit_codes(tmp_path, capsys):
    (tmp_path / "agents").mkdir()
    (tmp_path / "skills").mkdir()
    assert sgc.main(["--root", str(tmp_path)]) == 0
    assert sgc.main(["--root", str(tmp_path / "nope")]) == 2
    _role(tmp_path, "friday-security-reviewer", binding="read-only sandbox")
    _surface(tmp_path, "security",
             "Spawn `friday-security-reviewer` (model: **opus**) over it.\n")
    assert sgc.main(["--root", str(tmp_path)]) == 1
