"""graph_refresh.py — the refresh flow's deterministic core (FR-71). Stamps the
adopted graph as refreshed-at-HEAD, but ONLY when there is an adopted graph to
stamp. The soft-integration decision tree (FR-68) is the whole logic. Reference
runs the actual graphify rebuild first; this records freshness last (the
code → docs → graph ordering). Test-first (U6-1).
"""
import os
import subprocess
import sys

from guardkit import BUILD_ROOT

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import friday_substrate as fs  # noqa: E402
import graph_freshness_check as gfc  # noqa: E402
import graph_refresh as gr  # noqa: E402


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "f.txt").write_text("x", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "c0")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    return root, head


def _adopt_graphify_graph(root):
    out = root / "graphify-out"
    out.mkdir(exist_ok=True)
    (out / "graph.json").write_text('{"nodes":[],"edges":[]}', encoding="utf-8")


def test_no_graphify_does_not_stamp_and_guard8_still_passes(tmp_path):
    # Absent tool → friday's own index IS the graph; there is no adopted graph
    # to be stale, so no stamp, and guard #8 valid-passes on the absent stamp.
    root, head = _repo(tmp_path)
    res = gr.refresh(str(root), has_graphify=False, head=head)
    assert res["stamped"] is False
    assert res["backend"] == "friday-own"
    assert gfc.check(str(root))["verdict"] == "valid-pass"


def test_graphify_present_with_graph_stamps_head(tmp_path):
    root, head = _repo(tmp_path)
    _adopt_graphify_graph(root)
    res = gr.refresh(str(root), has_graphify=True, head=head)
    assert res["stamped"] is True
    assert res["commit"] == head
    assert res["backend"] == "graphify"
    # Round-trip: the stamp graph_refresh wrote reads back current under guard #8.
    assert gfc.check(str(root))["verdict"] == "valid-pass"


def test_graphify_present_but_no_graph_built_yet_does_not_stamp(tmp_path):
    # Installed but never run on this project — nothing to stamp; say so, don't
    # fabricate freshness for a graph that doesn't exist.
    root, head = _repo(tmp_path)
    res = gr.refresh(str(root), has_graphify=True, head=head)
    assert res["stamped"] is False
    assert res["backend"] == "graphify"


def test_no_head_cannot_stamp(tmp_path):
    root, _ = _repo(tmp_path)
    _adopt_graphify_graph(root)
    res = gr.refresh(str(root), has_graphify=True, head="")
    assert res["stamped"] is False


def test_stamp_advances_after_a_new_commit(tmp_path):
    # A second refresh at a later HEAD moves the stamp forward — freshness is
    # re-asserted, not frozen at first adoption.
    root, head0 = _repo(tmp_path)
    _adopt_graphify_graph(root)
    gr.refresh(str(root), has_graphify=True, head=head0)
    (root / "g.txt").write_text("y", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "c1")
    head1 = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                           capture_output=True, text=True, check=True).stdout.strip()
    # Before the new refresh, guard #8 sees it 1 behind.
    assert gfc.check(str(root))["verdict"] == "valid-fail"
    gr.refresh(str(root), has_graphify=True, head=head1)
    assert gfc.check(str(root))["verdict"] == "valid-pass"
