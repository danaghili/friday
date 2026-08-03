"""INC-207 FR-207.3 — the size rule in the synthesis oracle (tests first).

KH-2: this is the only edit in the increment that changes the meaning of an
existing passing verdict, so both directions are pinned here — below the
threshold nothing changes; above it the pointer mode is accepted AND a planted
false claim still blocks. AC-207.3's real-tree character-for-character run
happens at the close; these tests pin the logic that run exercises.
"""
import os
import sys

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools", "doc-synthesis")
sys.path.insert(0, TOOLS)

import synthesis_diff as sd  # noqa: E402


def _ir(n_modules, edges=()):
    mods = [{"id": f"m{i}", "path": f"m{i}.py", "loc": 1} for i in range(n_modules)]
    return {"modules": mods,
            "edges": [{"from": a, "to": b} for a, b in edges],
            "ambiguous_imports": []}


def _doc_full(ir):
    lines = ["# Building blocks", "", "## Component inventory", ""]
    lines += [f"- `{m['id']}`" for m in ir["modules"]]
    return "\n".join(lines) + "\n"


POINTER_DOC = ("# Building blocks\n\n## Component inventory\n\n"
               + sd.INVENTORY_POINTER_SENTINEL + "\n\n"
               "## Areas\n\nScreens live under `app/`; shared logic under `lib/`.\n")


# --- below the threshold: today's behaviour, unchanged ----------------------

def test_below_threshold_full_enumeration_still_passes():
    ir = _ir(3)
    res = sd.diff(ir, _doc_full(ir), None, threshold=300)
    assert res["ok"], res


def test_below_threshold_omission_still_blocks():
    ir = _ir(3)
    doc = "# B\n\n## Component inventory\n\n- `m0`\n- `m1`\n"
    res = sd.diff(ir, doc, None, threshold=300)
    kinds = {f["kind"] for f in res["findings"] if f["severity"] == "blocking"}
    assert "omitted-module" in kinds


def test_below_threshold_pointer_mode_is_not_a_free_pass():
    """Below the line the full enumeration is the contract; the pointer
    sentinel alone must NOT satisfy it (that would let any small project
    opt out of the guarantee silently)."""
    ir = _ir(3)
    res = sd.diff(ir, POINTER_DOC, None, threshold=300)
    assert not res["ok"]


# --- above the threshold: the oracle's job changes --------------------------

def test_above_threshold_pointer_mode_passes():
    ir = _ir(10)
    res = sd.diff(ir, POINTER_DOC, None, threshold=5)
    assert res["ok"], res


def test_above_threshold_planted_false_claim_still_blocks():
    """The plant goes INSIDE the Component inventory section — the
    heading-pinned home of module claims (contract) — because that is the
    surface the oracle polices in both modes; narrative under other headings
    was never module-checked below the threshold either."""
    ir = _ir(10)
    doc = POINTER_DOC.replace(
        sd.INVENTORY_POINTER_SENTINEL,
        sd.INVENTORY_POINTER_SENTINEL + "\n\n- `totally/invented.ts`")
    res = sd.diff(ir, doc, None, threshold=5)
    kinds = {f["kind"] for f in res["findings"] if f["severity"] == "blocking"}
    assert "hallucinated-module" in kinds


def test_above_threshold_full_enumeration_still_accepted():
    """A large project that somehow maintains the full list keeps passing —
    the mode switch adds an accepted shape, it never outlaws the old one."""
    ir = _ir(10)
    res = sd.diff(ir, _doc_full(ir), None, threshold=5)
    assert res["ok"], res


def test_above_threshold_omitted_enumeration_without_pointer_blocks():
    ir = _ir(10)
    doc = "# B\n\n## Component inventory\n\n- `m0`\n"
    res = sd.diff(ir, doc, None, threshold=5)
    assert not res["ok"]


def test_above_threshold_pointer_mode_skips_edge_diff():
    """Area-level diagrams are not module graphs; in pointer mode the mermaid
    edge diff is skipped rather than misread as hallucinations."""
    ir = _ir(10, edges=[("m0", "m1")])
    doc = POINTER_DOC + ("\n```mermaid\ngraph LR\n"
                         '    a["Screens"] --> b["Shared logic"]\n```\n')
    res = sd.diff(ir, doc, None, threshold=5)
    assert res["ok"], res


# --- the threshold declaration (D11, OQ-207.1) ------------------------------

def test_threshold_reads_declared_bar_from_standards_file(tmp_path):
    std = tmp_path / "docs" / "standards"
    std.mkdir(parents=True)
    (std / "coding-standards.md").write_text(
        "prose\n\nsynthesis: inventory-threshold <= 7\n", encoding="utf-8")
    assert sd.load_threshold(str(tmp_path)) == 7


def test_threshold_defaults_when_undeclared(tmp_path):
    assert sd.load_threshold(str(tmp_path)) == sd.DEFAULT_INVENTORY_THRESHOLD


def test_default_threshold_leaves_this_repo_below_the_line():
    """D10/D11: nothing changes today for any existing project — this repo's
    own module count sits under the default with headroom. Read fresh from the
    live IR at test time, never carried (INC-203 KH-2)."""
    import json
    ir_path = os.path.join(os.path.dirname(TOOLS), "..", "docs", "architecture",
                           "generated", "architecture-ir.json")
    with open(ir_path, encoding="utf-8") as fh:
        n = len(json.load(fh)["modules"])
    assert n < sd.DEFAULT_INVENTORY_THRESHOLD
