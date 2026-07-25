"""Logic-core #1 — normalize_heading() + the exact-after-normalization matcher.
The retrieval design is the whole point (NOT fuzzy, NOT embeddings): these
tests pin the normalization order and the no-fuzzy rule before the port."""
import mdparse


def test_normalize_order_numbering_emphasis_case():
    assert mdparse.normalize_heading("## **3. Foo**".lstrip("# ")) == "foo"
    assert mdparse.normalize_heading("2.3 Solution  Overview") == "solution overview"
    assert mdparse.normalize_heading("`Config` Surface ##") == "config surface"
    assert mdparse.normalize_heading("C#") == "c#"          # closing-hash strip is whitespace-gated
    assert mdparse.normalize_heading("1.5x speedup") == "1.5x speedup"  # mid-text numbering untouched


def test_exact_match_only_no_fuzzy():
    doc = mdparse.parse_document(b"# T\n\n## Solution Strategy\nbody\n\n## Constraints\nc\n")
    h, dups = mdparse.find_section(doc, "3. solution   strategy")
    assert h is not None and h.text == "Solution Strategy" and dups == 1
    miss, _ = mdparse.find_section(doc, "Solution")   # prefix is NOT a match
    assert miss is None
    miss2, _ = mdparse.find_section(doc, "Solution Stratgy")  # typo is NOT a match
    assert miss2 is None


def test_fenced_code_headings_ignored_and_spans():
    raw = b"# A\n\n## One\n```sh\n# not a heading\n```\n\n### child\nx\n\n## Two\ny\n"
    doc = mdparse.parse_document(raw)
    texts = [h.text for h in doc.headings]
    assert texts == ["A", "One", "child", "Two"]
    one = doc.headings[1]
    assert "child" in mdparse.section_text(doc, one)   # H2 span includes child H3
    assert "## Two" not in mdparse.section_text(doc, one)


def test_duplicate_headings_first_wins_with_count():
    doc = mdparse.parse_document(b"## X\na\n## X\nb\n")
    h, dups = mdparse.find_section(doc, "x")
    assert h.line == 1 and dups == 2
