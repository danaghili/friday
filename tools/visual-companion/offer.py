#!/usr/bin/env python3
"""The visual companion's JIT offer/route logic (FR-73) — adopted with credit
from superpowers' visual-companion.md (fold-in #6,
docs/research/rebuild/superpowers-brainstorming-foldins.md).

Two decisions, and deliberately nothing else:

  route(kind)              — does THIS question belong in the browser or the
                             terminal? Only a genuinely SHOWABLE artifact
                             (a mockup, a layout comparison, a diagram) goes to
                             the browser; a requirement / trade-off / conceptual
                             choice is talked through in the terminal. A UI
                             *topic* is not automatically visual — the kind must
                             be an explicit showable, or it routes to terminal.

  should_offer_opening(...)— the one-time, just-in-time opening offer, made the
                             FIRST time a showable question arises. Declined once
                             → never offered again. Already open → not re-offered.

  should_use_browser(...)  — after acceptance, the per-question route still holds:
                             an open companion does NOT make every later question
                             visual; a talkable question stays in the terminal.

Pure functions, no I/O, no state — the caller (the discovery/design expert)
owns the session flags. Pure stdlib.
"""
from __future__ import annotations

# A question goes to the browser only when there is something concrete to SEE.
VISUAL_KINDS = frozenset({
    "mockup", "layout-comparison", "diagram", "state-diagram",
    "architecture-diagram", "flow-diagram",
})
# Named for clarity in the surfaces; anything not explicitly visual is talkable.
TALKABLE_KINDS = frozenset({
    "requirement", "trade-off", "conceptual-choice", "open-question",
})


def route(kind: str) -> str:
    """'browser' iff `kind` is an explicit showable; 'terminal' otherwise
    (unknown kinds included — never push to the browser on doubt)."""
    return "browser" if kind in VISUAL_KINDS else "terminal"


def should_offer_opening(kind: str, *, declined: bool, is_open: bool) -> bool:
    """The just-in-time opening offer: True only on a showable question, when the
    PM has not declined the companion this session and it is not already open."""
    return route(kind) == "browser" and not declined and not is_open


def should_use_browser(kind: str, *, is_open: bool) -> bool:
    """Per-question routing once the companion is open: a showable question uses
    the browser; a talkable one stays in the terminal even mid-session."""
    return is_open and route(kind) == "browser"
