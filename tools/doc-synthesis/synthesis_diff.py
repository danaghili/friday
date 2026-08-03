#!/usr/bin/env python3
"""Extractor-vs-synthesis diff — THE QA oracle of the doc-synthesis loop (§6.7).

Structure is extracted deterministically; rationale is LLM-synthesized. This
tool diffs the two and classifies every disagreement:

  omitted-module / omitted-edge          (blocking) the synthesis dropped a
                                         fact the code proves — RUN-2's "LLM
                                         omitted the config node" class.
  ambiguous-edge                         (info)     a doc edge the IR lacks,
    matching an extractor-recorded bare-import ambiguity (2+ same-named
    candidates — the extractor refused to guess; the doc may know better)
  hallucinated-module / hallucinated-edge (blocking) the synthesis asserts
                                         structure the code does not contain.
  missing-inventory                      (blocking) the synthesized doc lacks
                                         the pinned `## Component inventory`
                                         section — nothing to diff against.
  no-diagram                             (warn) no mermaid block to edge-diff.
  uncaptured-why                         (info) load-bearing structure exists
                                         with ZERO DECISIONS.md entries — the
                                         §6.6 honesty backstop for the
                                         model-autonomous channel: a silent
                                         omission becomes a visible finding.

Synthesis contract (docs/contracts/synthesis-handoff.md, heading-pinned): the
building-blocks doc carries `## Component inventory` listing every module id
as inline code (or the exact sentinel `_No components identified._` for the
A.2 zero-module case), plus a mermaid `graph LR` whose node declarations are
`safe_id["real.id"]` — the same transform the renderer uses.

Usage:
  python3 tools/doc-synthesis/synthesis_diff.py --ir docs/architecture/generated/architecture-ir.json \
      --doc docs/architecture/05-building-blocks.md [--decisions docs/DECISIONS.md] [--json]

Exit codes: 0 no blocking findings · 1 blocking findings · 2 bad invocation.
Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

EMPTY_INVENTORY_SENTINEL = "_No components identified._"

# INC-207 FR-207.3 — the size rule. Above the threshold the inventory section
# may carry this exact sentinel instead of enumerating every module: the
# oracle then proves the generated inventory exists and still blocks any
# module the prose names that the code does not contain, but stops demanding
# a hand-maintained full enumeration (which no model sustains at real
# front-end size — the predictable end state of demanding it is the checker
# getting switched off). Below the threshold the sentinel is NOT accepted:
# today's full-enumeration contract is unchanged, character for character.
INVENTORY_POINTER_SENTINEL = ("_Inventory: generated — see "
                              "docs/architecture/generated/"
                              "architecture-ir.json._")
DEFAULT_INVENTORY_THRESHOLD = 300

_THRESHOLD_LINE_RE = re.compile(
    r"^synthesis:\s*inventory-threshold\s*<=\s*(\d+)\s*$", re.M)

_INVENTORY_ITEM_RE = re.compile(r"^\s*[-*]\s+`([^`]+)`")
_MERMAID_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.S)
_NODE_DECL_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\[\"([^\"]+)\"\]", re.M)
_EDGE_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*(?:-->|-\.->)(?:\|[^|\n]*\|)?\s*([A-Za-z0-9_]+)", re.M)


def _inventory_section(doc_text: str) -> list[str] | None:
    """Lines of the `## Component inventory` section, or None when absent.
    Uses the same exact-after-normalization matcher as friday-docs."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "doc-index"))
    import mdparse
    doc = mdparse.parse_document(doc_text.encode("utf-8"))
    heading, _ = mdparse.find_section(doc, "Component inventory")
    if heading is None:
        return None
    return mdparse.section_text(doc, heading).splitlines()


def _edge_findings(ir: dict, ir_edges: set, synth_text: str, add) -> None:
    """The mermaid half of the oracle: compare the diagram's edges against the
    IR's. A doc edge the IR lacks is a hallucination — UNLESS the extractor
    recorded that it REFUSED to resolve exactly this bare import (2+ same-named
    candidates, task #41). The doc may carry knowledge the static pass provably
    cannot (a sys.path insert, a conftest); punishing that as a hallucination is
    what deleted a TRUE edge from the docs on 2026-07-29. Surfaced as
    informational, never silently accepted."""
    m = _MERMAID_RE.search(synth_text)
    if m is None:
        if ir_edges:
            add("no-diagram", "warn",
                "no mermaid block found — edge-level diff skipped")
        return
    body = m.group(1)
    label_by_node = {nid: label for nid, label in _NODE_DECL_RE.findall(body)}

    def real(nid: str) -> str:
        return label_by_node.get(nid, nid)

    doc_edges = {(real(a), real(b)) for a, b in _EDGE_RE.findall(body)}
    for a, b in sorted(ir_edges - doc_edges):
        add("omitted-edge", "blocking",
            f"code has import edge `{a}` → `{b}` but the diagram omits it")
    amb = ir.get("ambiguous_imports", [])
    for a, b in sorted(doc_edges - ir_edges):
        rec = next((r for r in amb if r.get("from") == a
                    and b in r.get("candidates", [])), None)
        if rec is not None:
            add("ambiguous-edge", "info",
                f"diagram asserts `{a}` → `{b}`: the extractor saw the bare "
                f"`import {rec['name']}` but {len(rec['candidates'])} "
                "same-named modules exist and it refuses to guess — kept on "
                "the doc's authority; re-verify by hand if either side moves")
        else:
            add("hallucinated-edge", "blocking",
                f"diagram asserts `{a}` → `{b}` which the code does not contain")


def _inventory_findings(ir: dict, ir_modules: set, synth_text: str,
                        threshold: int, add) -> bool:
    """The inventory half of the oracle; returns pointer_mode (FR-207.3).
    The pointer sentinel counts ONLY above the threshold — below it, the full
    enumeration stays the contract, so a small project can never opt out
    silently."""
    inv_lines = _inventory_section(synth_text)
    if inv_lines is None:
        add("missing-inventory", "blocking",
            "synthesized doc lacks the pinned '## Component inventory' section "
            "(contract: docs/contracts/synthesis-handoff.md)")
        return False
    declared = {m.group(1) for ln in inv_lines
                for m in [_INVENTORY_ITEM_RE.match(ln)] if m}
    is_empty_decl = any(EMPTY_INVENTORY_SENTINEL in ln for ln in inv_lines)
    pointer_mode = (len(ir_modules) > threshold
                    and any(INVENTORY_POINTER_SENTINEL in ln
                            for ln in inv_lines))
    if ir.get("generated-empty") and not declared and not is_empty_decl:
        add("missing-inventory", "blocking",
            f"zero-module IR requires the '{EMPTY_INVENTORY_SENTINEL}' sentinel")
    if not pointer_mode:
        for missing in sorted(ir_modules - declared):
            add("omitted-module", "blocking",
                f"code contains `{missing}` but the synthesis inventory omits it")
    for extra in sorted(declared - ir_modules):
        add("hallucinated-module", "blocking",
            f"synthesis inventory names `{extra}` which the code does not contain")
    return pointer_mode


def load_threshold(root: str) -> int:
    """The declared per-project inventory threshold (INC-207 D11) — a typed
    line in docs/standards/coding-standards.md alongside the project's other
    measured bars. No file / no line → the default (the non-adopter empty
    case, same doctrine as the maintainability bars)."""
    p = os.path.join(root, "docs", "standards", "coding-standards.md")
    try:
        with open(p, encoding="utf-8") as fh:
            m = _THRESHOLD_LINE_RE.search(fh.read())
    except OSError:
        return DEFAULT_INVENTORY_THRESHOLD
    return int(m.group(1)) if m else DEFAULT_INVENTORY_THRESHOLD


def diff(ir: dict, synth_text: str, decisions_entries: list | None = None,
         threshold: int | None = None) -> dict:
    findings: list[dict] = []

    def add(kind: str, severity: str, detail: str) -> None:
        findings.append({"kind": kind, "severity": severity, "detail": detail})

    if threshold is None:
        threshold = DEFAULT_INVENTORY_THRESHOLD
    ir_modules = {m["id"] for m in ir.get("modules", [])}
    ir_edges = {(e["from"], e["to"]) for e in ir.get("edges", [])}

    pointer_mode = _inventory_findings(ir, ir_modules, synth_text, threshold, add)

    # In pointer mode the diagram is area-level narrative, not a module graph
    # — diffing its edges against module-id edges would misread every area
    # node as a hallucination, so the edge diff is skipped (the inventory
    # hallucination check above still bites on any module the prose invents).
    if not pointer_mode:
        _edge_findings(ir, ir_edges, synth_text, add)

    if decisions_entries is not None and not decisions_entries and ir_modules:
        add("uncaptured-why", "info",
            f"{len(ir_modules)} modules of load-bearing structure with ZERO "
            "DECISIONS.md entries — the why is uncaptured (a silent omission "
            "is now a visible finding; see §6.6 honesty story)")

    blocking = [f for f in findings if f["severity"] == "blocking"]
    return {"ok": not blocking, "findings": findings,
            "summary": ("synthesis agrees with extracted structure"
                        if not blocking else
                        f"{len(blocking)} blocking disagreement(s) between "
                        "extracted structure and synthesis")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ir", required=True)
    ap.add_argument("--doc", required=True)
    ap.add_argument("--decisions", default=None,
                    help="optional DECISIONS.md path for the uncaptured-why check")
    ap.add_argument("--root", default=".",
                    help="project root for the declared inventory threshold "
                         "(INC-207 D11; default: cwd)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        with open(args.ir, encoding="utf-8") as fh:
            ir = json.load(fh)
        with open(args.doc, encoding="utf-8") as fh:
            synth = fh.read()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"synthesis_diff: {exc}", file=sys.stderr)
        return 2
    entries = None
    if args.decisions:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import decisions as dec
        parsed = dec.parse_file(args.decisions)
        entries = parsed["entries"] if parsed["ok"] else []
    res = diff(ir, synth, entries, threshold=load_threshold(args.root))
    if args.json:
        print(json.dumps(res))
    else:
        print(res["summary"])
        for f in res["findings"]:
            print(f"  [{f['severity']}] {f['kind']}: {f['detail']}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
