"""INC-008 FR-8.5 / AC-8.1 / AC-8.2 / KH-1 / KH-3 — the enforcement gate checker.

Test-first, and this is the MAKE-OR-BREAK round-trip: the deterministic gate that
decides whether every current breach is DISPOSITIONED. It blocks the process, not
the flaky finding-set — a reproducible verdict on a non-reproducible judge output.

The round-trip proven here over real files:
  measure → (judge envelope) → the gate confirms each breach is justified-and-
  recorded OR fixed-and-re-measured-clean → pass; anything un-dispositioned → fail.

Pin #2 (re-measure-confirms-clean): a breach that has actually been fixed no
longer measures over the bar, so it drops out of the current-breach set and the
gate passes; an "unjustified" breach that is still over the bar is un-dispositioned
and the gate fails.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import maintainability_gate_check as gate  # noqa: E402

_CS = (
    "# Coding standards\n"
    "<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
    "maintainability: param-count <= 4\n"
    "<!-- FRIDAY-MAINTAINABILITY:END -->\n"
)
# one function that breaches param-count (7 > 4)
_SRC_BREACH = "def big(a, b, c, d, e, f, g):\n    return a\n"
# the same file, fixed (2 params, under the bar)
_SRC_FIXED = "def big(a, b):\n    return a\n"


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def _envelope(location, disposition):
    return (
        "maintainability-envelope: source=close count=1 armed=false\n\n"
        f"## M-1 — param-count 7 > 4 @ {location} (disposition: {disposition})\n"
        "standard: coding-standards.md §Size — parameter count <= 4\n"
        "reason: reasoned disposition for the test\n"
        "floor: none\n"
    )


def test_no_bars_passes(tmp_path):
    src = _write(tmp_path, "m.py", _SRC_BREACH)
    cs = _write(tmp_path, "cs.md", "# standards, no bars block\n")
    assert gate.check(root=str(tmp_path), standards=cs, envelope=None,
                      files=[src])["verdict"] == "valid-pass"


def test_breach_with_no_envelope_is_undispositioned(tmp_path):
    src = _write(tmp_path, "m.py", _SRC_BREACH)
    cs = _write(tmp_path, "cs.md", _CS)
    res = gate.check(root=str(tmp_path), standards=cs, envelope=None, files=[src])
    assert res["verdict"] == "valid-fail" and res["undispositioned"]


def test_justified_breach_passes(tmp_path):
    src = _write(tmp_path, "m.py", _SRC_BREACH)
    cs = _write(tmp_path, "cs.md", _CS)
    loc = f"{src}:1:big"
    env = _write(tmp_path, "env.md", _envelope(loc, "justified"))
    assert gate.check(root=str(tmp_path), standards=cs, envelope=env,
                      files=[src])["verdict"] == "valid-pass"


def test_relative_envelope_location_matches_absolute_measurement(tmp_path):
    """Surfaced live 2026-07-28 (INC-008 validation pass): the judge's envelope
    carries root-relative locations while the gate's own measurer run emits
    absolute paths — so every justified disposition failed to match and the
    entire breach set counted as un-dispositioned. Location identity must be
    normalized to root-relative on BOTH sides of the comparison."""
    src = _write(tmp_path, "m.py", _SRC_BREACH)
    cs = _write(tmp_path, "cs.md", _CS)
    env = _write(tmp_path, "env.md", _envelope("m.py:1:big", "justified"))
    assert gate.check(root=str(tmp_path), standards=cs, envelope=env,
                      files=[src])["verdict"] == "valid-pass"


def test_unjustified_but_still_breaching_fails(tmp_path):
    # the judge said "fix it" but it is still over the bar -> un-dispositioned
    src = _write(tmp_path, "m.py", _SRC_BREACH)
    cs = _write(tmp_path, "cs.md", _CS)
    loc = f"{src}:1:big"
    env = _write(tmp_path, "env.md", _envelope(loc, "unjustified"))
    res = gate.check(root=str(tmp_path), standards=cs, envelope=env, files=[src])
    assert res["verdict"] == "valid-fail" and res["undispositioned"]


def test_fixed_breach_re_measures_clean_and_passes(tmp_path):
    # Pin #2 / AC-8.2: after a REAL fix the breach is gone from the measured set,
    # so even an "unjustified" envelope entry leaves nothing un-dispositioned.
    src = _write(tmp_path, "m.py", _SRC_FIXED)
    cs = _write(tmp_path, "cs.md", _CS)
    loc = f"{src}:1:big"
    env = _write(tmp_path, "env.md", _envelope(loc, "unjustified"))
    assert gate.check(root=str(tmp_path), standards=cs, envelope=env,
                      files=[src])["verdict"] == "valid-pass"


def test_malformed_envelope_fails_closed_on_a_real_breach(tmp_path):
    src = _write(tmp_path, "m.py", _SRC_BREACH)
    cs = _write(tmp_path, "cs.md", _CS)
    env = _write(tmp_path, "env.md", "this is not a valid envelope\n")
    res = gate.check(root=str(tmp_path), standards=cs, envelope=env, files=[src])
    assert res["verdict"] == "valid-fail"


def test_verdict_is_the_fr61_shape(tmp_path):
    src = _write(tmp_path, "m.py", _SRC_BREACH)
    cs = _write(tmp_path, "cs.md", _CS)
    res = gate.check(root=str(tmp_path), standards=cs, envelope=None, files=[src])
    assert res["verdict"] in ("valid-pass", "valid-fail")
    assert "summary" in res


# --- what identifies "the same breach" (D-0136) -------------------------------------
#
# The old key was the literal `path:line:function` string, which is sensitive to
# exactly the wrong thing: it CHANGES when the code merely moves, and does NOT
# change when the code is rewritten. Both directions are wrong, and both are
# tested here.
#
# The failure was live, twice. Once as absolute-vs-relative paths (2026-07-28,
# fixed by _rel_location above), and again on 2026-07-29 when two settled
# breaches — tools/verify_coverage.py:91:check and
# tools/verify_review_format.py:160:_check_review, judged in the envelope and
# recorded as SD-0014/SD-0015 — re-measured at :112: and :167: after unrelated
# edits above them and were reported as brand new. The natural response, minting
# fresh deviation entries, produced duplicates that had to be withdrawn.

def test_a_settled_disposition_survives_the_function_moving_down(tmp_path):
    """The 2026-07-29 false alarm, pinned. Same file, same function, same metric,
    same number — only the line moved, because something above it grew. A
    judgement that evaporates when unrelated code is edited above it can never
    reach zero, which is what makes arming the hard block impossible."""
    src = _write(tmp_path, "m.py", "# a comment\n# another\n# and a third\n" + _SRC_BREACH)
    cs = _write(tmp_path, "cs.md", _CS)
    env = _write(tmp_path, "env.md", _envelope("m.py:1:big", "justified"))
    res = gate.check(root=str(tmp_path), standards=cs, envelope=env, files=[src])
    assert res["verdict"] == "valid-pass", res


def test_a_disposition_does_not_survive_the_breach_getting_worse(tmp_path):
    """The opposite failure, which the line-keyed scheme never caught: the judge
    justified ONE number, and the code then got worse while keeping its position.
    A justification is for the thing that was judged, not a standing pardon for
    the name — the same reasoning as the consent record's fingerprint."""
    src = _write(tmp_path, "m.py", "def big(a, b, c, d, e, f, g, h, i):\n    return a\n")
    cs = _write(tmp_path, "cs.md", _CS)
    env = _write(tmp_path, "env.md", _envelope("m.py:1:big", "justified"))  # judged at 7
    res = gate.check(root=str(tmp_path), standards=cs, envelope=env, files=[src])
    assert res["verdict"] == "valid-fail", res
    listed = " ".join(res["undispositioned"])
    assert "7" in listed and "9" in listed, listed   # both numbers, so it reads at a glance
    assert "judged" in listed.lower() or "worse" in listed.lower(), listed


def test_a_disposition_holds_when_the_breach_improves_but_still_breaches(tmp_path):
    """Improvement is not drift. Someone who took a justified breach from 9 to 7
    made things better; re-opening the judgement would punish the improvement and
    teach people to leave breaching code alone."""
    src = _write(tmp_path, "m.py", _SRC_BREACH)                     # 7 params
    cs = _write(tmp_path, "cs.md", _CS)
    env = _write(tmp_path, "env.md",
                 "maintainability-envelope: source=close count=1 armed=false\n\n"
                 "## M-1 — param-count 9 > 4 @ m.py:1:big (disposition: justified)\n"
                 "standard: coding-standards.md §Size — parameter count <= 4\n"
                 "reason: judged when it was worse than it is now\n"
                 "floor: none\n")
    assert gate.check(root=str(tmp_path), standards=cs, envelope=env,
                      files=[src])["verdict"] == "valid-pass"


def test_the_metric_is_part_of_the_identity(tmp_path):
    """One function can breach two bars. Justifying its parameter count says
    nothing about its nesting, so the two must not share an identity."""
    cs = _write(tmp_path, "cs.md",
                "# Coding standards\n<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
                "maintainability: param-count <= 4\n"
                "maintainability: nesting-depth <= 2\n"
                "<!-- FRIDAY-MAINTAINABILITY:END -->\n")
    src = _write(tmp_path, "m.py",
                 "def big(a, b, c, d, e, f, g):\n"
                 "    if a:\n        if b:\n            if c:\n"
                 "                return a\n    return b\n")
    env = _write(tmp_path, "env.md", _envelope("m.py:1:big", "justified"))  # param-count only
    res = gate.check(root=str(tmp_path), standards=cs, envelope=env, files=[src])
    assert res["verdict"] == "valid-fail", res
    listed = " ".join(res["undispositioned"])
    assert "nesting-depth" in listed and "param-count" not in listed, listed


def test_two_same_named_functions_in_one_file_still_need_their_own_line(tmp_path):
    """The one case a position-free key cannot separate: the measurer records a
    bare function name, so a method and a module-level function can collide. When
    a name is ambiguous the gate falls back to the exact line rather than letting
    one justification silently cover both — the safe direction."""
    src = _write(tmp_path, "m.py",
                 "class A:\n"
                 "    def big(self, a, b, c, d, e, f, g):\n        return a\n"
                 "\n"
                 "def big(a, b, c, d, e, f, g):\n    return a\n")
    cs = _write(tmp_path, "cs.md", _CS)
    env = _write(tmp_path, "env.md", _envelope("m.py:5:big", "justified"))
    res = gate.check(root=str(tmp_path), standards=cs, envelope=env, files=[src])
    assert res["verdict"] == "valid-fail", res
    # exactly one survives un-dispositioned: the method, which nobody justified
    assert len(res["undispositioned"]) == 1, res["undispositioned"]
    assert ":2:" in res["undispositioned"][0], res["undispositioned"]


def test_a_file_level_breach_keeps_matching_by_path(tmp_path):
    """file-size has no function and no line — its identity is the path alone,
    and the loosened key must not disturb that."""
    cs = _write(tmp_path, "cs.md",
                "# Coding standards\n<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
                "maintainability: file-size <= 2\n"
                "<!-- FRIDAY-MAINTAINABILITY:END -->\n")
    src = _write(tmp_path, "m.py", "a = 1\nb = 2\nc = 3\nd = 4\n")
    env = _write(tmp_path, "env.md",
                 "maintainability-envelope: source=close count=1 armed=false\n\n"
                 "## M-1 — file-size 4 > 2 @ m.py (disposition: justified)\n"
                 "standard: coding-standards.md §Size\n"
                 "reason: justified for the test\n"
                 "floor: none\n")
    assert gate.check(root=str(tmp_path), standards=cs, envelope=env,
                      files=[src])["verdict"] == "valid-pass"


# --- the verdict carries the bar meta the hook used to derive in-process ------
# (2026-08-06, D-1084 follow-on: hooks shell out, so arm / malformed / fatal
#  travel IN the checker's own JSON instead of a hook-side verify_claims import)

def test_verdict_carries_arm_and_bar_meta(tmp_path):
    cs = _write(tmp_path, "cs.md",
                "# s\n<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
                "maintainability: param-count <= 4\narm: block\n"
                "<!-- FRIDAY-MAINTAINABILITY:END -->\n")
    _write(tmp_path, "app.py", _SRC_FIXED)
    res = gate.check(root=str(tmp_path), standards=cs, envelope=None)
    assert res["arm"] == "block"
    assert res["bars_declared"] == 1
    assert res["malformed_bars"] == []
    assert res["fatal"] is None


def test_mixed_malformed_bar_rides_the_meta_and_valid_bars_still_enforce(tmp_path):
    cs = _write(tmp_path, "cs.md",
                "# s\n<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
                "maintainability: param-count <= 4\n"
                "maintainability: file-length at most 300\n"
                "<!-- FRIDAY-MAINTAINABILITY:END -->\n")
    _write(tmp_path, "app.py", _SRC_BREACH)
    res = gate.check(root=str(tmp_path), standards=cs, envelope=None)
    assert res["verdict"] == "valid-fail"
    assert res["malformed_bars"] == ["maintainability: file-length at most 300"]
    assert res["fatal"] is None


def test_all_malformed_bars_is_a_fatal_meta_never_a_silent_pass(tmp_path):
    cs = _write(tmp_path, "cs.md",
                "# s\n<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
                "maintainability: param-count at most 4\n"
                "<!-- FRIDAY-MAINTAINABILITY:END -->\n")
    _write(tmp_path, "app.py", _SRC_BREACH)
    res = gate.check(root=str(tmp_path), standards=cs, envelope=None)
    assert res["fatal"] and "malformed" in res["fatal"].lower()
    assert "param-count at most 4" in res["fatal"]
    assert res["verdict"] == "valid-pass"


def test_no_block_meta_says_zero_bars(tmp_path):
    cs = _write(tmp_path, "cs.md", "# s\nno block here\n")
    _write(tmp_path, "app.py", _SRC_FIXED)
    res = gate.check(root=str(tmp_path), standards=cs, envelope=None)
    assert res["bars_declared"] == 0
    assert res["arm"] == "warn"
