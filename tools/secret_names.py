#!/usr/bin/env python3
"""Secret-NAME enumerator — friday's structural guarantee that it never handles a
secret VALUE (FR-84; D-0056/D-0057).

The boundary (Dan's security rule): an agent must be *incapable* of touching a
secret value, not merely careful. So this tool reads only sources that carry
NAMES — the application's own declarations — and by construction never opens a
value file:
  - dotenv EXAMPLE files only (.env.example / .env.sample / .env.template /
    .env.dist / env.example …) — a name is parsed from `KEY=`; the placeholder
    to the right is discarded, never returned;
  - source references (os.environ[...] / os.environ.get(...) / os.getenv(...) /
    process.env.X / process.env['X']).
A real `.env` / `.env.local` / `.env.<env>` holds live values and is NEVER
opened — the allowlist of example basenames is the guarantee, not a scan.

There is no code path here that reads or returns a value. Output is a name list
with the source locations that declared each. Pure stdlib.

Exit codes: 0 ok · 2 bad invocation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# dotenv example basenames we MAY read NAMES from (right-hand side is a placeholder).
_EXAMPLE_ENV = frozenset({
    ".env.example", ".env.sample", ".env.template", ".env.dist", ".env.defaults",
    "env.example", "env.sample", "env.template",
})

# directories never worth scanning (vendored / generated / runtime).
_SKIP_DIRS = frozenset({
    ".git", "node_modules", ".friday", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", ".mypy_cache", ".pytest_cache",
    "coverage", ".idea", ".vscode", "vendor", "target",
})

_SRC_EXT = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs", ".go", ".rb", ".rs",
    ".java", ".kt", ".php", ".sh",
})

# `KEY=` (optionally `export KEY=`). The value is deliberately NOT captured.
_DOTENV_KEY = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")

# os.environ["X"] · os.environ.get("X") · os.getenv("X")
_PY_ENV = re.compile(
    r"os\.environ\s*\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"
    r"|os\.environ\s*\.\s*get\s*\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"
    r"|os\.getenv\s*\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")

# process.env.X · process.env["X"] · process.env['X']
_JS_ENV = re.compile(
    r"process\.env\.([A-Za-z_][A-Za-z0-9_]*)"
    r"|process\.env\s*\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\]")


def is_example_env_file(basename: str) -> bool:
    """A dotenv EXAMPLE file — safe to read NAMES from (values are placeholders)."""
    return basename in _EXAMPLE_ENV


def is_value_env_file(basename: str) -> bool:
    """A dotenv file that may hold real VALUES — NEVER opened by this tool."""
    if basename in _EXAMPLE_ENV:
        return False
    return basename == ".env" or basename.startswith(".env.")


def _scan_dotenv(full: str, rel: str, acc: dict) -> None:
    try:
        with open(full, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                m = _DOTENV_KEY.match(line)
                if m:
                    acc.setdefault(m.group(1), set()).add(rel)
    except OSError:
        pass


def _scan_source(full: str, rel: str, acc: dict) -> None:
    try:
        with open(full, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return
    for rx in (_PY_ENV, _JS_ENV):
        for m in rx.finditer(text):
            name = next(g for g in m.groups() if g)
            acc.setdefault(name, set()).add(rel)


def enumerate_names(root: str) -> list[dict]:
    """Required secret NAMES declared under `root`, each with its source files.
    Reads only example dotenv files and source references; value files are
    skipped by allowlist, never opened. [] when nothing is declared."""
    root = os.path.abspath(root)
    acc: dict[str, set] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if is_example_env_file(fn):
                _scan_dotenv(full, rel, acc)
            elif is_value_env_file(fn):
                continue  # the structural guarantee: a value file is NEVER read
            elif os.path.splitext(fn)[1] in _SRC_EXT:
                _scan_source(full, rel, acc)
    return [{"name": n, "sources": sorted(acc[n])} for n in sorted(acc)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="List required secret NAMES (never values) from app declarations")
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"secret_names: --root is not a directory: {root}", file=sys.stderr)
        return 2

    names = enumerate_names(root)
    if args.json:
        print(json.dumps(names, indent=2))
    else:
        if not names:
            print("(no declared secret names found)")
        for e in names:
            print(f"{e['name']}  —  {', '.join(e['sources'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
