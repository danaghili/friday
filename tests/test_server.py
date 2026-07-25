"""MCP core — the reader triad + path-safety (tools/doc-index/server.py).

The marquee JIT retrieval surface was shipped untested; these pin its
load-bearing contracts: exact-after-normalization heading match (NOT fuzzy),
the structured-refusal path containment (incl. the `plugin:` regime), and the
"index trouble never breaks a reader" guarantee.
"""
import server


def _doc(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "# Title\n\nintro\n\n## Solution Strategy\nbody line here\n\n"
        "## Constraints\ncc\n", encoding="utf-8")
    return str(tmp_path), "d.md"


# --- safe_doc_path: structured refusals, never raw exceptions ---------------

def test_safe_doc_path_success(tmp_path):
    root, rel = _doc(tmp_path)
    real, err = server.safe_doc_path(root, rel)
    assert err is None and real.endswith("d.md")


def test_safe_doc_path_directory_refused(tmp_path):
    (tmp_path / "sub").mkdir()
    real, err = server.safe_doc_path(str(tmp_path), "sub")
    assert real is None and err["error"] == "is_a_directory"


def test_safe_doc_path_missing_refused(tmp_path):
    real, err = server.safe_doc_path(str(tmp_path), "nope.md")
    assert real is None and err["error"] == "file_not_found"


def test_safe_doc_path_non_markdown_refused(tmp_path):
    (tmp_path / "x.txt").write_text("hi", encoding="utf-8")
    real, err = server.safe_doc_path(str(tmp_path), "x.txt")
    assert real is None and err["error"] == "not_markdown"


def test_safe_doc_path_escape_refused(tmp_path):
    root, _ = _doc(tmp_path)
    real, err = server.safe_doc_path(root, "../secrets.md")
    assert real is None and err["error"] == "path_outside_project"


def test_plugin_prefix_escape_refused(tmp_path):
    # plugin:../<x> resolves outside <plugin_root>/docs and is refused up front,
    # before any filesystem read — the containment guard, not a missing-file miss.
    real, err = server.safe_doc_path(str(tmp_path), "plugin:../README.md")
    assert real is None and err["error"] == "path_outside_project"


# --- reader triad -----------------------------------------------------------

def test_list_sections_maps_headings(tmp_path):
    root, rel = _doc(tmp_path)
    out = server.handle_list_sections(root, {"path": rel}, {})
    assert out["ok"] is True
    texts = [h["text"] for h in out["headings"]]
    assert "Solution Strategy" in texts and "Constraints" in texts


def test_get_section_exact_after_normalization(tmp_path):
    root, rel = _doc(tmp_path)
    # numbering + case + collapsed whitespace normalize away — still an EXACT match
    out = server.handle_get_section(
        root, {"path": rel, "heading": "3. solution   STRATEGY"}, {})
    assert out["ok"] is True and "body line here" in out["content"]
    assert out["cite"].startswith(rel + ":")


def test_get_section_miss_returns_available_not_fuzzy(tmp_path):
    root, rel = _doc(tmp_path)
    # a prefix is NOT a fuzzy match — miss, with the real headings handed back
    out = server.handle_get_section(root, {"path": rel, "heading": "Solution"}, {})
    assert out["ok"] is False and out["error"] == "heading_not_found"
    assert "query_norm" in out
    assert any(h["text"] == "Solution Strategy" for h in out["available"])


def test_search_in_finds_and_cites(tmp_path):
    root, rel = _doc(tmp_path)
    out = server.handle_search_in(root, {"path": rel, "query": "body"}, {})
    assert out["ok"] is True and out["match_count"] >= 1
    assert out["matches"][0]["cite"].startswith(rel + ":")


# --- call_tool: dispatch + the "index trouble never breaks a reader" rule ----

def test_call_tool_unknown_tool(tmp_path):
    out = server.call_tool("no_such_tool", {}, None, str(tmp_path))
    assert out["ok"] is False and out["error"] == "unknown_tool"


def test_call_tool_reader_survives_broken_index(tmp_path):
    # conn=None makes ensure_fresh raise; the reader must still serve its file
    # (advisory index: content retrieval live-parses and never depends on it).
    root, rel = _doc(tmp_path)
    out = server.call_tool("list_sections", {"path": rel}, None, root)
    assert out["ok"] is True
    assert any(h["text"] == "Constraints" for h in out["headings"])
