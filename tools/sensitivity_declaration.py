#!/usr/bin/env python3
"""The sensitivity declaration — one record something actually opens (INC-108).

The specimen this answers is not an unasked question. The audited project
classified its health data correctly, in plain English, at the top of the
schema file — and the label changed nothing, because no run-moment reads a
source comment; and its decision record and its privacy statement disagreed
about backups for the store's whole life without ever meeting. So this
module OWNS `docs/SENSITIVITY.md` (the D-0135 pattern): the durable,
committed record of what a project holds, opened by the deep clean's
read-back and carried by the client handover.

**The treatment set is CLOSED and silence is not in the vocabulary** (D1,
FR-108.2): every declared store answers every treatment, or answers
`not-applicable — <reason>`; a blank is a finding on the store, and prose
that considers an area without answering it is the reading's job to convict
(AC-108.3). The set's defining home is the contract
(`docs/contracts/sensitivity-declaration.md`); the member keys here are the
mechanical half of that contract.

**The floor behaves as a floor** (D2): the named classes are a minimum, and
a store holding something the list does not name declares with the class
the project names for it — `unclassified` is not an outcome this module can
produce.

**A shared copy is answered once** (D7, KH-4): project-level copy artefacts
and their lifetimes live in one section; a store's copies answer cites
`project-copies`; a store-level answer that NAMES a project artefact is
refused at declare time — a restatement is the drift the audited project's
one-dump-many-tables shape invites.

**The declaration is a LIVING record keyed by the store's own name**
(OQ-108.4): re-declaring a store updates it — a changed answer is the same
store with a new date, unlike INC-107's answered set where an edited
comment is a new decision. The two quarries genuinely differ: a deferral is
an utterance, a store is a thing.

**Nothing here reads data** (S-108.3): this module takes names, shapes and
postures as arguments and opens no file but its own record. It reports and
never blocks (S-108.1); its non-zero exit gates only friday's own machinery
(S-108.6). Pure stdlib.
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

BLOCK = "FRIDAY-SENSITIVITY"
COPIES_BLOCK = "FRIDAY-SENSITIVITY-COPIES"
# FR-108.3's six, each one a sentence in the contract; these keys are the
# mechanical spellings. Closed both ways: all present, none invented.
TREATMENTS = ("at-rest", "copies", "deletion", "reach", "basis", "told")
# FR-108.1's floor — a minimum, never a catalogue; a project-named class
# outside this list declares exactly like a listed one (D2).
FLOOR = ("health", "special-category", "credentials", "payment-instruments",
         "childrens-data")
_NA_RE = re.compile(r"^not-applicable\s*(?:[—–-]\s*(.*))?$", re.S)
_STORE_RE = re.compile(r"^[A-Za-z0-9_.\-/]+$")
_NONE_RE = re.compile(r"^none — (.+?) · declared: (\d{4}-\d{2}-\d{2})$", re.S)

HEADER = """# Sensitivity declarations (INC-108)

What this project holds that lands inside the sensitivity floor, one typed
line per store, with every treatment answered — written by
`tools/sensitivity_declaration.py` only, read back against reality at every
deep clean, carried by the client handover. Contract:
`docs/contracts/sensitivity-declaration.md`.

<!-- FRIDAY-SENSITIVITY:BEGIN -->
{body}
<!-- FRIDAY-SENSITIVITY:END -->

## Project copies (answered once, cited by every store — D7)

<!-- FRIDAY-SENSITIVITY-COPIES:BEGIN -->
{copies}
<!-- FRIDAY-SENSITIVITY-COPIES:END -->
"""


def _path(root: str) -> str:
    return os.path.join(fs.resolve_worktree_root(root), "docs", "SENSITIVITY.md")


def _read(root: str) -> str | None:
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


def _answers_block(store: str) -> str:
    return f"FRIDAY-SENSITIVITY-ANSWERS-{store}"


def _splice(text: str, block: str, body_lines: list[str], sentinel: str = "") -> str:
    begin, end = f"<!-- {block}:BEGIN -->", f"<!-- {block}:END -->"
    head, _, rest = text.partition(begin)
    _, _, tail = rest.partition(end)
    body = "\n".join(body_lines) if body_lines else sentinel
    return f"{head}{begin}\n{body}\n{end}{tail}"


def _validate_answers(answers: dict, project_artefacts: list[str]) -> str | None:
    """Every treatment present and answered; n/a carries its reason; a
    store-level copies answer never restates a project artefact. Returns the
    refusal detail, or None when valid."""
    unknown = sorted(set(answers) - set(TREATMENTS))
    if unknown:
        return (f"unknown treatment(s) {', '.join(unknown)} — the set is "
                f"closed: {', '.join(TREATMENTS)}")
    for key in TREATMENTS:
        val = " ".join((answers.get(key) or "").split())
        if not val:
            return (f"treatment '{key}' is blank — every treatment returns an "
                    "answer or an explicit not-applicable with its reason "
                    "(FR-108.2; silence is not in the vocabulary)")
        m = _NA_RE.match(val)
        if m and not (m.group(1) or "").strip():
            return (f"treatment '{key}' says not-applicable with no reason — "
                    "a not-applicable nobody justified is a blank wearing a "
                    "vocabulary word")
    copies_val = " ".join(answers.get("copies", "").split())
    for art in project_artefacts:
        if art in copies_val:
            return (f"the copies answer names the project-level artefact "
                    f"'{art}' — cite project-copies instead; a restated "
                    "lifetime is the drift D7 exists to prevent (KH-4)")
    return None


def project_copies(root: str = ".") -> list[dict]:
    text = _read(root)
    if text is None:
        return []
    out = []
    for ln in taglines.block_lines(text, COPIES_BLOCK) or []:
        parsed = taglines.parse_typed_line(ln)
        if not parsed or parsed[0] != "copy":
            continue
        head, sep, rest = parsed[1].partition(" · lifetime: ")
        life, _, decl = rest.partition(" · declared: ")
        if not sep or not life.strip():
            out.append({"malformed": True, "raw": ln})
            continue
        out.append({"malformed": False, "artefact": head.strip(),
                    "lifetime": life.strip(), "declared": decl.strip()})
    return out


def set_project_copies(root: str = ".", copies: list[dict] | None = None, *,
                       when: str | None = None) -> dict:
    """The project-level copy artefacts and their lifetimes, answered ONCE."""
    date = when or datetime.date.today().isoformat()
    text = _ensure(root)
    lines = [f"copy: {c['artefact']} · lifetime: {c['lifetime']} · declared: {date}"
             for c in (copies or [])]
    _atomic_write(_path(root), _splice(text, COPIES_BLOCK, lines,
                                       sentinel="_No project-level copy artefacts declared._"))
    return {"ok": True, "count": len(lines)}


def _ensure(root: str) -> str:
    text = _read(root)
    if text is None:
        os.makedirs(os.path.dirname(_path(root)), exist_ok=True)
        text = HEADER.format(body="_Never declared._",
                             copies="_No project-level copy artefacts declared._")
        _atomic_write(_path(root), text)
    return text


def declare(root: str = ".", *, store: str, store_class: str, answers: dict,
            requirements: list[str], when: str | None = None) -> dict:
    """Declare one sensitive store — or update it (a living record, keyed by
    the store's own name). Refuses a blank, an unreasoned n/a, an unknown
    treatment, and a restated project artefact; nothing lands on refusal."""
    if not _STORE_RE.match(store or ""):
        return {"ok": False, "detail": f"store name {store!r} — use the "
                                       "project's own identifier for it"}
    if not (store_class or "").strip():
        return {"ok": False, "detail": "class must be non-empty — the floor is "
                                       "a floor: name the project's own class "
                                       "when the list does not carry one (D2)"}
    arts = [c["artefact"] for c in project_copies(root) if not c["malformed"]]
    problem = _validate_answers(answers or {}, arts)
    if problem:
        return {"ok": False, "detail": problem}
    date = when or datetime.date.today().isoformat()
    req = ",".join(requirements) if requirements else "none"
    line = (f"sensitive-store: {store} · class: {store_class} · "
            f"declared: {date} · requirements: {req}")

    text = _upsert_store_line(_ensure(root), store, line)
    text = _upsert_answers_block(text, store, answers)
    _atomic_write(_path(root), text)
    return {"ok": True, "store": store, "date": date}


def _upsert_store_line(text: str, store: str, line: str) -> str:
    kept = []
    for ln in taglines.block_lines(text, BLOCK) or []:
        if ln.startswith("_") or ln.startswith("sensitive-stores:"):
            continue  # the sentinel / the none-line yield to a real store
        parsed = taglines.parse_typed_line(ln)
        entry = _parse_line(parsed[1]) if parsed and parsed[0] == "sensitive-store" else None
        if entry and not entry["malformed"] and entry["store"] == store:
            continue  # updating: the new line replaces this store's old one
        kept.append(ln)
    return _splice(text, BLOCK, kept + [line])


def _upsert_answers_block(text: str, store: str, answers: dict) -> str:
    ab = _answers_block(store)
    begin = f"<!-- {ab}:BEGIN -->"
    body = [f"{k}: {' '.join(answers[k].split())}" for k in TREATMENTS]
    if begin in text:
        return _splice(text, ab, body)
    return (text.rstrip() + "\n\n"
            + f"## {store} — treatment answers\n\n"
            + f"{begin}\n" + "\n".join(body) + f"\n<!-- {ab}:END -->\n")


def declare_none(root: str = ".", *, reason: str, when: str | None = None) -> dict:
    """FR-108.12/D12: a project with no sensitive store writes that down —
    dated, reasoned, distinct from both absent and clean-by-silence."""
    reason = " ".join((reason or "").split())
    if not reason:
        return {"ok": False, "detail": "the empty case carries its reason — "
                                       "'nothing declared' with no why is "
                                       "indistinguishable from never-asked"}
    date = when or datetime.date.today().isoformat()
    text = _ensure(root)
    if any(not e["malformed"] for e in entries(root)):
        return {"ok": False, "detail": "stores are declared — the none-line "
                                       "and store lines cannot coexist"}
    _atomic_write(_path(root), _splice(
        text, BLOCK, [f"sensitive-stores: none — {reason} · declared: {date}"]))
    return {"ok": True, "date": date}


def _parse_line(value: str) -> dict:
    parts = value.split(" · ")
    fields = {}
    head = parts[0].strip()
    for part in parts[1:]:
        k, _, v = part.partition(": ")
        fields[k.strip()] = v.strip()
    if not head or "class" not in fields or "declared" not in fields:
        return {"malformed": True, "raw": f"sensitive-store: {value}"}
    req = fields.get("requirements", "none")
    return {"malformed": False, "store": head, "class": fields["class"],
            "date": fields["declared"],
            "requirements": [] if req == "none" else [r.strip() for r in req.split(",")],
            "raw": f"sensitive-store: {value}"}


def entries(root: str = ".") -> list[dict]:
    """Every declared store with its answers, malformed lines kept+flagged."""
    text = _read(root)
    if text is None:
        return []
    out = []
    for ln in taglines.block_lines(text, BLOCK) or []:
        if ln.startswith("_") or ln.startswith("sensitive-stores:"):
            continue
        parsed = taglines.parse_typed_line(ln)
        if not parsed or parsed[0] != "sensitive-store":
            continue
        entry = _parse_line(parsed[1])
        if not entry["malformed"]:
            answers = taglines.block_typed(text, _answers_block(entry["store"])) or {}
            entry["answers"] = {k: v[0] for k, v in answers.items()}
        out.append(entry)
    return out


def _none_line(root: str) -> dict | None:
    text = _read(root)
    if text is None:
        return None
    for ln in taglines.block_lines(text, BLOCK) or []:
        parsed = taglines.parse_typed_line(ln)
        if parsed and parsed[0] == "sensitive-stores":
            m = _NONE_RE.match(parsed[1])
            if m:
                return {"reason": m.group(1), "date": m.group(2)}
    return None


def check(root: str = ".") -> dict:
    """The record's own well-formedness: every store answers every treatment
    (the file is hand-editable after declare, so this re-verifies), the
    empty case distinct from absent. Reports, never blocks (S-108.1) — the
    read-back against REALITY is the deep clean's model half, not this."""
    findings: list[dict] = []
    text = _read(root)
    if text is None:
        return {"clean": False, "empty": False, "findings": [
            {"kind": "never-declared",
             "detail": "no docs/SENSITIVITY.md — the question was never "
                       "answered; a project with nothing to declare declares "
                       "that (FR-108.5)"}]}
    all_entries = entries(root)
    none_line = _none_line(root)
    if not all_entries and none_line:
        return {"clean": True, "empty": True, "findings": [],
                "none": none_line}
    if not all_entries and not none_line:
        findings.append({"kind": "never-declared",
                         "detail": "the block carries neither store lines nor "
                                   "the dated none-line"})
    copies = project_copies(root)
    for c in copies:
        if c["malformed"]:
            findings.append({"kind": "malformed-copy", "store": None,
                             "detail": "copy artefact kept but not enumerable: "
                                       f"{c['raw']!r} — a copy the parser "
                                       "cannot read is named, never ignored "
                                       "(FR-108.13)"})
    arts = [c["artefact"] for c in copies if not c["malformed"]]
    for e in all_entries:
        findings.extend(_entry_findings(e, arts))
    return {"clean": not findings, "empty": False, "findings": findings}


def _entry_findings(e: dict, arts: list[str]) -> list[dict]:
    if e["malformed"]:
        return [{"kind": "malformed", "store": None,
                 "detail": f"unparseable line kept: {e['raw']!r}"}]
    findings = []
    answers = e.get("answers", {})
    for key in TREATMENTS:
        val = " ".join((answers.get(key) or "").split())
        m = _NA_RE.match(val) if val else None
        if not val or (m and not (m.group(1) or "").strip()):
            findings.append({"kind": "blank-treatment", "store": e["store"],
                             "treatment": key,
                             "detail": f"{e['store']}: treatment '{key}' "
                                       "has no answer — a blank is a "
                                       "finding, never clean (FR-108.2)"})
    copies_val = answers.get("copies", "")
    for art in arts:
        if art in copies_val:
            findings.append({"kind": "restated-copy", "store": e["store"],
                             "treatment": "copies",
                             "detail": f"{e['store']} restates project "
                                       f"artefact '{art}' — must cite "
                                       "project-copies (D7)"})
    return findings


def requirements_check(root: str = ".", *, oracles: list[str]) -> dict:
    """FR-108.4 (make-or-break) both ways: every listed requirement id exists
    in a real oracle (a dangling pointer reads as covered and is worse than
    none), and a store whose answers carry postures but whose line lists no
    requirement is INCOMPLETE by default — the schema-comment failure named
    at the moment it is cheapest to fix. Whether one answer is a posture is
    the model's judgement; the mechanical default is loud, and the one quiet
    case is a store answered not-applicable throughout. An oracle that could
    not be read is named, never folded into clean (S-108.2)."""
    findings: list[dict] = []
    oracle_text = ""
    for path in oracles:
        try:
            with open(path, encoding="utf-8") as fh:
                oracle_text += fh.read() + "\n"
        except OSError as exc:
            findings.append({"kind": "unread-oracle", "store": None,
                             "detail": f"oracle {path} unreadable ({exc}) — "
                                       "ids in it cannot be confirmed"})
    for e in entries(root):
        if e["malformed"]:
            continue
        for rid in e["requirements"]:
            if rid not in oracle_text:
                findings.append({"kind": "dangling-requirement",
                                 "store": e["store"],
                                 "detail": f"{e['store']} points at {rid} and "
                                           "no oracle carries it — a pointer "
                                           "into nothing reads as covered"})
        if not e["requirements"]:
            answers = e.get("answers", {})
            all_na = answers and all(
                _NA_RE.match(" ".join((answers.get(k) or "").split()) or "")
                for k in TREATMENTS)
            if not all_na:
                findings.append({"kind": "declaration-only", "store": e["store"],
                                 "detail": f"{e['store']} carries answers and "
                                           "no requirement id — the answer "
                                           "landed only in the declaration "
                                           "(FR-108.4, KH-2); missing: the "
                                           "FR/S line in the oracle being "
                                           "authored"})
    return {"clean": not findings, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="The sensitivity declaration "
                                             "(INC-108) — declare, list, check")
    sub = ap.add_subparsers(dest="verb", required=True)
    d = sub.add_parser("declare", help="declare or update one sensitive store")
    d.add_argument("--root", default=".")
    d.add_argument("--store", required=True)
    d.add_argument("--class", dest="store_class", required=True)
    d.add_argument("--requirements", default="",
                   help="comma-separated FR/S ids the answers produced")
    for t in TREATMENTS:
        d.add_argument(f"--{t}", required=True, dest=t.replace("-", "_"))
    d.add_argument("--when", default=None)
    n = sub.add_parser("declare-none", help="the dated empty case (D12)")
    n.add_argument("--root", default=".")
    n.add_argument("--reason", required=True)
    n.add_argument("--when", default=None)
    ls = sub.add_parser("list", help="every declaration, JSON")
    ls.add_argument("--root", default=".")
    c = sub.add_parser("check", help="record well-formedness; reports, never blocks")
    c.add_argument("--root", default=".")
    c.add_argument("--json", action="store_true")
    rq = sub.add_parser("requirements-check",
                        help="FR-108.4: listed ids exist in an oracle; "
                             "declaration-only stores reported incomplete")
    rq.add_argument("--root", default=".")
    rq.add_argument("--oracle", action="append", required=True,
                    help="oracle file to search (repeatable)")
    args = ap.parse_args(argv)
    if args.verb == "requirements-check":
        res = requirements_check(args.root, oracles=args.oracle)
        print(json.dumps(res))
        return 0 if res["clean"] else 1
    if args.verb == "declare":
        answers = {t: getattr(args, t.replace("-", "_")) for t in TREATMENTS}
        reqs = [r.strip() for r in args.requirements.split(",") if r.strip()]
        res = declare(args.root, store=args.store, store_class=args.store_class,
                      answers=answers, requirements=reqs, when=args.when)
        print(json.dumps(res))
        return 0 if res["ok"] else 1
    if args.verb == "declare-none":
        res = declare_none(args.root, reason=args.reason, when=args.when)
        print(json.dumps(res))
        return 0 if res["ok"] else 1
    if args.verb == "list":
        print(json.dumps({"entries": entries(args.root)}))
        return 0
    res = check(args.root)
    print(json.dumps(res) if args.json else
          ("sensitivity: clean" if res["clean"] else
           "sensitivity: %d finding(s)" % len(res["findings"])))
    return 0 if res["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
