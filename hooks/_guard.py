#!/usr/bin/env python3
"""friday guard skeleton — the ONE shape every guard is built from (U1
foundation; TECHNICAL_SOW_REBUILD US-11: FR-58 global rules, FR-60 identity
self-verify, FR-61 typed verdicts; AC-15 block-message form).

The doctrine, in one place so no guard re-derives it:

- **Typed verdicts, never exit codes (FR-61).** A checker is a deterministic
  script that prints ONE JSON object: {"verdict": "valid-pass"|"valid-fail",
  "summary": "...", ...}. `run_checker()` returns that object verbatim when it
  is well-formed and {"verdict": "no-verdict", "detail": "..."} for EVERY
  other outcome — missing script, crash, timeout, empty stdout, non-JSON,
  or JSON of the wrong shape. Exit codes are deliberately ignored: a checker
  may exit non-zero on a genuine FAIL and its verdict still counts.

- **Fail-open (FR-58).** `decide()` is the whole law as a pure function:
  only a block-tier guard holding a valid-fail verdict blocks; a warn-tier
  guard never blocks; no-verdict ALWAYS allows. A false block trains the PM
  to override guards — worse than a miss. The no-verdict detail is preserved
  so callers can leave a stderr breadcrumb (guard rot must stay visible,
  cf. guard #21).

- **Stranger-proof blocks (AC-15).** `block_message()` refuses to build a
  message missing any of its four parts: what was blocked, why in plain
  words, what to do next, and the override path. A half-mute block is OUR
  emission bug — raised at build time, never shipped.

- **Per-family emission.** The harness accepts different block channels per
  event family: PreToolUse rides hookSpecificOutput.permissionDecision=deny;
  Stop/SubagentStop/PostToolUse ride {"decision": "block"}. Warn-only
  families (e.g. FileChanged) have NO block channel — `emit_block()` raises
  rather than silently degrade a block into advice; the guard author must
  choose `emit_warn()` there on purpose.

- **Identity self-verify (FR-60 / ISSUE-007).** SubagentStop matchers cannot
  be trusted to filter by agent type; every subagent-scoped guard calls
  `subagent_identity()` in-hook. 'foreign' and 'typeless' events never arm
  and NEVER clear an armed gate; each guard documents its typeless posture.

Guards themselves stay thin: read event → (identity check) → run_checker →
decide → print the emission and exit 0. Hooks always exit 0 on their own
behalf; a block rides the JSON, never the exit code (house idiom, cf.
state_stop_gate.py).

Pure stdlib.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

# The only verdicts a checker may validly emit (FR-61). Anything else —
# including a missing "verdict" key — is an invalid verdict → no-verdict.
_VALID_VERDICTS = ("valid-pass", "valid-fail")

# Guard tiers (FR-55/56/57). "silent" guards journal or configure; they never
# emit user-facing decisions, so decide() treats them like warn-with-no-message.
_TIERS = ("block", "warn", "silent")

# Event families with a real block channel, and the JSON shape each expects.
# Families absent here (FileChanged, SessionStart, ...) cannot block — that is
# a fact about the harness, enforced by emit_block() raising.
_PRETOOL_FAMILIES = ("PreToolUse",)
_DECISION_FAMILIES = ("Stop", "SubagentStop", "PostToolUse")

# Default checker budget. PreToolUse windows must stay snappy (guard #7 was
# measured at 55–68 ms); 10 s is the generous ceiling before we stop trusting
# the run and fail open — a stuck checker must never stall the PM's session.
DEFAULT_TIMEOUT_S = 10


def run_checker(argv: list[str], timeout_s: float = DEFAULT_TIMEOUT_S,
                stdin_text: str | None = None) -> dict:
    """Run a checker subprocess and return its TYPED verdict.

    Returns the checker's own JSON object when it is a well-formed verdict;
    otherwise {"verdict": "no-verdict", "detail": <why>} covering every
    AC-14 fail-open condition (deleted / crashing / timeout / invalid or
    empty verdict). Never raises.

    `stdin_text` feeds a checker that must see CONTENT rather than just a path
    — a PreToolUse guard judging the change about to be written, which cannot
    read it from disk because it has not landed yet. Default None preserves the
    previous behaviour exactly for every other caller.
    """
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout_s,
                              input=stdin_text)
    except subprocess.TimeoutExpired:
        return {"verdict": "no-verdict", "detail": f"checker timed out after {timeout_s}s"}
    except Exception as exc:  # missing interpreter/script, OSError, ...
        return {"verdict": "no-verdict", "detail": f"checker unrunnable: {exc}"}

    out = (proc.stdout or "").strip()
    if not out:
        detail = (proc.stderr or "").strip()[:500] or "checker produced no output"
        return {"verdict": "no-verdict", "detail": detail}
    try:
        verdict = json.loads(out)
    except ValueError:
        return {"verdict": "no-verdict", "detail": f"checker output was not JSON: {out[:200]}"}
    if not isinstance(verdict, dict) or verdict.get("verdict") not in _VALID_VERDICTS:
        return {"verdict": "no-verdict", "detail": f"checker emitted an invalid verdict shape: {out[:200]}"}
    return verdict


@dataclass(frozen=True)
class Action:
    """What a guard should do: kind is 'allow' | 'block' | 'warn'. reason is
    the full block/warn text ('' for allow); detail carries the no-verdict
    breadcrumb for the caller's stderr."""
    kind: str
    reason: str = ""
    detail: str = ""


def decide(verdict: dict, tier: str, reason: str) -> Action:
    """The fail-open law as a pure function (FR-58).

    Only tier='block' with a valid-fail verdict blocks. tier='warn' surfaces
    the reason without blocking. no-verdict allows regardless of tier,
    carrying the checker's failure detail for a stderr breadcrumb.
    """
    if tier not in _TIERS:
        raise ValueError(f"tier must be one of {_TIERS}, got {tier!r}")
    kind = verdict.get("verdict") if isinstance(verdict, dict) else None
    if kind == "valid-fail":
        if tier == "block":
            return Action("block", reason=reason)
        if tier == "warn":
            return Action("warn", reason=reason)
        return Action("allow")  # silent tier: journal elsewhere, never message
    if kind == "valid-pass":
        return Action("allow")
    # no-verdict (or a caller bug handing us garbage): fail OPEN, keep the why.
    detail = verdict.get("detail", "") if isinstance(verdict, dict) else "malformed verdict object"
    return Action("allow", detail=str(detail))


def block_message(what: str, why: str, fix: str, override: str) -> str:
    """The stranger-proof four-part block text (AC-15): what was blocked, why
    in plain words, what to do next, and the override path. Raises ValueError
    on any missing part — a half-mute block is our own emission bug."""
    parts = {"what": what, "why": why, "fix": fix, "override": override}
    missing = [name for name, value in parts.items() if not (value or "").strip()]
    if missing:
        raise ValueError(f"block_message missing required part(s): {', '.join(missing)}")
    return (
        f"BLOCKED: {what.strip()}\n\n"
        f"Why: {why.strip()}\n\n"
        f"What to do next: {fix.strip()}\n"
        f"Override path: {override.strip()}"
    )


def emit_block(event_family: str, reason: str) -> dict:
    """The harness JSON that carries a block on the given event family.
    Raises ValueError for families with no block channel — degrading a block
    into silent advice must be a conscious emit_warn() choice, never a default."""
    if event_family in _PRETOOL_FAMILIES:
        return {"hookSpecificOutput": {
            "hookEventName": event_family,
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}
    if event_family in _DECISION_FAMILIES:
        return {"decision": "block", "reason": reason}
    raise ValueError(f"event family {event_family!r} has no block channel; use emit_warn")


def emit_warn(message: str) -> dict:
    """A user-visible warning that never blocks (FR-56 tier)."""
    return {"systemMessage": message}


def subagent_identity(event: dict, needle: str) -> str:
    """'match' | 'foreign' | 'typeless' for a SubagentStop-scoped guard
    (FR-60). Inline port of friday_substrate.event_matches_agent so a broken
    substrate import cannot silently disable identity checking — the two are
    kept in lockstep by tests/test_guard_skeleton.py + test_substrate.py."""
    val = None
    for key in ("agent_type", "subagent_type", "agentType", "subagentType"):
        candidate = event.get(key)
        if isinstance(candidate, str) and candidate.strip():
            val = candidate.strip()
            break
    if val is None:
        agent = event.get("agent")
        if isinstance(agent, dict):
            for key in ("type", "agent_type", "subagent_type", "agentType", "subagentType"):
                candidate = agent.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    val = candidate.strip()
                    break
    if val is None:
        return "typeless"
    return "match" if needle.lower() in val.lower() else "foreign"
