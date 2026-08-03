#!/usr/bin/env python3
"""The compaction guardrail: report what a project has, and insert what it lacks.

Contract: `docs/contracts/claude-scaffold.md` § The compaction guardrail and
§ Never-clobber. That contract is the SINGLE HOME of the two settings' values —
this tool reads them out of it and carries no copy of its own, so editing the
doctrine changes what gets written and the doctrine stays load-bearing rather than
decorative (INC-209 FR-209.1, D1).

Two jobs, deliberately in one module because they share one reader:

  --check   report-only. Names which of three states a project is in, including the
            half-configured one that looks fine and is documented to do nothing.
            Reads two named keys and reports nothing else about the file. Never
            blocks, never fails, never gates — exit 0 in every state including a
            project with no settings file at all (INC-209 FR-209.7, S-209.1,
            S-209.3, KH-2).

  --apply   the narrow, consented exception to never-clobber. Adds THIS PAIR and
            nothing else into a settings file friday has already handed over, only
            with --consented, never altering a value already present for either
            setting and never touching any other content (INC-209 FR-209.4, D2).

Why the insertion is surgical rather than a JSON round-trip. Re-dumping the file
would produce correct parsed values and destroy the PM's formatting, key order and
comments — in a file the PM rarely opens, so the damage would be found late or
never. So the write is a targeted text insertion, and every write is gated behind a
self-check that refuses anything which rewrote, reordered or reformatted an
existing line (INC-209 KH-1). A refusal leaves the file untouched.

The personal `settings.local.json` is never read and never written, on this path as
on every other (INC-209 S-209.2).
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CONTRACT = os.path.join(_HERE, os.pardir, "docs", "contracts", "claude-scaffold.md")

# The doctrine states each value as: `KEY` = `"VALUE"`. Matching the backticked
# form rather than any bare occurrence keeps prose mentions of a key from being
# mistaken for its definition.
_VALUE_RE = re.compile(r"`(CLAUDE_[A-Z0-9_]+)`\s*=\s*`\"([^\"]+)\"`")

# The in-file explanation. Names no value — they are on the next lines — and says
# who owns the block from here on (INC-209 FR-209.3).
_COMMENT = (
    "Seeded by friday (docs/contracts/claude-scaffold.md - INC-209): the compaction "
    "guardrail. The env pair below moves this project's automatic context tidy-up "
    "early, so session-continuity work has room to run instead of firing when the "
    "context is already nearly full. It assumes a large-window model, and it is a "
    "shared project default - override it in your own settings.local.json, or delete "
    "it here. This file is the project's from the moment it was written: friday never "
    "re-applies a seed you removed."
)


class DoctrineUnreadable(RuntimeError):
    """The contract that owns the values could not be read or parsed.

    Raised rather than defaulted on purpose: a guessed value written into a file
    friday does not own is exactly the harm this module exists to prevent.
    """


def doctrine_values(contract_path=None):
    """The two settings and their values, read from the doctrine that owns them.

    Returns an ordered mapping of key -> value string. Raises DoctrineUnreadable if
    the contract is missing or no longer states both values in the expected form —
    the caller decides what to do, and for --apply the answer is always "refuse".
    """
    path = contract_path or _DEFAULT_CONTRACT
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise DoctrineUnreadable(f"cannot read {path}: {exc}") from exc
    found = dict(_VALUE_RE.findall(text))
    missing = {"CLAUDE_CODE_AUTO_COMPACT_WINDOW", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"} - set(found)
    if missing:
        raise DoctrineUnreadable(
            f"{path} no longer states a value for: {', '.join(sorted(missing))}"
        )
    # Fixed order so reports and insertions are deterministic.
    return {
        "CLAUDE_CODE_AUTO_COMPACT_WINDOW": found["CLAUDE_CODE_AUTO_COMPACT_WINDOW"],
        "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": found["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"],
    }


def settings_path(root):
    """The committed project settings file. Never `settings.local.json` (S-209.2)."""
    return os.path.join(root, ".claude", "settings.json")


def _read(root):
    """(raw_text, parsed) for the project's settings, or (None, None) / (text, None)."""
    path = settings_path(root)
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None, None
    try:
        return text, json.loads(text)
    except (ValueError, UnicodeDecodeError):
        return text, None


# --------------------------------------------------------------------------
# --check : report only, never blocks
# --------------------------------------------------------------------------

def check(root, contract_path=None):
    """Report which of the states a project is in. Never raises, never blocks.

    States: `both`, `half-configured`, `neither`, `no-settings-file`,
    `unreadable-settings`, `doctrine-unreadable`. The half-configured state is named
    distinctly because it is the one that reads as healthy at a glance and is
    documented to do nothing (KH-2).

    Only the two key NAMES ever appear in the result — no other key, value, or
    allowance from the file is copied out (S-209.3).
    """
    report = {"root": root, "state": None, "present": [], "missing": [], "blocking": False}
    try:
        keys = list(doctrine_values(contract_path))
    except DoctrineUnreadable as exc:
        report["state"] = "doctrine-unreadable"
        report["detail"] = str(exc)
        return report

    text, parsed = _read(root)
    if text is None:
        report["state"] = "no-settings-file"
        report["missing"] = keys
        return report
    if parsed is None:
        report["state"] = "unreadable-settings"
        report["missing"] = keys
        return report

    env = parsed.get("env") or {}
    if not isinstance(env, dict):
        env = {}
    report["present"] = [k for k in keys if k in env]
    report["missing"] = [k for k in keys if k not in env]
    if not report["missing"]:
        report["state"] = "both"
    elif report["present"]:
        report["state"] = "half-configured"
    else:
        report["state"] = "neither"
    return report


# --------------------------------------------------------------------------
# --apply : the narrow consented exception
# --------------------------------------------------------------------------

_EMPTY_ENV_RE = re.compile(r'^\s*"env"\s*:\s*\{\s*\}\s*,?\s*$')


def _indent_of(text):
    """The file's own indent step, copied rather than imposed."""
    for line in text.splitlines():
        stripped = line.lstrip(" ")
        if stripped and stripped != line and stripped.startswith('"'):
            return " " * (len(line) - len(stripped))
    return "  "


def _insert_keys(text, additions, indent):
    """Insert `additions` at the START of the env block, touching nothing else.

    Inserting at the start rather than the end is what keeps the write surgical: a
    new entry followed by existing ones needs only its own trailing comma, so no
    pre-existing line has to gain or lose one.

    Three shapes are handled: an existing multi-line env block, an existing empty
    `"env": {}` (the one line this function may rewrite, since it holds none of the
    PM's content), and no env block at all.
    """
    lines = text.splitlines(keepends=True)

    # Shape 2: an empty env block on one line — expand it, then fall through.
    for i, line in enumerate(lines):
        if _EMPTY_ENV_RE.match(line):
            pad = line[: len(line) - len(line.lstrip(" "))]
            trailing = "," if line.rstrip().endswith(",") else ""
            body = "".join(
                f'{pad}{indent}"{k}": "{v}",\n' for k, v in additions.items()
            )
            body = body.rstrip(",\n") + "\n"
            lines[i] = f'{pad}"env": {{\n{body}{pad}}}{trailing}\n'
            return "".join(lines)

    # Shape 1: an existing multi-line env block — insert directly after its opener.
    for i, line in enumerate(lines):
        if re.match(r'^\s*"env"\s*:\s*\{\s*$', line):
            pad = line[: len(line) - len(line.lstrip(" "))]
            block = "".join(
                f'{pad}{indent}"{k}": "{v}",\n' for k, v in additions.items()
            )
            lines.insert(i + 1, block)
            return "".join(lines)

    # Shape 3: no env block — open one immediately after the root brace.
    for i, line in enumerate(lines):
        if line.strip() == "{":
            pad = line[: len(line) - len(line.lstrip(" "))]
            body = "".join(
                f'{pad}{indent}{indent}"{k}": "{v}",\n' for k, v in additions.items()
            )
            body = body.rstrip(",\n") + "\n"
            lines.insert(i + 1, f'{pad}{indent}"env": {{\n{body}{pad}{indent}}},\n')
            return "".join(lines)

    raise ValueError("could not locate an insertion point")


def _insert_comment(text, indent):
    """Place the explanatory key as the first entry of the root object."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip() == "{":
            pad = line[: len(line) - len(line.lstrip(" "))]
            encoded = json.dumps(_COMMENT)
            lines.insert(i + 1, f'{pad}{indent}"$comment": {encoded},\n')
            return "".join(lines)
    raise ValueError("could not locate the root object")


def _surviving(old_text, new_text):
    """True when every old line still appears, in order, in the new text.

    This is the whole KH-1 guarantee expressed as one predicate: a rewrite that
    reformats, reorders or re-indents anything breaks the subsequence and the write
    is refused. The single exemption is an empty `"env": {}` line, which holds none
    of the PM's content and must be expanded to hold the pair.
    """
    new_iter = iter(new_text.splitlines())
    for line in old_text.splitlines():
        if _EMPTY_ENV_RE.match(line):
            continue
        if line not in new_iter:
            return False
    return True


def _values_preserved(old_parsed, new_parsed, additions, comment_added):
    """Every pre-existing key keeps its exact value; only the additions are new."""
    if not isinstance(new_parsed, dict):
        return False
    for key, value in old_parsed.items():
        if key == "env":
            continue
        if new_parsed.get(key) != value:
            return False
    old_env = old_parsed.get("env") or {}
    new_env = new_parsed.get("env") or {}
    for key, value in old_env.items():
        if new_env.get(key) != value:
            return False
    if set(new_env) - set(old_env) != set(additions):
        return False
    extra_root = set(new_parsed) - set(old_parsed)
    allowed = {"env"} | ({"$comment"} if comment_added else set())
    return not (extra_root - allowed)


_REFUSALS = {
    "no-consent": "no explicit PM yes was given, so the file was not opened for writing "
                  "(docs/contracts/claude-scaffold.md § Never-clobber)",
    "no-settings-file": "this project has no committed settings file, so there is nothing "
                        "to reach into — a greenfield scaffold writes it fresh and needs "
                        "no exception",
    "unparseable": "the settings file is not valid JSON — friday does not repair a file "
                   "it does not own",
    "already-present": "both settings are already present; their values are the project's",
    "unsafe-rewrite": "the proposed write would have altered content beyond the inserted "
                      "setting; refused and the file left exactly as it was (KH-1)",
}


def _refuse(result, reason, detail=None):
    """Every refusal path in one shape: name the reason, explain, change nothing."""
    result["reason"] = reason
    result["notes"].append(detail or _REFUSALS.get(reason, reason))
    return result


def _plan(root, contract_path, result):
    """Read the project and work out what is missing. Returns (text, parsed, additions).

    Returns None when there is nothing to do or nothing safe to do, having already
    recorded the reason on `result`. Splitting this out keeps `apply` a readable
    sequence of authority → plan → compose → verify → write.
    """
    try:
        values = doctrine_values(contract_path)
    except DoctrineUnreadable as exc:
        _refuse(result, "doctrine-unreadable", f"{exc} — refusing to write a value friday guessed")
        return None

    text, parsed = _read(root)
    if text is None:
        _refuse(result, "no-settings-file")
        return None
    if parsed is None:
        _refuse(result, "unparseable")
        return None

    env = parsed.get("env") or {}
    if not isinstance(env, dict):
        env = {}
    additions = {k: v for k, v in values.items() if k not in env}
    if not additions:
        _refuse(result, "already-present")
        return None
    return text, parsed, additions


def _compose(text, parsed, additions, result):
    """Build the proposed file text. Returns (new_text, comment_added) or None.

    Nothing is written here — the caller verifies the proposal first.
    """
    indent = _indent_of(text)
    try:
        new_text = _insert_keys(text, additions, indent)
    except (ValueError, TypeError) as exc:
        _refuse(result, "unsafe-rewrite", f"insertion could not be made safely: {exc}")
        return None

    # FR-209.3 / OQ-209.3 — the explanation rides along only when there is nothing
    # of the PM's to displace. An existing $comment is never rewritten.
    if "$comment" in parsed:
        result["notes"].append(
            "this file already carries its own $comment, which friday never rewrites — "
            "the seeded block's explanation was reported here rather than forced in"
        )
        return new_text, False
    try:
        return _insert_comment(new_text, indent), True
    except ValueError:
        result["notes"].append("could not place the explanatory $comment; left absent")
        return new_text, False


def _verified(text, parsed, new_text, additions, comment_added, result):
    """The KH-1 gate: a proposal is only allowed through if it changed nothing else."""
    try:
        new_parsed = json.loads(new_text)
    except ValueError as exc:
        _refuse(result, "unsafe-rewrite", f"the proposed file did not parse ({exc}); nothing written")
        return False
    if not _surviving(text, new_text) or not _values_preserved(
        parsed, new_parsed, additions, comment_added
    ):
        _refuse(result, "unsafe-rewrite")
        return False
    return True


def apply(root, consented=False, contract_path=None, greenfield=False):
    """Add the missing half of the pair.

    Two authorities, and never a default. `consented=True` is the narrow exception
    to never-clobber: an existing file friday has already handed over, opened only
    after an explicit PM yes. `greenfield=True` is the ordinary write at
    `/friday:init`, where friday is writing the file at that very moment and no
    exception is involved at all — the distinction the doctrine draws in
    § The retrofit doors, kept as two separate flags so neither can stand in for
    the other by accident.

    Returns a result dict; `applied` is False for every refusal and the file is
    left byte-identical in every one of them. Reasons: `no-consent`,
    `no-settings-file`, `unparseable`, `already-present`, `doctrine-unreadable`,
    `unsafe-rewrite`, `write-failed`.
    """
    result = {
        "root": root, "applied": False, "reason": None, "added": [],
        "comment_placed": False, "notes": [],
    }

    if not (consented or greenfield):
        return _refuse(result, "no-consent")

    planned = _plan(root, contract_path, result)
    if planned is None:
        return result
    text, parsed, additions = planned

    composed = _compose(text, parsed, additions, result)
    if composed is None:
        return result
    new_text, comment_added = composed

    if not _verified(text, parsed, new_text, additions, comment_added, result):
        return result

    try:
        with open(settings_path(root), "w", encoding="utf-8") as fh:
            fh.write(new_text)
    except OSError as exc:
        return _refuse(result, "write-failed", str(exc))

    result["applied"] = True
    result["added"] = list(additions)
    result["comment_placed"] = comment_added
    return result


# --------------------------------------------------------------------------
# The recorded decline (INC-209 FR-209.6, D7)
# --------------------------------------------------------------------------

# The marker the next door greps for. A typed tag line rather than a sentence,
# because a reworded entry must never silently stop being findable — that would
# restart exactly the re-asking this exists to end.
DECLINE_TAG = "compaction-seed: declined"

_DECISIONS_WRITER = os.path.join(_HERE, "decisions_append.py")


def decisions_record_path(root):
    """Where a project's decision record lives. Created by the writer when absent."""
    return os.path.join(root, "docs", "DECISIONS.md")


def decline_recorded(root):
    """True when this project has already told friday no.

    Reads the project's own decision record and looks for the tag line. A project
    with no record has not declined — absence of a record is not a decline.
    """
    path = decisions_record_path(root)
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            return any(line.strip() == DECLINE_TAG for line in fh)
    except OSError:
        return False


def record_decline(root, reason, writer=None):
    """Write the PM's no into the project's own decision record.

    Goes through the existing decisions writer rather than opening the file
    directly — the writer owns id allocation, the lock, and the journal event, and
    it creates the record when a project has none yet (OQ-209.4: adopt can meet a
    project mid-reconstruction, and the answer still has to be durable).

    The PM's reason is carried as given. A paraphrase would leave the record unable
    to answer, months later, why this project does not carry the guardrail.
    """
    import subprocess  # local: the pure-read paths above must not pay for this

    cmd = [
        sys.executable, writer or _DECISIONS_WRITER,
        "--root", root,
        "--title", "The compaction guardrail was offered and declined",
        "--decision",
        "friday offered to add the compaction guardrail to this project's committed "
        "settings and the PM declined. Every later retrofit door reads this entry and "
        "stays quiet, so the question is not asked again (friday INC-209 FR-209.6). "
        "Re-offering is a matter of deleting this entry or asking friday directly.\n"
        + DECLINE_TAG,
        "--why", reason,
        "--rejected",
        "Seeding it anyway (the settings file is the project's property and a no is a "
        "decision, not a gap); asking again at the next door (an offer that returns "
        "after a decline teaches the PM to click past friday's questions).",
        "--channel", "pm-ratified", "--weight", "two-way", "--floor", "none",
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return {"ok": False, "error": (proc.stderr or proc.stdout).strip()}


def should_offer(root, contract_path=None):
    """The door-facing verb: may this surface offer the seed, and why not.

    Returns (offer, reason). The reason is the check's state name, or `declined`
    when the project's record already carries a no. Reading the record comes FIRST:
    a declined project is never even inspected for what it is missing.
    """
    if decline_recorded(root):
        return False, "declined"
    state = check(root, contract_path)["state"]
    return state in ("half-configured", "neither", "no-settings-file"), state


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

_STATE_PROSE = {
    "both": "carries the compaction guardrail",
    "half-configured": (
        "carries only one of the two settings — this looks configured and is "
        "documented to do nothing on the sessions friday runs"
    ),
    "neither": "does not carry the compaction guardrail",
    "no-settings-file": "has no committed settings file",
    "unreadable-settings": "has a settings file friday could not parse",
    "doctrine-unreadable": "could not be judged — the doctrine that owns the values is unreadable",
}


def _build_parser():
    """The CLI surface. Split from main so each mode stays a short, readable branch."""
    parser = argparse.ArgumentParser(
        description="Report or seed the compaction guardrail (INC-209; contract: "
                    "docs/contracts/claude-scaffold.md)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report only; never blocks")
    mode.add_argument("--apply", action="store_true", help="insert the missing setting")
    mode.add_argument(
        "--should-offer", action="store_true",
        help="what a retrofit door should do here: offer, or stay quiet and why",
    )
    mode.add_argument(
        "--decline", action="store_true",
        help="record the PM's no in the project's decision record (needs --reason)",
    )
    parser.add_argument(
        "--greenfield", action="store_true",
        help="the init write path: friday is writing this file now, so no exception applies",
    )
    parser.add_argument("--root", default=".", help="the target project root")
    parser.add_argument(
        "--consented", action="store_true",
        help="the PM gave an explicit yes at the door that offered it (required by --apply)",
    )
    parser.add_argument("--reason", default=None, help="the PM's reason, as given (--decline)")
    parser.add_argument("--contract", default=None, help="override the doctrine path")
    parser.add_argument("--json", action="store_true")
    return parser


def _cmd_check(args):
    report = check(args.root, args.contract)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{args.root}: {_STATE_PROSE.get(report['state'], report['state'])}")
        if report["missing"] and report["state"] != "both":
            print(f"  missing: {', '.join(report['missing'])}")
    return 0  # report-only: exit 0 in every state (S-209.1)


def _cmd_should_offer(args):
    offer, why = should_offer(args.root, args.contract)
    if args.json:
        print(json.dumps({"root": args.root, "offer": offer, "reason": why}, indent=2))
    elif offer:
        print(f"{args.root}: offer the compaction guardrail ({why})")
    else:
        print(f"{args.root}: say nothing ({why})")
    return 0  # advisory, like the check it reads (S-209.1)


def _cmd_decline(args, parser):
    if not args.reason:
        parser.error("--decline needs --reason: the PM's own words are the record")
    result = record_decline(args.root, args.reason)
    if args.json:
        print(json.dumps(result, indent=2))
    elif result.get("ok"):
        print(f"recorded {result.get('id')} in {result.get('path')}")
    else:
        print(f"could not record the decline: {result.get('error')}")
    return 0 if result.get("ok") else 1


def _cmd_apply(args):
    result = apply(args.root, consented=args.consented, contract_path=args.contract,
                   greenfield=args.greenfield)
    if args.json:
        print(json.dumps(result, indent=2))
    elif result["applied"]:
        print(f"{args.root}: added {', '.join(result['added'])}")
    else:
        print(f"{args.root}: not applied ({result['reason']})")
    if not args.json:
        for note in result["notes"]:
            print(f"  {note}")
    return 0


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.check:
        return _cmd_check(args)
    if args.should_offer:
        return _cmd_should_offer(args)
    if args.decline:
        return _cmd_decline(args, parser)
    return _cmd_apply(args)


if __name__ == "__main__":
    sys.exit(main())
