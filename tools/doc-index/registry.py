#!/usr/bin/env python3
"""friday-docs registry — the ADVISORY sync-on-query SQLite index.

Vehicle kept from v0.4.0, cargo rewritten: the indexed surface is the
arc42/DECISIONS substrate (documents + decision entries + open [ACTION] tag
lines), not the retired feature tree.

Binding architecture facts:
- ADVISORY: content-bearing retrieval (the reader triad) NEVER reads this
  index — it live-parses. The index only powers cross-document aggregates
  (resolve/status), and gate decisions re-check files.
- Sync-on-query: `ensure_fresh()` runs at the top of EVERY tools/call —
  stat-compare mtime/size, hash only changed files, re-parse dirty only, one
  transaction. The index can never be more than one query-cycle stale, and if
  it is wrong the reader triad is unaffected.
- Location: `<shared .friday>/index.db` via friday_substrate (Appendix B —
  worktree sessions share one index). Gitignored, derived, regenerable.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE)))  # tools/
import decisions as declib  # noqa: E402
import friday_substrate as fs  # noqa: E402
import taglines  # noqa: E402

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents (
  path TEXT PRIMARY KEY, mtime_ns INTEGER, size INTEGER, content_hash TEXT);
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY, id_str TEXT, title TEXT, whenz TEXT, channel TEXT,
  weight TEXT, floor TEXT, back_filled INTEGER, src_path TEXT);
CREATE TABLE IF NOT EXISTS actions (
  path TEXT, line INTEGER, tag TEXT, descr TEXT, source TEXT, role TEXT,
  datez TEXT, PRIMARY KEY (path, line));
"""


def project_root() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def db_path(root: str) -> str:
    return os.path.join(fs.friday_dir(root), "index.db")


def connect(root: str) -> sqlite3.Connection:
    path = db_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        conn = sqlite3.connect(path)
    except sqlite3.OperationalError:
        conn = sqlite3.connect(":memory:")  # degraded but functional (advisory)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _tracked_docs(root: str) -> list[str]:
    wroot = fs.resolve_worktree_root(root)
    out = []
    claude = os.path.join(wroot, "CLAUDE.md")
    if os.path.isfile(claude):
        out.append(claude)
    for dirpath, dirnames, filenames in os.walk(os.path.join(wroot, "docs")):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        out += [os.path.join(dirpath, f) for f in sorted(filenames) if f.endswith(".md")]
    return out


def _reindex_doc(conn: sqlite3.Connection, root: str, path: str, raw: bytes) -> None:
    wroot = fs.resolve_worktree_root(root)
    rel = os.path.relpath(path, wroot)
    text = raw.decode("utf-8", errors="replace")
    conn.execute("DELETE FROM actions WHERE path = ?", (rel,))
    for note in taglines.scan_notes(text):
        conn.execute(
            "INSERT OR REPLACE INTO actions VALUES (?,?,?,?,?,?,?)",
            (rel, note["line"], note["tag"], note["desc"], note["source"],
             note["role"], note["date"]))
    if rel.replace(os.sep, "/") in ("docs/DECISIONS.md",) or rel.startswith(
            os.path.join("docs", "decisions")):
        conn.execute("DELETE FROM decisions WHERE src_path = ?", (rel,))
        parsed = declib.parse(text)
        for e in parsed["entries"]:
            conn.execute(
                "INSERT OR REPLACE INTO decisions VALUES (?,?,?,?,?,?,?,?,?)",
                (e["id"], e["id_str"], e["title"], e.get("when", ""),
                 e.get("channel", ""), e.get("weight", ""), e.get("floor", ""),
                 int(e["back_filled"]), rel))


def ensure_fresh(conn: sqlite3.Connection, root: str) -> dict:
    """Stat-compare, hash-on-change, re-parse dirty only, one transaction."""
    resynced: list[str] = []
    wroot = fs.resolve_worktree_root(root)
    seen: set[str] = set()
    with conn:
        for path in _tracked_docs(root):
            rel = os.path.relpath(path, wroot)
            seen.add(rel)
            try:
                st = os.stat(path)
            except OSError:
                continue
            row = conn.execute("SELECT mtime_ns, size, content_hash FROM documents "
                               "WHERE path = ?", (rel,)).fetchone()
            if row and row["mtime_ns"] == st.st_mtime_ns and row["size"] == st.st_size:
                continue
            try:
                with open(path, "rb") as fh:
                    raw = fh.read()
            except OSError:
                continue
            digest = hashlib.sha256(raw).hexdigest()
            if row and row["content_hash"] == digest:
                conn.execute("UPDATE documents SET mtime_ns=?, size=? WHERE path=?",
                             (st.st_mtime_ns, st.st_size, rel))
                continue
            conn.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?,?)",
                         (rel, st.st_mtime_ns, st.st_size, digest))
            _reindex_doc(conn, root, path, raw)
            resynced.append(rel)
        for row in conn.execute("SELECT path FROM documents").fetchall():
            if row["path"] not in seen:
                conn.execute("DELETE FROM documents WHERE path=?", (row["path"],))
                conn.execute("DELETE FROM actions WHERE path=?", (row["path"],))
    return {"resynced": resynced, "stale_possible": False}


# --- lead-only aggregates ---------------------------------------------------------

def resolve(conn: sqlite3.Connection, root: str, query: str) -> dict:
    """D-NNNN or ADR id → the indexed entry + related files. Advisory."""
    q = query.strip()
    if q.upper().startswith("D-"):
        row = conn.execute("SELECT * FROM decisions WHERE id_str = ?",
                           (q.upper(),)).fetchone()
        if not row:
            return {"ok": False, "error": "unknown_id", "id": q,
                    "hint": "no such D-NNNN in docs/DECISIONS.md or its archives"}
        wroot = fs.resolve_worktree_root(root)
        adrs = []
        adr_dir = os.path.join(wroot, "docs", "architecture", "decisions")
        if os.path.isdir(adr_dir):
            for name in sorted(os.listdir(adr_dir)):
                try:
                    with open(os.path.join(adr_dir, name), encoding="utf-8") as fh:
                        if q.upper() in fh.read():
                            adrs.append(f"docs/architecture/decisions/{name}")
                except OSError:
                    pass
        return {"ok": True, "match_count": 1,
                "decision": {k: row[k] for k in row.keys()}, "related_adrs": adrs,
                "cite": f"{row['src_path']} § {row['id_str']}"}
    return {"ok": False, "error": "unknown_id_shape", "id": q,
            "hint": "resolve takes a D-NNNN decision id"}


def status(conn: sqlite3.Connection, root: str, scope: str) -> dict:
    if scope == "actions":
        rows = conn.execute("SELECT * FROM actions WHERE tag = 'ACTION' "
                            "ORDER BY path, line").fetchall()
        return {"ok": True, "scope": "actions",
                "open_actions": [dict(r) for r in rows], "count": len(rows)}
    # default scope: decisions + state roll-up
    rows = conn.execute("SELECT * FROM decisions ORDER BY id").fetchall()
    by_channel: dict[str, int] = {}
    floors: dict[str, int] = {}
    for r in rows:
        by_channel[r["channel"]] = by_channel.get(r["channel"], 0) + 1
        if r["floor"] and r["floor"] != "none":
            floors[r["floor"]] = floors.get(r["floor"], 0) + 1
    asks_dir = os.path.join(fs.friday_dir(root), "asks")
    try:
        parked = len([n for n in os.listdir(asks_dir) if n.endswith("-request.md")])
    except OSError:
        parked = 0
    state = None
    try:
        with open(os.path.join(fs.resolve_worktree_root(root), "CLAUDE.md"),
                  encoding="utf-8") as fh:
            block = taglines.block_typed(fh.read(), "FRIDAY-STATE")
        state = (block or {}).get("state", [None])[0]
    except OSError:
        pass
    return {"ok": True, "scope": "decisions", "state": state,
            "decision_count": len(rows), "by_channel": by_channel,
            "floor_touches": floors, "parked_asks": parked,
            "latest": [dict(rows[i]) for i in range(max(0, len(rows) - 5), len(rows))]}
