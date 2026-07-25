#!/usr/bin/env python3
"""FRIDAY-CLAIMS ground-truth verifier — the doc-drift detector proper.

Content-independent (preserve-list §2.5): checks the typed FRIDAY-CLAIMS block
in CLAUDE.md against REAL machine-readable ground truth via string-mechanical
checks — never a semantic/YAML interpretation. Kept in concept from v0.4.0,
extended for Python-stack projects (vnext dogfoods on Python).

Claim types (closed vocabulary — an unknown claim key is a malformation):
  stack:      `[location:]name[@major|constraint][ (annotation)]` — the claim
              names WHERE its evidence lives (BUG-001). Bare / `manifest:` =
              project-declared: comment-stripped, word-bounded match in a
              manifest (package.json, requirements.txt, pyproject.toml,
              Pipfile, setup.py, setup.cfg) or a PEP 723 `# /// script`
              inline block — never machine state. `path:` = a runnable on
              PATH (`path:python3` is the legitimate spelling of the old bare
              PATH claim). `files:` = a source file stem or directory segment
              equal to the name token (hyphen/underscore-insensitive).
              `harness:` / `external:` = provided by the harness or a network
              service — honestly `unverifiable`, NOT drift; the caller
              disposes. A trailing `(annotation)` is documentation and never
              changes what is tested. Version pins: `name@major` and
              `name>=X.Y` verify against declared text; on `path:` the pin is
              recorded as not version-checked.
  ci-gate:    every named tool token appears in some .github/workflows/* file
              text (string-level, never YAML-parsed). No workflows dir →
              `unverifiable`, which is NOT drift — the caller disposes.
  threshold:  `coverage >= N` vs numeric thresholds in known coverage configs;
              none found → `unverifiable`.
  non-goal:   NEVER checked here — semantic; reported `semantic_only`.
  provenance: closed value vocabulary (taglines.PROVENANCE_VALUES, FR-67) —
              a well-formed value is `semantic_only` (whether the spec truly
              was born that way is history, not string-checkable); an unknown
              value is drift. ABSENCE is a declared gap readers tolerate —
              only doc_gate's spec kind requires it.
  world:      closed value vocabulary (taglines.WORLD_VALUES, FR-66) — same
              rules as provenance ("does this land in an occupied world" is
              judgment; the recorded value's spelling is not).

Exit codes: 0 no drift · 1 drift · 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

CLAIM_TYPES = ("stack", "ci-gate", "non-goal", "threshold", "provenance", "world")
_STACK_LOCATIONS = ("manifest", "path", "files", "harness", "external")
_STACK_ENTRY_RE = re.compile(
    r"^\s*(?:(manifest|path|files|harness|external):)?"   # explicit evidence location
    r"([A-Za-z0-9@/_.+-]+?)"                               # name (npm scopes keep @/)
    r"(?:@(\d+))?"                                         # @major pin
    r"(?:\s*(>=|<=|==|~=|>|<)\s*([0-9][A-Za-z0-9.*]*))?"   # or a version constraint
    r"(?:\s*\(([^)]+)\))?\s*$")                            # annotation — never a rule switch
_THRESHOLD_RE = re.compile(r"^coverage\s*>=\s*(\d+)\s*$")
_SOURCE_EXTS = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rb", ".rs", ".java")
_EXCLUDED_WALK = {".git", "node_modules", ".friday", "docs", "dist", "build",
                  "__pycache__", ".venv", "venv"}


def parse_block(claude_md_text: str) -> list[dict] | None:
    """Claim lines from the FRIDAY-CLAIMS block; None if no block. Comments
    (lines without a typed key) inside the block are tolerated ONLY as
    `<!-- -->`; anything else is returned with type 'malformed'."""
    lines = taglines.block_lines(claude_md_text, "FRIDAY-CLAIMS")
    if lines is None:
        return None
    claims = []
    for ln in lines:
        if ln.startswith("<!--"):
            continue
        parsed = taglines.parse_typed_line(ln)
        if parsed and parsed[0] in CLAIM_TYPES:
            claims.append({"type": parsed[0], "value": parsed[1], "raw": ln})
        else:
            claims.append({"type": "malformed", "value": ln, "raw": ln})
    return claims


def well_formed(claude_md_text: str) -> tuple[bool, list[str]]:
    """The K0/K1 structural check: block present, at least one claim line,
    every non-comment line parses to a known claim type."""
    claims = parse_block(claude_md_text)
    if claims is None:
        return False, ["no FRIDAY-CLAIMS block in CLAUDE.md"]
    errs = [f"unparseable claim line: {c['raw']!r}" for c in claims
            if c["type"] == "malformed"]
    if not claims:
        errs.append("FRIDAY-CLAIMS block is empty — at least one typed claim required")
    return (not errs), errs


# --- ground-truth lookups (string-mechanical) ------------------------------------

def _manifest_texts(root: str) -> dict[str, str]:
    out = {}
    for fn in ("package.json", "requirements.txt", "pyproject.toml", "Pipfile",
               "setup.py", "setup.cfg"):
        p = os.path.join(root, fn)
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as fh:
                    out[fn] = fh.read()
            except OSError:
                pass
    return out


_PEP723_OPEN = re.compile(r"^#\s*///\s*script\s*$")
_PEP723_CLOSE = re.compile(r"^#\s*///\s*$")


def _inline_script_blocks(root: str) -> dict[str, str]:
    """PEP 723 `# /// script … # ///` blocks, uncommented — the manifest of a
    manifest-less uv-run project (BUG-001 D5)."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_WALK]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8") as fh:
                    lines = fh.read().splitlines()
            except OSError:
                continue
            block: list[str] = []
            inside = False
            for ln in lines:
                stripped = ln.strip()
                if not inside and _PEP723_OPEN.match(stripped):
                    inside = True
                    continue
                if inside and _PEP723_CLOSE.match(stripped):
                    rel = os.path.relpath(p, root)
                    out[f"{rel} (PEP 723)"] = "\n".join(block)
                    block, inside = [], False
                    continue
                if inside:
                    block.append(stripped.lstrip("#").strip())
    return out


def _declared_texts(root: str) -> dict[str, str]:
    """Every place a project DECLARES a dependency, comments stripped so a
    documented removal can never verify a claim (BUG-001 D1)."""
    out = {}
    for fn, text in _manifest_texts(root).items():
        out[fn] = text if fn == "package.json" else re.sub(r"#[^\n]*", "", text)
    out.update(_inline_script_blocks(root))  # already uncommented
    return out


def _name_pattern(name: str) -> re.Pattern:
    # Word-bounded within package-name charset: `yaml` never hits `pyyaml`.
    return re.compile(r"(?<![A-Za-z0-9_.-])" + re.escape(name) + r"(?![A-Za-z0-9_-])")


def _files_evidence(root: str, token: str) -> str | None:
    """A source file STEM or a directory path segment equal to the token
    (hyphen/underscore-insensitive) — never a substring (BUG-001 D2)."""
    want = token.lower().replace("-", "_")
    exts = set(_SOURCE_EXTS)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_WALK]
        for d in dirnames:
            if d.lower().replace("-", "_") == want:
                return os.path.relpath(os.path.join(dirpath, d), root) + os.sep
        for fn in filenames:
            stem, ext = os.path.splitext(fn)
            if ext in exts and stem.lower().replace("-", "_") == want:
                return os.path.relpath(os.path.join(dirpath, fn), root)
    return None


def _constraint_evidence(texts: dict[str, str], name: str, op: str, ver: str) -> str | None:
    if name in ("python", "python3"):
        pat = re.compile(r"requires-python\s*=?\s*[\"']?\s*" + re.escape(op) + r"\s*" + re.escape(ver))
    else:
        pat = re.compile(r"(?<![A-Za-z0-9_.-])" + re.escape(name)
                         + r"\s*[\"']?\s*" + re.escape(op) + r"\s*" + re.escape(ver))
    for fn, text in texts.items():
        if pat.search(text):
            return fn
    return None


def _check_stack(root: str, value: str) -> tuple[str, str]:
    m = _STACK_ENTRY_RE.match(value)
    if not m:
        if ":" in value:
            loc = value.split(":", 1)[0]
            return "drift", (f"unknown evidence location {loc!r} — one of "
                             f"{'|'.join(_STACK_LOCATIONS)}, or omit for project-declared")
        return "drift", f"stack entry does not parse: {value!r}"
    loc, name, major, op, ver, _annotation = m.groups()
    if loc in ("harness", "external"):
        provided = "harness-provided" if loc == "harness" else "an external service"
        return "unverifiable", (f"{name}: {provided} — not string-checkable "
                                f"from the repo; the caller disposes")
    if loc == "path":
        if shutil.which(name):
            pin = f"@{major}" if major else (f"{op}{ver}" if op else "")
            note = f" ({pin} not version-checked on PATH)" if pin else ""
            return "pass", f"{name} on PATH{note}"
        return "drift", f"{name} not on PATH"
    if loc == "files":
        hit = _files_evidence(root, name.split("/")[-1])
        return (("pass", f"file evidence: {hit}") if hit else
                ("drift", f"no source file stem or directory named {name!r}"))
    # Bare / manifest: — project-declared only; machine state never verifies it.
    texts = _declared_texts(root)
    if major:
        pat = re.compile(r"(?<![A-Za-z0-9_.-])" + re.escape(name)
                         + r"[\"'@=~^><\s:]{0,4}" + re.escape(major) + r"(?![0-9])")
        for fn, text in texts.items():
            if pat.search(text):
                return "pass", f"{name}@{major} declared in {fn}"
        return "drift", f"{name}@{major} not declared at that major in any manifest or inline block"
    if op:
        fn = _constraint_evidence(texts, name, op, ver)
        if fn:
            return "pass", f"{name}{op}{ver} declared in {fn}"
        for fn, text in texts.items():
            if _name_pattern(name).search(text):
                return "drift", f"{name} declared in {fn} but constraint {op}{ver} not found"
        return "drift", f"{name}{op}{ver} not declared in any manifest or inline block"
    for fn, text in texts.items():
        if _name_pattern(name).search(text):
            return "pass", f"{name} declared in {fn}"
    return "drift", f"{name} not declared in any manifest or PEP 723 inline block"


def _check_ci_gate(root: str, value: str) -> tuple[str, str]:
    wf_dir = os.path.join(root, ".github", "workflows")
    if not os.path.isdir(wf_dir):
        return "unverifiable", "no .github/workflows/ directory"
    texts = []
    for fn in sorted(os.listdir(wf_dir)):
        if fn.endswith((".yml", ".yaml")):
            try:
                with open(os.path.join(wf_dir, fn), encoding="utf-8") as fh:
                    texts.append(fh.read())
            except OSError:
                pass
    tool = value.split()[0] if value.split() else value
    if any(tool in t for t in texts):
        return "pass", f"{tool!r} named in a workflow file"
    return "drift", f"{tool!r} not named in any workflow file"


def _check_threshold(root: str, value: str) -> tuple[str, str]:
    m = _THRESHOLD_RE.match(value)
    if not m:
        return "unverifiable", f"unrecognized threshold grammar: {value!r}"
    want = int(m.group(1))
    for fn in ("pyproject.toml", "setup.cfg", ".coveragerc", "package.json",
               "vitest.config.ts", "jest.config.js"):
        p = os.path.join(root, fn)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        found = re.search(r"fail[_-]?under\D{0,5}(\d+)|\"branches\"\s*:\s*(\d+)", text)
        if found:
            have = int(next(g for g in found.groups() if g))
            return (("pass", f"config {fn} enforces {have} >= {want}")
                    if have >= want else
                    ("drift", f"config {fn} enforces {have} < claimed {want}"))
    return "unverifiable", "no coverage config found"


def _check_closed_vocab(value: str, vocab: tuple[str, ...]) -> tuple[str, str]:
    """FR-66/FR-67 claims: the value's spelling is mechanical; its truth is
    judgment. A well-formed value is semantic_only, never 'pass' — this tool
    cannot know how a spec was born or whose world it lands in."""
    if value.strip() in vocab:
        return "semantic_only", "value well-formed; its truth is Lens-2 territory"
    return "drift", f"unknown value {value!r} — must be one of {'|'.join(vocab)}"


def check_all(root: str) -> dict:
    try:
        with open(os.path.join(root, "CLAUDE.md"), encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return {"ok": True, "skipped": "no CLAUDE.md", "results": []}
    claims = parse_block(text)
    if claims is None:
        return {"ok": True, "skipped": "no FRIDAY-CLAIMS block", "results": []}
    results = []
    for c in claims:
        if c["type"] == "stack":
            verdict, detail = _check_stack(root, c["value"])
        elif c["type"] == "ci-gate":
            verdict, detail = _check_ci_gate(root, c["value"])
        elif c["type"] == "threshold":
            verdict, detail = _check_threshold(root, c["value"])
        elif c["type"] == "non-goal":
            verdict, detail = "semantic_only", "never string-checked; Lens-2 territory"
        elif c["type"] == "provenance":
            verdict, detail = _check_closed_vocab(c["value"], taglines.PROVENANCE_VALUES)
        elif c["type"] == "world":
            verdict, detail = _check_closed_vocab(c["value"], taglines.WORLD_VALUES)
        else:
            verdict, detail = "drift", f"malformed claim line: {c['raw']!r}"
        results.append({"claim": c["raw"], "verdict": verdict, "detail": detail})
    drift = [r for r in results if r["verdict"] == "drift"]
    return {"ok": not drift, "results": results, "drift_count": len(drift),
            "summary": ("FRIDAY-CLAIMS: no drift" if not drift else
                        f"FRIDAY-CLAIMS: {len(drift)} drifted claim(s)")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--all", action="store_true", help="check every claim (default)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        print(f"verify_claims: no such dir: {args.root}", file=sys.stderr)
        return 2
    res = check_all(os.path.abspath(args.root))
    print(json.dumps(res) if args.json else res.get("summary", json.dumps(res)))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
