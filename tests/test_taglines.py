"""Typed tag-line grammar tests — foundation primitive (preserve-list §1.1).
Hard-won lesson #6: structured grammars define + test their EMPTY case."""
import taglines


def test_note_line_roundtrip():
    line = taglines.format_note_line("ACTION", "rename the config key",
                                     source="F015", role="Architect", date="2026-04-12")
    parsed = taglines.parse_note_line(line)
    assert parsed == {"tag": "ACTION", "desc": "rename the config key",
                      "source": "F015", "role": "Architect", "date": "2026-04-12"}


def test_note_tags_closed_vocabulary():
    assert taglines.parse_note_line("- [SHRUG] whatever (From X — Y — 2026-01-01)") is None
    for tag in ("ACTION", "INFO", "DONE", "OBSOLETE"):
        assert taglines.parse_note_line(
            f"- [{tag}] thing (From F001 — Lead — 2026-01-01)")["tag"] == tag


def test_prose_is_never_a_tag_line():
    assert taglines.parse_note_line("we should [ACTION] this later") is None
    assert taglines.parse_typed_line("This has a colon: but is prose sentence") is None


def test_typed_line_parse():
    assert taglines.parse_typed_line("verdict: approved") == ("verdict", "approved")
    assert taglines.parse_typed_line("spec-compliance: meets-spec") == ("spec-compliance", "meets-spec")
    assert taglines.parse_typed_line("  finding: 🔴 1 src/x.py:9 — broken") == (
        "finding", "🔴 1 src/x.py:9 — broken")


def test_marker_block_extraction_and_empty_case():
    doc = "pre\n<!-- FRIDAY-CLAIMS:BEGIN -->\nstack: flask@3\n<!-- FRIDAY-CLAIMS:END -->\npost\n"
    assert taglines.block_lines(doc, "FRIDAY-CLAIMS") == ["stack: flask@3"]
    empty_doc = "<!-- FRIDAY-CLAIMS:BEGIN -->\n<!-- FRIDAY-CLAIMS:END -->\n"
    assert taglines.block_lines(empty_doc, "FRIDAY-CLAIMS") == []      # empty ≠ error
    assert taglines.block_lines("no block here", "FRIDAY-CLAIMS") is None  # absent ≠ empty


def test_scan_notes_empty_case():
    assert taglines.scan_notes("just prose\nno tags anywhere\n") == []
