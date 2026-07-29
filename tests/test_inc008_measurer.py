"""INC-008 FR-8.2 / KH-4 — the mechanical measurer (layer 1).

Test-first. Deterministic, content-independent counters for the solid three
metrics, stdlib-only for the Python case (ast + tokenize):
  - complexity  : McCabe cyclomatic, per function
  - size        : file LOC, function length, parameter count, nesting depth
  - duplication : token-run clones across files (KH-4 — must really fire, not
                  be assumed; proven here on a constructed clone and, in B8,
                  on friday's real hook duplication)
The measurer reads a project's declared bars and reports each breach as
{location, metric, measured, bar}; the SAME measurement path re-verifies a fix
(the fix-verifier, Pin #2). The empty case (no files / no bars) is first-class.
"""
import os
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import maintainability_measure as mm  # noqa: E402


# --- complexity (McCabe) -------------------------------------------------------

def test_cyclomatic_counts_decision_points():
    src = textwrap.dedent('''
        def f(x):
            if x:
                return 1
            for i in range(x):
                if i > 2 or i < 0:
                    return i
            return 0
    ''')
    funcs = {fn["name"]: fn for fn in mm.measure_source(src, "f.py")["functions"]}
    # base 1 + if(+1) + for(+1) + if(+1) + or(+1) = 5
    assert funcs["f"]["complexity"] == 5


def test_trivial_function_is_complexity_one():
    src = "def g():\n    return 42\n"
    funcs = mm.measure_source(src, "g.py")["functions"]
    assert funcs[0]["complexity"] == 1


# --- size ----------------------------------------------------------------------

def test_size_metrics():
    src = textwrap.dedent('''
        def h(a, b, c):
            if a:
                if b:
                    return c
            return 0
    ''')
    fn = mm.measure_source(src, "h.py")["functions"][0]
    assert fn["param-count"] == 3
    assert fn["nesting-depth"] == 2          # if inside if
    assert fn["function-size"] >= 4          # def + body lines


def test_file_loc_counts_nonblank_noncomment():
    src = "# a comment\n\nx = 1\n\ndef f():\n    return x\n"
    m = mm.measure_source(src, "f.py")
    assert m["file"]["file-size"] == 3       # x=1, def f, return x


# --- duplication (KH-4: must really fire) --------------------------------------

def test_duplication_detects_a_real_clone(tmp_path):
    block = (
        "def handler(event):\n"
        "    ctx = load_context(event)\n"
        "    if ctx is None:\n"
        "        return fail_open()\n"
        "    result = process(ctx)\n"
        "    return emit(result)\n"
    )
    (tmp_path / "a.py").write_text("import os\n" + block)
    (tmp_path / "b.py").write_text("import sys\n" + block)
    dup = mm.measure_paths([str(tmp_path / "a.py"), str(tmp_path / "b.py")])["duplication"]
    assert dup["blocks"] >= 1                 # the shared block is found
    assert dup["duplication-pct"] > 0


def test_no_duplication_on_distinct_files(tmp_path):
    (tmp_path / "a.py").write_text("def one():\n    return 1\n")
    (tmp_path / "b.py").write_text("def two(x, y):\n    return x * y + 7\n")
    dup = mm.measure_paths([str(tmp_path / "a.py"), str(tmp_path / "b.py")])["duplication"]
    assert dup["blocks"] == 0


# --- breach comparison vs declared bars ----------------------------------------

def test_breaches_reports_over_bar_only():
    src = textwrap.dedent('''
        def big(a, b, c, d, e, f, g):
            return a
        def small(x):
            return x
    ''')
    measured = mm.measure_source(src, "m.py")
    bars = {"param-count": {"metric": "param-count", "limit": 4, "pct": False}}
    breaches = mm.breaches(measured, bars)
    locs = {(b["metric"], b["location"].split(":")[-1]) for b in breaches}
    assert ("param-count", "big") in locs      # 7 params > 4
    assert ("param-count", "small") not in locs  # 1 param <= 4


def test_breach_carries_measured_and_bar():
    src = "def big(a, b, c, d, e):\n    return a\n"
    measured = mm.measure_source(src, "m.py")
    bars = {"param-count": {"metric": "param-count", "limit": 3, "pct": False}}
    b = mm.breaches(measured, bars)[0]
    assert b["metric"] == "param-count" and b["measured"] == 5 and b["bar"] == 3


# --- empty cases (first-class) -------------------------------------------------

def test_no_bars_means_no_breaches():
    src = "def big(a, b, c, d, e, f, g, h):\n    return a\n"
    measured = mm.measure_source(src, "m.py")
    assert mm.breaches(measured, {}) == []     # no bars declared -> zero breaches


def test_empty_paths_measure_clean(tmp_path):
    m = mm.measure_paths([])
    assert m["functions"] == [] and m["files"] == []
    assert m["duplication"]["blocks"] == 0
