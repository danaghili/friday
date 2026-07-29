#!/usr/bin/env python3
"""INC-008 layer 1 — the mechanical maintainability measurer (FR-8.2).

Deterministic, content-independent counters for the solid three metrics the gate
trusts, stdlib-only for the Python case (`ast` + `tokenize`) — no runtime
dependency, honouring friday's stdlib-only non-goal while still measuring real
code:

  - complexity  : McCabe cyclomatic complexity, per function (1 + decision points).
  - size        : file LOC · function length (physical span) · parameter count ·
                  nesting depth.
  - duplication : token-run clones across files (KH-4 — a rolling-window match
                  over a normalised token stream; proven to really fire, never
                  assumed).

100% recall on the objective metrics is the point: a countable breach cannot hide
from the scan (the maintenance philosophy's guarantee, FR-8.11). The SAME path
re-measures a fix — `breaches()` after a fix must return the location strictly
under its bar (the fix-verifier, Pin #2 / AC-8.2).

This tool MEASURES and reports breaches against a project's declared bars; it
never judges (that is the agent, layer 2) and never blocks (that is the hook,
layer 3). Pure stdlib. Exit 0 always — measurement is a report, not a gate.
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import os
import sys
import tokenize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

# Function-level metrics vs the whole-file / whole-tree ones.
FUNC_METRICS = ("complexity", "function-size", "param-count", "nesting-depth")

# Dirs we never measure — vendored, generated, VCS internals, or docs (shipping
# source does not live under docs/; a project's docs/archive of frozen historical
# scripts is not governed code — mirrors verify_claims' own walk exclusion).
_EXCLUDED_WALK = {".git", "node_modules", ".friday", "dist", "build",
                  "__pycache__", ".venv", "venv", "docs"}

# Compound statements that add a nesting level.
_BLOCKS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)
_FUNC_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef)


# --- complexity (McCabe) -------------------------------------------------------

def _own_descendants(node):
    """Every descendant of `node` that belongs to THIS function — i.e. not inside
    a nested function definition (which is measured as its own function)."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _FUNC_DEFS):
            continue
        yield child
        yield from _own_descendants(child)


def cyclomatic(func_node) -> int:
    """McCabe cyclomatic complexity of one function: 1 + the number of decision
    points (if / elif / for / while / except / boolean-operator / comprehension-if
    / ternary). Nested function bodies are excluded (each is its own function)."""
    count = 1
    for node in _own_descendants(func_node):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While,
                             ast.ExceptHandler, ast.IfExp)):
            count += 1
        elif isinstance(node, ast.BoolOp):
            count += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            count += len(node.ifs)
    return count


def _nesting_depth(node, depth: int = 0) -> int:
    """Deepest nesting of compound blocks inside a function body (a first-level
    if/for/while/with/try is depth 1). Nested function defs are not descended into.
    NOTE: an `elif` is an If in the orelse, so a long elif chain reads as extra
    depth — a known rough edge of this metric, accepted (bars are tunable, and the
    gate is warn-first)."""
    best = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _FUNC_DEFS):
            continue
        nxt = depth + 1 if isinstance(child, _BLOCKS) else depth
        best = max(best, _nesting_depth(child, nxt))
    return best


def _param_count(func_node) -> int:
    a = func_node.args
    n = len(a.posonlyargs) + len(a.args) + len(a.kwonlyargs)
    if a.vararg:
        n += 1
    if a.kwarg:
        n += 1
    return n


# --- size ----------------------------------------------------------------------

def _file_loc(src: str) -> int:
    """Lines of code: non-blank lines that are not comment-only. A deliberately
    simple, content-independent count (not a full docstring stripper)."""
    loc = 0
    for line in src.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            loc += 1
    return loc


# --- per-source measurement ----------------------------------------------------

def measure_source(src: str, path: str) -> dict:
    """Measure one Python source. Returns
    {"file": {"path", "file-size"}, "functions": [ {name, location, complexity,
    function-size, param-count, nesting-depth} ], "parse_error": bool}.
    A file that does not parse still yields its LOC (fail-soft) with no functions."""
    file_rec = {"path": path, "file-size": _file_loc(src)}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {"file": file_rec, "functions": [], "parse_error": True}
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, _FUNC_DEFS):
            span = (getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno + 1
            functions.append({
                "name": node.name,
                "location": f"{path}:{node.lineno}:{node.name}",
                "complexity": cyclomatic(node),
                "function-size": span,
                "param-count": _param_count(node),
                "nesting-depth": _nesting_depth(node),
            })
    return {"file": file_rec, "functions": functions, "parse_error": False}


def measure_file(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return measure_source(fh.read(), path)


# --- duplication (token clones, KH-4) ------------------------------------------

def _significant_tokens(src: str) -> list[tuple[str, int]]:
    """Normalised significant tokens as (key, lineno). Layout tokens
    (NEWLINE/NL/INDENT/DEDENT/COMMENT/ENCODING) are dropped; NUMBER and STRING are
    normalised to their type so numeric/string edits don't hide a clone; NAME and
    OP keep their text so structure and keywords match. A file that fails to
    tokenise contributes nothing (fail-soft)."""
    out: list[tuple[str, int]] = []
    try:
        toks = tokenize.generate_tokens(io.StringIO(src).readline)
        for tok in toks:
            if tok.type in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT,
                            tokenize.DEDENT, tokenize.COMMENT, tokenize.ENCODING,
                            tokenize.ENDMARKER):
                continue
            if tok.type == tokenize.NUMBER:
                key = "#num"
            elif tok.type == tokenize.STRING:
                key = "#str"
            else:
                key = tok.string
            out.append((key, tok.start[0]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return []
    return out


def _tokenize_paths(paths: list[str]) -> dict[str, list[tuple[str, int]]]:
    """Significant tokens per path (fail-soft: an unreadable file contributes []).."""
    per_file: dict[str, list[tuple[str, int]]] = {}
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                per_file[p] = _significant_tokens(fh.read())
        except OSError:
            per_file[p] = []
    return per_file


def _positions_far_enough(positions: list[int], flat: list, min_tokens: int) -> bool:
    """A hash collides at ≥2 positions — but only counts as a real clone if two of
    them are in different files or ≥min_tokens apart (not the same overlapping run)."""
    for a in range(len(positions)):
        for b in range(a + 1, len(positions)):
            pa, pb = positions[a], positions[b]
            if flat[pa][1] != flat[pb][1] or abs(pa - pb) >= min_tokens:
                return True
    return False


def _duplicated_token_indices(flat: list, min_tokens: int) -> set[int]:
    """Token indices covered by any duplicated window of `min_tokens` tokens."""
    window_positions: dict[int, list[int]] = {}
    for i in range(len(flat) - min_tokens + 1):
        h = hash(tuple(flat[i + k][0] for k in range(min_tokens)))
        window_positions.setdefault(h, []).append(i)
    dup: set[int] = set()
    for positions in window_positions.values():
        if len(positions) >= 2 and _positions_far_enough(positions, flat, min_tokens):
            for pos in positions:
                dup.update(range(pos, pos + min_tokens))
    return dup


def _count_dup_blocks(per_file: dict, dup_lines: set) -> int:
    """Contiguous duplicated regions per file — a meaningful block count rather
    than a raw window tally."""
    blocks = 0
    for p in per_file:
        prev = None
        for ln in sorted({ln for (pp, ln) in dup_lines if pp == p}):
            if prev is None or ln - prev > 1:
                blocks += 1
            prev = ln
    return blocks


def duplication(paths: list[str], min_tokens: int = 25) -> dict:
    """Token-run clone detection across `paths`. A window of `min_tokens`
    consecutive significant tokens that appears at ≥2 positions (in different files
    or non-overlapping in one) marks those lines as duplicated. Returns
    {"blocks": <count of duplicated regions>, "duplicated-lines", "total-lines",
    "duplication-pct"}. Empty input → all zeros (the tested empty case)."""
    per_file = _tokenize_paths(paths)
    flat = [(key, p, ln) for p, toks in per_file.items() for key, ln in toks]
    dup_lines = {(flat[i][1], flat[i][2]) for i in _duplicated_token_indices(flat, min_tokens)}
    total_lines = sum(len({ln for _, ln in toks}) for toks in per_file.values())
    pct = round(100.0 * len(dup_lines) / total_lines, 1) if total_lines else 0.0
    return {"blocks": _count_dup_blocks(per_file, dup_lines),
            "duplicated-lines": len(dup_lines), "total-lines": total_lines,
            "duplication-pct": pct}


# --- tree measurement + breach comparison --------------------------------------

def measure_paths(paths: list[str], min_tokens: int = 25) -> dict:
    """Measure every path; aggregate functions + files and compute duplication.
    Empty input measures clean (the tested empty case)."""
    functions, files = [], []
    for p in paths:
        try:
            m = measure_file(p)
        except OSError:
            continue
        functions.extend(m["functions"])
        files.append(m["file"])
    return {"functions": functions, "files": files,
            "duplication": duplication(paths, min_tokens=min_tokens)}


def load_bars(coding_standards_text: str) -> dict:
    """Declared bars as {metric: {metric, limit, pct}} from a coding-standards
    file's FRIDAY-MAINTAINABILITY block. Reuses the taglines grammar (one home).
    No block / no bars → {} (the non-adopter case — breaches() then returns [])."""
    lines = taglines.block_lines(coding_standards_text, "FRIDAY-MAINTAINABILITY") or []
    bars: dict = {}
    for ln in lines:
        parsed = taglines.parse_typed_line(ln)
        if parsed and parsed[0] == "maintainability":
            bar = taglines.parse_maintainability_bar(parsed[1])
            if bar:
                bars[bar["metric"]] = bar
    return bars


def breaches(measured: dict, bars: dict) -> list[dict]:
    """Every measured value strictly OVER its declared bar, as
    {location, metric, measured, bar}. No bars → no breaches (the non-adopter
    zero-change invariant). This is also the fix-verifier: a fixed location must
    no longer appear here (AC-8.2)."""
    out: list[dict] = []
    for fn in measured.get("functions", []):
        for metric in FUNC_METRICS:
            bar = bars.get(metric)
            val = fn.get(metric)
            if bar and val is not None and val > bar["limit"]:
                out.append({"location": fn["location"], "metric": metric,
                            "measured": val, "bar": bar["limit"]})
    files = measured.get("files")
    if files is None and "file" in measured:
        files = [measured["file"]]
    bar = bars.get("file-size")
    if bar:
        for f in (files or []):
            if f.get("file-size", 0) > bar["limit"]:
                out.append({"location": f["path"], "metric": "file-size",
                            "measured": f["file-size"], "bar": bar["limit"]})
    dup = measured.get("duplication")
    bar = bars.get("duplication")
    if bar and dup and dup.get("duplication-pct", 0) > bar["limit"]:
        out.append({"location": "<tree>", "metric": "duplication",
                    "measured": dup["duplication-pct"], "bar": bar["limit"]})
    return out


def _walk_py(root: str) -> list[str]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_WALK]
        for fn in filenames:
            if fn.endswith(".py"):
                found.append(os.path.join(dirpath, fn))
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Measure code health and report breaches "
                                             "against a project's declared bars.")
    ap.add_argument("--root", default=".", help="tree to measure when no files are named")
    ap.add_argument("--standards", help="coding-standards file holding the declared bars")
    ap.add_argument("--min-tokens", type=int, default=25, help="duplication window size")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("files", nargs="*", help="specific files to measure (else walk --root)")
    args = ap.parse_args(argv)

    files = args.files or _walk_py(os.path.abspath(args.root))
    bars = {}
    if args.standards:
        try:
            with open(args.standards, encoding="utf-8") as fh:
                bars = load_bars(fh.read())
        except OSError as exc:
            print(f"maintainability_measure: {exc}", file=sys.stderr)
            return 2
    measured = measure_paths(files, min_tokens=args.min_tokens)
    brs = breaches(measured, bars)
    out = {"breach_count": len(brs), "breaches": brs,
           "measured": {"functions": len(measured["functions"]),
                        "files": len(measured["files"]),
                        "duplication": measured["duplication"]},
           "bars_declared": sorted(bars.keys())}
    if args.json:
        print(json.dumps(out))
    else:
        print(f"{len(brs)} breach(es) over {len(bars)} declared bar(s) "
              f"across {len(measured['files'])} file(s)")
        for b in brs:
            print(f"  {b['metric']}: {b['measured']} > {b['bar']}  @ {b['location']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
