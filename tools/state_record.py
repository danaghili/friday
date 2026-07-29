#!/usr/bin/env python3
"""The PROP-028 dirty bit — the ONE writer of `record-status:` (D-0106).

A closed project's `FRIDAY-STATE` block carries two fields that together say
"this record was true, and here is when we last checked":

    last-verified: 2026-07-20
    record-status: verified | stale

`/friday:reconcile` has always cleared `stale` back to `verified`. Nothing ever
set it. So the promise — *closed never means frozen; any later change flips the
record stale* — was half a mechanism: reconcile faithfully cleared a flag that
could not arrive, and drift after close was invisible. Found twice independently,
ratified as D-0106, and this is the missing half.

**Both directions live here, deliberately.** The setter (feature / patch / bug,
when they land changes) and the clearer (reconcile, on a clean run) are one
file, so "what the bit means" cannot drift between the lane that raises it and
the lane that lowers it — the failure this house has now hit in the
maintainability gate's two authorities. The exclusivity is still real: only
reconcile is *instructed* to call `--mark verified`.

**It edits one line.** Not "reads the block and rebuilds it" — `format_block`
would reorder fields and rewrite a record that the closer's K5 gate, the
foundation gate and the build-epoch resolver all read. The unit of change here
is a single line, and the tests assert the rest of the file is byte-identical.

**Not applicable is the common case.** `record-status:` exists only on a CLOSED
record. Every lane will call this on every run, most of them mid-build or against
a project with no state block at all, so "nothing to do" is an ordinary quiet
outcome that exits 0 — never an error, and never a lazily-created field.

Contract: `docs/contracts/state-record.md`. Exit codes: 0 done or not applicable
· 1 asked to flip a bit that is not there · 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402
import taglines  # noqa: E402

BLOCK = "FRIDAY-STATE"
FIELD = "record-status"
STAMP = "last-verified"
STATUSES = ("verified", "stale")


def _result(ok: bool, changed: bool, detail: str) -> dict:
    return {"ok": ok, "changed": changed, "detail": detail}


def _claude_path(root: str) -> str:
    return os.path.join(fs.resolve_worktree_root(root), "CLAUDE.md")


def _set_field(text: str, field: str, value: str) -> str:
    """Replace one typed line inside the block, leaving every other byte alone."""
    out, inside = [], False
    for line in text.split("\n"):
        if f"{BLOCK}:BEGIN" in line:
            inside = True
        elif f"{BLOCK}:END" in line:
            inside = False
        if inside:
            parsed = taglines.parse_typed_line(line)
            if parsed and parsed[0] == field:
                line = f"{field}: {value}"
        out.append(line)
    return "\n".join(out)


def _apply(root: str, want: str, *, stamp: str | None) -> dict:
    """Move the bit to `want`, or explain why there is nothing to move."""
    path = _claude_path(root)
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return _result(True, False, f"no CLAUDE.md at {path} — nothing to mark")

    block = taglines.block_typed(text, BLOCK)
    if not block:
        return _result(True, False, "no FRIDAY-STATE block — not a friday project record")
    state = (block.get("state") or [""])[0]
    if state != "closed":
        # The bit describes a record that was declared finished. Mid-build the
        # whole project is in motion, so there is nothing meaningful to dirty.
        return _result(True, False,
                       f"state is {state!r}, not 'closed' — the dirty bit only "
                       f"exists on a closed record")
    current = (block.get(FIELD) or [""])[0]
    if not current:
        # verify_state's K5 blocks a close without this field, so a closed record
        # missing it is already broken. Adding one here would backdate a claim
        # nobody made and hide the breach.
        return _result(False, False,
                       f"closed record has no `{FIELD}:` line to flip — that is a "
                       f"K5 breach in its own right (docs/contracts/state-record.md)")
    if current == want and not (stamp and want == "verified"):
        return _result(True, False, f"{FIELD} is already {want!r}")

    updated = _set_field(text, FIELD, want)
    if stamp and want == "verified":
        # Clearing the bit re-dates the record: it is being asserted true NOW.
        # Marking it stale must never touch this, or the gap reconcile exists to
        # notice is erased in the act of recording it.
        #
        # This replaces the whole line, so the closer's `(close)` annotation is
        # dropped — deliberately. After a reconcile the stamp is a reconcile,
        # not a close, and keeping the note would misdescribe its own origin.
        # K5 requires the field present, not annotated, so the record stays
        # verifiable across the rewrite.
        updated = _set_field(updated, STAMP, stamp)
    if updated == text:
        return _result(True, False, f"{FIELD} is already {want!r}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(updated)
    if want == "verified":
        _stamp_commit(root)
    if current == want:
        # D-0141: a clean reconcile over an already-verified record re-dates it.
        # Reporting that as "verified -> verified" reads like a bug; say what
        # actually moved.
        return _result(True, True,
                       f"re-dated {STAMP}: {stamp} ({FIELD} was already {want!r})")
    return _result(True, True, f"{FIELD}: {current} -> {want}")


def _stamp_commit(root: str) -> None:
    """Record WHERE the code was when the record was verified.

    The companion to the clear, and the thing the warn-tier backstop compares
    against later (`tools/state_advisory_check.py`, D-0107): without it that
    guard knows the record claims `verified` but not what it was verified
    AGAINST, so it could never tell a moved tree from a still one.

    It lives in the shared `.friday/` substrate rather than in the record
    itself, deliberately — the FRIDAY-STATE block is read by the closer's K5
    gate, the foundation gate and the epoch resolver, and adding a field to it
    would be a contract change for every one of them. Best-effort by design:
    no git, no repo, or an unwritable substrate simply leaves no stamp, and an
    absent stamp makes the backstop go quiet rather than guess. Marking stale
    never touches it — the backstop must keep knowing where `verified` was.
    """
    try:
        proc = subprocess.run(["git", "-C", fs.resolve_worktree_root(root),
                               "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            return
        # friday_dir() only names the path; on a project whose substrate has
        # never been written this is the first thing in it.
        substrate = fs.friday_dir(root)
        os.makedirs(substrate, exist_ok=True)
        with open(os.path.join(substrate, "state-verified.stamp"),
                  "w", encoding="utf-8") as fh:
            fh.write(proc.stdout.strip() + "\n")
    except (OSError, subprocess.SubprocessError):
        return  # never let a missing stamp break the clear itself


def mark_stale(root: str = ".") -> dict:
    """Called by a lane that LANDED CHANGES on a closed project (D-0106).

    Never touches `last-verified:` — that field records when the record was last
    confirmed true, and the distance between it and now is the signal.
    """
    return _apply(root, "stale", stamp=None)


def mark_verified(root: str = ".", *, when: str | None = None) -> dict:
    """Reconcile's exclusive clear, on a clean run only."""
    return _apply(root, "verified",
                  stamp=when or datetime.date.today().isoformat())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Set or clear the PROP-028 record-status dirty bit (D-0106)")
    ap.add_argument("--mark", required=True, choices=STATUSES,
                    help="stale: a lane landed changes · verified: reconcile's clear")
    ap.add_argument("--root", default=".")
    ap.add_argument("--when", default=None,
                    help="date for last-verified: on a clear (default: today)")
    args = ap.parse_args(argv)
    res = (mark_stale(args.root) if args.mark == "stale"
           else mark_verified(args.root, when=args.when))
    print(json.dumps(res))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
