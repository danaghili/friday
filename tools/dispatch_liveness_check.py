#!/usr/bin/env python3
"""INC-200 FR-200.1/2/3 — the dispatch-liveness + contract-path checker.

The pattern-level cure for the class three audits kept finding: a role named
on paper by prose that routes to it, with nothing anywhere that actually
spawns it. Five roles were orphaned that way (closer, architect, operations,
experiment-runner, running-cost) and no lint caught any of them.

**It triggers on the role FILE EXISTING, never on the role being mentioned**
(D2, PM-ratified). That distinction is load-bearing and was measured: fourteen
of fifteen roles are named on some live surface and `friday-architect` in
none — so a mention-triggered rule gives a clean pass to the single most
orphaned role in the roster. Existence-triggered is simpler and strictly
catches more.

A role passes by one of exactly two routes:

1. **Dispatched** — some live surface carries a spawn naming BOTH the agent
   and its `model:` on the same line (`(`friday-tester`, model: sonnet)`).
   Same-line is deliberate precision-first house style, the same choice
   `verify_spawn_coverage.py` makes: prose that merely mentions a role must
   not read as a dispatch, because that prose IS the defect.
2. **Declared exception** — the role file carries one typed, greppable
   `dispatch-exception: <reason>` line saying no lane dispatches it and why.
   The exception stays visible and greppable rather than becoming a silent
   loosening of the rule; a bare line with no reason is refused.

It also asserts (FR-200.3) that every `docs/contracts/<name>.md` path
mentioned on a live surface resolves to a real file — a pure existence check,
no prose parsing. That kills a class which has already bitten:
`compaction-package.md` claimed a seam handoff had "its own contract" when no
such file had ever existed (D-0117). Typed both-sides enforcement needs a
sides-declaration grammar across all twelve contracts first and is deferred by
name (INC-200 §9b OQ-200.4).

**Hard failure by design (exit 1).** This checks friday's OWN source, in
friday's own suite and ship gate — a sibling of the spec-ID strip gate and the
skill-standard floor, never a hook gating a PM's project. The warn-first /
fail-open doctrine governs the latter and does not apply here (S-200.5: no
project gains a new block from this increment).

Usage:
  python3 tools/dispatch_liveness_check.py [--root .] [--json]

Exit codes: 0 clean · 1 orphan role or phantom contract · 2 bad invocation.
Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Where the roster lives, and which trees count as "live surfaces". Archived
# and historical material is deliberately out of scope: a pre-rebuild doc
# describing a deleted role is a record, not a promise.
ROLE_DIRS = ("agents",)
SURFACE_DIRS = ("skills", "commands", "agents", "hooks", "tools", "docs/contracts")
SURFACE_EXTS = (".md", ".py")

_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
_EXCEPTION_RE = re.compile(r"^dispatch-exception:\s*(.+?)\s*$", re.MULTILINE)
_CONTRACT_RE = re.compile(r"docs/contracts/([A-Za-z0-9._-]+\.md)")


def _walk(root: str, rel_dirs, exts) -> list[str]:
    out: list[str] = []
    for rel in rel_dirs:
        base = os.path.join(root, rel)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames
                           if d not in (".git", "archive", "__pycache__")]
            for fn in filenames:
                if fn.endswith(exts):
                    out.append(os.path.join(dirpath, fn))
    return sorted(set(out))


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ""


def roster(root: str) -> dict[str, str]:
    """Every declared role: {role-name: its file path}. The closed, countable
    list the rule triggers on."""
    found: dict[str, str] = {}
    for path in _walk(root, ROLE_DIRS, (".md",)):
        m = _NAME_RE.search(_read(path))
        if m:
            found[m.group(1)] = path
    return found


def _dispatch_sites(text: str, role: str) -> bool:
    """True when some line names BOTH the role and a model — a real spawn."""
    for line in text.splitlines():
        if role in line and "model:" in line:
            return True
    return False


def check(*, root: str = ".") -> dict:
    """Return the typed verdict {verdict, orphans, missing_contracts, ...}."""
    root = os.path.abspath(root)
    roles = roster(root)
    surfaces = _walk(root, SURFACE_DIRS, SURFACE_EXTS)
    texts = {p: _read(p) for p in surfaces}

    orphans: list[str] = []
    excepted: list[str] = []
    for role, role_path in sorted(roles.items()):
        own = _read(role_path)
        m = _EXCEPTION_RE.search(own)
        if m and m.group(1).strip():
            excepted.append(role)
            continue
        # A role's own file carries `name:` + `model:` in its frontmatter; it
        # can never dispatch itself, so it is excluded from its own search.
        if any(_dispatch_sites(t, role)
               for p, t in texts.items() if p != role_path):
            continue
        orphans.append(role)

    missing: list[str] = []
    for path, text in texts.items():
        for name in set(_CONTRACT_RE.findall(text)):
            if not os.path.isfile(os.path.join(root, "docs", "contracts", name)):
                missing.append(f"docs/contracts/{name} (cited in "
                               f"{os.path.relpath(path, root)})")
    missing = sorted(set(missing))

    if orphans or missing:
        bits = []
        if orphans:
            bits.append(f"{len(orphans)} role(s) declared but never dispatched: "
                        + ", ".join(orphans)
                        + " — give each a real spawn (naming the agent AND its "
                          "model:) or a `dispatch-exception: <reason>` line")
        if missing:
            bits.append(f"{len(missing)} contract path(s) cited but absent: "
                        + "; ".join(missing))
        return {"verdict": "valid-fail", "orphans": orphans,
                "missing_contracts": missing, "roles_checked": len(roles),
                "excepted": excepted, "summary": " · ".join(bits)}

    return {"verdict": "valid-pass", "orphans": [], "missing_contracts": [],
            "roles_checked": len(roles), "excepted": excepted,
            "summary": (f"dispatch liveness OK: {len(roles)} role(s) checked, "
                        f"{len(excepted)} declared exception(s), every cited "
                        "contract path resolves")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Dispatch-liveness + contract-path "
                                             "checker (INC-200 FR-200.1/2/3)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        print(f"dispatch_liveness_check: no such dir: {args.root}", file=sys.stderr)
        return 2
    res = check(root=args.root)
    if args.json:
        print(json.dumps(res))
    else:
        print(res["summary"])
        for role in res["orphans"]:
            print(f"  orphan role: {role}")
        for m in res["missing_contracts"]:
            print(f"  phantom contract: {m}")
    return 0 if res["verdict"] == "valid-pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
