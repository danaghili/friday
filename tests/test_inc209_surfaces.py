"""INC-209 FR-209.2 / FR-209.5 / AC-209.5 / AC-209.6 — the lane surfaces.

Two guarantees are pinned here, and they pull in opposite directions on purpose.

The first is COVERAGE: every door the doctrine names must actually be wired, and
the setup agent's announcement must carry all four of its pieces. The INC-208 close
learned this the expensive way — a batch edit keyed on a shared phrase reached the
playbooks that happened to share the wording and silently missed six lanes that
genuinely dispatch. The requirement said "every lane", so the test says every lane,
by name, from the doctrine's own list.

The second is RESTRAINT: no surface may restate a value the doctrine owns (FR-209.1,
D1). Two copies of a number are two numbers that can drift apart, and the drift
would be invisible — both files would look right on their own.

AC-209.6's greenfield case is proven against a fixture shaped like what init writes
(a permissions block, no env home yet), because that is the file the strategist
hands to the seeding step.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import compaction_seed as seed  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_STRATEGIST = os.path.join(_ROOT, "agents", "bootstrap", "strategist.md")
_CONTRACT = os.path.join(_ROOT, "docs", "contracts", "claude-scaffold.md")

# The doors the doctrine names as permitted to take the exception, and the one it
# names as needing none. Kept as an explicit list so adding a door to the contract
# without wiring it is a test failure rather than a quiet gap.
_RETROFIT_DOORS = ["adopt", "backfill", "patch"]
_NO_EXCEPTION_NEEDED = ["init"]


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _lane(name):
    return os.path.join(_ROOT, "skills", name, "SKILL.md")


# --------------------------------------------------------------------------
# FR-209.5 — the doors, named exhaustively and actually wired
# --------------------------------------------------------------------------

def test_every_retrofit_door_is_wired_to_the_tool():
    """FR-209.5 — each named door reaches the seed tool, not a remembered habit."""
    for door in _RETROFIT_DOORS:
        text = _read(_lane(door))
        assert "compaction_seed.py" in text, f"/friday:{door} does not reach the seed tool"
        assert "--should-offer" in text, (
            f"/friday:{door} does not ask before offering — a door that skips the "
            "should-offer read will re-ask a project that already declined"
        )
        assert "--consented" in text, f"/friday:{door} does not name the consent flag"
        assert "--decline" in text, f"/friday:{door} does not record a no"


def test_every_retrofit_door_cites_the_contract_rather_than_restating_it():
    """D-0083 — one home for the rule; each door is a pointer to it."""
    for door in _RETROFIT_DOORS:
        text = _read(_lane(door))
        assert "claude-scaffold.md" in text, f"/friday:{door} does not cite the doctrine"


def test_the_greenfield_door_is_not_wired_to_the_exception():
    """FR-209.5 — init writes the file fresh, so it must not carry retrofit wiring.

    A door that does not need the exception and takes it anyway is how a narrow
    exception becomes a habit (S-209.5).
    """
    for door in _NO_EXCEPTION_NEEDED:
        path = _lane(door)
        if not os.path.isfile(path):
            continue
        assert "--consented" not in _read(path), (
            f"/friday:{door} names the consent flag, but greenfield needs no exception"
        )


def test_the_doors_resolve_the_tool_through_the_plugin_root():
    """INC-208 KH-3 — a bare relative path resolves against the PM's project.

    friday's own suite runs inside this repo, where a relative path happens to
    resolve, so this failure only ever shows up on someone else's machine.
    """
    surfaces = [_lane(d) for d in _RETROFIT_DOORS] + [_STRATEGIST]
    for path in surfaces:
        for line in _read(path).splitlines():
            if "compaction_seed.py" in line:
                assert "${CLAUDE_PLUGIN_ROOT}" in line, (
                    f"{os.path.relpath(path, _ROOT)} cites the tool by a bare path: "
                    f"{line.strip()}"
                )


# --------------------------------------------------------------------------
# FR-209.2 / AC-209.5 — the announcement's four pieces
# --------------------------------------------------------------------------

def test_the_setup_agent_announcement_carries_all_four_pieces():
    """AC-209.5 — read directly out of the surface, not summarised.

    The four: what it does, what it assumes, that it is a shared default an
    individual may override in their own personal file, and how to remove it.
    """
    text = _read(_STRATEGIST)
    assert "compaction guardrail" in text, "§ 7a never mentions the guardrail"
    section = text[text.index("compaction guardrail"):]
    section = section[:4000]
    assert "tidy up their own context early" in section, "the announcement omits what it does"
    assert "assumes" in section, "the announcement omits the assumption it carries"
    assert "settings.local.json" in section, (
        "the announcement omits that an individual may override it in their own file"
    )
    assert "remove it permanently" in section, "the announcement omits how to remove it"


def test_the_setup_agent_states_the_assumption_rather_than_detecting_it():
    """KH-3 — an undetectable assumption named plainly is honest; dressed as
    detection it is not. Pins that the surface says so in as many words."""
    text = _read(_STRATEGIST)
    section = text[text.index("compaction guardrail"):][:4000]
    assert "never detected" in section or "not detected" in section


# --------------------------------------------------------------------------
# FR-209.1 — no surface carries a second copy of the values
# --------------------------------------------------------------------------

def test_no_lane_surface_restates_a_value_the_doctrine_owns():
    """FR-209.1, D1 — the drift this prevents would be invisible in both files."""
    values = seed.doctrine_values()
    surfaces = [_STRATEGIST] + [_lane(d) for d in _RETROFIT_DOORS + _NO_EXCEPTION_NEEDED]
    for path in surfaces:
        if not os.path.isfile(path):
            continue
        text = _read(path)
        for key, value in values.items():
            assert f'"{value}"' not in text, (
                f"{os.path.relpath(path, _ROOT)} restates the value of {key} — the "
                "doctrine is the single home of it (FR-209.1)"
            )


def test_only_the_doctrine_states_the_values():
    """The other half of the same guarantee, from the doctrine's side."""
    values = seed.doctrine_values()
    text = _read(_CONTRACT)
    for key, value in values.items():
        assert f'`"{value}"`' in text, f"the doctrine no longer carries {key}'s value"


# --------------------------------------------------------------------------
# AC-209.6 — the greenfield result
# --------------------------------------------------------------------------

def test_a_greenfield_scaffold_carries_the_pair_and_its_explanation(tmp_path):
    """AC-209.6 — against a fixture shaped like what init writes."""
    claude = tmp_path / ".claude"
    claude.mkdir()
    # what the strategist has written by the time seeding runs: permissions, no env
    (claude / "settings.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash(pytest:*)"]}}, indent=2) + "\n",
        encoding="utf-8",
    )

    result = seed.apply(str(tmp_path), greenfield=True)
    assert result["applied"] is True
    assert result["comment_placed"] is True

    parsed = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    assert parsed["env"] == seed.doctrine_values()
    assert "compaction" in parsed["$comment"].lower()
    assert parsed["permissions"] == {"allow": ["Bash(pytest:*)"]}

    # S-209.2 — the personal file was not created, listed rather than assumed
    assert sorted(os.listdir(str(claude))) == ["settings.json"]


def test_greenfield_and_consent_are_separate_authorities(tmp_path):
    """Neither flag may stand in for the other.

    Greenfield is 'friday is writing this file right now'; consent is 'the PM said
    yes about a file that is already the project's'. Collapsing them would let the
    init path silently authorise a retrofit.
    """
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "settings.json").write_text('{\n  "env": {}\n}\n', encoding="utf-8")
    before = (claude / "settings.json").read_bytes()

    assert seed.apply(str(tmp_path))["reason"] == "no-consent"
    assert (claude / "settings.json").read_bytes() == before
