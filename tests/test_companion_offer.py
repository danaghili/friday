"""The visual companion's JIT offer/route logic (FR-73) — the pure decision core,
adopted with credit from superpowers' visual-companion.md (fold-in #6 of
superpowers-brainstorming-foldins.md). Two decisions live here and nothing else:
the one-time OPENING offer (offered just-in-time, declined = never again) and the
per-question ROUTE (showable → browser, everything else → terminal, EVEN after
the companion is open). Test-first (U6-2).
"""
import os
import sys

from guardkit import BUILD_ROOT

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools", "visual-companion"))
import offer  # noqa: E402


# --- route: a question goes to the browser only if it is genuinely showable ----

def test_showable_kinds_route_to_browser():
    for kind in ("mockup", "layout-comparison", "diagram", "state-diagram",
                 "architecture-diagram"):
        assert offer.route(kind) == "browser", kind


def test_talkable_kinds_route_to_terminal():
    for kind in ("requirement", "trade-off", "conceptual-choice", "open-question"):
        assert offer.route(kind) == "terminal", kind


def test_unknown_kind_is_conservatively_terminal():
    # Never push to the browser on doubt — a UI *topic* is not automatically
    # visual; only an explicitly showable artifact is.
    assert offer.route("something-new") == "terminal"
    assert offer.route("ui-question") == "terminal"


# --- the opening offer: just-in-time, once, declinable-for-good ----------------

def test_opening_offered_on_first_showable_question():
    assert offer.should_offer_opening("mockup", declined=False, is_open=False) is True


def test_opening_never_offered_on_a_talkable_question():
    # JIT means the FIRST genuinely-showable question — a trade-off question never
    # triggers the offer, even as the very first question of the session.
    assert offer.should_offer_opening("trade-off", declined=False, is_open=False) is False


def test_declined_is_never_re_offered():
    assert offer.should_offer_opening("mockup", declined=True, is_open=False) is False


def test_not_re_offered_once_already_open():
    assert offer.should_offer_opening("diagram", declined=False, is_open=True) is False


# --- per-question routing AFTER acceptance -------------------------------------

def test_open_companion_still_sends_talkable_questions_to_terminal():
    # The per-question test outlives acceptance: opening the browser does not make
    # every later question visual.
    assert offer.should_use_browser("trade-off", is_open=True) is False


def test_open_companion_sends_showable_questions_to_browser():
    assert offer.should_use_browser("mockup", is_open=True) is True


def test_closed_companion_never_uses_browser():
    assert offer.should_use_browser("mockup", is_open=False) is False
