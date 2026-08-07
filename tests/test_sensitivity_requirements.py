"""INC-108 FR-108.4 (make-or-break) — the answer reaches the spec, not only
the record.

The audited project's schema comment is what 'the record captures it anyway'
produces (KH-2): a correct classification, in the right file, consumed by
nothing. The declaration points at numbered requirements; this check makes
the pointing verifiable both ways — a listed id must exist in a real oracle,
and a declaration carrying postures with no requirement at all is INCOMPLETE
by default, never quietly fine. Whether one answer IS a posture is the
model's judgement; the default here is loud.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import sensitivity_declaration as sd  # noqa: E402


ANSWERS = {
    "at-rest": "R2 server-side encryption, verified",
    "copies": "cites project-copies",
    "deletion": "withdrawal wipes the live row; dump residue lives the window",
    "reach": "admin and owner",
    "basis": "explicit consent",
    "told": "privacy page names the window",
}
NA = {k: "not-applicable — fixture store holds no per-person rows"
      for k in ANSWERS}


def _root(tmp_path, oracle_ids=("FR-9.1", "S-9.2")):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    body = "\n".join(f"- **{i} — a requirement.** Text." for i in oracle_ids)
    (root / "docs" / "INC-9.md").write_text("# INC-9\n" + body + "\n",
                                            encoding="utf-8")
    return str(root)


def test_listed_ids_found_in_the_oracle_is_clean(tmp_path):
    root = _root(tmp_path)
    sd.declare(root, store="s", store_class="health", answers=ANSWERS,
               requirements=["FR-9.1", "S-9.2"], when="2026-08-04")
    out = sd.requirements_check(root, oracles=[os.path.join(root, "docs", "INC-9.md")])
    assert out["clean"] is True, out["findings"]


def test_a_dangling_requirement_id_is_a_finding(tmp_path):
    """A declaration pointing at FR-9.9 that no oracle carries is a pointer
    into nothing — worse than none, because it reads as covered."""
    root = _root(tmp_path)
    sd.declare(root, store="s", store_class="health", answers=ANSWERS,
               requirements=["FR-9.9"], when="2026-08-04")
    out = sd.requirements_check(root, oracles=[os.path.join(root, "docs", "INC-9.md")])
    assert out["clean"] is False
    assert any(f["kind"] == "dangling-requirement" and "FR-9.9" in f["detail"]
               for f in out["findings"])


def test_postures_with_no_requirement_is_incomplete(tmp_path):
    """AC-108.4's second direction: the answers landed only in the
    declaration. Reported incomplete, naming the store — the schema-comment
    failure, caught at the moment it is cheapest to fix."""
    root = _root(tmp_path)
    sd.declare(root, store="s", store_class="health", answers=ANSWERS,
               requirements=[], when="2026-08-04")
    out = sd.requirements_check(root, oracles=[os.path.join(root, "docs", "INC-9.md")])
    assert out["clean"] is False
    assert any(f["kind"] == "declaration-only" and f["store"] == "s"
               for f in out["findings"])


def test_all_not_applicable_needs_no_requirement(tmp_path):
    """FR-108.4: a not-applicable answer produces no requirement and is
    recorded as itself — a store with nothing to hold owes no FR line."""
    root = _root(tmp_path)
    sd.declare(root, store="s", store_class="credentials", answers=NA,
               requirements=[], when="2026-08-04")
    out = sd.requirements_check(root, oracles=[os.path.join(root, "docs", "INC-9.md")])
    assert out["clean"] is True, out["findings"]


def test_unreadable_oracle_is_named_never_folded_into_clean(tmp_path):
    """S-108.2's shape at this seam: an oracle that could not be read is not
    an oracle with no ids in it."""
    root = _root(tmp_path)
    sd.declare(root, store="s", store_class="health", answers=ANSWERS,
               requirements=["FR-9.1"], when="2026-08-04")
    missing = os.path.join(root, "docs", "NOPE.md")
    out = sd.requirements_check(root, oracles=[missing])
    assert out["clean"] is False
    assert any(f["kind"] == "unread-oracle" for f in out["findings"])
