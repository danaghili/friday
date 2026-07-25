"""graph_query.py — the one seam every explore consumer (adopt, harden scout,
feature) calls to ask the code graph. Soft integration (FR-68): graphify present
→ route to `graphify query`; absent → answer from friday's own EXTRACTED IR.
Both AC-18 paths live here. Test-first (U6-1).
"""
import json
import os
import sys

from guardkit import BUILD_ROOT

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import graph_query as gq  # noqa: E402


def _friday_ir(root, modules):
    gen = root / "docs" / "architecture" / "generated"
    gen.mkdir(parents=True, exist_ok=True)
    (gen / "architecture-ir.json").write_text(
        json.dumps({"modules": modules, "edges": []}), encoding="utf-8")


def test_present_routes_to_graphify(tmp_path):
    seen = {}

    def fake_runner(question, root):
        seen["q"] = question
        return {"ok": True, "answer": "NODE lane_clear() [src=friday_substrate.py loc=L233]"}

    res = gq.query("what writes the .friday root", str(tmp_path),
                   has_graphify=True, graph_present=True, runner=fake_runner)
    assert res["backend"] == "graphify"
    assert "lane_clear" in res["answer"]
    assert seen["q"] == "what writes the .friday root"


def test_absent_falls_back_to_friday_ir(tmp_path):
    _friday_ir(tmp_path, [
        {"id": "friday_substrate", "path": "tools/friday_substrate.py", "loc": 333},
        {"id": "lane", "path": "tools/lane.py", "loc": 40},
    ])
    res = gq.query("substrate", str(tmp_path), has_graphify=False)
    assert res["backend"] == "friday-own"
    hits = [m["id"] for m in res["modules"]]
    assert "friday_substrate" in hits
    assert "lane" not in hits  # 'substrate' does not match lane.py


def test_present_but_no_graph_falls_back(tmp_path):
    # Installed but this project has no built graph yet → the fallback still
    # answers; a consumer is never left with nothing (AC-18 absent path).
    _friday_ir(tmp_path, [{"id": "receipt", "path": "tools/receipt.py", "loc": 150}])
    res = gq.query("receipt", str(tmp_path), has_graphify=True, graph_present=False)
    assert res["backend"] == "friday-own"
    assert res["modules"][0]["id"] == "receipt"


def test_fallback_with_no_ir_is_honest_not_a_crash(tmp_path):
    res = gq.query("anything", str(tmp_path), has_graphify=False)
    assert res["backend"] == "friday-own"
    assert res["modules"] == []
    assert "reference" in res["note"].lower()  # points at how to build the IR


def test_result_carries_the_extracted_only_evidence_rule(tmp_path):
    # FR-70: whatever the backend, the consumer is reminded to cite EXTRACTED as
    # evidence and treat INFERRED as leads.
    _friday_ir(tmp_path, [{"id": "x", "path": "tools/x.py", "loc": 1}])
    res = gq.query("x", str(tmp_path), has_graphify=False)
    assert "EXTRACTED" in res["evidence_rule"]
    assert "INFERRED" in res["evidence_rule"]
