#!/usr/bin/env python3
"""INC-204 FR-204.3 — the secret-store posture checker, value-blind by construction.

Proves, over the real tree and WITHOUT opening a value file (KH-1, S-204.1):
  1. the project declares where its secret values live — a `secret-store:` typed
     line inside the `FRIDAY-SECRET-STORE` marker block in the project CLAUDE.md
     (FR-204.2; grammar: `tools/taglines.py`) — or carries a recorded
     accepted-risk decline with a reason;
  2. no value-carrying dotenv file is tracked by git (classification by FILENAME
     through `tools/secret_names.py`'s existing allowlist — the same structural
     guarantee FR-84 makes, extended, never weakened);
  3. the ignore rules cover the dotenv value class (`.env`, `.env.local`).

What it deliberately cannot do: verify the declaration is TRUE (friday cannot
see inside a store it must never touch) — it proves consistency between the
declaration and the tree, nothing more. The only file it opens is CLAUDE.md;
git answers everything else. There is no code path here that reads, holds,
returns or writes a secret value.

The stated limit (INC-204 D8, S-204.6): nothing in friday catches a SHORT
house literal — a four-digit alarm code, a PIN — that reaches a record; a
scan for one is indistinguishable from a scan for line numbers, and the
registry that could tell them apart was refused (D1). The control is at the
source (values live in the declared store, never in the tree), and the
remedy for one that has already leaked is ROTATION — cleaning the document
does not close a door it already described.

Verdict semantics (S-204.3): an absent declaration and a recorded decline are
different states. A decline with a reason passes, named in the summary, and
downgrades tracked-value-file findings to notes — FR-204.5's bite condition is
(tracked value files AND no accepted-risk record), and the bite itself lives in
the handoff keys gate, never here. This tool reports; consumers decide (D4).

Usage:
  python3 tools/secret_posture_check.py [--root .] [--json]

Exit codes: 0 valid-pass · 1 valid-fail · 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import secret_names  # noqa: E402
import taglines  # noqa: E402

BLOCK = "FRIDAY-SECRET-STORE"
_RISK_PREFIX = "accepted-risk"
# The dotenv value class whose ignore coverage is always checked — the one
# class the allowlist owns outright. Stack-specific value files are the
# don't-read rule's jurisdiction (FR-204.8), not this checker's.
_IGNORE_CLASS = (".env", ".env.local")


def parse_declaration(claude_md_text: str) -> dict | None:
    """The FR-204.2 grammar. Returns {"kind": "store", "store": …} |
    {"kind": "accepted-risk", "reason": …} | {"kind": "malformed", "line": …} |
    None. The defined empty case: no block, or a block with no `secret-store:`
    line, is None — never declared, distinct from declined (S-204.3)."""
    typed = taglines.block_typed(claude_md_text, BLOCK)
    if not typed or "secret-store" not in typed:
        return None
    value = typed["secret-store"][0].strip()
    if value.startswith(_RISK_PREFIX):
        reason = value[len(_RISK_PREFIX):].lstrip(" —–-").strip()
        if not reason:
            # a risk nobody gave a reason for was not accepted by anybody
            return {"kind": "malformed", "line": value}
        return {"kind": "accepted-risk", "reason": reason}
    if not value:
        return {"kind": "malformed", "line": value}
    return {"kind": "store", "store": value}


def _git_lines(root: str, *args: str) -> list[str] | None:
    """git output lines, or None when git itself is unavailable/not a repo —
    the caller reports that state instead of folding it into clean (S-203.1)."""
    try:
        proc = subprocess.run(["git", *args], cwd=root, capture_output=True,
                              text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 and args[0] == "ls-files":
        return None
    return proc.stdout.splitlines()


def _is_ignored(root: str, path: str) -> bool:
    try:
        proc = subprocess.run(["git", "check-ignore", "-q", "--", path],
                              cwd=root, capture_output=True, timeout=30)
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _scan_tree(root: str, accepted: bool,
               findings: list[dict], notes: list[dict]) -> None:
    """The git-facing half: tracked value files + ignore-class coverage.
    Under an accepted-risk record results land as notes, not findings
    (FR-204.5's bite condition encoded in the verdict semantics)."""
    tracked = _git_lines(root, "ls-files")
    if tracked is None:
        notes.append({"kind": "no-git",
                      "detail": "not a git repository — tracking and ignore "
                                "checks skipped, reported rather than passed"})
        return
    tracked_set = set(tracked)
    for path in sorted(tracked_set):
        if secret_names.is_value_env_file(os.path.basename(path)):
            item = {"kind": "tracked-value-file", "path": path,
                    "detail": f"value-carrying dotenv tracked by git: {path}"
                              " (reported by path, never by content)"}
            (notes if accepted else findings).append(item)
    for candidate in _IGNORE_CLASS:
        if candidate in tracked_set:
            continue  # already a tracked-value-file finding above
        if not _is_ignored(root, candidate):
            item = {"kind": "unignored-value-class", "path": candidate,
                    "detail": f"ignore rules do not cover {candidate} — a "
                              "future value file would land in git"}
            (notes if accepted else findings).append(item)


def check(*, root: str = ".") -> dict:
    """The typed verdict: {verdict, declaration, findings, notes, summary}."""
    root = os.path.abspath(root)
    findings: list[dict] = []
    notes: list[dict] = []

    claude_md = os.path.join(root, "CLAUDE.md")
    try:
        with open(claude_md, encoding="utf-8") as fh:
            declaration = parse_declaration(fh.read())
    except OSError:
        declaration = None

    if declaration is None:
        findings.append({
            "kind": "no-declaration",
            "detail": "no secret-store declaration and no accepted-risk record "
                      "in CLAUDE.md — where do this project's secret values "
                      "live? (FRIDAY-SECRET-STORE block, FR-204.2)"})
    elif declaration["kind"] == "malformed":
        findings.append({
            "kind": "malformed-declaration",
            "detail": "secret-store line is neither a store nor an "
                      "accepted-risk with a reason — a reasonless decline is "
                      "not an accepted risk (S-204.3)"})

    accepted = bool(declaration) and declaration["kind"] == "accepted-risk"
    _scan_tree(root, accepted, findings, notes)

    verdict = "valid-fail" if findings else "valid-pass"
    if declaration and declaration["kind"] == "store":
        head = f"store declared: {declaration['store']}"
    elif accepted:
        head = f"accepted-risk on record: {declaration['reason']}"
    else:
        head = "no secret-store declaration"
    summary = (f"secret posture {verdict}: {head} · {len(findings)} finding(s), "
               f"{len(notes)} note(s)")
    return {"verdict": verdict, "declaration": declaration,
            "findings": findings, "notes": notes, "summary": summary}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Secret-store posture checker — value-blind by construction "
                    "(INC-204 FR-204.3)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        print(f"secret_posture_check: no such dir: {args.root}", file=sys.stderr)
        return 2
    res = check(root=args.root)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(res["summary"])
        for f in res["findings"]:
            print(f"  finding: {f['detail']}")
        for n in res["notes"]:
            print(f"  note: {n['detail']}")
    return 0 if res["verdict"] == "valid-pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
