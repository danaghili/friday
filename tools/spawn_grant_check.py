#!/usr/bin/env python3
"""The spawn-grant checker — a role's declared tool list must actually bind.

**The measured fact** (`docs/research/probe-teammate-tool-grants.md`, Claude
Code v2.1.220): passing a `name` when spawning a role overwrites the recorded
`agentType` with that name. The role's definition can then no longer be
resolved, and the spawn code falls through to its no-definition branch:

    tools: i?.tools ? Co([...i.tools, /* team tools */]) : ["*"]

`["*"]` is every tool in the session. Measured on friday's own security
reviewer, whose file declares `Read, Grep, Glob` plus three docs tools: named,
it came up holding all eight direct tools plus ~300 MCP tools — the user's
mail, chat, files, calendar, home automation and a browser — and ran a shell
command. Un-named, the identical file delivered exactly its six declared tools,
MCP scoping included.

So the same role file is a real sandbox on one spawn path and pure decoration
on the other, and nothing in friday's source records which path a lane takes.
That is this house's recurring failure class — a promise that reads as enforced
and is not — and asking the lead to remember is not a mechanism.

**The rule.** A role opts in by carrying one typed, greppable

    grant-binding: <reason>

line, meaning "my declared tool grant is load-bearing; spawn me unnamed or it
evaporates". Every live surface that dispatches such a role must carry

    spawn-unnamed: <role-name>

The trigger is the role file's own declaration, never a mention — the same
existence-triggered choice `dispatch_liveness_check.py` makes, for the same
measured reason. A bare `grant-binding:` with no reason is refused rather than
passed, so the opt-in cannot become a silent loosening.

**What this deliberately cannot see** (stated rather than glossed, the KH-4
discipline): it proves the un-named instruction is *present* on every
dispatching surface. It cannot read intent, so it cannot catch a surface that
carries the marker and then tells the lead to pass a name anyway. Guarding the
presence of the instruction is the half that mechanises; the other half stays
prose. Roles dispatched nowhere are `dispatch_liveness_check.py`'s defect, not
this one's — two checkers must never claim the same fault, or fixing it
silences one and not the other.

**Hard failure by design (exit 1).** This checks friday's OWN source, in
friday's own suite and ship gate — a sibling of the dispatch-liveness checker
and the spec-ID strip gate, never a hook gating a PM's project. The warn-first
/ fail-open doctrine governs the latter and does not apply here (S-200.5).

Usage:
  python3 tools/spawn_grant_check.py [--root .] [--json]

Exit codes: 0 clean · 1 unguarded dispatch or bare declaration · 2 bad
invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Same roster and surface trees as the dispatch-liveness sibling: archived and
# historical material is a record, not a promise.
ROLE_DIRS = ("agents",)
SURFACE_DIRS = ("skills", "commands", "agents", "hooks", "tools", "docs/contracts")
SURFACE_EXTS = (".md", ".py")

_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
_BINDING_RE = re.compile(r"^grant-binding:\s*(.*?)\s*$", re.MULTILINE)


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


def binding_roles(root: str) -> tuple[dict[str, str], list[str]]:
    """Roles that declare their grant load-bearing.

    Returns ({role-name: file path}, [roles whose declaration carried no
    reason]). A bare line is reported, never silently honoured.
    """
    declared: dict[str, str] = {}
    bare: list[str] = []
    for path in _walk(root, ROLE_DIRS, (".md",)):
        text = _read(path)
        nm = _NAME_RE.search(text)
        bd = _BINDING_RE.search(text)
        if not (nm and bd):
            continue
        if not bd.group(1).strip():
            bare.append(nm.group(1))
            continue
        declared[nm.group(1)] = path
    return declared, sorted(bare)


def _dispatches(text: str, role: str) -> bool:
    """True when some line names BOTH the role and a model — a real spawn.

    Same same-line rule as `verify_spawn_coverage.py` and the liveness sibling:
    prose that merely mentions a role must not read as a dispatch, because that
    prose IS the defect those checkers exist to catch.
    """
    return any(role in line and "model:" in line for line in text.splitlines())


def _marked(text: str, role: str) -> bool:
    """True when the surface carries the typed un-named marker for THIS role.

    Matched per-line and anchored, so a marker naming a sibling role cannot
    launder a different role's dispatch through.
    """
    want = re.compile(rf"^\s*spawn-unnamed:\s*{re.escape(role)}\s*$")
    return any(want.match(line) for line in text.splitlines())


def check(*, root: str = ".") -> dict:
    """Return the typed verdict {verdict, unguarded, bare_declarations, ...}."""
    root = os.path.abspath(root)
    declared, bare = binding_roles(root)
    surfaces = _walk(root, SURFACE_DIRS, SURFACE_EXTS)
    texts = {p: _read(p) for p in surfaces}

    unguarded: list[str] = []
    for role, role_path in sorted(declared.items()):
        for path, text in sorted(texts.items()):
            # A role's own file states its `grant-binding:` reason; that reason
            # must never satisfy the rule for itself, so the file is excluded
            # from its own search exactly as the liveness sibling does.
            if path == role_path:
                continue
            if _dispatches(text, role) and not _marked(text, role):
                unguarded.append(f"{role} @ {os.path.relpath(path, root)}")

    if unguarded or bare:
        bits = []
        if unguarded:
            bits.append(
                f"{len(unguarded)} dispatch(es) of a grant-binding role with no "
                "un-named marker — add a `spawn-unnamed: <role>` line to each "
                "surface, and make its spawn instruction pass no agent name")
        if bare:
            bits.append(f"{len(bare)} bare `grant-binding:` line(s) with no reason: "
                        + ", ".join(bare))
        return {"verdict": "valid-fail", "unguarded": unguarded,
                "bare_declarations": bare, "roles_checked": len(declared),
                "summary": " · ".join(bits)}

    return {"verdict": "valid-pass", "unguarded": [], "bare_declarations": [],
            "roles_checked": len(declared),
            "summary": (f"spawn grants OK: {len(declared)} grant-binding role(s), "
                        "every dispatch carries its un-named marker")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Spawn-grant checker — a declared tool list must bind")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        print(f"spawn_grant_check: no such dir: {args.root}", file=sys.stderr)
        return 2
    res = check(root=args.root)
    if args.json:
        print(json.dumps(res))
    else:
        print(res["summary"])
        for u in res["unguarded"]:
            print(f"  unguarded dispatch: {u}")
        for b in res["bare_declarations"]:
            print(f"  bare grant-binding: {b}")
    return 0 if res["verdict"] == "valid-pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
