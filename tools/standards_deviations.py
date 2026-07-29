#!/usr/bin/env python3
"""INC-008 FR-8.6 — the standards-deviation ledger writer + schema.

The governance spine: a JUSTIFIED maintainability breach becomes a durable,
accountable record here instead of silent erosion — the local "penalty for
eroding maintainability" the ecosystem lacks. A SIBLING of the decision log
(docs/DECISIONS.md): the same proven machinery — a single writer under an
advisory `fcntl` lock, monotonic SD-NNNN ids from a shared-substrate counter,
two capture channels, growing-log cap + archive-on-overflow, and a byte-exact
tested empty form — but its OWN schema and file, so a trickle of small breaches
never buries the load-bearing design decisions (D4). This is the ONLY home for a
*measured* breach; a *taste* departure goes to an ADR (KH-7 — two clean homes).

It reuses `friday_substrate` (the shared lock / worktree-root / time primitives)
and deliberately does NOT touch `tools/decisions.py` (out of blast radius, D10).
Reuse note: the ledger mechanics here and in decisions.py could converge on a
shared core in a later increment — logged to the reuse register, not refactored
now (the "note, don't change" refactor stance).

Serialization (contract: docs/contracts/standards-deviation.md):

    ## SD-0001 — <metric> <measured> > <bar> @ <location>
    **When:** <ISO-8601Z> · **Channel:** pm-ratified|model-autonomous · **Floor:** none|<cat>
    - **Justification:** ...
    - **Standard:** ...

Two channels (D4): `pm-ratified` (the PM ratified the deviation) and
`model-autonomous` (the judge recorded it; the autonomous ones are cross-checked
at reconcile). Pure stdlib.
"""
from __future__ import annotations

import argparse
import fcntl
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402

EMPTY_SENTINEL = "_No standards deviations recorded yet._"
CHANNELS = ("pm-ratified", "model-autonomous")
FLOORS = ("none", "auth-security", "schema-data")
DEFAULT_PATH = os.path.join("docs", "STANDARDS-DEVIATIONS.md")
DEFAULT_CAP = 100

_H1_RE = re.compile(r"^# Standards Deviations\b")
_ENTRY_RE = re.compile(r"^## (SD-(\d{4,})) — (.+?)\s*$")
_TITLE_RE = re.compile(r"^([a-z-]+)\s+(\d+%?)\s+>\s+(\d+%?)\s+@\s+(.+)$")
_META_KEY_RE = re.compile(r"\*\*([A-Za-z-]+):\*\*\s*(.+?)\s*$")
_BULLET_RE = re.compile(r"^- \*\*(Justification|Standard):\*\*\s*(.*)$")

_MARKER_COMMENT = (
    "<!-- FRIDAY-STANDARDS-DEVIATIONS v1 — append via tools/standards_deviations.py (never\n"
    "     hand-edit past entries). Schema contract: docs/contracts/standards-deviation.md.\n"
    "     Growing-log discipline: entry cap {cap}; overflow MOVES the oldest half to\n"
    "     docs/deviations/archive-NNN.md — completion is a move, not a flag. -->")


# --- serializer -----------------------------------------------------------------

def empty_form(project: str = "friday project", cap: int = DEFAULT_CAP) -> str:
    """The zero-deviation serialization — exact, tested, produced on --init."""
    return (f"# Standards Deviations — {project}\n\n"
            f"{_MARKER_COMMENT.format(cap=cap)}\n\n"
            f"{EMPTY_SENTINEL}\n")


def format_entry(*, id_num: int, metric: str, measured: str, bar: str, location: str,
                 justification: str, standard: str, when: str, channel: str,
                 floor: str) -> str:
    title = f"{metric} {measured} > {bar} @ {location}"
    return (f"## SD-{id_num:04d} — {title}\n"
            f"**When:** {when} · **Channel:** {channel} · **Floor:** {floor}\n"
            f"- **Justification:** {justification}\n"
            f"- **Standard:** {standard}\n")


def validate_fields(channel: str, floor: str) -> list[str]:
    """Closed vocabularies. Returns [] when valid, else human-readable errors."""
    errs: list[str] = []
    if channel not in CHANNELS:
        errs.append(f"channel must be one of {'|'.join(CHANNELS)}, got {channel!r}")
    if floor not in FLOORS:
        errs.append(f"floor must be one of {'|'.join(FLOORS)}, got {floor!r}")
    return errs


# --- parser --------------------------------------------------------------------

def parse(text: str) -> dict:
    """{ok, empty, entries[], errors[]}. Precision-first: unknown prose between
    entries is tolerated; structural violations of the pinned grammar are not."""
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or not _H1_RE.match(lines[0]):
        return {"ok": False, "empty": False, "entries": [],
                "errors": ["missing pinned H1 '# Standards Deviations …' on line 1"]}

    has_sentinel = any(ln.strip() == EMPTY_SENTINEL for ln in lines)
    entries: list[dict] = []
    current: dict | None = None

    def close(entry: dict | None) -> None:
        if entry is None:
            return
        tm = _TITLE_RE.match(entry.get("title", ""))
        if tm:
            entry["metric"], entry["measured"], entry["bar"], entry["location"] = tm.groups()
        else:
            errors.append(f"{entry['id_str']}: title does not parse as "
                          "`<metric> <measured> > <bar> @ <location>`")
        for field in ("when", "channel", "floor"):
            if field not in entry:
                errors.append(f"{entry['id_str']}: missing **{field.capitalize()}:** on the meta line")
        for field in ("justification", "standard"):
            if field not in entry:
                errors.append(f"{entry['id_str']}: missing - **{field.capitalize()}:** bullet")
        errors.extend(f"{entry['id_str']}: {e}" for e in validate_fields(
            entry.get("channel", ""), entry.get("floor", "none")))
        entries.append(entry)

    for ln in lines[1:]:
        m = _ENTRY_RE.match(ln)
        if m:
            close(current)
            current = {"id_str": m.group(1), "id": int(m.group(2)), "title": m.group(3)}
            continue
        if current is None:
            continue
        bm = _BULLET_RE.match(ln)
        if bm:
            current[bm.group(1).lower()] = bm.group(2)
            continue
        if ln.startswith("**When:**"):
            for part in ln.split(" · "):
                km = _META_KEY_RE.search(part)
                if km:
                    current[km.group(1).lower()] = km.group(2)
    close(current)

    if entries and has_sentinel:
        errors.append("sentinel line coexists with entries — the first append must "
                      "REPLACE the empty form's sentinel")
    if not entries and not has_sentinel:
        errors.append(f"zero entries but no '{EMPTY_SENTINEL}' sentinel — not a valid empty form")
    ids = [e["id"] for e in entries]
    if len(set(ids)) != len(ids):
        errors.append("duplicate SD-NNNN ids")

    return {"ok": not errors, "empty": (not entries and has_sentinel),
            "entries": entries, "errors": errors}


def parse_file(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return parse(fh.read())
    except OSError as exc:
        return {"ok": False, "empty": False, "entries": [], "errors": [f"unreadable: {exc}"]}


# --- monotonic append (mirrors the decision-log discipline) ---------------------

def _locked(root: str):
    fdir = fs.friday_dir(root)
    os.makedirs(fdir, exist_ok=True)
    return open(os.path.join(fdir, "deviations.lock"), "a+")


def _read_counter(root: str) -> int:
    try:
        with open(os.path.join(fs.friday_dir(root), "deviations.counter"), encoding="utf-8") as fh:
            return int(fh.read().strip() or "0")
    except (OSError, ValueError):
        return 0


def _write_counter(root: str, value: int) -> None:
    path = os.path.join(fs.friday_dir(root), "deviations.counter")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(str(value))
    os.replace(tmp, path)


def _atomic_write(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def append_entry(root: str, *, metric: str, measured: str, bar: str, location: str,
                 justification: str, standard: str, channel: str = "model-autonomous",
                 floor: str = "none", when: str | None = None, path: str = DEFAULT_PATH,
                 cap: int = DEFAULT_CAP, project: str | None = None) -> tuple[str, str]:
    """Append one schema-valid deviation; returns (id_str, entry_text). Raises
    ValueError on invalid fields (nothing written). The file written is the
    CHECKOUT's copy; the id counter is the SHARED substrate's — worktrees isolate
    code but share the counter, so ids never collide (Appendix B)."""
    errs = validate_fields(channel, floor)
    if errs:
        raise ValueError("; ".join(errs))
    wroot = fs.resolve_worktree_root(root)
    abs_path = os.path.join(wroot, path)

    with _locked(root) as lockfh:
        fcntl.flock(lockfh, fcntl.LOCK_EX)
        try:
            if os.path.isfile(abs_path):
                with open(abs_path, encoding="utf-8") as fh:
                    text = fh.read()
            else:
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                text = empty_form(project or os.path.basename(wroot), cap)
            parsed = parse(text)
            local_max = max((e["id"] for e in parsed["entries"]), default=0)
            next_id = max(_read_counter(root), local_max) + 1

            entry = format_entry(id_num=next_id, metric=metric, measured=measured,
                                 bar=bar, location=location, justification=justification,
                                 standard=standard, when=when or fs.now_iso(),
                                 channel=channel, floor=floor)
            if parsed["empty"]:
                text = "\n".join(ln for ln in text.splitlines()
                                 if ln.strip() != EMPTY_SENTINEL).rstrip() + "\n"
            text = text.rstrip() + "\n\n" + entry
            _atomic_write(abs_path, text)
            _write_counter(root, next_id)
            _archive_if_needed(wroot, abs_path, cap)
        finally:
            fcntl.flock(lockfh, fcntl.LOCK_UN)
    return f"SD-{next_id:04d}", entry


def _reformat(e: dict) -> str:
    return format_entry(id_num=e["id"], metric=e.get("metric", "?"),
                        measured=e.get("measured", "?"), bar=e.get("bar", "?"),
                        location=e.get("location", "?"),
                        justification=e.get("justification", "?"),
                        standard=e.get("standard", "?"), when=e.get("when", "?"),
                        channel=e.get("channel", "model-autonomous"),
                        floor=e.get("floor", "none"))


def _archive_if_needed(wroot: str, abs_path: str, cap: int) -> None:
    with open(abs_path, encoding="utf-8") as fh:
        text = fh.read()
    parsed = parse(text)
    if not parsed["ok"] or len(parsed["entries"]) <= cap:
        return
    keep_from = len(parsed["entries"]) - (cap // 2)
    moved, kept = parsed["entries"][:keep_from], parsed["entries"][keep_from:]
    arch_dir = os.path.join(wroot, "docs", "deviations")
    os.makedirs(arch_dir, exist_ok=True)
    n = 1
    while os.path.exists(os.path.join(arch_dir, f"archive-{n:03d}.md")):
        n += 1
    arch_text = f"# Standards Deviations — archive {n:03d}\n\n" + "\n".join(_reformat(e) for e in moved)
    _atomic_write(os.path.join(arch_dir, f"archive-{n:03d}.md"), arch_text)
    head = text.splitlines()
    h1 = head[0] if head else "# Standards Deviations"
    marker = "\n".join(ln for ln in head[1:8] if ln.startswith("<!--") or ln.startswith("    "))
    live = h1 + "\n\n" + (marker + "\n\n" if marker else "") + "\n".join(_reformat(e) for e in kept)
    _atomic_write(abs_path, live)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Append a standards deviation "
                                             "(contract: docs/contracts/standards-deviation.md)")
    ap.add_argument("--init", action="store_true", help="write the empty form and exit")
    ap.add_argument("--root", default=".")
    ap.add_argument("--project", default=None)
    ap.add_argument("--metric"); ap.add_argument("--measured"); ap.add_argument("--bar")
    ap.add_argument("--location"); ap.add_argument("--justification"); ap.add_argument("--standard")
    ap.add_argument("--channel", default="model-autonomous", choices=CHANNELS)
    ap.add_argument("--floor", default="none", choices=FLOORS)
    ap.add_argument("--when", default=None)
    args = ap.parse_args(argv)
    if args.init:
        wroot = fs.resolve_worktree_root(args.root)
        p = os.path.join(wroot, DEFAULT_PATH)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if not os.path.isfile(p):
            _atomic_write(p, empty_form(args.project or os.path.basename(wroot)))
        print(p)
        return 0
    required = (args.metric, args.measured, args.bar, args.location,
                args.justification, args.standard)
    if not all(required):
        print("standards_deviations: --metric --measured --bar --location "
              "--justification --standard are all required to append", file=sys.stderr)
        return 2
    try:
        idn, _ = append_entry(args.root, metric=args.metric, measured=args.measured,
                              bar=args.bar, location=args.location,
                              justification=args.justification, standard=args.standard,
                              channel=args.channel, floor=args.floor, when=args.when,
                              project=args.project)
    except ValueError as exc:
        print(f"standards_deviations: {exc}", file=sys.stderr)
        return 2
    print(idn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
