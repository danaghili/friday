"""INC-107 FR-107.1/107.2/107.8 — the loose-deferral scan.

The mechanical half of the fourth prose reader: comment text only, the
contiguous comment block as the reported unit, a deliberately generous
vocabulary matched against the block's whitespace-flattened text (a phrase
that wraps across comment lines is still the phrase — INC-110 KH-4's lesson
applied at birth), and everything the scan could not reach named as itself.
The reading, the home test and the answered set are the model half and live
elsewhere; nothing here judges a candidate.
"""
import json
import os
import stat
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import loose_deferral_scan as scan_mod  # noqa: E402


def _scan(root):
    return scan_mod.scan(str(root))


def test_block_is_the_unit_several_hits_one_candidate(tmp_path):
    (tmp_path / "route.ts").write_text(
        "// INTENTIONALLY MINIMAL health check.\n"
        "// The trade-off: liveness only, no DB ping.\n"
        "// TODO: add the deeper check.\n"
        "// Revisit when both conditions hold.\n"
        "export const ok = 1\n", encoding="utf-8")
    out = _scan(tmp_path)
    assert len(out["candidates"]) == 1
    c = out["candidates"][0]
    assert c["file"] == "route.ts"
    assert (c["line_start"], c["line_end"]) == (1, 4)
    assert "INTENTIONALLY MINIMAL" in c["text"]


def test_flagship_shape_marker_deep_in_block_returns_whole_block(tmp_path):
    (tmp_path / "health.py").write_text(
        "# The endpoint guarantees process liveness only.\n"
        "# The trade-off was accepted at design time.\n"
        "# See 3-architecture.md section 'When to revisit'.\n"
        "x = 1\n", encoding="utf-8")
    out = _scan(tmp_path)
    assert len(out["candidates"]) == 1
    c = out["candidates"][0]
    assert c["line_start"] == 1 and c["line_end"] == 3
    assert "guarantees process liveness" in c["text"]


def test_comment_text_only_string_literals_never_match(tmp_path):
    (tmp_path / "copy.ts").write_text(
        'export const msg = "This video is not yet available";\n'
        'assert(status !== "deferred");\n', encoding="utf-8")
    out = _scan(tmp_path)
    assert out["candidates"] == []


def test_wrapped_phrase_across_comment_lines_still_matches(tmp_path):
    (tmp_path / "menu.tsx").write_text(
        "// This focus handling is a known\n"
        "// gap in the playlist menu.\n"
        "const a = 1\n", encoding="utf-8")
    out = _scan(tmp_path)
    assert len(out["candidates"]) == 1
    assert out["candidates"][0]["line_end"] == 2


def test_not_implemented_idiom_matches_even_wrapped(tmp_path):
    (tmp_path / "state.ts").write_text(
        "/* The refreshing state is defined for forward-compat but is NOT\n"
        "   implemented in this wave; see the architecture note. */\n"
        "type A = 1\n", encoding="utf-8")
    out = _scan(tmp_path)
    assert len(out["candidates"]) == 1
    assert "not implemented" in out["candidates"][0]["markers"]


def test_block_comment_span_is_one_candidate(tmp_path):
    (tmp_path / "player.js").write_text(
        "/* Renewal is deferred to a later\n"
        "   version; no date is set. */\n"
        "let x = 1\n", encoding="utf-8")
    out = _scan(tmp_path)
    assert len(out["candidates"]) == 1
    assert (out["candidates"][0]["line_start"],
            out["candidates"][0]["line_end"]) == (1, 2)


def test_separate_blocks_are_separate_candidates(tmp_path):
    (tmp_path / "webhook.ts").write_text(
        "// TODO (F063): stuck-sending recovery is manual SQL surgery.\n"
        "const a = 1\n"
        "// KNOWN GAP: no focus trap here.\n"
        "const b = 2\n", encoding="utf-8")
    out = _scan(tmp_path)
    assert len(out["candidates"]) == 2


def test_config_comments_are_in_the_hunting_ground(tmp_path):
    (tmp_path / "settings.ini").write_text(
        "# TODO: pin this to the real region post-launch\n"
        "region = eu-west-1\n", encoding="utf-8")
    out = _scan(tmp_path)
    assert len(out["candidates"]) == 1


def test_documents_are_not_hunted(tmp_path):
    (tmp_path / "PLAN.md").write_text(
        "## Known gaps\nTODO: everything here is deferred.\n",
        encoding="utf-8")
    out = _scan(tmp_path)
    assert out["candidates"] == []
    assert all(u != "PLAN.md" for u in out["unparsed"])


def test_unknown_syntax_named_as_unparsed_never_silent(tmp_path):
    (tmp_path / "prog.zig").write_text("// TODO: port this\n",
                                       encoding="utf-8")
    out = _scan(tmp_path)
    assert "prog.zig" in out["unparsed"]
    assert out["candidates"] == []


def test_unreadable_file_named_as_unread(tmp_path):
    p = tmp_path / "locked.py"
    p.write_text("# TODO: fix\n", encoding="utf-8")
    os.chmod(p, 0)
    try:
        out = _scan(tmp_path)
        assert "locked.py" in out["unread"]
    finally:
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)


def test_value_shaped_token_reported_by_location_never_reproduced(tmp_path):
    # keyish prefix + long hex run — value-shaped to the scanner, but NOT
    # a real vendor key pattern (GitHub push protection blocks those even
    # as fixtures).
    planted = "sk_9f8e7d6c5b4a3210fedcba9876543210"
    (tmp_path / "deploy.env.example").write_text(
        "# TODO: rotate %s before launch\nKEY=placeholder\n" % planted,
        encoding="utf-8")
    out = _scan(tmp_path)
    assert len(out["candidates"]) == 1
    dumped = json.dumps(out)
    assert planted not in dumped
    assert "value withheld" in out["candidates"][0]["text"]


def test_empty_case_states_what_was_scanned(tmp_path):
    (tmp_path / "clean.py").write_text("x = 1  # plain comment\n",
                                       encoding="utf-8")
    out = _scan(tmp_path)
    assert out["candidates"] == []
    assert out["scanned_files"] >= 1


def test_cli_emits_json(tmp_path):
    (tmp_path / "a.py").write_text("# TODO: later pass\n", encoding="utf-8")
    tool = os.path.join(os.path.dirname(__file__), "..", "tools",
                        "loose_deferral_scan.py")
    r = subprocess.run([sys.executable, tool, "--root", str(tmp_path),
                        "--json"], capture_output=True, text=True)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert len(out["candidates"]) == 1
