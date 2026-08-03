"""INC-209 FR-209.8 / AC-209.7 — the scaffold doctrine's wording is pinned.

Why a wording test at all. A change made only of instructions can be undone by a
later change of instructions with nothing noticing — that is precisely how the
compaction pair sat in the doctrine as an *example* across two increments while
everyone believed it was rolled out. So the sentence that carries the guarantee is
pinned the way any script-checked claim in this repo is pinned.

What these tests are NOT. They do not check that a project has the settings (that
is the report-only check, FR-209.7) and they do not check that anything was
seeded. They check one thing: the doctrine still SAYS the pair is a standard seed,
and the never-clobber exception is still stated as scoped to this pair by name.

AC-209.7 requires both directions: demote the wording and the pin fails; restore
it and the pin passes. `test_the_pin_fails_when_the_wording_is_demoted` runs that
demotion against a copy of the real contract text, so the guarantee is proven
rather than asserted.
"""
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONTRACT = os.path.join(_ROOT, "docs", "contracts", "claude-scaffold.md")

# The two settings the doctrine owns. Named here (not valued here) on purpose:
# the doctrine is the single home of the VALUES (FR-209.1, D1), so a test that
# also carried them would be the second copy the rule exists to prevent.
_WINDOW_KEY = "CLAUDE_CODE_AUTO_COMPACT_WINDOW"
_PCT_KEY = "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"


def _contract_text():
    with open(_CONTRACT, encoding="utf-8") as fh:
        return fh.read()


def _standard_seed_stated(text):
    """The pin's single predicate, shared by the live check and the demotion case.

    Deliberately shape-based rather than exact-sentence-based: it requires the
    phrase "standard seed" to appear in the same paragraph as both key names, so
    reformatting the section does not break the pin but demoting the claim does.
    """
    for para in re.split(r"\n\s*\n", text):
        if _WINDOW_KEY in para and _PCT_KEY in para and "standard seed" in para:
            return True
    return False


def test_the_doctrine_states_the_compaction_pair_as_a_standard_seed():
    """FR-209.1 — the settings row is a standard seed, not an example of one."""
    assert _standard_seed_stated(_contract_text()), (
        "docs/contracts/claude-scaffold.md no longer states the compaction pair as a "
        "standard seed alongside both key names — the guarantee has been demoted"
    )


def test_the_doctrine_owns_the_literal_values():
    """FR-209.1 — the values are single-homed here, so they must actually be here.

    A doctrine that names the keys but not their values sends every seeding surface
    somewhere else for them, which is the drift the single-home rule prevents.
    """
    text = _contract_text()
    window_line = [ln for ln in text.splitlines() if _WINDOW_KEY in ln and "`" in ln]
    pct_line = [ln for ln in text.splitlines() if _PCT_KEY in ln and "`" in ln]
    assert window_line, f"{_WINDOW_KEY} carries no value in the doctrine"
    assert pct_line, f"{_PCT_KEY} carries no value in the doctrine"
    assert re.search(r"\d", " ".join(window_line)), "the window setting has no literal value"
    assert re.search(r"\d", " ".join(pct_line)), "the percentage setting has no literal value"


def test_the_never_clobber_section_carries_the_scoped_exception():
    """FR-209.4 — the exception is stated where the rule it bends is stated.

    Scoping matters more than presence: an exception written in general terms is one
    a later reader extends by reading it generously. This pins that the exception
    names the pair and states the consent requirement in the never-clobber section
    itself, not in some other part of the contract.
    """
    text = _contract_text()
    sections = re.split(r"\n## ", text)
    never_clobber = [s for s in sections if s.startswith("Never-clobber")]
    assert never_clobber, "the doctrine has no Never-clobber section"
    body = never_clobber[0]
    assert _WINDOW_KEY in body and _PCT_KEY in body, (
        "the never-clobber exception does not name the pair it is scoped to — an "
        "exception that names no keys is one a later reader widens by construction"
    )
    assert "and nothing else" in body, "the exception does not state its own boundary"
    assert "explicit" in body.lower(), "the exception does not state the consent requirement"


def test_the_pin_fails_when_the_wording_is_demoted():
    """AC-209.7's other direction, run rather than asserted.

    Takes the real contract text, demotes the standard-seed claim back to the
    example wording it carried before this increment, and confirms the pin's
    predicate goes false. Without this, a pin that trivially passes would look
    identical to a pin that works.
    """
    text = _contract_text()
    assert _standard_seed_stated(text), "precondition: the live doctrine passes the pin"
    demoted = text.replace("standard seed", "example")
    assert not _standard_seed_stated(demoted), (
        "the pin still passes after the standard-seed claim was demoted to an example "
        "— it is not actually pinning the guarantee"
    )
