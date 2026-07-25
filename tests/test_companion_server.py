"""The visual companion's zero-dep stdlib server (FR-72) and its event-stream
capture (FR-74). CompanionState is the pure, testable core; serve() is thin
http.server plumbing over it, exercised once for real on an ephemeral port. The
load-bearing behaviours: a new question clears a stale selection; a selection
(with its exploration path) round-trips; and "continue in terminal" clears the
board. Test-first (U6-2).
"""
import json
import os
import sys
import threading
import urllib.request

from guardkit import BUILD_ROOT

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools", "visual-companion"))
import companion_server as companion  # noqa: E402


# --- CompanionState: the pure core --------------------------------------------

def test_new_question_clears_a_prior_selection():
    st = companion.CompanionState()
    st.set_question({"title": "Which layout?", "options": ["A", "B"]})
    st.record_selection("A", path=["A", "B", "A"])
    assert st.read_selection() is not None
    st.set_question({"title": "Which colour?", "options": ["teal", "indigo"]})
    # Stale choice from the previous question must not leak into the new one.
    assert st.read_selection() is None


def test_selection_round_trips_with_its_exploration_path():
    st = companion.CompanionState()
    st.set_question({"title": "Which?", "options": ["A", "B"]})
    st.record_selection("B", path=["A", "B", "A", "B"])
    sel = st.read_selection()
    assert sel["choice"] == "B"
    assert sel["path"] == ["A", "B", "A", "B"]  # hesitation is data (FR-74)


def test_continue_in_terminal_clears_the_board():
    st = companion.CompanionState()
    st.set_question({"title": "Which?", "options": ["A", "B"]})
    st.record_selection("A", path=["A"])
    st.continue_in_terminal()
    assert st.current_question() is None
    assert st.read_selection() is None


def test_render_shows_the_question_and_options():
    st = companion.CompanionState()
    st.set_question({"title": "Which layout feels right?", "options": ["Split", "Stacked"]})
    html = st.render()
    assert "Which layout feels right?" in html
    assert "Split" in html and "Stacked" in html


def test_render_with_no_question_is_the_continuing_screen():
    st = companion.CompanionState()
    html = st.render()
    assert "terminal" in html.lower()  # the "continuing in terminal…" clearing screen


# --- serve(): one real round-trip over the stdlib server -----------------------

def _post(url, obj):
    data = json.dumps(obj).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, resp.read().decode("utf-8")


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as resp:
        return resp.status, resp.read().decode("utf-8")


def test_full_http_round_trip_on_an_ephemeral_port():
    st = companion.CompanionState()
    httpd, url = companion.serve(st, host="127.0.0.1", port=0)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        # agent posts a question → browser renders it
        status, _ = _post(url + "/question",
                          {"title": "Which layout?", "options": ["Split", "Stacked"]})
        assert status == 200
        _, page = _get(url + "/")
        assert "Which layout?" in page

        # browser posts the click + path → agent reads it back
        status, _ = _post(url + "/select", {"choice": "Split", "path": ["Split", "Stacked", "Split"]})
        assert status == 200
        _, body = _get(url + "/selection")
        sel = json.loads(body)["selection"]
        assert sel["choice"] == "Split"
        assert sel["path"][-1] == "Split"

        # agent says "continuing in terminal" → board clears
        _post(url + "/continue", {})
        _, body = _get(url + "/selection")
        assert json.loads(body)["selection"] is None
    finally:
        httpd.shutdown()
        httpd.server_close()
