#!/usr/bin/env python3
"""INC-008 layer-3 enforcement hook (FR-8.5 / AC-8.1/8.5 / KH-5 / S-8.4).

The close-time maintainability backstop, built from the guard skeleton (Pin #1 —
it reuses `_guard.run_checker` / `decide` / `block_message` / `emit_block` /
`emit_warn`, adding NO new enforcement mechanism). A global friday Stop gate:
cheap no-op everywhere except a friday project that has DECLARED maintainability
bars (~one stat elsewhere). When bars are declared, it runs the deterministic
disposition-completeness checker over the real tree and:

  - blocks ONLY on an un-dispositioned breach, and ONLY when the project has
    ARMED the block (`arm: block`); warn-first (disarmed) SURFACES the same thing
    without blocking;
  - FAILS OPEN on every checker fault (missing / crash / timeout / invalid
    verdict → no-verdict → allow) — a false block trains the PM to disable the
    gate, worse than a miss (KH-5);
  - emits STRANGER-PROOF blocks (what / why / fix / override).

The non-adopter invariant (FR-8.13): a project with no declared bars never reaches
the checker — zero new behavior. Always exits 0; a block rides the JSON decision.
Pure stdlib.

The cheap self-gate (task #7): the full checker is an AST parse plus a
whole-tree duplication scan, and it used to run on EVERY Stop for an adopting
project — mostly to conclude, again, that nothing changed. The gate now keeps a
stamp of the last CLEAN scan (`<shared .friday>/maintainability-scan.stamp`):
the tree's .py file count and the newest mtime across those files, the
standards file and the judge's envelope. A Stop whose signature matches the
stamp skips the scan outright — stat calls only, no file reads, no subprocess.
Three asymmetries carry the safety:

  - only a CLEAN verdict writes the stamp — a standing breach is re-evaluated
    at every Stop, because the envelope can change between them;
  - the standards and the envelope are part of the signature — a tightened bar
    or a withdrawn disposition creates a breach on an UNCHANGED tree;
  - the stamp names its worktree root — `.friday/` is shared across worktrees,
    and worktree A's clean scan must not silence worktree B's different tree.

Known residual, accepted: replacing a file via `mv` with one carrying an OLDER
mtime and the same tree count defeats the signature until the next real edit.
The stamp is a cache, never an authority — corrupt or missing means scan.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402


def _block_reason(summary: str, *, checker: str, standards: str, root: str) -> str:
    """The stranger-proof four-part block text (AC-15).

    The override part earns its length: it names the file the checker actually
    reads. It used to name only the deviations ledger, which the checker never
    consults — so a reader who followed the instruction exactly stayed blocked
    with nowhere to go. A block whose stated escape hatch does not work is worse
    than no block, because the next message is not believed either (BUG-005's
    shape). Pinned by test_the_block_names_an_override_that_actually_clears_it.
    """
    return _guard.block_message(
        what="this session is concluding with un-dispositioned maintainability breaches",
        why=("friday measured code-health breaches that are neither recorded as a "
             "justified deviation nor fixed-and-re-measured-clean:\n" + summary),
        fix=("run the maintainability judge at harden/close to disposition each breach "
             "(justify-and-record or fix-and-re-measure), then re-check:\n"
             f'  python3 "{checker}" --root . --standards '
             f'{os.path.relpath(standards, root)} --envelope .friday/maintainability-envelope.md'),
        override=("this gate reads the judge's envelope at "
                  ".friday/maintainability-envelope.md — a breach clears when "
                  "that file carries a matching finding marked `justified`, and "
                  "again if the code later measures WORSE than the number that "
                  "was judged. Recording the justification durably in "
                  "docs/STANDARDS-DEVIATIONS.md (tools/standards_deviations.py) "
                  "is part of dispositioning it, but the ledger alone does not "
                  "clear the gate. To step back to warn-first, set `arm: warn` "
                  "in the coding-standards maintainability block."))


_STAMP_NAME = "maintainability-scan.stamp"

# The signature's own walk skips only the universal heavy-derived dirs — a
# strict SUBSET of the measurer's exclusion set, so the signature always sees
# a SUPERSET of the measured files. Drift between the two sets can then only
# invalidate the stamp and cost an extra scan, never silence a real change.
# (Local because the hook layer shells out to the logic core and never
# imports it — the 2026-08-05 reconcile's layering conviction, D-1084.)
_SIG_SKIP = {".git", ".friday", "node_modules", "__pycache__", ".venv", "venv"}


def _tree_signature(root: str, standards: str, envelope: str) -> tuple[int, float]:
    """(py-file count, newest mtime across py files + standards + envelope).
    Stat-only — the whole point is that this costs nothing next to the scan:
    no file reads, no subprocess, so the stamp fast path stays free."""
    latest, count = 0.0, 0
    for dirpath, dirnames, filenames in os.walk(os.path.abspath(root)):
        dirnames[:] = [d for d in dirnames if d not in _SIG_SKIP]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            try:
                latest = max(latest, os.stat(os.path.join(dirpath, fn)).st_mtime)
                count += 1
            except OSError:
                continue
    for path in (standards, envelope):
        try:
            latest = max(latest, os.stat(path).st_mtime)
        except OSError:
            continue  # an absent envelope is a valid state, not a signal
    return count, latest


def _stamp_path(fs, root: str) -> str:
    return os.path.join(fs.friday_dir(root), _STAMP_NAME)


def _stamp_matches(fs, root: str, sig: tuple[int, float]) -> bool:
    """True only when the last CLEAN scan saw exactly this tree. Any doubt —
    absent, unreadable, another worktree's root, drifted numbers — means scan."""
    try:
        with open(_stamp_path(fs, root), encoding="utf-8") as fh:
            stamp = json.load(fh)
        return (stamp.get("root") == root
                and stamp.get("count") == sig[0]
                and stamp.get("max_mtime") == sig[1])
    except (OSError, ValueError):
        return False


def _write_stamp(fs, root: str, sig: tuple[int, float]) -> None:
    """Record the clean scan. Best-effort: an unwritable substrate just means
    the next Stop scans again — the cache must never break the gate."""
    try:
        os.makedirs(fs.friday_dir(root), exist_ok=True)
        with open(_stamp_path(fs, root), "w", encoding="utf-8") as fh:
            json.dump({"root": root, "count": sig[0], "max_mtime": sig[1]}, fh)
    except OSError:
        pass


def _standards_or_none(root: str) -> str | None:
    """The adopter fast gate: the standards path when the project carries a
    FRIDAY-MAINTAINABILITY block, else None (a non-adopter owes zero behavior
    and never spawns the checker). Marker-presence only — the bar GRAMMAR
    lives in the logic core and comes back in the checker's own verdict
    (arm / bars_declared / malformed_bars / fatal), because this hook shells
    out and never imports it (D-1084)."""
    standards = os.path.join(root, "docs", "standards", "coding-standards.md")
    if not os.path.isfile(standards):
        return None  # no coding-standards file — a non-adopter; zero new behavior
    try:
        with open(standards, encoding="utf-8") as fh:
            if "<!-- FRIDAY-MAINTAINABILITY:BEGIN -->" not in fh.read():
                return None  # no block — non-adopter invariant
    except OSError:
        return None
    return standards


def _verdict_meta(verdict: dict) -> tuple[str | None, str, str]:
    """(fatal, malformed-note, arm) from the checker's verdict JSON — the bar
    meta the logic core computed so this hook never parses bars itself
    (D-1085)."""
    malformed = verdict.get("malformed_bars") or []
    note = ""
    if malformed:
        note = ("\nMALFORMED bar line(s) NOT being enforced (fix the typo in "
                "docs/standards/coding-standards.md):\n  "
                + "\n  ".join(malformed))
    return verdict.get("fatal"), note, verdict.get("arm", "warn")


def _emit(action, *, summary: str, checker: str, standards: str, root: str) -> bool:
    """Print the decided outcome. True when something was emitted (so the
    caller knows a clean pass earned the skip-stamp instead)."""
    if action.kind == "block":
        print(json.dumps(_guard.emit_block(
            "Stop", _block_reason(summary, checker=checker, standards=standards,
                                  root=root))))
    elif action.kind == "warn":
        print(json.dumps(_guard.emit_warn(
            "Maintainability (warn-first — not blocking): " + summary
            + "\nDisposition these at harden/close; arm the hard block with "
              "`arm: block` in the coding-standards maintainability block once you "
              "trust the numbers.")))
    elif action.detail:
        print(f"maintainability_gate: failing open — {action.detail}", file=sys.stderr)
    else:
        return False
    return True


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)  # also puts tools/ on sys.path
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        if not fs.should_engage(cwd):
            return 0
        # A session may start in a project subdirectory — anchor every path on
        # the worktree root, like every sibling Stop gate (raw cwd silently
        # no-ops the whole capability from a subdir).
        root = fs.resolve_worktree_root(cwd)
        standards = _standards_or_none(root)
        if standards is None:
            return 0

        # The cheap self-gate: signature taken BEFORE the scan, so an edit that
        # lands mid-scan raises the mtime past what gets stamped and the next
        # Stop re-scans — the race resolves toward scanning, never skipping.
        # An all-malformed block never earns a stamp, so its warn re-fires
        # every Stop exactly as it did when the hook parsed bars itself.
        # One path authority (D-0148): the substrate names where the envelope
        # lives; the judge writes there through the checker's --write mode.
        # Hand-joining here is how producer and consumer silently split.
        envelope = fs.envelope_path(root)
        sig = _tree_signature(root, standards, envelope)
        if _stamp_matches(fs, root, sig):
            return 0  # last scan was clean and nothing relevant has moved since

        checker = os.path.join(plugin_root, "tools", "maintainability_gate_check.py")
        if not os.path.isfile(checker):
            return 0  # fail-open: no checker, no block
        argv = [sys.executable, checker, "--root", root, "--standards", standards]
        if os.path.isfile(envelope):
            argv += ["--envelope", envelope]

        timeout_s = float(os.environ.get("FRIDAY_GUARD_TIMEOUT_S", "60"))
        verdict = _guard.run_checker(argv, timeout_s=timeout_s)
        fatal, note, arm = _verdict_meta(verdict)
        if fatal:
            print(json.dumps(_guard.emit_warn(fatal)))
            return 0
        action = _guard.decide(verdict, "block" if arm == "block" else "warn",
                               reason="")
        summary = (verdict.get("summary", "maintainability breaches are un-dispositioned")
                   + note)

        emitted = _emit(action, summary=summary, checker=checker,
                        standards=standards, root=root)
        if not emitted and verdict.get("verdict") == "valid-pass" \
                and not note:
            # Clean, and every declared bar parsed — the only outcome that
            # earns the skip-cache. A malformed bar keeps the scan live so a
            # future fix to the surfacing logic is never suppressed by a stamp.
            _write_stamp(fs, root, sig)
    except Exception as exc:  # never let the gate stall a session
        print(f"maintainability_gate: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
