#!/usr/bin/env python3
"""The conformance sweep — mechanical full recall over the rules a project
wrote down and the baseline invariants nobody writes down (INC-105
FR-105.5, FR-105.8, FR-105.9; D5, D9, D11).

Layer-1 of the measure-judge-answer pattern, rebuilt as a SIBLING of the
maintainability measurer (D9 — INC-207 D12's out-of-scope stance on that
file governs and is cited, not restated): the measurer reads Python syntax
trees; this reads text and the extracted graph, so it runs on projects in
languages the measurer never parses. It counts and never judges — every
finding goes to the judge's conformance worklist for its written answer
(FR-105.7), and nothing here blocks anything anywhere (S-105.1, D6).

- **Checks** come from the project's own FRIDAY-CONFORMANCE block
  (`tools/conformance_checks.py` — the one reader). `forbid`: every match
  is a finding. `require`: every scope file lacking the pattern is a
  finding. `cycle`: `tools/import_cycles.py` walks the extracted graph.
- **Baseline invariants** come from friday's shipped catalog
  (`docs/conformance-baseline.md`, FRIDAY-BASELINE block): each carries the
  condition that switches it on (D5 — `always`, `exists: <globs>`, or
  `found: <regex>`; exact, never a similarity judgement) and its provenance
  mark (D4's honest tail). A self-switched-off rule is NAMED in the report
  every time and is not by itself a stain — correct non-engagement is not a
  silence about something owed; the silences that dirty the verdict are the
  ones below.
- **The three silences are named, never absorbed (S-105.2, KH-2):**
  found-not-checked (an `unchecked` line), switched-off-here, and
  out-of-reach (a cycle check with no extracted graph — INC-207 D1's reach,
  cited). An unreadable file is unread; a malformed or invalid check is
  could-not-run WITH its reason; an orphaned check still runs and is named.
- **Findings carry the rule and the location, never the line's value
  (S-105.4, KH-5):** path and line number only — the search reads exactly
  the lines credentials sit on, and nothing here reproduces one.
- The check lines' own home is cut from matching (a whole-tree forbid would
  otherwise convict its own definition), the same self-exclusion the anchor
  search makes.

Exit 0 whatever it finds. Contract: `docs/contracts/conformance-envelope.md`.
Pure stdlib.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conformance_checks as cc  # noqa: E402
import friday_substrate as fs  # noqa: E402
import import_cycles  # noqa: E402
import taglines  # noqa: E402

BASELINE_BLOCK = "FRIDAY-BASELINE"
BASELINE_KINDS = ("forbid", "require", "cycle")
_DEFAULT = object()
_DEFAULT_BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "docs", "conformance-baseline.md")
_SKIP_DIRS = {".git", ".friday", "node_modules", "__pycache__", ".venv",
              "venv", ".pytest_cache", ".ruff_cache", "dist", "build"}
# An archive keeps what it was written with (D7) — a finding there can never
# be fixed, so sweeping it manufactures permanent ceremony for the judge.
_ARCHIVE_DIR = "docs/archive"


def _gitignored(root: str, paths: list[str]) -> set[str]:
    """The subset of `paths` the project's own .gitignore excludes — the
    project declaring 'not part of me' (the D-1075 pattern; a derived cache
    rebuilt mid-run moved a baseline count 14 with zero source change). No
    git, or git unavailable: nothing is excluded (the plain walk stands)."""
    if not paths:
        return set()
    try:
        proc = subprocess.run(
            ["git", "-C", root, "check-ignore", "--stdin", "-z"],
            input="\0".join(paths) + "\0", capture_output=True, text=True,
            timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return {p for p in proc.stdout.split("\0") if p}


def _walk_files(top: str) -> tuple[list[str], list[str]]:
    files: list[str] = []
    unread: list[str] = []
    for dirpath, dirnames, filenames in os.walk(top):
        reld = os.path.relpath(dirpath, top).replace(os.sep, "/")
        reld = "" if reld == "." else reld
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in _SKIP_DIRS
            and (f"{reld}/{d}" if reld else d) != _ARCHIVE_DIR)
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, top).replace(os.sep, "/")
            if not os.access(full, os.R_OK):
                unread.append(rel)
                continue
            files.append(rel)
    ignored = _gitignored(top, files)
    if ignored:
        files = [f for f in files if f not in ignored]
    return files, unread


class _Lines:
    """Per-file line cache. The standards file's own conformance block is
    blanked before matching — a check must never convict its own line."""

    def __init__(self, top: str):
        self.top = top
        self.cache: dict[str, list[str] | None] = {}
        self.unread: list[str] = []

    def get(self, rel: str) -> list[str] | None:
        if rel in self.cache:
            return self.cache[rel]
        try:
            with open(os.path.join(self.top, rel), encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            self.cache[rel] = None
            self.unread.append(rel)
            return None
        if "\0" in text[:1024]:
            self.cache[rel] = None
            return None
        # A check line or a catalog line carries its own pattern's text —
        # both typed blocks are blanked wherever they appear, so no check
        # convicts its own definition and no switch-on condition engages
        # against the catalog that declares it.
        for block in (cc.BLOCK, BASELINE_BLOCK):
            if f"<!-- {block}:BEGIN -->" in text:
                text = _blank_block(text, block)
        lines = text.splitlines()
        self.cache[rel] = lines
        return lines


def _blank_block(text: str, block: str) -> str:
    begin, end = f"<!-- {block}:BEGIN -->", f"<!-- {block}:END -->"
    if begin not in text or end not in text:
        return text
    head, _, rest = text.partition(begin)
    inside, _, tail = rest.partition(end)
    return head + "\n" * inside.count("\n") + tail


def _in_scope(rel: str, scope: str | None) -> bool:
    if not scope:
        return True
    return any(fnmatch.fnmatch(rel, g.strip())
               for g in scope.split(",") if g.strip())


def _excepted(rel: str, excepts: list[str]) -> bool:
    base = rel.split("/")[-1]
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(base, p)
               for p in excepts)


def _scan(check: dict, files: list[str], lines: _Lines,
          extra: dict) -> tuple[list[dict], int]:
    """forbid/require over the walked tree. Findings carry path and line
    number only — never the matched line's content (S-105.4)."""
    try:
        rx = re.compile(check["pattern"])
    except re.error as err:
        raise ValueError(f"pattern does not compile: {err}") from err
    findings: list[dict] = []
    refusals: list[dict] = []
    checked = 0
    for rel in files:
        if not _in_scope(rel, check.get("scope")) \
                or _excepted(rel, check.get("excepts") or []):
            continue
        content = lines.get(rel)
        if content is None:
            continue
        checked += 1
        matches = [i for i, ln in enumerate(content, 1) if rx.search(ln)]
        if check["kind"] == "forbid":
            findings += [{"check": check["id"], "rule": check["rule"],
                          "path": rel, "line": i, **extra} for i in matches]
            refusals += [_infile_refusal(rel, i) for i in matches
                         if "conformance-except" in content[i - 1]]
        elif not matches:
            findings.append({"check": check["id"], "rule": check["rule"],
                             "path": rel, "line": None, **extra})
            refusals += [_infile_refusal(rel, i)
                         for i, ln in enumerate(content, 1)
                         if "conformance-except" in ln]
    return findings, checked, refusals


def _infile_refusal(rel: str, line: int) -> dict:
    """OQ-105.6, resolved refuse-side: an in-file exception is named and
    never honoured — scattering exceptions across the tree is the disease
    the single home exists to end (FR-105.9, FB-06's residue)."""
    return {"value": f"in-file conformance-except at {rel}:{line}",
            "reason": "an in-file exception is refused by name — exceptions "
                      "are pattern-shaped and live on the check line, their "
                      "single home (FR-105.9, OQ-105.6)"}


def _run_cycle(root: str, check: dict, extra: dict,
               report: dict) -> tuple[list[dict], int]:
    out = import_cycles.walk(root)
    if out["outcome"] == "out-of-reach":
        report["out_of_reach"].append({"id": check["id"],
                                       "rule": check["rule"],
                                       "reason": out["reason"]})
        return [], 0
    findings = [{"check": check["id"], "rule": check["rule"],
                 "cycle": cycle, **extra} for cycle in out["cycles"]]
    return findings, len(out["cycles"])


def _run_check(root: str, check: dict, files: list[str], lines: _Lines,
               report: dict, extra: dict | None = None) -> None:
    extra = extra or {"source": "declared"}
    if check["kind"] == "unchecked":
        report["found_not_checked"].append(
            {"id": check["id"], "rule": check["rule"],
             "from": check["from"]})
        return
    try:
        if check["kind"] == "cycle":
            findings, checked = _run_cycle(root, check, extra, report)
        else:
            findings, checked, refusals = _scan(check, files, lines, extra)
            report["refused_excepts"] += refusals
    except ValueError as err:
        report["could_not_run"].append({"id": check["id"], "reason": str(err)})
        return
    for f in findings:
        f["fingerprint"] = check.get("fingerprint")
    report["findings"] += findings
    if not findings and not (check["kind"] == "cycle"
                             and report["out_of_reach"]
                             and report["out_of_reach"][-1]["id"]
                             == check["id"]):
        report["clean_checks"].append({"id": check["id"],
                                       "kind": check["kind"],
                                       "files_checked": checked,
                                       "fingerprint":
                                           check.get("fingerprint", "")})


def _parse_baseline_line(value: str) -> dict | None:
    rest, pattern = cc._peel(value, "pattern")
    rest, scope = cc._peel(rest, "scope")
    rest, provenance = cc._peel(rest, "provenance")
    rest, when = cc._peel(rest, "when")
    head, rule = cc._peel(rest, "rule")
    parts = head.split(" ")
    if (len(parts) != 2 or parts[1] not in BASELINE_KINDS or rule is None
            or when is None or provenance is None
            or not provenance.split(" — ")[0] in ("scarred", "unscarred")):
        return None
    return {"id": parts[0], "kind": parts[1], "rule": rule, "when": when,
            "provenance": provenance, "scope": scope, "pattern": pattern,
            "excepts": [], "from": "conformance-baseline.md"}


def _engaged(when: str, files: list[str], lines: _Lines) -> bool | None:
    """D5's switch-on condition — exact, mechanical, closed vocabulary."""
    if when == "always":
        return True
    if when.startswith("exists: "):
        globs = [g.strip() for g in when[8:].split(",") if g.strip()]
        return any(fnmatch.fnmatch(rel, g) or
                   fnmatch.fnmatch(rel.split("/")[-1], g)
                   for rel in files for g in globs)
    if when.startswith("found: "):
        try:
            rx = re.compile(when[7:])
        except re.error:
            return None
        return any((content := lines.get(rel)) and
                   any(rx.search(ln) for ln in content) for rel in files)
    return None


def _run_baselines(root: str, path: str, files: list[str], lines: _Lines,
                   report: dict) -> None:
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        report["could_not_run"].append(
            {"id": "baseline-catalog",
             "reason": f"baseline catalog absent at {path} — the seeded "
                       "invariants could not be evaluated"})
        return
    block = taglines.block_lines(text, BASELINE_BLOCK)
    for line in block or []:
        parsed = taglines.parse_typed_line(line)
        inv = (_parse_baseline_line(parsed[1])
               if parsed and parsed[0] == "baseline" else None)
        if inv is None:
            if line.strip() and not line.startswith("_"):
                report["could_not_run"].append(
                    {"id": "baseline", "reason": f"malformed line: {line}"})
            continue
        engaged = _engaged(inv["when"], files, lines)
        if engaged is None:
            report["could_not_run"].append(
                {"id": inv["id"],
                 "reason": f"switch-on condition unreadable: {inv['when']}"})
        elif engaged:
            _run_check(root, inv, files, lines, report,
                       extra={"source": "baseline",
                              "provenance": inv["provenance"]})
        else:
            report["switched_off"].append({"id": inv["id"],
                                           "rule": inv["rule"],
                                           "condition": inv["when"]})


def sweep(root: str = ".", baseline_path=_DEFAULT) -> dict:
    """One full sweep: every written check, every switched-on invariant,
    every silence named. Report-only — the verdict is honest, the exit is 0."""
    top = fs.resolve_worktree_root(root)
    home = cc.read(root)
    files, unreadable = _walk_files(top)
    lines = _Lines(top)
    report: dict = {"checks_home": home["status"], "findings": [],
                    "clean_checks": [], "found_not_checked": [],
                    "switched_off": [], "out_of_reach": [],
                    "could_not_run": [], "orphaned": [],
                    "refused_excepts": [], "unread": list(unreadable)}
    for entry in home["malformed"]:
        report["could_not_run"].append({"id": "-",
                                        "reason": f"malformed line: {entry}"})
    for check in home["checks"]:
        if check["orphaned"]:
            report["orphaned"].append({"id": check["id"],
                                       "reason": check["orphaned"]})
        report["refused_excepts"] += check["refused_excepts"]
        if check["invalid"]:
            report["could_not_run"].append({"id": check["id"],
                                            "reason": check["invalid"]})
            continue
        _run_check(root, check, files, lines, report)
    if baseline_path is not _DEFAULT and baseline_path is None:
        pass
    else:
        path = (os.path.normpath(_DEFAULT_BASELINE)
                if baseline_path is _DEFAULT else baseline_path)
        _run_baselines(root, path, files, lines, report)
    report["unread"] = sorted(set(report["unread"]) | set(lines.unread))
    dirty = (report["findings"] or report["found_not_checked"]
             or report["out_of_reach"] or report["could_not_run"]
             or report["unread"] or report["orphaned"]
             or home["status"] == "absent")
    report["verdict"] = "not-clean" if dirty else "clean"
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", default=".")
    p.add_argument("--baseline", default=None,
                   help="override the shipped baseline catalog path")
    p.add_argument("--no-baseline", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    baseline = (None if args.no_baseline
                else (args.baseline if args.baseline else _DEFAULT))
    out = sweep(args.root, baseline_path=baseline)
    if args.json:
        print(json.dumps(out, indent=2))
        return 0
    print(f"conformance: {out['verdict']} — "
          f"{len(out['findings'])} finding(s), "
          f"{len(out['clean_checks'])} clean check(s), "
          f"{len(out['found_not_checked'])} found-not-checked, "
          f"{len(out['switched_off'])} switched-off, "
          f"{len(out['out_of_reach'])} out-of-reach, "
          f"{len(out['could_not_run'])} could-not-run, "
          f"{len(out['unread'])} unread")
    for f in out["findings"]:
        where = f.get("cycle", {}).get("modules") or \
            f"{f['path']}:{f['line']}" if f.get("line") else f.get("path")
        print(f"  {f['check']}: {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
