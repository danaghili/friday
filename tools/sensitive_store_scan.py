#!/usr/bin/env python3
"""INC-108 OQ-108.3 / FR-108.13 — enumerate a project's declared stores.

The mechanical half of the deep clean's sensitivity catch-up: walk the
project tree for the store declarations its own schema artefacts carry,
so the stores that came through no door (a hand-added table, a column
nobody asked about) surface as candidates against docs/SENSITIVITY.md.
Exact matching only (the standing non-goal): the pgTable family, CREATE
TABLE, prisma models, __tablename__. Anything storage-shaped the scanner
cannot read or cannot parse is NAMED in the report — a store that could
not be examined is never a store with nothing to declare (S-108.2).

Value-blindness is structural (S-108.3, KH-6): data-store files (.sqlite,
.db, dumps) and dotenv files are never opened — the former are named as
unexamined storage, the latter skipped outright; everything read is
schema text, which carries names and shapes, never rows.

The scan enumerates; the model judges sensitivity against the floor
(docs/contracts/sensitivity-declaration.md); nothing here blocks (S-108.4).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Storage syntaxes this scanner actually reads, keyed by extension.
_TS_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
_PARSED_EXT = _TS_EXT | {".sql", ".prisma", ".py"}

_PGTABLE = re.compile(r"\b(?:pg|sqlite|mysql)Table\(\s*[\"']([A-Za-z0-9_]+)[\"']")
_CREATE = re.compile(
    r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"'`]?([A-Za-z0-9_.]+)[\"'`]?",
    re.IGNORECASE)
_PRISMA = re.compile(r"^\s*model\s+([A-Za-z0-9_]+)\s*\{", re.MULTILINE)
_TABLENAME = re.compile(r"__tablename__\s*=\s*[\"']([A-Za-z0-9_]+)[\"']")

# Directory names that say "storage lives here" — an unparseable file under
# one of these is a place stores could hide, so it is named, never skipped.
_STORAGE_DIRS = {"migrations", "migration", "schema", "schemas", "db",
                 "database", "models", "prisma", "drizzle", "alembic"}
# Data-store files: named as unexamined storage and NEVER opened (S-108.3).
_DATA_EXT = {".sqlite", ".sqlite3", ".db", ".dump", ".rdb"}
# Prose/config shapes that do not define stores — kept out of the noise.
_INERT_EXT = {".md", ".txt", ".lock", ".log"}

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
              "dist", "build", ".next", ".friday"}


def _extract(ext: str, text: str) -> list[str]:
    if ext in _TS_EXT:
        return _PGTABLE.findall(text)
    if ext == ".sql":
        return _CREATE.findall(text)
    if ext == ".prisma":
        return _PRISMA.findall(text)
    if ext == ".py":
        return _TABLENAME.findall(text)
    return []


def scan(root: str = ".") -> dict:
    root = os.path.abspath(root)
    stores: dict[str, dict] = {}
    unparsed: list[str] = []
    unread: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        in_storage_dir = bool(
            _STORAGE_DIRS & set(os.path.relpath(dirpath, root).split(os.sep)))
        for name in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, name), root)
            rel = rel.replace(os.sep, "/")
            ext = os.path.splitext(name)[1].lower()
            if name.startswith(".env"):
                continue
            if ext in _DATA_EXT:
                unparsed.append(rel)
                continue
            if ext not in _PARSED_EXT:
                if in_storage_dir and ext not in _INERT_EXT:
                    unparsed.append(rel)
                continue
            try:
                with open(os.path.join(dirpath, name), encoding="utf-8",
                          errors="replace") as fh:
                    text = fh.read()
            except OSError:
                unread.append(rel)
                continue
            for store in _extract(ext, text):
                stores.setdefault(store, {"store": store, "file": rel})
    _ir_models(root, stores, unread)
    return {"stores": [stores[k] for k in sorted(stores)],
            "unparsed_storage": sorted(unparsed),
            "unread": sorted(unread)}


_IR_REL = "docs/architecture/generated/architecture-ir.json"


def _ir_models(root: str, stores: dict, unread: list) -> None:
    """The extracted IR's data_models are the second candidate source —
    dataclass-shaped models no schema regex sees. Absent IR is a quiet
    no-op (the walk is primary; not every project ran /friday:reference);
    a corrupt one is named, never crashed on."""
    path = os.path.join(root, *_IR_REL.split("/"))
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as fh:
            ir = json.load(fh)
    except (OSError, ValueError):
        unread.append(_IR_REL)
        return
    for dm in ir.get("data_models", []):
        name = dm.get("name")
        if name:
            stores.setdefault(
                name, {"store": name, "file": dm.get("module", _IR_REL)})


def compare(root: str = ".") -> dict:
    """Enumerated vs declared — the catch-up's worklist, judged by the model.

    `undeclared` are candidates, not verdicts: whether one lands inside the
    floor is the reading pass's call. `declared_not_seen` is the read-back's
    assist: a declared store the tree no longer shows.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sensitivity_declaration as sd
    scanned = scan(root)
    declared = {e["store"] for e in sd.entries(root) if not e["malformed"]}
    seen = {s["store"] for s in scanned["stores"]}
    return {
        "undeclared": [s for s in scanned["stores"]
                       if s["store"] not in declared],
        "declared_not_seen": sorted(declared - seen),
        "unparsed_storage": scanned["unparsed_storage"],
        "unread": scanned["unread"],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("verb", nargs="?", choices=["scan", "compare"],
                    default="scan")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = scan(args.root) if args.verb == "scan" else compare(args.root)
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        for key, rows in out.items():
            for row in rows:
                print(f"{key}: {row if isinstance(row, str) else row['store'] + ' (' + row['file'] + ')'}")
    if args.verb == "compare" and (out["undeclared"] or out["declared_not_seen"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
