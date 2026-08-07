#!/usr/bin/env python3
"""Import-cycle detection over the extracted graph (INC-105 FR-105.6, D10).

The graph friday already extracts (`docs/architecture/generated/
architecture-ir.json`) carries every import edge with its source, target,
line and whether the import is deferred inside a function body — so cycle
detection is a strongly-connected-component walk over that array, written
here rather than bound to `graph_query` (whose own fallback never opens the
edge array; D10 corrects PROP-116 on the record).

- **The deferred flag is evidence, never a filter:** an all-deferred cycle
  is a real two-way dependency deliberately broken at load time, which is a
  judgement about design rather than a fact about the graph. The
  `exclude_deferred` walk exists only as AC-105.4's red-first lever — the
  conformance sweep never passes it.
- **An absent graph is out-of-reach, never clean (S-105.2):** a language the
  extractor does not read, or a project `/friday:reference` has not run on;
  the reach is INC-207 D1's, cited. A generated-empty extraction is its own
  distinct outcome — a real, well-formed document that proved zero modules.

Consumed by `tools/conformance_sweep.py` for checks of kind `cycle`.
Contract: `docs/contracts/conformance-envelope.md`. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402

IR_REL = os.path.join("docs", "architecture", "generated",
                      "architecture-ir.json")
OUT_OF_REACH = ("the extracted graph is not here — a language the extractor "
                "does not read (its reach is INC-207 D1's), or a project "
                "/friday:reference has never run on; reported as out of "
                "reach, never as clean")


def _load_ir(root: str) -> dict | None:
    path = os.path.join(fs.resolve_worktree_root(root), IR_REL)
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _components(nodes: list[str], edges: list[dict]) -> list[list[str]]:
    """Iterative Kosaraju: order by first-pass finish time, then sweep the
    reversed graph. Deterministic — nodes visited in sorted order."""
    fwd: dict[str, list[str]] = {n: [] for n in nodes}
    rev: dict[str, list[str]] = {n: [] for n in nodes}
    for e in edges:
        if e["from"] in fwd and e["to"] in fwd:
            fwd[e["from"]].append(e["to"])
            rev[e["to"]].append(e["from"])
    order = _finish_order(sorted(nodes), fwd)
    seen: set[str] = set()
    components: list[list[str]] = []
    for node in reversed(order):
        if node in seen:
            continue
        members = _reach(node, rev, seen)
        components.append(sorted(members))
    return components


def _finish_order(nodes: list[str], graph: dict[str, list[str]]) -> list[str]:
    seen: set[str] = set()
    order: list[str] = []
    for start in nodes:
        if start in seen:
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        seen.add(start)
        while stack:
            node, idx = stack.pop()
            targets = sorted(graph[node])
            if idx < len(targets):
                stack.append((node, idx + 1))
                nxt = targets[idx]
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append((nxt, 0))
            else:
                order.append(node)
    return order


def _reach(start: str, graph: dict[str, list[str]],
           seen: set[str]) -> list[str]:
    members = []
    stack = [start]
    seen.add(start)
    while stack:
        node = stack.pop()
        members.append(node)
        for nxt in sorted(graph[node]):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return members


def walk(root: str = ".", exclude_deferred: bool = False) -> dict:
    """One cycle walk. Outcomes, all distinct (S-105.2): cycles-found ·
    clean (a real graph proved acyclic) · empty (a real extraction proved
    zero modules) · out-of-reach (no graph to walk — never clean)."""
    ir = _load_ir(root)
    if ir is None:
        return {"outcome": "out-of-reach", "cycles": [],
                "reason": OUT_OF_REACH}
    if ir.get("generated-empty") or not ir.get("modules"):
        return {"outcome": "empty", "cycles": [],
                "reason": "the extraction ran and proved zero modules — a "
                          "well-formed empty document, distinct from clean"}
    edges = [e for e in ir.get("edges", [])
             if not (exclude_deferred and e.get("deferred"))]
    nodes = [m["id"] for m in ir["modules"]]
    cycles = []
    for members in _components(nodes, edges):
        inside = [e for e in edges
                  if e["from"] in members and e["to"] in members]
        if len(members) > 1 or any(e["from"] == e["to"] for e in inside):
            cycles.append({"modules": members,
                           "edges": [{"from": e["from"], "to": e["to"],
                                      "line": e.get("line"),
                                      "deferred": bool(e.get("deferred"))}
                                     for e in sorted(
                                         inside, key=lambda e:
                                         (e["from"], e["to"]))]})
    cycles.sort(key=lambda c: c["modules"][0])
    outcome = "cycles-found" if cycles else "clean"
    return {"outcome": outcome, "cycles": cycles}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", default=".")
    p.add_argument("--exclude-deferred", action="store_true",
                   help="AC-105.4's red-first lever ONLY — the sweep never "
                        "filters on the deferred flag (D10)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    out = walk(args.root, exclude_deferred=args.exclude_deferred)
    if args.json:
        print(json.dumps(out, indent=2))
        return 0
    line = f"import-cycles: {out['outcome']}"
    if out.get("reason"):
        line += f" — {out['reason']}"
    print(line)
    for cycle in out["cycles"]:
        print("  cycle: " + " ↔ ".join(cycle["modules"]))
        for e in cycle["edges"]:
            flag = " [deferred]" if e["deferred"] else ""
            print(f"    {e['from']} -> {e['to']} (line {e['line']}){flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
