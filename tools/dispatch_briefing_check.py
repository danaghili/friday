#!/usr/bin/env python3
"""Dispatch-briefing checker — report-only (INC-208 FR-208.5, S-208.1).

The problem it exists for: every lane that starts a helper agent writes that
helper a briefing, the briefing has a fixed skeleton, and before INC-208 no
file held the skeleton — so it was reassembled from memory at every dispatch
and pieces went missing silently. Both briefings on disk at discovery were
missing the same required piece. A written template alone cannot report that;
this checker reads the briefings that were ACTUALLY sent and names what is
absent.

Two defect classes, both observed at discovery:

  missing-field     a saved briefing whose typed `dispatch:` line omits a
                    required field (the drawer path being the observed one).
  unsaved-briefing  a dispatch the journal records with no briefing saved at
                    all — `spawn_telemetry.py --prompt-file` was not used.

Plus one honest non-verdict:

  unchecked-briefing  a saved briefing with no typed line. Reported as
                    UNCHECKED rather than passed — silence here would be the
                    checker certifying a file it never actually read.

WHY IT SCOPES OFF THE JOURNAL (KH-1, the make-or-break precision property):
`docs/contracts/compaction-package.md` gives `mission.md` two legitimate
producers — a dispatch briefing, and the orchestrator's OWN self-authored
lane-entry note. Walking the drawers and judging every `mission.md` would
report the lead's own notes as defective briefings, at close time, on the
lead's own work — exactly how a report-only checker earns the reputation that
gets it switched off. So the worklist is "which dispatches the journal
records", never "which files exist": a drawer nobody dispatched into is
invisible to this checker by construction rather than by filter.

Contract: `docs/contracts/compaction-package.md` (the drawer layout and the
typed line's shape — cited, never restated). Template: the shared briefing
template it names. Grammar: `tools/taglines.py`, no new parser (FR-208.4).

Usage:
  python3 tools/dispatch_briefing_check.py [--root .] [--session-id SID] [--json]

Exit code is ALWAYS 0 — this reports, it never gates (S-208.1). Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

DISPATCH_TAG = "dispatch"
REQUIRED_FIELDS = ("lane", "role", "drawer", "template")
MISSION_LAYER = "mission.md"


def parse_dispatch_line(line: str) -> dict | None:
    """The typed line's `key=value` fields, or None when the line is not a
    dispatch tag line. Grammar shape follows the change-trail's leading tag
    line (`trail: lane=… id=… date=…`) — one line, space-separated pairs,
    parsed through the shared tag-line reader."""
    parsed = taglines.parse_typed_line(line)
    if parsed is None or parsed[0] != DISPATCH_TAG:
        return None
    fields: dict[str, str] = {}
    for token in parsed[1].split():
        if "=" not in token:
            continue
        key, _, value = token.partition("=")
        if key:
            fields[key] = value
    return fields


def briefing_line(text: str) -> dict | None:
    """The dispatch fields of a briefing, or None when its FIRST non-blank
    line is not a dispatch tag line. The position rule matters: a typed line
    buried mid-document is prose about a briefing, not the briefing's own
    machine-readable header."""
    for raw in text.splitlines():
        if not raw.strip():
            continue
        return parse_dispatch_line(raw)
    return None


def _dispatched_roles(root: str) -> list[str]:
    """Agent slugs the journal records a spawn for, in first-seen order.
    Unreadable or absent journal → empty list: unsure ALLOWS (S-208.1)."""
    path = os.path.join(root, ".friday", "journal.jsonl")
    roles: list[str] = []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return roles
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue                      # one bad line never voids the rest
        if rec.get("event") != "spawn":
            continue
        agent = (rec.get("data") or {}).get("agent")
        if agent and agent not in roles:  # one dispatch record per agent
            roles.append(agent)
    return roles


def _briefing_path(root: str, role: str, session_id: str | None) -> str | None:
    """The saved briefing for this role — this session's drawer first, then any
    other session's.

    The cross-session fallback is not laxity, it is the anti-cry-wolf rule
    (KH-1) applied to a fact the journal cannot express: the journal spans every
    session friday has ever run, while a drawer is per-session, so a dispatch
    briefed properly in an earlier session has no briefing in TODAY's drawer.
    This checker's own first live run reported nine such dispatches as unsaved,
    every one of them a false alarm. A briefing found in any drawer is a
    briefing that was saved; a role briefed in none is still the real defect
    and is still reported."""
    base = os.path.join(root, ".friday", "compaction")
    ordered = ([session_id] if session_id else []) + [
        s for s in _sessions(base) if s != session_id]
    for sid in ordered:
        for drawer in _role_drawers(base, sid, role):
            candidate = os.path.join(base, sid, drawer, MISSION_LAYER)
            if os.path.isfile(candidate):
                return candidate
    return None


def _sessions(base: str) -> list[str]:
    try:
        return sorted(os.listdir(base))
    except OSError:
        return []


def _role_drawers(base: str, session_id: str, role: str) -> list[str]:
    """Drawer names that belong to this role: the bare slug, plus any
    instance-suffixed form (`<role>-208`). The template tells a lane to
    instance-suffix when it dispatches the same role twice in one session so
    the second briefing does not overwrite the first agent's notes — a lookup
    that only knew the bare slug would turn the template's own advice into a
    false alarm."""
    names = [role]
    try:
        names += sorted(d for d in os.listdir(os.path.join(base, session_id))
                        if d.startswith(role + "-"))
    except OSError:
        pass
    return names


def check(root: str, *, session_id: str | None = None) -> dict:
    """Report every dispatch whose briefing is missing, unchecked, or short a
    required field. Findings carry NAMES and paths only — never briefing body
    text (S-208.2)."""
    findings: list[dict] = []
    roles = _dispatched_roles(root)
    if session_id is None:
        session_id = _newest_session(root)
    for role in roles:
        path = _briefing_path(root, role, session_id)
        if path is None:
            findings.append({"kind": "unsaved-briefing", "role": role,
                             "detail": "dispatch recorded with no briefing "
                                       "saved (spawn_telemetry.py "
                                       "--prompt-file was not used)"})
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            findings.append({"kind": "unsaved-briefing", "role": role,
                             "detail": "dispatch recorded with no briefing "
                                       "saved (spawn_telemetry.py "
                                       "--prompt-file was not used)"})
            continue
        fields = briefing_line(text)
        if fields is None:
            findings.append({"kind": "unchecked-briefing", "role": role,
                             "file": path,
                             "detail": "saved briefing carries no typed "
                                       "`dispatch:` line — reported unchecked, "
                                       "never passed"})
            continue
        for field in REQUIRED_FIELDS:
            if not fields.get(field):
                findings.append({"kind": "missing-field", "role": role,
                                 "file": path, "field": field,
                                 "detail": f"typed line omits `{field}`"})
    return {"ok": not findings, "findings": findings,
            "summary": ("every recorded dispatch saved a complete briefing"
                        if not findings else
                        f"{len(findings)} dispatch-briefing finding(s) — "
                        "report only, nothing blocked")}


def _newest_session(root: str) -> str | None:
    """The newest drawer session id, when the caller named none."""
    base = os.path.join(root, ".friday", "compaction")
    try:
        entries = [(os.path.getmtime(os.path.join(base, d)), d)
                   for d in os.listdir(base)
                   if os.path.isdir(os.path.join(base, d))]
    except OSError:
        return None
    return max(entries)[1] if entries else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--session-id", default=None,
                    help="drawer session id (default: the newest drawer)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = check(args.root, session_id=args.session_id)
    if args.json:
        print(json.dumps(res))
    else:
        print(res["summary"])
        for f in res["findings"]:
            where = f.get("file", f["role"])
            print(f"  [{f['kind']}] {where}: {f['detail']}")
    return 0                              # report-only, always (S-208.1)


if __name__ == "__main__":
    raise SystemExit(main())
