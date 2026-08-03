#!/usr/bin/env python3
"""The scheduled-job list — photographed once, confirmed once, diffed forever
(INC-102 FR-102.7, D6; value-blind by refusal: S-102.3, KH-4).

This module OWNS `docs/ops/scheduled-jobs.md` (the D-0135 pattern). It exists
because the audited project's own documentation called hand-edited schedules
its number one recurring operational failure — twice bitten, nothing written
down, nothing comparing written to installed. One typed line per job:

    job: <name> · schedule: <cron-ish> · source: <where> · purpose: <prose> · confirmed: <date>|pending

- **photograph** copies what is installed into a PENDING entry. The file
  itself states that a photograph was taken off the machine and ratifies
  nothing — a pending entry represents nobody's decision (D6).
- **confirm** is the PM's once-per-job answer — does it belong, what is it
  for — recorded with its date. Only the PM's word flips pending.
- **diff** compares the machine's current jobs to the list. While any entry
  is pending, differences are a PENDING BASELINE, never drift; once the
  baseline is confirmed, any difference is a finding naming the job
  (AC-102.10). Report-only, always exit 0 (S-102.2).
- **The write is value-blind by refusal (KH-4):** a live schedule routinely
  carries a credential inline on the command that runs the job, and this is
  the one place this increment writes. There is no field for a command, and
  every field is scanned for value shapes — a URL userinfo, a known token
  prefix, a secret-bearing assignment, a long high-entropy token — and
  refused before anything touches disk. The refusal names the FIELD and
  never echoes the content: the list records names, schedules and purposes,
  never the value-bearing parts of a command (S-102.3). The
  repository-carries-names, store-carries-values invariant (INC-204 D2) is
  untouched.
- **A malformed line is kept and flagged, never dropped**; the empty case
  (`_No scheduled jobs recorded._`) is distinct from an absent file.

Contract: `docs/contracts/ops-battery.md` § the job list. Pure stdlib.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402
import taglines  # noqa: E402

BLOCK = "FRIDAY-SCHEDULED-JOBS"
SENTINEL = "_No scheduled jobs recorded._"

_F_SCHED = " · schedule: "
_F_SRC = " · source: "
_F_PURP = " · purpose: "
_F_CONF = " · confirmed: "
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Value shapes refused in ANY field. Deliberately over-broad: a false refusal
# costs a rewording, a false pass costs a credential rotation on somebody's
# production system.
_VALUE_SHAPES = (
    re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s:@]+:[^@\s]+@"),  # URL userinfo
    re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{16,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}"),                        # JWT head
    re.compile(r"(?i)\b(?:password|passwd|pwd|token|secret|api[_-]?key|apikey|auth(?:orization)?)\s*[=:]\s*\S{6,}"),
    re.compile(r"\b(?=[A-Za-z0-9+/=_-]*[0-9])(?=[A-Za-z0-9+/=_-]*[A-Za-z])[A-Za-z0-9+/=_-]{32,}\b"),
)

HEADER = """# Scheduled jobs — the committed list

One line per scheduled job: the name friday gave it, its schedule, where it is installed, and its purpose — never the value-bearing parts of a command (S-102.3). An entry marked `confirmed: pending` was photographed off the machine by `tools/scheduled_jobs.py` and ratifies nothing: it represents nobody's decision until the PM confirms the job belongs there and what it is for (INC-102 D6). Row set and verdict grammar: `docs/contracts/ops-battery.md`.

<!-- FRIDAY-SCHEDULED-JOBS:BEGIN -->
{body}
<!-- FRIDAY-SCHEDULED-JOBS:END -->
"""


def _path(root: str) -> str:
    return os.path.join(fs.resolve_worktree_root(root), "docs", "ops",
                        "scheduled-jobs.md")


def _read_text(root: str) -> str | None:
    try:
        with open(_path(root), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def _atomic_write(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def _scan_values(**fields: str) -> None:
    """Refuse any field carrying a value shape. Names the field, never the
    content — echoing the value into an error message is leaking it."""
    for field, value in fields.items():
        for shape in _VALUE_SHAPES:
            if shape.search(value or ""):
                raise ValueError(
                    f"the {field} field looks like it carries a value — the "
                    f"list records names, schedules and purposes, never the "
                    f"value-bearing parts of a command (S-102.3); reword "
                    f"without the value")


def _parse_value(value: str) -> dict | None:
    """One `job:` VALUE → entry dict, or None when malformed. purpose is the
    only free-prose field; confirmed anchors on the LAST marker so prose
    cannot shift it."""
    head, sep, confirmed = value.rpartition(_F_CONF)
    if not sep:
        return None
    name, sep, rest = head.partition(_F_SCHED)
    if not sep or not _NAME_RE.match(name.strip()):
        return None
    schedule, sep, rest = rest.partition(_F_SRC)
    if not sep:
        return None
    source, sep, purpose = rest.partition(_F_PURP)
    if not sep:
        return None
    confirmed = confirmed.strip()
    if confirmed != "pending" and not _DATE_RE.match(confirmed):
        return None
    return {"name": name.strip(), "schedule": schedule.strip(),
            "source": source.strip(), "purpose": purpose.strip(),
            "confirmed": confirmed}


def _format_line(job: dict) -> str:
    return (f"job: {job['name']}{_F_SCHED}{job['schedule']}{_F_SRC}"
            f"{job['source']}{_F_PURP}{job['purpose']}{_F_CONF}{job['confirmed']}")


def _splice(text: str, body_lines: list[str]) -> str:
    begin, end = f"<!-- {BLOCK}:BEGIN -->", f"<!-- {BLOCK}:END -->"
    head, _, rest = text.partition(begin)
    _, _, tail = rest.partition(end)
    body = "\n".join(body_lines) if body_lines else SENTINEL
    return f"{head}{begin}\n{body}\n{end}{tail}"


def read(root: str = ".") -> dict:
    """status: 'absent' (never photographed) | 'empty' | 'recorded'."""
    text = _read_text(root)
    if text is None:
        return {"status": "absent", "jobs": {}, "malformed": []}
    lines = taglines.block_lines(text, BLOCK)
    if lines is None:
        return {"status": "absent", "jobs": {}, "malformed": []}
    jobs: dict[str, dict] = {}
    malformed: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped == SENTINEL or stripped.startswith("<!--"):
            continue
        parsed = taglines.parse_typed_line(line)
        if not parsed or parsed[0] != "job":
            malformed.append(line)
            continue
        entry = _parse_value(parsed[1])
        if entry is None:
            malformed.append(line)
            continue
        jobs[entry.pop("name")] = entry
    status = "recorded" if jobs or malformed else "empty"
    return {"status": status, "jobs": jobs, "malformed": malformed}


def init(root: str = ".") -> dict:
    if _read_text(root) is not None:
        return {"ok": True, "detail": "list already exists"}
    path = _path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _atomic_write(path, HEADER.format(body=SENTINEL))
    return {"ok": True, "detail": f"initialized {path}"}


def _write_jobs(root: str, jobs: dict[str, dict], malformed: list[str]) -> None:
    text = _read_text(root)
    if text is None:
        init(root)
        text = _read_text(root)
    body = [_format_line({"name": n, **j}) for n, j in sorted(jobs.items())]
    _atomic_write(_path(root), _splice(text, body + malformed))


def photograph(root: str = ".", *, name: str, schedule: str, source: str,
               purpose: str) -> dict:
    """Copy one installed job into a PENDING entry — a photograph ratifies
    nothing (D6). Upserts by name; the value scan runs before any write."""
    name = (name or "").strip()
    schedule = " ".join((schedule or "").split())
    source = (source or "").strip()
    purpose = " ".join((purpose or "").split())
    if not _NAME_RE.match(name):
        raise ValueError("name must be a lowercase slug (a-z 0-9 . _ -) — "
                         "friday names the job, it never copies the command")
    if " " in source:
        raise ValueError("source is a single token (crontab, systemd, ci, …)")
    if not schedule or not purpose:
        raise ValueError("schedule and purpose are both required — an entry "
                         "nobody can act on forces nothing")
    _scan_values(name=name, schedule=schedule, source=source, purpose=purpose)
    state = read(root)
    jobs = state["jobs"]
    jobs[name] = {"schedule": schedule, "source": source, "purpose": purpose,
                  "confirmed": "pending"}
    _write_jobs(root, jobs, state["malformed"])
    return {"ok": True, "name": name, "confirmed": "pending"}


def confirm(root: str = ".", name: str = "", *, purpose: str | None = None,
            when: str | None = None) -> dict:
    """The PM's once-per-job answer, dated. Optionally updates the purpose
    with what the PM actually said — scanned like every other write."""
    state = read(root)
    if name not in state["jobs"]:
        return {"ok": False, "detail": f"{name!r} is not in the list — "
                                       f"photograph it first"}
    date = when or datetime.date.today().isoformat()
    if not _DATE_RE.match(date):
        raise ValueError(f"date must be YYYY-MM-DD, got {date!r}")
    if purpose is not None:
        purpose = " ".join(purpose.split())
        _scan_values(purpose=purpose)
        state["jobs"][name]["purpose"] = purpose
    state["jobs"][name]["confirmed"] = date
    _write_jobs(root, state["jobs"], state["malformed"])
    return {"ok": True, "name": name, "confirmed": date}


def diff(root: str = ".", *, installed: list[tuple[str, str]]) -> dict:
    """Machine vs list. While any entry is pending the baseline is
    unratified: differences are pending items, never findings (AC-102.10).
    Once every entry is confirmed, every difference is a finding naming the
    job. Report-only."""
    state = read(root)
    jobs = state["jobs"]
    pending_names = {n for n, j in jobs.items() if j["confirmed"] == "pending"}
    baseline = "pending" if (pending_names or state["status"] != "recorded") \
        else "confirmed"
    findings: list[str] = []
    pending: list[str] = []
    machine = {n: s for n, s in installed}
    sink = pending if baseline == "pending" else findings
    for name, sched in machine.items():
        if name not in jobs:
            sink.append(f"{name} runs on the machine ({sched}) but is not in "
                        f"the committed list")
        elif jobs[name]["schedule"] != sched:
            sink.append(f"{name}: installed schedule {sched} differs from the "
                        f"listed {jobs[name]['schedule']}")
    for name, job in jobs.items():
        if name not in machine:
            sink.append(f"{name} is in the committed list but not installed "
                        f"on the machine")
    if baseline == "pending":
        pending.extend(f"{n} awaits the PM's confirmation" for n in
                       sorted(pending_names))
    return {"baseline": baseline, "findings": findings, "pending": pending,
            "malformed": state["malformed"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="The scheduled-job list — photograph, confirm, diff "
                    "(INC-102 FR-102.7, D6)")
    sub = ap.add_subparsers(dest="verb", required=True)
    ph = sub.add_parser("photograph", help="copy one installed job in, PENDING")
    ph.add_argument("--root", default=".")
    ph.add_argument("--name", required=True)
    ph.add_argument("--schedule", required=True)
    ph.add_argument("--source", required=True)
    ph.add_argument("--purpose", required=True)
    cf = sub.add_parser("confirm", help="the PM's once-per-job answer, dated")
    cf.add_argument("--root", default=".")
    cf.add_argument("--name", required=True)
    cf.add_argument("--purpose", default=None)
    cf.add_argument("--when", default=None)
    df = sub.add_parser("diff", help="machine vs list — report only, exit 0")
    df.add_argument("--root", default=".")
    df.add_argument("--installed", action="append", default=[],
                    metavar="NAME@SCHEDULE",
                    help="one installed job, repeatable: name@schedule")
    ls = sub.add_parser("read", help="current state, JSON")
    ls.add_argument("--root", default=".")
    ini = sub.add_parser("init", help="write the empty list")
    ini.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    try:
        if args.verb == "photograph":
            res = photograph(args.root, name=args.name, schedule=args.schedule,
                             source=args.source, purpose=args.purpose)
        elif args.verb == "confirm":
            res = confirm(args.root, args.name, purpose=args.purpose,
                          when=args.when)
        elif args.verb == "diff":
            pairs = []
            for item in args.installed:
                name, _, sched = item.partition("@")
                pairs.append((name.strip(), sched.strip()))
            print(json.dumps(diff(args.root, installed=pairs)))
            return 0
        elif args.verb == "read":
            print(json.dumps(read(args.root)))
            return 0
        else:
            res = init(args.root)
    except ValueError as exc:
        print(json.dumps({"ok": False, "detail": str(exc)}))
        return 1
    print(json.dumps(res))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
