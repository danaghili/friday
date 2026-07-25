"""Guard-skeleton tests — U1 foundation (TECHNICAL_SOW_REBUILD US-11: FR-58,
FR-60, FR-61; AC-14's fail-open conditions exercised at the skeleton level,
AC-15's block-message form).

The skeleton (hooks/_guard.py) is the ONE shape every guard is built from:
- run_checker(): runs a deterministic checker script and returns a TYPED
  verdict — valid-pass / valid-fail / no-verdict — keyed on verdict VALIDITY
  (the JSON shape the checker emits), never on exit code (FR-61).
- decide(): only a valid-fail verdict from a block-tier guard may block;
  no-verdict ALWAYS allows (fail-open, FR-58); warn-tier never blocks.
- block_message(): every block self-explains to a stranger — what was
  blocked, why in plain words, what to do next, and the override path
  (FR-58 / AC-15). A missing part is OUR contract violation: raised.
- emit_*(): the per-event-family JSON the harness expects.
- subagent_identity(): the ISSUE-007 in-hook identity check every
  SubagentStop-scoped guard must call (FR-60) — foreign or typeless events
  never clear an armed gate.

Fail-open matrix covered here (checker deleted / crashing / timing out /
empty output / garbage output / wrong-shape JSON) — the per-guard AC-14
tests re-exercise these through each real guard.
"""
import json
import os
import stat
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks"))
import _guard  # noqa: E402


# --- checker fixtures: tiny real scripts, one per failure mode -----------------

def _write_checker(tmp_path, name: str, body: str) -> str:
    path = tmp_path / name
    path.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


@pytest.fixture
def checker_pass(tmp_path):
    return _write_checker(tmp_path, "ok_pass.py", """
        import json
        print(json.dumps({"verdict": "valid-pass", "summary": "record backs the claim"}))
    """)


@pytest.fixture
def checker_fail(tmp_path):
    return _write_checker(tmp_path, "ok_fail.py", """
        import json
        print(json.dumps({"verdict": "valid-fail", "summary": "seeded lie found"}))
        raise SystemExit(1)  # exit code must NOT be what the guard keys on
    """)


@pytest.fixture
def checker_crash(tmp_path):
    return _write_checker(tmp_path, "crash.py", """
        raise RuntimeError("checker blew up before any verdict")
    """)


@pytest.fixture
def checker_slow(tmp_path):
    return _write_checker(tmp_path, "slow.py", """
        import time
        time.sleep(30)
    """)


@pytest.fixture
def checker_empty(tmp_path):
    return _write_checker(tmp_path, "empty.py", """
        pass  # exits 0 with no output at all
    """)


@pytest.fixture
def checker_garbage(tmp_path):
    return _write_checker(tmp_path, "garbage.py", """
        print("this is not JSON")
    """)


@pytest.fixture
def checker_wrong_shape(tmp_path):
    return _write_checker(tmp_path, "wrong_shape.py", """
        import json
        print(json.dumps({"ok": True}))  # JSON, but not a typed verdict
    """)


# --- run_checker: typed verdicts, keyed on validity never exit code -------------

def test_valid_pass_verdict(checker_pass):
    v = _guard.run_checker([sys.executable, checker_pass])
    assert v["verdict"] == "valid-pass"
    assert v["summary"] == "record backs the claim"


def test_valid_fail_verdict_despite_nonzero_exit(checker_fail):
    """FR-61: verdicts are keyed on verdict validity, never on exit code —
    a checker may exit non-zero on a genuine FAIL and the verdict still counts."""
    v = _guard.run_checker([sys.executable, checker_fail])
    assert v["verdict"] == "valid-fail"
    assert v["summary"] == "seeded lie found"


def test_missing_checker_is_no_verdict(tmp_path):
    v = _guard.run_checker([sys.executable, str(tmp_path / "does-not-exist.py")])
    assert v["verdict"] == "no-verdict"


def test_crashing_checker_is_no_verdict(checker_crash):
    v = _guard.run_checker([sys.executable, checker_crash])
    assert v["verdict"] == "no-verdict"


def test_timing_out_checker_is_no_verdict(checker_slow):
    v = _guard.run_checker([sys.executable, checker_slow], timeout_s=1)
    assert v["verdict"] == "no-verdict"


def test_empty_output_is_no_verdict(checker_empty):
    v = _guard.run_checker([sys.executable, checker_empty])
    assert v["verdict"] == "no-verdict"


def test_garbage_output_is_no_verdict(checker_garbage):
    v = _guard.run_checker([sys.executable, checker_garbage])
    assert v["verdict"] == "no-verdict"


def test_wrong_shape_json_is_no_verdict(checker_wrong_shape):
    """JSON that parses but is not a typed verdict is an INVALID verdict —
    the AC-14 'invalid/empty verdict' fail-open condition."""
    v = _guard.run_checker([sys.executable, checker_wrong_shape])
    assert v["verdict"] == "no-verdict"


def test_no_verdict_carries_detail_for_stderr(checker_crash):
    """The guard fails open but the WHY is preserved for stderr breadcrumbs —
    silence about a broken checker would hide guard rot (cf. guard #21's
    tamper-visibility principle)."""
    v = _guard.run_checker([sys.executable, checker_crash])
    assert v.get("detail")


# --- decide: the fail-open law as a pure function --------------------------------

def _msg():
    return _guard.block_message(
        what="Closing the bug lane",
        why="BUG-004 has no committed regression test.",
        fix="Commit the reproduction as a failing test, then close.",
        override="If you are deliberately closing without one, record a PM decision first.",
    )


def test_block_tier_blocks_only_on_valid_fail(checker_fail):
    action = _guard.decide({"verdict": "valid-fail", "summary": "lie"}, tier="block", reason=_msg())
    assert action.kind == "block"
    assert "regression test" in action.reason


def test_block_tier_allows_on_valid_pass():
    action = _guard.decide({"verdict": "valid-pass"}, tier="block", reason=_msg())
    assert action.kind == "allow"


def test_block_tier_fails_open_on_no_verdict():
    """FR-58: a missing/crashing/garbled checker ALLOWS the action."""
    action = _guard.decide({"verdict": "no-verdict", "detail": "boom"}, tier="block", reason=_msg())
    assert action.kind == "allow"


def test_warn_tier_never_blocks():
    """FR-56: warning guards never block, even on a valid failing verdict."""
    action = _guard.decide({"verdict": "valid-fail", "summary": "stale"}, tier="warn", reason=_msg())
    assert action.kind == "warn"
    assert action.kind != "block"


def test_unknown_tier_is_our_contract_violation():
    with pytest.raises(ValueError):
        _guard.decide({"verdict": "valid-pass"}, tier="blocky", reason=_msg())


# --- block_message: the stranger-proof four-part form (AC-15) --------------------

def test_block_message_contains_all_four_parts():
    msg = _msg()
    for part in ("Closing the bug lane", "no committed regression test",
                 "Commit the reproduction", "record a PM decision"):
        assert part in msg


def test_block_message_rejects_missing_parts():
    """A block that cannot say what/why/next/override is OUR emission bug —
    raised at build time, never shipped half-mute (boundary validation)."""
    with pytest.raises(ValueError):
        _guard.block_message(what="X", why="", fix="do Y", override="Z")


# --- emit shapes: per event family ------------------------------------------------

def test_emit_block_pretooluse_shape():
    out = _guard.emit_block("PreToolUse", "reason text")
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == "reason text"


@pytest.mark.parametrize("family", ["Stop", "SubagentStop", "PostToolUse"])
def test_emit_block_decision_shape(family):
    out = _guard.emit_block(family, "reason text")
    assert out == {"decision": "block", "reason": "reason text"}


def test_emit_block_unknown_family_raises():
    with pytest.raises(ValueError):
        _guard.emit_block("FileChanged", "r")  # no block channel there — warn instead


def test_emit_warn_shape():
    assert _guard.emit_warn("heads up") == {"systemMessage": "heads up"}


def test_emitted_json_is_serializable():
    json.dumps(_guard.emit_block("PreToolUse", "r"))
    json.dumps(_guard.emit_warn("w"))


# --- subagent identity (FR-60 / ISSUE-007) ----------------------------------------

def test_identity_match():
    assert _guard.subagent_identity({"agent_type": "friday-closer"}, "closer") == "match"


def test_identity_foreign_never_clears():
    assert _guard.subagent_identity({"agent_type": "friday-tester"}, "closer") == "foreign"


def test_identity_typeless_is_its_own_posture():
    """#27755: agent_type may arrive empty/missing — that is 'typeless', a
    distinct posture each guard documents; it is never silently 'match'."""
    assert _guard.subagent_identity({}, "closer") == "typeless"
    assert _guard.subagent_identity({"agent_type": "  "}, "closer") == "typeless"
