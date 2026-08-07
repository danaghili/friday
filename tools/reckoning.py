#!/usr/bin/env python3
"""The consumer reckoning record — "no change required" becomes a claim with
a test attached (INC-104 FR-104.4/104.5/104.6/104.8, D9).

The audited project's impact analysis named the right consumers and cleared
them in untested prose; the clearances were believed for months and both were
false. This record makes that artefact unwritable: every enumerated consumer
gets one typed answer from a closed set, a clearance cannot exist without the
observable that would prove it wrong AND the thing that exercises it, and the
per-change `searched:` line states what ran and what could not be covered —
derived by this module, never accepted as caller prose, so a completeness
claim has no field to live in (S-104.2).

This module OWNS `docs/RECKONINGS.md` (the D-0135 pattern: a module owning a
whole record type writes its own record; the substrate is reached only for
shared primitives). Two line shapes, one per fact:

    reckoning: cleared code change=INC-104 from=declared 2026-08-03 what: tools/rollback.sh · evidence: cites the deploy contract · observable: a reboot restores the recorded tag · exercised-by: tests/test_rollback.py::test_reboot
    searched: change=INC-104 2026-08-03 declared=ran name-match=ran reading=ran person=answered · name: sha-tag · not-covered: a dependency on a behaviour that carries no name in it cannot be found by the name search

- **The answer vocabulary is CLOSED** and its single home is the contract
  table in `docs/contracts/reckoning-record.md`; ANSWERS below is the
  operational copy and a committed test locks the two together. The word is
  `reckoning`, not `disposition` — that token already names three other
  things in this tree and a fourth meaning would make every exact-phrase
  search for any of them return the others (D9).
- **A bare clearance is REFUSED (AC-104.2):** `cleared` with no observable
  never lands, and the refusal says why. `cleared` whose observable nothing
  exercises RESOLVES to `not-proven` with the reason on the line — reported
  in the result, never silent.
- **Silence is not in the vocabulary (FR-104.4):** a consumer enumerated but
  never recorded here is an unanswered finding for the report layer — this
  record holds answers, and `has()` tells the deep-clean catch-up whether a
  change carries any record of having been reconciled at all (FR-104.9).
- **The three person states are three states (AC-104.5):** `answered`,
  `nothing-known` and `not-asked` are distinct values on the `searched:`
  line; an answer of "nothing that I know of" is an answer.
- **The record carries names, never values (S-104.4):** evidence is a path
  and the fact of a match; nothing here quotes a matched line's content.
- **The empty case is a valid, distinct outcome:** an absent file means the
  question was never asked here; an empty block means initialized with
  nothing reckoned yet; a `searched:` line with zero reckonings means the
  enumeration ran and found nothing — three different facts, never merged.
- **A malformed line is kept and flagged, never dropped.**

Grammar note: free-prose fields may contain ` · ` and marker-like words; the
parser therefore peels segments RIGHTMOST-first in reverse emission order
(the parked ledger's anchor lesson), so the emitted shape always round-trips.
Contract: `docs/contracts/reckoning-record.md`. Pure stdlib.
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

KEY = "reckoning"
BLOCK = "FRIDAY-RECKONINGS"
SENTINEL = "_No reckonings yet._"
# Typed lines the live block may hold before the oldest whole changes move
# to docs/reckonings/archive-NNN.md (contract § The growing-log discipline).
CAP = 100

ANSWERS = ("moves-with-change", "cleared", "not-proven", "not-a-consumer")
CLASSES = ("code", "process")
SOURCES = ("declared", "name-match", "reading", "person")
PERSON_STATES = ("answered", "nothing-known", "not-asked")
RUN_STATES = ("ran", "skipped")
NAME_MATCH_STATES = ("ran", "too-common", "skipped")

NO_EXERCISER = ("nothing exercises the named observable — resolved to "
                "not-proven rather than cleared (AC-104.2)")
NAMELESS_LIMIT = ("a dependency on a behaviour that carries no name in it "
                  "cannot be found by the name search")

# Which prose segments each answer requires / forbids (FR-104.5, FR-104.6).
# evidence is required everywhere — an unopenable consumer proves nothing.
_PARTS = {
    "moves-with-change": {"required": (), "forbidden": ("observable", "exercised_by", "because")},
    "cleared": {"required": ("observable", "exercised_by"), "forbidden": ("because",)},
    "not-proven": {"required": ("observable", "because"), "forbidden": ("exercised_by",)},
    "not-a-consumer": {"required": ("because",), "forbidden": ("observable", "exercised_by")},
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TOKEN_RE = re.compile(r"^\S+$")
_RECK_HEAD_RE = re.compile(
    r"^(" + "|".join(ANSWERS) + r") (" + "|".join(CLASSES) + r") "
    r"change=(\S+) from=(" + "|".join(SOURCES) + r") "
    r"(\d{4}-\d{2}-\d{2}) what: (.*)$", re.DOTALL)
_SEARCHED_HEAD_RE = re.compile(
    r"^change=(\S+) (\d{4}-\d{2}-\d{2}) declared=(\S+) name-match=(\S+) "
    r"reading=(\S+) person=(\S+) · name: (.*)$", re.DOTALL)

HEADER = """# Consumer reckonings — the turned-around question's record

One typed line per enumerated consumer — its answer, its class, the source that found it, and (for a clearance) the observable that would prove it wrong plus what exercises it — and one `searched:` line per change stating what ran and what could not be covered. Written by `tools/reckoning.py` only; the answer vocabulary and both line grammars live in `docs/contracts/reckoning-record.md` (the reckoning's single home). History lives in git — this file holds the current state, never the story.

<!-- FRIDAY-RECKONINGS:BEGIN -->
{body}
<!-- FRIDAY-RECKONINGS:END -->
"""


def _path(root: str) -> str:
    return os.path.join(fs.resolve_worktree_root(root), "docs", "RECKONINGS.md")


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


def _flat(text: str) -> str:
    return " ".join((text or "").split())


def _peel(rest: str, marker: str) -> tuple[str, str | None]:
    """Split off the RIGHTMOST ` · {marker}: ` segment; (remainder, segment)
    or (rest, None) when the marker is absent."""
    head, sep, tail = rest.rpartition(f" · {marker}: ")
    if not sep:
        return rest, None
    return head, tail


def _parse_reckoning(value: str) -> dict | None:
    m = _RECK_HEAD_RE.match(value)
    if not m:
        return None
    answer, cls, change, source, date, rest = m.groups()
    rest, because = _peel(rest, "because")
    rest, exercised_by = _peel(rest, "exercised-by")
    rest, observable = _peel(rest, "observable")
    what, evidence = _peel(rest, "evidence")
    if evidence is None or not what:
        return None
    parts = {"observable": observable, "exercised_by": exercised_by,
             "because": because}
    rule = _PARTS[answer]
    if any(parts[p] is None for p in rule["required"]):
        return None
    if any(parts[p] is not None for p in rule["forbidden"]):
        return None
    return {"answer": answer, "class": cls, "change": change,
            "source": source, "date": date, "what": what,
            "evidence": evidence, "observable": observable,
            "exercised_by": exercised_by, "because": because}


def _format_reckoning(row: dict) -> str:
    line = (f"reckoning: {row['answer']} {row['class']} "
            f"change={row['change']} from={row['source']} {row['date']} "
            f"what: {row['what']} · evidence: {row['evidence']}")
    if row.get("observable"):
        line += f" · observable: {row['observable']}"
    if row.get("exercised_by"):
        line += f" · exercised-by: {row['exercised_by']}"
    if row.get("because"):
        line += f" · because: {row['because']}"
    return line


def _parse_searched(value: str) -> dict | None:
    m = _SEARCHED_HEAD_RE.match(value)
    if not m:
        return None
    change, date, declared, name_match, reading, person, rest = m.groups()
    rest, not_covered = _peel(rest, "not-covered")
    if not_covered is None or not rest:
        return None
    if (declared not in RUN_STATES or name_match not in NAME_MATCH_STATES
            or reading not in RUN_STATES or person not in PERSON_STATES):
        return None
    return {"change": change, "date": date, "declared": declared,
            "name_match": name_match, "reading": reading, "person": person,
            "name": rest, "not_covered": not_covered}


def _format_searched(sw: dict) -> str:
    return (f"searched: change={sw['change']} {sw['date']} "
            f"declared={sw['declared']} name-match={sw['name_match']} "
            f"reading={sw['reading']} person={sw['person']} "
            f"· name: {sw['name']} · not-covered: {sw['not_covered']}")


def _derive_not_covered(declared: str, name_match: str, reading: str,
                        person: str) -> str:
    """FR-104.8's structural statement, re-derived on every run. Callers
    cannot pass this text — the field a completeness claim would need does
    not exist (S-104.2)."""
    parts = [NAMELESS_LIMIT]
    if name_match == "too-common":
        parts.append("the name was too common to search usefully — the "
                     "other sources carry the enumeration (OQ-104.3)")
    elif name_match == "skipped":
        parts.append("the name search did not run")
    if declared == "skipped":
        parts.append("the declared-citation scan did not run")
    if reading == "skipped":
        parts.append("the model's read did not run")
    if person == "not-asked":
        parts.append("the person was not asked")
    return "; ".join(parts)


def read(root: str = ".") -> dict:
    """The record's current state. `status` is one of three REAL outcomes:
    'absent' (the question was never asked here), 'empty' (initialized,
    nothing reckoned yet), 'recorded'. Malformed lines ride along flagged."""
    text = _read_text(root)
    if text is None:
        return {"status": "absent", "reckonings": [], "searched": {},
                "malformed": []}
    lines = taglines.block_lines(text, BLOCK)
    if lines is None:
        return {"status": "absent", "reckonings": [], "searched": {},
                "malformed": []}
    reckonings: list[dict] = []
    searched: dict[str, dict] = {}
    malformed: list[str] = []
    for line in lines:
        if line == SENTINEL:
            continue
        parsed = taglines.parse_typed_line(line)
        if parsed and parsed[0] == KEY:
            entry = _parse_reckoning(parsed[1])
            (reckonings.append(entry) if entry else malformed.append(line))
        elif parsed and parsed[0] == "searched":
            entry = _parse_searched(parsed[1])
            if entry:
                searched[entry.pop("change")] = entry
            else:
                malformed.append(line)
        else:
            malformed.append(line)
    status = ("recorded" if reckonings or searched or malformed else "empty")
    return {"status": status, "reckonings": reckonings, "searched": searched,
            "malformed": malformed}


def init(root: str = ".") -> dict:
    """Write the record with its empty block — nothing reckoned yet, as a
    written fact. A no-op when the record already exists."""
    if _read_text(root) is not None:
        return {"ok": True, "detail": "record already exists"}
    path = _path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _atomic_write(path, HEADER.format(body=SENTINEL))
    return {"ok": True, "detail": f"initialized {path}"}


_ARCHIVE_HEADER = """# Consumer reckonings — archived lines

Moved out of `docs/RECKONINGS.md` by `tools/reckoning.py` at its `CAP` — whole changes, never split (`docs/contracts/reckoning-record.md` § The growing-log discipline). Lines preserved verbatim; `has()` no longer sees them, and a change old enough to land here predates the anchor of any honest clean run.

"""


def _oldest_changes(state: dict) -> list[str]:
    """Every change in the live record, oldest first. A change's age is the
    EARLIEST date on any of its lines — an upsert refreshes the line it
    touches, and must not rejuvenate the change's other lines with it."""
    ages: dict[str, str] = {}
    for change, sw in state["searched"].items():
        ages[change] = min(ages.get(change, sw["date"]), sw["date"])
    for r in state["reckonings"]:
        ages[r["change"]] = min(ages.get(r["change"], r["date"]), r["date"])
    return sorted(ages, key=lambda c: (ages[c], c))


def _next_archive_path(root: str) -> str:
    folder = os.path.join(fs.resolve_worktree_root(root), "docs", "reckonings")
    os.makedirs(folder, exist_ok=True)
    taken = [int(m.group(1)) for f in os.listdir(folder)
             if (m := re.match(r"archive-(\d{3})\.md$", f))]
    return os.path.join(folder, f"archive-{max(taken, default=0) + 1:03d}.md")


def _archive_overflow(root: str, state: dict) -> None:
    """The growing-log discipline: past CAP typed lines, the oldest whole
    changes — `searched:` line and reckonings together, never split — move
    to the archive until the live record fits. Malformed lines are not
    typed lines: they stay live and flagged, whatever the count."""
    order = _oldest_changes(state)
    moved: list[str] = []
    while (len(state["searched"]) + len(state["reckonings"]) > CAP
           and len(order) > 1):
        change = order.pop(0)
        sw = state["searched"].pop(change, None)
        if sw is not None:
            moved.append(_format_searched({"change": change, **sw}))
        kept = [r for r in state["reckonings"] if r["change"] != change]
        moved += [_format_reckoning(r) for r in state["reckonings"]
                  if r["change"] == change]
        state["reckonings"] = kept
    if moved:
        _atomic_write(_next_archive_path(root),
                      _ARCHIVE_HEADER + "\n".join(moved) + "\n")


def _rewrite(root: str, state: dict) -> None:
    _archive_overflow(root, state)
    text = _read_text(root)
    if text is None:
        init(root)
        text = _read_text(root)
    body = [_format_searched({"change": c, **sw})
            for c, sw in state["searched"].items()]
    body += [_format_reckoning(r) for r in state["reckonings"]]
    body += state["malformed"]
    begin, end = f"<!-- {BLOCK}:BEGIN -->", f"<!-- {BLOCK}:END -->"
    head, _, rest = text.partition(begin)
    _, _, tail = rest.partition(end)
    joined = "\n".join(body) if body else SENTINEL
    _atomic_write(_path(root), f"{head}{begin}\n{joined}\n{end}{tail}")


def _refuse(reason: str) -> dict:
    return {"ok": False, "reason": reason}


_ROW_KEYS = frozenset(("change", "what", "class", "source", "answer",
                       "evidence", "observable", "exercised_by", "because",
                       "when"))
_SEARCHED_KEYS = frozenset(("change", "declared", "name_match", "reading",
                            "person", "name", "when"))


def _date_or_reason(when: str | None) -> tuple[str, str | None]:
    date = when or datetime.date.today().isoformat()
    if not _DATE_RE.match(date):
        return "", f"date must be YYYY-MM-DD, got {date!r}"
    return date, None


def _row_vocab_reason(row: dict) -> str | None:
    if row["answer"] not in ANSWERS:
        return (f"unknown answer {row['answer']!r} — the closed set's single "
                f"home is docs/contracts/reckoning-record.md")
    if row["class"] not in CLASSES:
        return f"class must be one of {'|'.join(CLASSES)}, got {row['class']!r}"
    if row["source"] not in SOURCES:
        return f"source must be one of {'|'.join(SOURCES)}, got {row['source']!r}"
    if not _TOKEN_RE.match(row["change"]):
        return f"change must be a single token, got {row['change']!r}"
    if not row["what"]:
        return "a reckoning names its consumer — what is required"
    if not row["evidence"]:
        return ("a reckoning carries the evidence that its consumer exists — "
                "a reader must be able to open it (FR-104.2)")
    return None


def _clearance_reason(row: dict) -> str | None:
    """AC-104.2, both halves: a bare clearance is refused with the reason;
    an unexercised one resolves to not-proven IN PLACE, flagged on the row."""
    if row["answer"] != "cleared":
        return None
    if not row["observable"]:
        return ("a clearance with no named observable is not a clearance — "
                "it is the untested sentence this record exists to end; name "
                "what would prove it wrong or record not-proven "
                "(FR-104.5, AC-104.2)")
    if not row["exercised_by"]:
        row.update(answer="not-proven", because=NO_EXERCISER,
                   resolved_to="not-proven")
    return None


def _parts_reason(answer: str, row: dict) -> str | None:
    rule = _PARTS[answer]
    for part in rule["required"]:
        if not row[part]:
            return (f"{answer} requires {part.replace('_', '-')} — the "
                    "reason or observable is the answer's substance, not "
                    "decoration (FR-104.4)")
    for part in rule["forbidden"]:
        if row[part]:
            return (f"{part.replace('_', '-')} does not belong on {answer} — "
                    "a category error, refused")
    return None


def record(root: str = ".", row: dict | None = None) -> dict:
    """Upsert one consumer's reckoning — one line per (change, consumer),
    latest call wins. `row` keys are the closed set _ROW_KEYS; the clearance
    rule is enforced HERE, at the only door a line can enter through: no
    observable → refused; an observable with no exerciser → the line lands
    as not-proven, reported in the result, never silent."""
    row = dict(row or {})
    unknown = set(row) - _ROW_KEYS
    if unknown:
        return _refuse(f"unknown field(s) {sorted(unknown)} — the row's "
                       "closed keys live in docs/contracts/reckoning-record.md")
    for key in _ROW_KEYS - {"when"}:
        row[key] = _flat(row.get(key, ""))
    reason = _row_vocab_reason(row) or _clearance_reason(row) \
        or _parts_reason(row["answer"], row)
    if reason:
        return _refuse(reason)
    date, reason = _date_or_reason(row.pop("when", None) or None)
    if reason:
        return _refuse(reason)
    resolved_to = row.pop("resolved_to", None)
    entry = {**{k: (row[k] or None) for k in
                ("observable", "exercised_by", "because")},
             **{k: row[k] for k in
                ("answer", "class", "change", "source", "what", "evidence")},
             "date": date}
    state = read(root)
    state["reckonings"] = [r for r in state["reckonings"]
                           if not (r["change"] == row["change"]
                                   and r["what"] == row["what"])] + [entry]
    _rewrite(root, state)
    out = {"ok": True, "change": row["change"], "what": row["what"],
           "answer": row["answer"]}
    if resolved_to:
        out["resolved_to"] = resolved_to
    return out


def _searched_vocab_reason(spec: dict) -> str | None:
    if not _TOKEN_RE.match(spec["change"]):
        return f"change must be a single token, got {spec['change']!r}"
    if spec["declared"] not in RUN_STATES:
        return f"declared must be one of {'|'.join(RUN_STATES)}"
    if spec["name_match"] not in NAME_MATCH_STATES:
        return f"name-match must be one of {'|'.join(NAME_MATCH_STATES)}"
    if spec["reading"] not in RUN_STATES:
        return f"reading must be one of {'|'.join(RUN_STATES)}"
    if spec["person"] not in PERSON_STATES:
        return (f"person must be one of {'|'.join(PERSON_STATES)} — three "
                "states, never merged (AC-104.5)")
    if not spec["name"]:
        return ("name is required — record what the name search looked for, "
                "or that it was skipped, by name")
    return None


def searched(root: str = ".", spec: dict | None = None) -> dict:
    """Upsert the change's `searched:` line — what ran, what the person
    said, and the derived statement of what could not be covered. One line
    per change, re-derived on every run (FR-104.8). `not_covered` is NOT an
    accepted key — the statement has no door to arrive through (S-104.2)."""
    spec = dict(spec or {})
    unknown = set(spec) - _SEARCHED_KEYS
    if unknown:
        return _refuse(f"unknown field(s) {sorted(unknown)} — not-covered is "
                       "derived from the source states, never accepted "
                       "(S-104.2)")
    for key in _SEARCHED_KEYS - {"when"}:
        spec[key] = _flat(spec.get(key, ""))
    reason = _searched_vocab_reason(spec)
    if reason:
        return _refuse(reason)
    date, reason = _date_or_reason(spec.pop("when", None) or None)
    if reason:
        return _refuse(reason)
    entry = {"date": date, "declared": spec["declared"],
             "name_match": spec["name_match"], "reading": spec["reading"],
             "person": spec["person"], "name": spec["name"],
             "not_covered": _derive_not_covered(spec["declared"],
                                                spec["name_match"],
                                                spec["reading"],
                                                spec["person"])}
    state = read(root)
    state["searched"][spec["change"]] = entry
    _rewrite(root, state)
    return {"ok": True, "change": spec["change"],
            "not_covered": entry["not_covered"]}


def has(root: str = ".", change: str = "") -> dict:
    """Does this change carry any record of having been reconciled? The
    deep-clean catch-up's question (FR-104.9). A `searched:` line with zero
    reckonings counts — the enumeration ran and found nothing, which is a
    record, not an absence."""
    state = read(root)
    count = sum(1 for r in state["reckonings"] if r["change"] == change)
    recorded = count > 0 or change in state["searched"]
    return {"recorded": recorded, "reckonings": count}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record", help="upsert one consumer's reckoning")
    r.add_argument("--change", required=True)
    r.add_argument("--what", required=True)
    r.add_argument("--class", dest="cls", required=True, choices=CLASSES)
    r.add_argument("--from", dest="source", required=True, choices=SOURCES)
    r.add_argument("--answer", required=True)
    r.add_argument("--evidence", required=True)
    r.add_argument("--observable", default="")
    r.add_argument("--exercised-by", dest="exercised_by", default="")
    r.add_argument("--because", default="")
    r.add_argument("--when", default=None, help="date override (default: today)")
    s = sub.add_parser("searched", help="upsert the change's sources line")
    s.add_argument("--change", required=True)
    s.add_argument("--declared", required=True, choices=RUN_STATES)
    s.add_argument("--name-match", dest="name_match", required=True,
                   choices=NAME_MATCH_STATES)
    s.add_argument("--reading", required=True, choices=RUN_STATES)
    s.add_argument("--person", required=True, choices=PERSON_STATES)
    s.add_argument("--name", required=True)
    s.add_argument("--when", default=None, help="date override (default: today)")
    rd = sub.add_parser("read", help="current state, JSON")
    h = sub.add_parser("has", help="does a change carry any reckoning record")
    h.add_argument("--change", required=True)
    sub.add_parser("init", help="write the empty record — nothing reckoned yet")
    args = p.parse_args(argv)
    if args.cmd == "record":
        out = record(args.root, {
            "change": args.change, "what": args.what, "class": args.cls,
            "source": args.source, "answer": args.answer,
            "evidence": args.evidence, "observable": args.observable,
            "exercised_by": args.exercised_by, "because": args.because,
            "when": args.when})
    elif args.cmd == "searched":
        out = searched(args.root, {
            "change": args.change, "declared": args.declared,
            "name_match": args.name_match, "reading": args.reading,
            "person": args.person, "name": args.name, "when": args.when})
    elif args.cmd == "read":
        out = read(args.root)
    elif args.cmd == "has":
        out = has(args.root, args.change)
    else:
        out = init(args.root)
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
