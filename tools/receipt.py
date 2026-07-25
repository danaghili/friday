#!/usr/bin/env python3
"""Verify receipts — the host-independent enforcement backstop (PROP-041 kept).

Both hook systems fail OPEN at the runner layer and MCP is structurally
advisory, so the durable backstop is out-of-band evidence: every verifier run
leaves a receipt binding its verdict to a sha256 of the exact record surface
it judged (CLAUDE.md + docs/** — implementation code deliberately NOT hashed).
An out-of-band job re-runs the verifier fresh AND checks the receipt's
tree-hash matches the current tree; it trusts neither a chat claim nor any
single hook invocation. Receipts prove "a real run saw this exact tree and
said ok"; they are NOT tamper-proof — the independent re-run catches a forged
receipt because the verdict must also reproduce.

Layout: `<shared .friday>/receipts/<verifier>.json` (Appendix B: resolved via
the git common dir, so worktree runs land in the one shared substrate;
overwritten per run — history lives in CI logs; gitignored, so a receipt can
never be committed as stale evidence).

CLI:
  python3 tools/receipt.py write --root . --verifier state|claims|coverage|spawn-coverage
  python3 tools/receipt.py check --root . --verifier state [--max-age SECS] [--json]

Exit codes: write → verifier's own semantics; check → 0 backstop satisfied,
1 finding, 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402

SCHEMA = 1
VERIFIERS = ("state", "claims", "coverage", "spawn-coverage")


def tree_hash(root: str) -> str:
    """sha256 over the record surface: CLAUDE.md + docs/** (sorted relpaths;
    path AND content hashed, so a rename changes the hash)."""
    h = hashlib.sha256()
    paths: list[str] = []
    if os.path.isfile(os.path.join(root, "CLAUDE.md")):
        paths.append("CLAUDE.md")
    for dirpath, dirnames, filenames in os.walk(os.path.join(root, "docs")):
        dirnames.sort()
        for fn in sorted(filenames):
            paths.append(os.path.relpath(os.path.join(dirpath, fn), root))
    for rel in sorted(paths):
        h.update(rel.encode("utf-8", "replace") + b"\0")
        try:
            with open(os.path.join(root, rel), "rb") as fh:
                h.update(fh.read())
        except OSError:
            h.update(b"<unreadable>")
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def receipt_path(root: str, verifier: str) -> str:
    return os.path.join(fs.friday_dir(root), "receipts", f"{verifier}.json")


def leave_receipt(root: str, verifier: str, ok: bool, blocking: int) -> None:
    """Best-effort by contract: must never turn a working verifier run into a
    crash — the receipt is evidence, not a gate of its own."""
    try:
        now = time.time()
        payload = {"schema": SCHEMA, "verifier": verifier, "ts": now,
                   "iso": _dt.datetime.fromtimestamp(now, _dt.timezone.utc).isoformat(),
                   "tree_hash": tree_hash(fs.resolve_worktree_root(root)),
                   "ok": bool(ok), "blocking": int(blocking)}
        path = receipt_path(root, verifier)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        os.replace(tmp, path)
    except Exception:
        pass


def _run_verifier(root: str, verifier: str) -> tuple[bool, int]:
    """In-process run of the named sibling verifier — receipts and verdicts
    must come from the same code the plugin ships."""
    if verifier == "state":
        import verify_state
        res = verify_state.verify_state(root)
    elif verifier == "claims":
        import verify_claims
        res = verify_claims.check_all(fs.resolve_worktree_root(root))
    elif verifier == "coverage":
        import verify_coverage
        res = verify_coverage.check(fs.resolve_worktree_root(root))
    else:
        import verify_spawn_coverage
        res = verify_spawn_coverage.check_commands(
            os.path.join(fs.resolve_worktree_root(root), "commands"))
    blocking = sum(1 for f in res.get("failures", res.get("gaps", []))
                   if f.get("severity", "blocking") == "blocking")
    return bool(res["ok"]), blocking


def cmd_write(root: str, verifier: str) -> int:
    ok, blocking = _run_verifier(root, verifier)
    leave_receipt(root, verifier, ok, blocking)
    print(json.dumps({"ok": ok, "receipt": receipt_path(root, verifier)}))
    return 0 if ok else 1


def cmd_check(root: str, verifier: str, max_age: float | None, as_json: bool) -> int:
    findings: list[str] = []
    ok_now, blocking = _run_verifier(root, verifier)
    if not ok_now:
        findings.append(f"fresh {verifier} verify FAILS ({blocking} blocking)")
    path = receipt_path(root, verifier)
    receipt = None
    try:
        with open(path, encoding="utf-8") as fh:
            receipt = json.load(fh)
    except FileNotFoundError:
        findings.append(f"no receipt at {path} — the in-flow verify never ran "
                        "or its evidence was removed")
    except (OSError, ValueError):
        findings.append(f"receipt at {path} unreadable or malformed")
    if receipt is not None:
        if not receipt.get("ok"):
            findings.append("receipt records a FAILING run")
        if receipt.get("tree_hash") != tree_hash(fs.resolve_worktree_root(root)):
            findings.append("receipt tree_hash does not match the current tree — "
                            "the record surface changed after the last in-flow verify")
        if max_age is not None and time.time() - float(receipt.get("ts", 0)) > max_age:
            findings.append("receipt exceeds --max-age")
    ok = not findings
    if as_json:
        print(json.dumps({"ok": ok, "verifier": verifier, "findings": findings}))
    else:
        print(f"receipt check ({verifier}): "
              + ("backstop satisfied" if ok else "FAILED\n  - " + "\n  - ".join(findings)))
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="friday verify receipts")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("write", "check"):
        p = sub.add_parser(name)
        p.add_argument("--root", default=".")
        p.add_argument("--verifier", required=True, choices=VERIFIERS)
        if name == "check":
            p.add_argument("--max-age", type=float, default=None)
            p.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        print(f"receipt: no such directory: {args.root}", file=sys.stderr)
        return 2
    if args.cmd == "write":
        return cmd_write(args.root, args.verifier)
    return cmd_check(args.root, args.verifier, args.max_age, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
