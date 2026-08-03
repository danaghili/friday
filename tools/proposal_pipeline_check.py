#!/usr/bin/env python3
"""Pipeline checker (INC-202: FR-202.6, FR-202.9, AC-202.11) — the ledger
cannot lie.

Six typed finding classes, each grounded in a failure this repo actually
had, none speculative:

  folder-field-disagreement        the file's stage folder and its own header
                                   status differ (PROP-105/107's live shape)
  unparseable-header               a stage resident with no readable fenced
                                   header — post-migration that is breakage
  closed-increment-still-in-progress  a `02-in-progress` proposal whose named
                                   increment has closed — the PROP-200 class.
                                   "Closed" is mechanical: the increment's
                                   change trail exists (the close's artifact)
  folder-bearing-path              a live surface writing a proposal path with
                                   a folder in it — the INC-007/008 dead-
                                   pointer class; D1's enforcement (FR-202.6c)
  retired-folder                   a retired name (open/ shipped/ rejected/
                                   research/) existing at all under proposals/
                                   — the invisible merge-resurrection (KH-5)
  frozen-body-edited               a proposal whose header names an increment
                                   has a body differing from the first
                                   committed version that named it — the D3
                                   freeze line, enforced (AC-202.11). Baseline
                                   is read from git (--follow, so stage moves
                                   don't reset it); no git / never committed
                                   with the field = no baseline = silent skip

Empty cases are VALID (KH-6): no proposals dir, empty stages, a proposal with
no increment field, an increment with no proposal — all clean, never crashes.

Scan boundary for folder-bearing-path: append-only records keep their old
names by doctrine (FR-202.11 — DECISIONS.md + docs/decisions/, trails,
reviews, increments, BUGS, feedback-log, archives) and are excluded, as are
the proposal bodies themselves and `_research` (records, not pointers),
`tests/` (fixtures construct violation specimens on purpose), and derived
build/cache output that is regenerated rather than authored (`node_modules`,
`__pycache__`, `graphify-out` — a frozen snapshot in a cache is nobody's live
surface, D-1008). Everything else that names a stage-bearing proposal path is
a finding.

Blocking is the CALLER's choice: the feature close treats exit 1 as a hard
stop (D8 — a deliberate, recorded departure from fail-open, S-202.5);
reconcile reports and moves on. This tool only states facts. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proposal_pipeline as pp  # noqa: E402

_PATH_RE = re.compile(
    r"proposals/(?:0[1-5]-[a-z-]+|" + "|".join(pp.RETIRED) + r")/PROP-\d+")

_SKIP_DIRS = {".git", ".friday", "node_modules", "__pycache__", ".pytest_cache",
              "tests", "proposals", "decisions", "trails", "reviews",
              "increments", "archive", "graphify-out"}
_SKIP_FILES = {"DECISIONS.md", "BUGS.md", "feedback-log.md"}
_SCAN_EXTS = (".md", ".py", ".json")


def _stage_findings(root: str) -> list[dict]:
    """Classes (a) folder-field-disagreement and unparseable-header, walked
    over every stage resident."""
    findings = []
    for stage in pp.STAGES:
        d = os.path.join(pp.proposals_dir(root), stage)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not (fn.startswith("PROP-") and fn.endswith(".md")):
                continue
            path = os.path.join(d, fn)
            with open(path, encoding="utf-8") as fh:
                header = pp.read_header(fh.read())
            if header is None:
                findings.append({"class": "unparseable-header", "file": path,
                                 "detail": f"{fn} in {stage} has no readable fenced header"})
                continue
            claimed = dict(header["fields"]).get("status", "")
            if claimed != stage:
                findings.append({
                    "class": "folder-field-disagreement", "file": path,
                    "detail": f"{fn} sits in {stage} but its header claims "
                              f"{claimed or '(no status field)'}"})
    return findings


def _closed_increment_findings(root: str) -> list[dict]:
    """Class (b): the PROP-200 replay. The close writes docs/trails/INC-NNN.md;
    a trail existing while the proposal still says in-progress is the drift."""
    findings = []
    d = os.path.join(pp.proposals_dir(root), "02-in-progress")
    if not os.path.isdir(d):
        return findings
    for fn in sorted(os.listdir(d)):
        if not (fn.startswith("PROP-") and fn.endswith(".md")):
            continue
        path = os.path.join(d, fn)
        with open(path, encoding="utf-8") as fh:
            header = pp.read_header(fh.read())
        inc = dict(header["fields"]).get("increment") if header else None
        m = re.fullmatch(r"INC-(\d+)", inc or "")
        if not m:
            continue  # no (parseable) increment link — a defined state, not a finding
        trail = os.path.join(root, "docs", "trails", f"INC-{int(m.group(1)):03d}.md")
        if os.path.isfile(trail):
            findings.append({
                "class": "closed-increment-still-in-progress", "file": path,
                "detail": f"{fn} names {inc}, whose trail exists ({trail}) — "
                          "the build closed and the proposal never moved"})
    return findings


def _folder_path_findings(root: str) -> list[dict]:
    """Class (c): live surfaces writing folder-bearing proposal paths."""
    findings = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fn in sorted(files):
            if not fn.endswith(_SCAN_EXTS) or fn in _SKIP_FILES:
                continue
            path = os.path.join(base, fn)
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except (OSError, UnicodeDecodeError):
                continue
            for hit in sorted(set(_PATH_RE.findall(text))):
                findings.append({
                    "class": "folder-bearing-path", "file": path,
                    "detail": f"writes {hit!r} — refer to proposals by name (D1)"})
    return findings


def _retired_findings(root: str) -> list[dict]:
    """Class (d): a retired folder name existing at all (KH-5), even empty."""
    return [{"class": "retired-folder",
             "file": os.path.join(pp.proposals_dir(root), name),
             "detail": f"retired folder name {name}/ exists under proposals/ — "
                       "a merge resurrected the old layout"}
            for name in pp.RETIRED
            if os.path.isdir(os.path.join(pp.proposals_dir(root), name))]


def _git(root: str, *args: str) -> str | None:
    """Read-only git call; None on ANY failure (no git, no repo, bad object,
    timeout) — the frozen-body class then skips silently. The guard doctrine:
    a checker that cannot see allows; it never invents a finding."""
    try:
        out = subprocess.run(["git", "-C", root, *args],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def _baseline_body(root: str, relpath: str) -> str | None:
    """The body at the FIRST committed version of this proposal whose header
    names an increment — the D3 freeze moment — followed through stage
    renames (--follow, so a correct 02→03 move never resets the freeze).
    None = no baseline: never committed with the field, or no usable
    history."""
    log = _git(root, "log", "--follow", "--format=%H", "--name-only",
               "--", relpath)
    if not log:
        return None
    pairs: list[tuple[str, str]] = []  # newest-first: (sha, path at that sha)
    sha = None
    for line in log.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"[0-9a-f]{40}", line):
            sha = line
        elif sha:
            pairs.append((sha, line))
            sha = None
    for csha, histpath in reversed(pairs):  # oldest first
        text = _git(root, "show", f"{csha}:{histpath}")
        if text is None:
            continue
        header = pp.read_header(text)
        if header and dict(header["fields"]).get("increment"):
            return header["body"]
    return None


def _frozen_body_findings(root: str) -> list[dict]:
    """Class (f) frozen-body-edited: everything below the fence freezes the
    moment the header names an increment (D3, AC-202.11). Header-only edits
    pass by construction — only the body region is compared. A proposal with
    no increment field, no git history, or no committed linked version is a
    defined skip, never a finding."""
    findings = []
    for stage in pp.STAGES:
        d = os.path.join(pp.proposals_dir(root), stage)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not (fn.startswith("PROP-") and fn.endswith(".md")):
                continue
            path = os.path.join(d, fn)
            with open(path, encoding="utf-8") as fh:
                header = pp.read_header(fh.read())
            if not header or not dict(header["fields"]).get("increment"):
                continue
            baseline = _baseline_body(root, os.path.relpath(path, root))
            if baseline is None or header["body"] == baseline:
                continue
            findings.append({
                "class": "frozen-body-edited", "file": path,
                "detail": f"{fn} names its increment, so the region below "
                          "the fence is frozen (D3) — its body differs from "
                          "the first committed version that named the "
                          "increment; corrections belong in the increment "
                          "file or DECISIONS.md, never back-edited"})
    return findings


def check(root: str) -> dict:
    """All six classes over one tree. A tree with no proposals dir at all is
    the valid whole-ledger empty case: clean."""
    findings = (_stage_findings(root) + _closed_increment_findings(root)
                + _folder_path_findings(root) + _retired_findings(root)
                + _frozen_body_findings(root))
    return {"verdict": "clean" if not findings else "findings",
            "findings": findings}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Proposal-pipeline drift checker")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = check(args.root)
    if args.json:
        print(json.dumps(res, indent=None))
    else:
        print(res["verdict"] + "".join(
            f"\n  [{f['class']}] {f['detail']}" for f in res["findings"]))
    return 0 if res["verdict"] == "clean" else 1


if __name__ == "__main__":
    raise SystemExit(main())
