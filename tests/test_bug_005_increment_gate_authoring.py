"""BUG-005 — the increment gate demanded a pointer that doctrine forbids yet.

**The defect.** `hooks/spec_write_guard.py` always passed `--parent` to
`tools/doc_gate.py`, and the gate treats the parent's `## Increments` pointer as
unconditionally required whenever a parent is supplied. But the pointer is an
**approval-time** artifact: D-0121 and D-0076 refuse it before the PM approves,
and all nine live TSOW pointers carry an `(approved <date>)` stamp. The guard
fires on the *write*. So the only moment the gate ran was the only moment it
could not pass, and every increment ever authored had to be waved through by
hand — a gate that reads as enforcing and in practice is ignored, which is the
exact failure class this repo keeps removing.

**Isolated at diagnosis**, same file, only the parent differing:

    doc_gate --kind increment --file docs/increments/INC-201.md
      → valid-pass, "increment OK: 32 dotted ID(s), pointer-linked"
    …same file, --parent docs/TECHNICAL_SOW.md (no pointer yet)
      → valid-fail, "…has no pointer to INC-201.md…"
    …same file, --parent <scratch TSOW carrying the pointer>
      → valid-pass

**The sharper half.** `spec_write_guard.py` is the ONLY live caller of
`doc_gate.py` for increments. Nothing checked the pointer when an increment
actually fed a build. So the clause did not merely fire at the wrong moment —
it fired at the one moment it could not pass and never at the moment its own
error text names ("an unapproved orphan increment cannot feed a build").

**The fix, PM-chosen: move the check, do not delete it.** Authoring stops
enforcing the pointer; the requirement moves to consumption, where consumption
is identified mechanically — an increment whose dotted IDs carry dispositions in
`docs/reviews/coverage.md` is one a build has consumed, and dispositions are the
build's own artifact, not prose. So there is no judgment call and no new
vocabulary.

Note `tests/test_guard_spec_write.py::test_orphan_increment_is_blocked` asserted
the defective behaviour and is inverted by this fix. A test changed to make a
fix pass is normally a smell; here the test encoded the bug.
"""
import json
import os
import re
import subprocess
import sys

from guardkit import BUILD_ROOT, run_hook

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GOOD_SPEC = """# TSOW — testproj

provenance: born-from-discovery

## Requirements
- **FR-1** The thing works.
"""

GOOD_INCREMENT = """# INC-1

## Requirements
- **FR-1.1** A slice of the thing.
"""

PARENT_WITH_POINTER = GOOD_SPEC + "\n## Increments\n- docs/increments/INC-1.md\n"


def _proj(tmp_path, *, tsow_text=GOOD_SPEC):
    root = tmp_path / "proj"
    (root / "docs" / "increments").mkdir(parents=True)
    (root / "docs" / "TECHNICAL_SOW.md").write_text(tsow_text, encoding="utf-8")
    (root / "CLAUDE.md").write_text(
        "# proj\n\n<!-- FRIDAY-CLAIMS:BEGIN -->\nstack: python3\n"
        "<!-- FRIDAY-CLAIMS:END -->\n", encoding="utf-8")
    return root


def _event(root, path):
    return {"hook_event_name": "PostToolUse", "tool_name": "Write",
            "cwd": str(root), "tool_input": {"file_path": str(path)}}


# --- the reproduction ---------------------------------------------------------------

def test_authoring_an_increment_is_not_blocked_for_the_missing_pointer(tmp_path):
    """THE BUG. A freshly written increment has no TSOW pointer *by doctrine* —
    the lead appends it at PM approval. The write-guard must not refuse it."""
    proj = _proj(tmp_path)  # deliberately no `## Increments` pointer
    inc = proj / "docs" / "increments" / "INC-1.md"
    inc.write_text(GOOD_INCREMENT, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "spec_write_guard.py", _event(proj, inc))
    assert p.stdout.strip() == "", (
        "an increment being authored was blocked for a pointer that cannot "
        f"exist yet: {p.stdout}")


def test_a_malformed_increment_is_still_blocked(tmp_path):
    """The fix must not turn the guard off. An undotted requirement ID is the
    increment kind's own lie, and it still has to be caught while authoring."""
    proj = _proj(tmp_path)
    inc = proj / "docs" / "increments" / "INC-1.md"
    inc.write_text(GOOD_INCREMENT.replace("- **FR-1.1**", "- **FR-1**"),
                   encoding="utf-8")
    p = run_hook(BUILD_ROOT, "spec_write_guard.py", _event(proj, inc))
    out = json.loads(p.stdout)
    assert out["decision"] == "block", out


def test_a_pointer_linked_increment_is_still_untouched(tmp_path):
    """The post-approval state keeps passing — the fix loosens one clause, not
    the gate."""
    proj = _proj(tmp_path, tsow_text=PARENT_WITH_POINTER)
    inc = proj / "docs" / "increments" / "INC-1.md"
    inc.write_text(GOOD_INCREMENT, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "spec_write_guard.py", _event(proj, inc))
    assert p.stdout.strip() == ""


# --- the moved check: the pointer is enforced at CONSUMPTION ------------------------

_DOTTED = re.compile(r"^disposition:\s+(?:FR|AC|S|NFR|US)-(\d+)\.\d+\b", re.MULTILINE)


def _consumed_increments(root):
    """Increment numbers a build has actually consumed.

    Identified mechanically: an increment whose dotted IDs carry dispositions in
    the coverage ledger is one a build has fed on — dispositions are written by
    the build, so this needs no prose and no new vocabulary. Returns a set of
    zero-padded increment ids ("201", "008").
    """
    cov = os.path.join(root, "docs", "reviews", "coverage.md")
    try:
        with open(cov, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return set()
    return {n.zfill(3) for n in _DOTTED.findall(text)}


def _gate(root, inc_path):
    proc = subprocess.run(
        [sys.executable, os.path.join(root, "tools", "doc_gate.py"),
         "--kind", "increment", "--file", inc_path,
         "--parent", os.path.join(root, "docs", "TECHNICAL_SOW.md")],
        capture_output=True, text=True, cwd=root)
    return json.loads(proc.stdout)


def test_the_consumption_rule_is_vacuous_on_an_empty_tree(tmp_path):
    """Empty case: no coverage ledger at all yields no consumed increments,
    rather than an exception or a false positive."""
    assert _consumed_increments(str(tmp_path)) == set()
