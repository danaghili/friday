#!/usr/bin/env python3
"""Deterministic JavaScript/TypeScript pass — the front-end half of the
extractor (INC-207 FR-207.1). A sibling of extract_architecture.py rather
than a growth of it (OQ-207.3): the Python extractor sits close to the
declared file-size bar, and a second language is a second module.

Reads, never executes (S-207.1). Tolerant line-level reading under the
refusal discipline D-0151 established and D2 extends: an edge is emitted only
when its target file exists on disk; every intra-project-looking specifier
that does not resolve is recorded by name in `js_unresolved`, never guessed,
and no record anywhere carries a confidence field. External package imports
(`react`, `next`) are not refusals — like the Python pass's stdlib/pip
imports, they are simply outside the intra-tree graph.

Emits into the shared IR (contract: docs/contracts/synthesis-handoff.md):
  modules[]       {id, path, loc}      id = real on-disk relative path,
                                       extension included (D8) — never dotted
  edges[]         {from, to, kind:"import", line, deferred}
                                       deferred=True only for dynamic import()
  routes[]        Next.js app router (page.* → method "PAGE"; route.* → one
                  record per exported HTTP-method handler), Next.js pages
                  router (pages → "PAGE"; pages/api → method "ANY"), Express
                  where the complete address is certain in one file (D4)
  components[]    {name, module, line} exported capitalised bindings in
                  .jsx/.tsx only — React's own rule (D5)
  js_unresolved[] {from, name, kind:"import"|"route-prefix", candidates, line}
                  the named-refusal list (FR-207.2; D-0151's record shape,
                  plus a kind so Express prefix refusals share the home)

The caller (extract_architecture.extract) walks the tree and merges; a tree
with no JS-family file gets none of the JS-only keys, so a Python-only
project's IR is byte-identical to today's (AC-207.7).

Pure stdlib.
"""
from __future__ import annotations

import os
import re

JS_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")

# The JS walk's own skip set — NOT the Python walk's. Two deliberate
# differences: `.next` (build output full of generated .js) joins it, and
# `docs` leaves it — "docs" is a real route segment in real apps
# (app/docs/[...slug]/page.tsx), so pruning it at every depth would silently
# delete real routes. A ROOT-level docs/ (this repo's own documentation tree)
# is still pruned, by the walk below, not by this set.
JS_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".friday", ".venv",
                "venv", ".pytest_cache", ".ruff_cache", "dist", "build",
                ".next"}


def js_files(root: str, src_dirs: list[str] | None = None) -> list[str]:
    """Walk the tree for JS-family files under the JS skip rules."""
    root = os.path.abspath(root)
    bases = [os.path.join(root, s) for s in (src_dirs or ["."])]
    out: list[str] = []
    for base in bases:
        for dirpath, dirnames, filenames in os.walk(base):
            keep = []
            for d in sorted(dirnames):
                if d in JS_SKIP_DIRS:
                    continue
                if d == "docs" and os.path.normpath(dirpath) == root:
                    continue
                keep.append(d)
            dirnames[:] = keep
            for fn in sorted(filenames):
                if fn.endswith(JS_EXTENSIONS):
                    out.append(os.path.join(dirpath, fn))
    return sorted(set(out))
_HTTP_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS")
_EXPRESS_METHODS = {"get", "post", "put", "delete", "patch", "head",
                    "options", "all"}
# Resolution order for extensionless specifiers — Node's own lookup order,
# TypeScript-first because a .ts/.tsx source tree is the measured majority.
_TRY_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


# --- comment/string-aware stripping ------------------------------------------

def _code_step(src: str, i: int, out: list[str]) -> tuple[int, str | None]:
    ch = src[i]
    nxt = src[i + 1] if i + 1 < len(src) else ""
    if ch == "/" and nxt in ("/", "*"):
        out.append("  ")
        return i + 2, ("//" if nxt == "/" else "/*")
    out.append(ch)
    return i + 1, (ch if ch in ("'", '"', "`") else None)


def _comment_step(src: str, i: int, mode: str,
                  out: list[str]) -> tuple[int, str | None]:
    ch = src[i]
    nxt = src[i + 1] if i + 1 < len(src) else ""
    if mode == "//":
        out.append("\n" if ch == "\n" else " ")
        return i + 1, (None if ch == "\n" else "//")
    if ch == "*" and nxt == "/":
        out.append("  ")
        return i + 2, None
    out.append("\n" if ch == "\n" else " ")
    return i + 1, "/*"


def _string_step(src: str, i: int, mode: str, out: list[str],
                 keep: bool) -> tuple[int, str | None]:
    ch = src[i]
    if ch == "\\":
        out.append(src[i:i + 2] if keep else "  ")
        return i + 2, mode
    if ch == mode:
        out.append(ch)
        return i + 1, None
    out.append(ch if keep else ("\n" if ch == "\n" else " "))
    return i + 1, mode


def _strip_comments(src: str, keep_strings: bool = False) -> str:
    """Blank out comments — and, unless `keep_strings`, string CONTENTS too —
    preserving newlines, string delimiters, and every offset (the output is
    the same length as the input), so specifier regexes never match inside
    either and quoted payloads can be re-read from the ORIGINAL by span.
    `keep_strings=True` is the JSONC mode: the alias table's keys and values
    are the payload and must survive."""
    out: list[str] = []
    i, n = 0, len(src)
    mode: str | None = None  # None | "'" | '"' | "`" | "//" | "/*"
    while i < n:
        if mode is None:
            i, mode = _code_step(src, i, out)
        elif mode in ("//", "/*"):
            i, mode = _comment_step(src, i, mode, out)
        else:
            i, mode = _string_step(src, i, mode, out, keep_strings)
    return "".join(out)


# --- tsconfig / jsconfig alias table -----------------------------------------

def _jsonc_loads(text: str):
    import json
    stripped = _strip_comments(text, keep_strings=True)
    stripped = re.sub(r",\s*([}\]])", r"\1", stripped)  # trailing commas
    return json.loads(stripped)


def load_alias_table(root: str) -> dict:
    """{"baseUrl": abs-or-None, "paths": {pattern: [targets]}} from the root
    tsconfig.json (jsconfig.json fallback). A file that will not parse yields
    an empty table — refusals then surface downstream, never a crash."""
    for name in ("tsconfig.json", "jsconfig.json"):
        p = os.path.join(root, name)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as fh:
                data = _jsonc_loads(fh.read())
        except Exception:
            return {"baseUrl": None, "paths": {}}
        opts = data.get("compilerOptions") or {}
        base = opts.get("baseUrl")
        base_abs = os.path.normpath(os.path.join(root, base)) if base else None
        return {"baseUrl": base_abs, "paths": opts.get("paths") or {}}
    return {"baseUrl": None, "paths": {}}


# --- specifier extraction + resolution ---------------------------------------

_SPEC_RES = [
    # static: import ... from 'x' / export ... from 'x'  (multiline-tolerant)
    (re.compile(r"\bfrom\s*(['\"])([^'\"\n]+)\1"), False),
    # bare side-effect: import 'x'
    (re.compile(r"\bimport\s*(['\"])([^'\"\n]+)\1"), False),
    # CommonJS: require('x')
    (re.compile(r"\brequire\s*\(\s*(['\"])([^'\"\n]+)\1\s*\)"), False),
    # dynamic: import('x') — the one deferred shape
    (re.compile(r"\bimport\s*\(\s*(['\"])([^'\"\n]+)\1\s*\)"), True),
]


def _specifiers(src: str) -> list[tuple[str, int, bool]]:
    """(specifier, line, deferred) from comment/string-stripped source; the
    stripped text keeps quote delimiters, so the specifier is re-read from the
    original by span."""
    stripped = _strip_comments(src)
    seen_spans: set[tuple[int, int]] = set()
    out: list[tuple[str, int, bool]] = []
    for regex, deferred in _SPEC_RES:
        for m in regex.finditer(stripped):
            span = m.span(2)
            if span in seen_spans:
                continue
            seen_spans.add(span)
            spec = src[span[0]:span[1]]
            line = stripped.count("\n", 0, m.start()) + 1
            out.append((spec, line, deferred))
    out.sort(key=lambda t: t[1])
    return out


def _try_file(base: str, files: set[str]) -> str | None:
    """Resolve a candidate absolute path (sans-or-with extension) to a real
    file in the walked set: exact, +ext, /index+ext — Node's order."""
    norm = os.path.normpath(base)
    if norm in files:
        return norm
    for ext in _TRY_EXTS:
        if norm + ext in files:
            return norm + ext
    for ext in _TRY_EXTS:
        idx = os.path.join(norm, "index" + ext)
        if idx in files:
            return idx
    return None


def resolve_specifier(spec: str, importer_abs: str, root: str,
                      aliases: dict, files: set[str]) -> tuple[str | None, bool]:
    """→ (absolute target path | None, was_intra_project_attempt). External
    package names return (None, False) — not refusals."""
    if spec.startswith("."):
        return _try_file(os.path.join(os.path.dirname(importer_abs), spec),
                         files), True
    for pattern, targets in (aliases.get("paths") or {}).items():
        if pattern.endswith("/*"):
            prefix = pattern[:-1]  # keep the slash: "@/" from "@/*"
            if spec.startswith(prefix):
                rest = spec[len(prefix):]
                for target in targets:
                    tbase = target[:-1] if target.endswith("*") else target
                    hit = _try_file(os.path.join(root, tbase, rest), files)
                    if hit:
                        return hit, True
                return None, True
        elif spec == pattern:
            for target in targets:
                hit = _try_file(os.path.join(root, target), files)
                if hit:
                    return hit, True
            return None, True
    if aliases.get("baseUrl") and not spec.startswith("@"):
        hit = _try_file(os.path.join(aliases["baseUrl"], spec), files)
        if hit:
            return hit, True
    return None, False


# --- routes ------------------------------------------------------------------

def _next_path_from_segments(segments: list[str]) -> str | None:
    """Folder chain → Next.js address (KH-4's conventions): (group) removed,
    [param]/[...catchall] kept verbatim, any _folder in the chain → not a
    route at all."""
    parts: list[str] = []
    for seg in segments:
        if seg.startswith("_"):
            return None
        if seg.startswith("(") and seg.endswith(")"):
            continue
        parts.append(seg)
    return "/" + "/".join(parts) if parts else "/"


def _route_methods(src: str) -> list[str]:
    stripped = _strip_comments(src)
    found = set()
    for m in _HTTP_METHODS:
        if re.search(r"\bexport\s+(?:async\s+)?function\s+" + m + r"\b", stripped) \
                or re.search(r"\bexport\s+const\s+" + m + r"\s*=", stripped):
            found.add(m)
    # Named-export lists — `export { GET }` / `export { handler as GET,
    # handler as POST }` (the NextAuth shape, caught by the real-project
    # proving run): the exported NAME is the last word of each item.
    for m in re.finditer(r"\bexport\s*\{([^}]*)\}", stripped):
        for item in m.group(1).split(","):
            name = item.split()[-1] if item.split() else ""
            if name in _HTTP_METHODS:
                found.add(name)
    return [m for m in _HTTP_METHODS if m in found]


def _next_routes(root: str, mid: str, abs_path: str, src: str) -> list[dict]:
    rel_parts = mid.split("/")
    routes: list[dict] = []
    stem = os.path.splitext(rel_parts[-1])[0]
    # App router: <...>/app/<segments>/page.* | route.*
    if "app" in rel_parts[:-1] and stem in ("page", "route"):
        app_i = rel_parts.index("app")
        path = _next_path_from_segments(rel_parts[app_i + 1:-1])
        if path is None:
            return []
        if stem == "page":
            routes.append({"method": "PAGE", "path": path, "handler": "page",
                           "module": mid, "line": 1, "protocol": "http"})
        else:
            for m in _route_methods(src):
                routes.append({"method": m, "path": path, "handler": m,
                               "module": mid, "line": 1, "protocol": "http"})
        return routes
    # Pages router: <...>/pages/<path>.<ext>
    if "pages" in rel_parts[:-1]:
        pages_i = rel_parts.index("pages")
        segs = rel_parts[pages_i + 1:-1] + ([] if stem == "index" else [stem])
        if any(s.startswith("_") for s in [*segs, stem]):
            return []
        path = "/" + "/".join(segs) if segs else "/"
        if len(rel_parts) > pages_i + 1 and rel_parts[pages_i + 1] == "api":
            routes.append({"method": "ANY", "path": path, "handler": "default",
                           "module": mid, "line": 1, "protocol": "http"})
        else:
            routes.append({"method": "PAGE", "path": path, "handler": "page",
                           "module": mid, "line": 1, "protocol": "http"})
    return routes


def _express_routes(mid: str, src: str) -> tuple[list[dict], list[dict]]:
    """(routes, refusals). Same-file certainty only (D4): receivers created
    from express() are roots; Router() receivers count only when this same
    file mounts them under a literal prefix — otherwise every registration on
    that router is one route-prefix refusal (the prefix lives elsewhere)."""
    stripped = _strip_comments(src)
    if "express" not in stripped:
        return [], []
    apps = set(re.findall(r"(?:const|let|var)\s+(\w+)\s*=\s*express\s*\(\s*\)",
                          stripped))
    routers = set(re.findall(
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:express\.)?Router\s*\(\s*\)",
        stripped))
    # String CONTENTS are blanked in `stripped` (offsets preserved), so every
    # path literal is re-read from the ORIGINAL source by span.
    mounts: dict[str, str] = {}
    for m in re.finditer(
            r"(\w+)\.use\s*\(\s*['\"]([^'\"\n]*)['\"]\s*,\s*(\w+)\s*\)",
            stripped):
        owner, child = m.group(1), m.group(3)
        if owner in apps and child in routers:
            mounts[child] = src[m.start(2):m.end(2)]
    routes: list[dict] = []
    refused: set[str] = set()
    for m in re.finditer(r"(\w+)\.(\w+)\s*\(\s*['\"]([^'\"\n]*)['\"]", stripped):
        recv, meth = m.group(1), m.group(2)
        path = src[m.start(3):m.end(3)]
        if meth not in _EXPRESS_METHODS:
            continue
        line = stripped.count("\n", 0, m.start()) + 1
        if recv in apps:
            routes.append({"method": meth.upper(), "path": path, "handler": recv,
                           "module": mid, "line": line, "protocol": "http"})
        elif recv in routers:
            if recv in mounts:
                full = (mounts[recv].rstrip("/") + path) or "/"
                routes.append({"method": meth.upper(), "path": full,
                               "handler": recv, "module": mid, "line": line,
                               "protocol": "http"})
            else:
                refused.add(recv)
    refusals = [{"from": mid, "name": r, "kind": "route-prefix",
                 "candidates": [], "line": 1} for r in sorted(refused)]
    return routes, refusals


# --- components --------------------------------------------------------------

_COMPONENT_RES = [
    re.compile(r"\bexport\s+(?:default\s+)?(?:async\s+)?function\s+([A-Z]\w*)"),
    re.compile(r"\bexport\s+(?:default\s+)?class\s+([A-Z]\w*)"),
    re.compile(r"\bexport\s+const\s+([A-Z]\w*)\s*="),
]


def _components(mid: str, src: str) -> list[dict]:
    if not mid.endswith((".jsx", ".tsx")):
        return []
    stripped = _strip_comments(src)
    out, seen = [], set()
    for regex in _COMPONENT_RES:
        for m in regex.finditer(stripped):
            name = m.group(1)
            if name in seen:
                continue
            seen.add(name)
            out.append({"name": name, "module": mid,
                        "line": stripped.count("\n", 0, m.start()) + 1})
    out.sort(key=lambda c: c["line"])
    return out


# --- driver ------------------------------------------------------------------

def extract_js(root: str, files: list[str]) -> dict:
    """files: absolute paths of the JS-family files the caller walked.
    Returns the five JS-side collections; the caller merges them into the IR."""
    root = os.path.abspath(root)
    file_set = {os.path.normpath(p) for p in files}
    aliases = load_alias_table(root)

    def mid_of(abs_path: str) -> str:
        return os.path.relpath(abs_path, root).replace(os.sep, "/")

    out = {"modules": [], "edges": [], "routes": [], "components": [],
           "js_unresolved": []}
    for abs_path in sorted(file_set):
        mid = mid_of(abs_path)
        try:
            with open(abs_path, encoding="utf-8") as fh:
                src = fh.read()
        except (OSError, UnicodeDecodeError):
            continue  # unreadable file: not a module, and nothing to refuse
        out["modules"].append({"id": mid, "path": mid,
                               "loc": src.count("\n") + 1})
        seen_edges: set[tuple[str, str]] = set()
        for spec, line, deferred in _specifiers(src):
            target, intra = resolve_specifier(spec, abs_path, root, aliases,
                                              file_set)
            if target is not None:
                dst = mid_of(target)
                if dst == mid or (mid, dst) in seen_edges:
                    continue
                seen_edges.add((mid, dst))
                out["edges"].append({"from": mid, "to": dst, "kind": "import",
                                     "line": line, "deferred": deferred})
            elif intra:
                out["js_unresolved"].append({"from": mid, "name": spec,
                                             "kind": "import",
                                             "candidates": [], "line": line})
        out["routes"].extend(_next_routes(root, mid, abs_path, src))
        ex_routes, ex_refusals = _express_routes(mid, src)
        out["routes"].extend(ex_routes)
        out["js_unresolved"].extend(ex_refusals)
        out["components"].extend(_components(mid, src))
    out["edges"].sort(key=lambda e: (e["from"], e["to"]))
    out["routes"].sort(key=lambda r: (r["path"], r["method"]))
    return out
