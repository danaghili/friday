"""INC-105 FR-105.6 — import cycles over the extracted graph
(tools/import_cycles.py).

A strongly-connected-component walk over the IR friday already extracts
(D10 corrects PROP-116 on the record: graph_query is a router that never
opens the edge array). The deferred flag on each edge is carried as
evidence for the judge and never used to suppress a finding — an
all-deferred cycle is a real two-way dependency deliberately broken at load
time, and hiding it would be the counter deciding a question the judge
exists to answer. An absent graph is out-of-reach, never clean; a
generated-empty extraction is its own distinct outcome (S-105.2, KH-2).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import import_cycles  # noqa: E402


def _ir(root, modules, edges, generated_empty=False):
    path = os.path.join(str(root), "docs", "architecture", "generated")
    os.makedirs(path, exist_ok=True)
    doc = {"generated-by": "/friday:reference",
           "modules": [{"id": m, "path": m.replace(".", "/") + ".py",
                        "loc": 10} for m in modules],
           "edges": [{"from": f, "to": t, "kind": "import", "line": ln,
                      "deferred": d} for f, t, ln, d in edges]}
    if generated_empty:
        doc["generated-empty"] = True
    with open(os.path.join(path, "architecture-ir.json"), "w",
              encoding="utf-8") as fh:
        json.dump(doc, fh)


def test_mutual_import_is_one_cycle_with_both_edges(tmp_path):
    _ir(tmp_path, ["tools.a", "tools.b", "tools.c"],
        [("tools.a", "tools.b", 10, True), ("tools.b", "tools.a", 20, True),
         ("tools.c", "tools.a", 5, False)])
    out = import_cycles.walk(str(tmp_path))
    assert out["outcome"] == "cycles-found"
    (cycle,) = out["cycles"]
    assert cycle["modules"] == ["tools.a", "tools.b"]
    assert len(cycle["edges"]) == 2
    assert all(e["deferred"] for e in cycle["edges"])


def test_longer_cycle_reports_every_forming_edge(tmp_path):
    _ir(tmp_path, ["a", "b", "c", "d"],
        [("a", "b", 1, False), ("b", "c", 2, False), ("c", "a", 3, False),
         ("c", "d", 4, False)])
    out = import_cycles.walk(str(tmp_path))
    (cycle,) = out["cycles"]
    assert cycle["modules"] == ["a", "b", "c"]
    assert {(e["from"], e["to"]) for e in cycle["edges"]} == {
        ("a", "b"), ("b", "c"), ("c", "a")}


def test_deferred_is_evidence_not_a_filter(tmp_path):
    """D10: the sweep's walk reports the all-deferred cycle; the
    deferred-excluded walk exists only as AC-105.4's red-first lever and
    returns nothing on the same graph."""
    _ir(tmp_path, ["a", "b"],
        [("a", "b", 1, True), ("b", "a", 2, True)])
    assert import_cycles.walk(str(tmp_path))["outcome"] == "cycles-found"
    red = import_cycles.walk(str(tmp_path), exclude_deferred=True)
    assert red["outcome"] == "clean"


def test_self_import_is_a_cycle(tmp_path):
    _ir(tmp_path, ["a", "b"], [("a", "a", 7, False), ("a", "b", 8, False)])
    out = import_cycles.walk(str(tmp_path))
    (cycle,) = out["cycles"]
    assert cycle["modules"] == ["a"]


def test_acyclic_graph_is_clean_as_a_distinct_outcome(tmp_path):
    _ir(tmp_path, ["a", "b", "c"],
        [("a", "b", 1, False), ("b", "c", 2, False)])
    out = import_cycles.walk(str(tmp_path))
    assert out["outcome"] == "clean"
    assert out["cycles"] == []


def test_absent_graph_is_out_of_reach_never_clean(tmp_path):
    out = import_cycles.walk(str(tmp_path))
    assert out["outcome"] == "out-of-reach"
    assert "extractor" in out["reason"] or "reference" in out["reason"]


def test_generated_empty_is_its_own_outcome(tmp_path):
    _ir(tmp_path, [], [], generated_empty=True)
    out = import_cycles.walk(str(tmp_path))
    assert out["outcome"] == "empty"
    assert out["outcome"] != "clean"


def test_two_disjoint_cycles_both_report_deterministically(tmp_path):
    _ir(tmp_path, ["m", "n", "x", "y"],
        [("x", "y", 1, False), ("y", "x", 2, False),
         ("m", "n", 3, False), ("n", "m", 4, False)])
    out = import_cycles.walk(str(tmp_path))
    assert [c["modules"] for c in out["cycles"]] == [["m", "n"], ["x", "y"]]
