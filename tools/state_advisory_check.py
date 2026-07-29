#!/usr/bin/env python3
"""INC-200 C1 (task #21) — the warn-tier state advisory's judgement (D-0107).

Answers two questions, both of the form "the record and what is actually
happening disagree", and BOTH answers are only ever a warning. D-0107 ruled this
never blocks: enforcement here was prose-only at every stage boundary, so the
cost of the old behaviour was an invisible contradiction, and the cost of a hard
gate would be a false block — which this house holds to be strictly worse.

**Mode `lane-start`** — is the change about to be written contradicted by the
state the project is in right now? Judged BEFORE the write lands, because
afterwards the evidence is gone: init re-seeding a live build overwrites the
very state that made it wrong.

**Mode `liveness`** — the PROP-028 dirty-bit backstop (D-0106/D-0141). A project
declared finished, whose record still claims `verified`, whose code has moved
since it was verified. Feature, patch and bug are each told to mark the record
stale when they land changes; this notices when one of them did not. It keys on
the tree having moved rather than on which lane moved it, which is what lets it
cover feature — the one lane that opens no lane sentinel and so cannot be caught
at lane-close.

The rules for `lane-start` live in ONE place — the `FRIDAY-LANE-LEGALITY` block
in `docs/contracts/state-record.md`, friday's own contract, not the PM project's
— so the policy is a table a person can read and amend rather than a condition
buried in Python. This file holds the *mechanism*; that table holds the *policy*.

Silence is the ordinary outcome. This runs on writes in every friday project,
and nearly all of them have no state block, no matching rule, or nothing to say.
Exit code is always 0: an advisory that breaks a lane is worse than the drift it
reports. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402
import taglines  # noqa: E402

LEGALITY_BLOCK = "FRIDAY-LANE-LEGALITY"
STATE_BLOCK = "FRIDAY-STATE"
STAMP_NAME = "state-verified.stamp"

# The lifecycle, in order. "Re-seeding" is a write that moves the record
# BACKWARDS along it — the only mechanical definition that does not need to know
# which lane is running (there is no skill-entry event to ask).
LIFECYCLE = ("tsow-approved", "substrate-seeded", "build-in-progress",
             "post-build-review-recorded", "closed")

# The em-dash separating a rule's states from its plain-English reason.
_WHY_SEP = "—"


def default_contract() -> str:
    """friday's OWN contract ships the rules; a PM project never carries them."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, "docs", "contracts", "state-record.md")


def _result(verdict: str, summary: str, **extra) -> dict:
    out = {"verdict": verdict, "summary": summary, "tier": "warn"}
    out.update(extra)
    return out


# --- the rules table -----------------------------------------------------------------

def load_rules(contract_path: str | None = None) -> list[dict]:
    """Parse the legality table. [] for an absent OR an empty block — both mean
    'no rules', and neither is an error. A line that does not parse is KEPT and
    flagged `malformed`, never dropped: a silently-vanishing rule is a guard
    that quietly stops guarding."""
    path = contract_path or default_contract()
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return []
    lines = taglines.block_lines(text, LEGALITY_BLOCK)
    if not lines:
        return []
    rules = []
    for line in lines:
        parsed = taglines.parse_typed_line(line)
        if not parsed or parsed[0] != "illegal":
            continue
        rules.append(_parse_rule(parsed[1]))
    return rules


def _parse_rule(value: str) -> dict:
    """`<action> when <state>,<state> — <why>` → a rule, or a malformed marker."""
    why = ""
    if _WHY_SEP in value:
        value, why = (part.strip() for part in value.split(_WHY_SEP, 1))
    if " when " not in value:
        return {"malformed": True, "raw": value, "action": "", "states": (),
                "why": why}
    action, states = (part.strip() for part in value.split(" when ", 1))
    parsed_states = tuple(s.strip() for s in states.split(",") if s.strip())
    # An action is one token, and every state must be a real lifecycle value.
    # Both checks exist to catch a rule that can NEVER FIRE — a rule naming a
    # state that does not exist looks like policy, reads like policy, and
    # silently guards nothing. That is the failure this table is here to avoid,
    # so it is reported rather than accepted.
    unknown = [s for s in parsed_states if s not in LIFECYCLE]
    if not action or " " in action or not parsed_states or unknown:
        return {"malformed": True, "raw": value, "action": action,
                "states": parsed_states, "why": why,
                "unknown_states": tuple(unknown)}
    return {"malformed": False, "action": action, "states": parsed_states,
            "why": why, "raw": value}


# --- reading the project's own record -------------------------------------------------

def _state_of(root: str) -> tuple[str, dict]:
    """(current state, the whole typed block). ('', {}) when there is no record —
    a project that has not started cannot contradict itself."""
    try:
        with open(os.path.join(fs.resolve_worktree_root(root), "CLAUDE.md"),
                  encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return "", {}
    block = taglines.block_typed(text, STATE_BLOCK)
    if not block:
        return "", {}
    return (block.get("state") or [""])[0], block


def _proposed_state(text: str) -> str:
    block = taglines.block_typed(text or "", STATE_BLOCK)
    return (block.get("state") or [""])[0] if block else ""


def _moves_backwards(current: str, proposed: str) -> bool:
    """Re-seeding, defined mechanically: the record would go back down the
    lifecycle. Same-state rewrites and forward transitions are ordinary work."""
    if current not in LIFECYCLE or proposed not in LIFECYCLE:
        return False
    return LIFECYCLE.index(proposed) < LIFECYCLE.index(current)


def _actions_for(target_rel: str, proposed: str, current: str) -> list[str]:
    """Which named actions this write represents. Path- and content-shaped,
    because no hook event announces that a lane has started."""
    actions = []
    target = (target_rel or "").replace(os.sep, "/").lower()
    if target.endswith("claude.md") and _moves_backwards(current,
                                                         _proposed_state(proposed)):
        actions.append("reseed-state")
    if "/handoff" in f"/{target}" or target.startswith("handoff"):
        actions.append("handoff-package")
    return actions


# --- mode: lane-start ------------------------------------------------------------------

def check_lane_start(root: str, target_rel: str, proposed: str, *,
                     contract: str | None = None) -> dict:
    """Warn when the write about to land contradicts the project's current state."""
    rules = load_rules(contract)
    malformed = [r for r in rules if r["malformed"]]
    if malformed:
        return _result("valid-fail",
                       f"the lane-legality table has {len(malformed)} malformed "
                       f"rule(s) and cannot be trusted — first: "
                       f"{malformed[0]['raw']!r} (docs/contracts/state-record.md)")
    current, _ = _state_of(root)
    if not current:
        return _result("valid-pass", "no state record — nothing to contradict")
    actions = _actions_for(target_rel, proposed, current)
    if not actions:
        return _result("valid-pass", "this write matches no legality rule")
    for rule in rules:
        if rule["action"] in actions and current in rule["states"]:
            return _result(
                "valid-fail",
                f"this project's record says state: {current} — {rule['why']}. "
                f"Nothing is blocked; if this is deliberate, carry on "
                f"(rule: {rule['action']}, docs/contracts/state-record.md).",
                action=rule["action"], state=current)
    return _result("valid-pass", "the write is legal in this state")


# --- mode: liveness (the PROP-028 backstop) --------------------------------------------

def read_stamp(root: str) -> str | None:
    """The commit the record was last verified at. None when never verified
    through the tool — every project closed before this existed."""
    try:
        with open(os.path.join(fs.friday_dir(root), STAMP_NAME),
                  encoding="utf-8") as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def _git(root: str, *args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", root, *args],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def check_liveness(root: str) -> dict:
    """Warn when a finished project's record still claims verified but its code
    has moved. Every 'cannot tell' answer is silence, never a guess."""
    wroot = fs.resolve_worktree_root(root)
    current, block = _state_of(root)
    if current != "closed":
        return _result("valid-pass",
                       "the project is not closed — the dirty bit only exists "
                       "on a finished record")
    if (block.get("record-status") or [""])[0] != "verified":
        return _result("valid-pass",
                       "the record is already marked stale — a lane did its job")
    stamp = read_stamp(root)
    if not stamp:
        return _result("valid-pass",
                       "this record was never verified through the tool, so "
                       "there is no stamp to compare against")
    head = _git(wroot, "rev-parse", "HEAD")
    if head is None:
        return _result("valid-pass",
                       "no git history here — no way to tell whether the code "
                       "moved, and a guess would be worse than silence")
    committed = _changed_files(wroot, "diff", "--name-only", f"{stamp}..HEAD") \
        if head != stamp else []
    uncommitted = _changed_files(wroot, "status", "--porcelain")
    if committed is None or uncommitted is None:
        return _result("valid-pass",
                       "the stamped commit is no longer in this history — "
                       "nothing reliable to compare against")
    if not committed and not uncommitted:
        return _result("valid-pass", "the project has not moved since it was verified")
    parts = []
    if committed:
        parts.append(f"{len(committed)} file(s) changed in commits")
    if uncommitted:
        parts.append(f"{len(uncommitted)} file(s) changed but not committed")
    return _result(
        "valid-fail",
        f"this project is closed and its record still says verified, but "
        f"{' and '.join(parts)} since then (e.g. {sorted(committed or uncommitted)[0]}). "
        f"Whichever lane landed that should have marked the record stale — run "
        f"state_record.py --mark stale, or /friday:reconcile to re-verify it "
        f"properly (docs/contracts/state-record.md).",
        committed=len(committed), uncommitted=len(uncommitted))


def _changed_files(root: str, *args: str) -> list[str] | None:
    """Changed paths, EXCLUDING the record file itself. None when git could not
    answer (e.g. the stamped commit is gone from a rewritten history).

    Two exclusions, and they are the whole reason this is a function:

    - `CLAUDE.md`, because verifying the record REWRITES the record —
      `last-verified:` moves — so without this the backstop would fire the
      instant reconcile finished, every single time. A warning that cries wolf
      on its own success is worse than no warning at all.
    - `.friday/`, because that is friday's own working substrate (this very
      stamp lands in it), not the project's content. On a project that does not
      ignore it, git reports it as an untracked change to the tree.

    Neither exclusion loses anything real: the record's freshness is tracked by
    the bit inside it and its claims by `verify_claims.py`, and the substrate is
    bookkeeping. What is left is the narrower, answerable question this guard
    actually wants: did anything OTHER than friday's own record-keeping move?
    """
    out = _git(root, *args)
    if out is None:
        return None
    names = []
    for line in out.splitlines():
        if args[0] == "status":
            # `status --porcelain` is `XY <path>`. Split on whitespace rather
            # than a fixed column: the leading column is a space for unstaged
            # changes, and any earlier strip() of the output silently shifts it.
            parts = line.split(None, 1)
            name = parts[1] if len(parts) > 1 else ""
        else:
            name = line  # `diff --name-only` is a bare path, spaces and all
        name = name.strip().split(" -> ")[-1].strip('"').rstrip("/")
        if not name or os.path.basename(name) == "CLAUDE.md":
            continue
        if name == ".friday" or name.startswith(".friday/"):
            continue
        names.append(name)
    return names


# --- mode: due (the D-0111 standing-care signals) ------------------------------------------

DEFAULT_DUE_DAYS = 30
_DUE_RE = re.compile(r"^(\d{1,4})d$")
_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def check_due(root: str, *, today: str | None = None) -> dict:
    """The two D-0111 due-signals, both scoped to a CLOSED project, both
    warn-tier, both at the session's natural start — no cron, no nagging.

    1. The handover that never happened: closed, and no `docs/handoff/README.md`
       (the contract's "start here" marker — a bare folder is not a package).
    2. The reconcile that is overdue: `last-verified:` aged past the project's
       own `reconcile-due: <N>d` line (optional, FRIDAY-STATE), default 30d.
       This leans on D-0141 on purpose: a clean reconcile re-dates the field
       even when nothing was dirty, so its age is an honest clock.

    Every "cannot tell" is silence EXCEPT a malformed threshold or an
    unparseable date — a project that thinks it set a policy deserves to hear
    the policy did not parse, and an unreadable clock must not read as fresh.
    A closed record with no `last-verified:` at all is K5's breach; staying
    quiet here avoids double-reporting it.
    """
    import datetime as _dt
    wroot = fs.resolve_worktree_root(root)
    current, block = _state_of(root)
    if current != "closed":
        return _result("valid-pass", "not a closed project — no standing care due")

    problems = []

    # Signal 1 — the terminal seam nothing ever used to name (NF10).
    if not os.path.isfile(os.path.join(wroot, "docs", "handoff", "README.md")):
        problems.append(
            "this project is closed but no handover package exists — nothing "
            "says the owner ever received one. /friday:handoff assembles it "
            "(docs/contracts/handoff-package.md)")

    # Signal 2 — the overdue reconcile. A malformed threshold is reported and
    # the age check SKIPPED: the project set a policy that did not parse, and
    # silently substituting the default would enforce a bar nobody chose.
    threshold, threshold_ok = DEFAULT_DUE_DAYS, True
    due_raw = (block.get("reconcile-due") or [""])[0]
    if due_raw:
        m = _DUE_RE.match(due_raw.strip())
        if m:
            threshold = int(m.group(1))
        else:
            threshold_ok = False
            problems.append(
                f"the record's own threshold line does not parse — "
                f"`reconcile-due: {due_raw}` (expected `<N>d`, e.g. 30d); "
                f"fix the line rather than trusting a default it did not set")
    # No `last-verified:` on a closed record is K5's breach — quiet here.
    last_raw = (block.get("last-verified") or [""])[0]
    if last_raw and threshold_ok:
        m = _DATE_RE.match(last_raw.strip())
        if not m:
            problems.append(
                f"`last-verified: {last_raw}` is not a readable date — an "
                f"unreadable clock must not pass for a fresh one")
        else:
            now = _dt.date.fromisoformat(today) if today else _dt.date.today()
            age = (now - _dt.date.fromisoformat(m.group(1))).days
            if age > threshold:
                problems.append(
                    f"the record was last re-verified {age} days ago — past "
                    f"this project's {threshold}-day bar. A clean "
                    f"/friday:reconcile re-dates it (D-0141)")

    if not problems:
        return _result("valid-pass", "standing care is current")
    return _result("valid-fail", "; and ".join(problems))


# --- CLI --------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Warn-tier state advisory: lane-start legality + the "
                    "PROP-028 dirty-bit backstop (D-0107/D-0106)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--mode", required=True,
                    choices=("lane-start", "liveness", "due"))
    ap.add_argument("--file", default="", help="lane-start: the write's target")
    ap.add_argument("--contract", default=None,
                    help="override the legality table's location (tests)")
    ap.add_argument("--today", default=None,
                    help="due: date override for the age arithmetic (tests)")
    args = ap.parse_args(argv)
    if args.mode == "due":
        res = check_due(args.root, today=args.today)
    elif args.mode == "liveness":
        res = check_liveness(args.root)
    else:
        proposed = sys.stdin.read() if not sys.stdin.isatty() else ""
        res = check_lane_start(args.root, args.file, proposed,
                               contract=args.contract)
    print(json.dumps(res))
    return 0  # always: an advisory never breaks the lane it advises


if __name__ == "__main__":
    raise SystemExit(main())
