"""Weave template resolution: checkout, wheel package data, container.

cmd_build_web reads web/packaged.html. A source checkout has it at
the repo root; a pip-installed wheel (a pack author running
`ratatoskr weave` from their own repo) has it only as package data;
containers keep it under VEFR_HOME. _template_candidates() must
cover all three, in that preference order - and the wheel config
must actually ship the file.

The last two tests here are about what goes INTO the woven file: the
pack grammars. The expander in the template is the same algorithm as
the engine's own (src/vefr/grammar.py), so it has to parse as shipped
and it has to keep the same two promises - a grammar that feeds
itself stops at the cap, and a reference that does not resolve
expands to nothing rather than to half a line.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

import pytest

from vefr import cli
from vefr.paths import app_home

GRAMMARS = {
    "whisper": {"origin": ["#who# says #news#."],
                "who": ["the innkeeper", "the ferryman"],
                "news": ["the road east is watched"]},
    "weather": {"origin": ["#sky# over #place#."],
                "sky": ["Rain"], "place": ["the town"]},
    "name": {"origin": ["#adj# #noun#"],
             "adj": ["Grey"], "noun": ["Hollow"]},
}


def test_candidates_cover_all_three_layouts_in_order():
    here = Path(cli.__file__).resolve()
    expected = [
        here.parents[2] / "web" / "packaged.html",   # source checkout
        here.parent / "web" / "packaged.html",        # wheel package data
        app_home() / "web" / "packaged.html",         # container / VEFR_HOME
    ]
    assert cli._template_candidates() == expected


def test_checkout_template_exists():
    """In a source checkout (dev box and CI) candidate 1 must be real."""
    checkout = Path(cli.__file__).resolve().parents[2] / "web" / "packaged.html"
    assert checkout.exists()
    assert any(p.exists() for p in cli._template_candidates())


def test_wheel_config_ships_template_as_package_data():
    """The wheel must force-include the template - that is what makes
    the package-data candidate true for an installed engine.

    Without this pin the wheel-layout candidate silently points at a
    file nobody ships and weave breaks again for pack authors.
    """
    repo = Path(cli.__file__).resolve().parents[2]
    cfg = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = cfg["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include["web/packaged.html"] == "vefr/web/packaged.html"


# ---- the woven file: the grammar block, and does the whole file parse ----

pytestmark_grammar = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)


def _woven() -> str:
    """A real woven file, with no pool and so no model call anywhere."""
    repo = Path(cli.__file__).resolve().parents[2]
    return cli.weave_html(repo / "worlds" / "sample-world")


def _script_of(html: str) -> str:
    match = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    assert match, "the woven file carries no <script> block"
    return match.group(1)


def _grammar_code(html: str) -> str:
    """The shipped expander, taken verbatim: the baked block, the seed
    helpers it leans on, and the algorithm itself between its own
    section markers."""
    parts = [
        re.search(r"window\.VEFR_GRAMMARS = .*?;\n", html).group(0),
        re.search(r"function mulberry32\(seed\) \{.*?\n\}\n", html, re.DOTALL).group(0),
        re.search(r"function saveSeed\(\) \{.*?\n\}\n", html, re.DOTALL).group(0),
        re.search(r"function nextDraw\(\) \{.*?\n\}\n", html, re.DOTALL).group(0),
        re.search(
            r"// ---- the pack grammars ----.*?(?=// ---- the fragment banks ----)",
            html, re.DOTALL,
        ).group(0),
    ]
    return "".join(parts)


@pytestmark_grammar
def test_the_woven_template_still_parses():
    """The built file is real JavaScript: node compiles its whole
    script block, so a template edit that breaks the parse is caught
    here rather than by a player opening the file."""
    html = _woven()
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "woven.js"
        script.write_text(_script_of(html), encoding="utf-8")
        result = subprocess.run(
            ["node", "--check", str(script)],
            capture_output=True, text=True, timeout=60,
        )
    assert result.returncode == 0, (
        f"the woven file does not parse:\n{result.stdout}\n{result.stderr}")


@pytestmark_grammar
def test_the_shipped_expander_caps_and_refuses():
    """The same two promises the engine's expander keeps, proved on the
    code that actually ships: a self-feeding grammar stops, and a
    reference that names no rule expands to nothing (never a line with
    a hole in it)."""
    html = _woven()
    code = (
        "const window = {};\n"
        "const localStorage = { _s: {},"
        " getItem(k) { return k in this._s ? this._s[k] : null; },"
        " setItem(k, v) { this._s[k] = String(v); } };\n"
        + _grammar_code(html)
        + "const out = {};\n"
        "out.known = grammarExpand(" + json.dumps(GRAMMARS["weather"]) + ", mulberry32(7));\n"
        "out.unknown = grammarExpand({origin: ['the #nowhere# end.']}, mulberry32(7));\n"
        "out.noOrigin = grammarExpand({who: ['x']}, mulberry32(7));\n"
        "out.notAGrammar = grammarExpand(['x'], mulberry32(7));\n"
        "out.selfFeed = grammarExpand({origin: ['#origin# again']}, mulberry32(7));\n"
        "out.pingPong = grammarExpand({origin: ['#a#'], a: ['#b#'], b: ['#a#']}, mulberry32(7));\n"
        "out.nested = grammarExpand({origin: ['#outer#!'], outer: ['#in# and #in#'],"
        " in: ['deep']}, mulberry32(7));\n"
        # The cap counts the origin draw too, so 199 references is the
        # last expansion that fits and 200 is the first that does not.
        "const fits = {origin: [Array(199).fill('#a#').join(' ')], a: ['x']};\n"
        "const trips = {origin: [Array(200).fill('#a#').join(' ')], a: ['x']};\n"
        "out.fits = grammarExpand(fits, mulberry32(7));\n"
        "out.trips = grammarExpand(trips, mulberry32(7));\n"
        "out.maxExpansions = GRAMMAR_MAX_EXPANSIONS;\n"
        "out.spentBudget = grammarDraw(trips.a, mulberry32(1), [0]) === null;\n"
        "window.VEFR_GRAMMARS = " + json.dumps(GRAMMARS) + ";\n"
        "out.fromPack = grammarFromPack('name');\n"
        "out.absentPack = grammarFromPack('nothing');\n"
        "console.log(JSON.stringify(out));\n"
    )
    result = subprocess.run(["node", "-e", code], capture_output=True,
                            text=True, timeout=60)
    assert result.returncode == 0, (
        f"the shipped expander failed:\n{result.stdout}\n{result.stderr}")
    got = json.loads(result.stdout)

    # A known grammar expands, and only into words the pack declared.
    assert got["known"] == "Rain over the town."
    assert got["nested"] == "deep and deep!"
    # Every refusal is the empty string, never a half-built line.
    for key in ("unknown", "noOrigin", "notAGrammar", "selfFeed",
                "pingPong", "trips", "absentPack"):
        assert got[key] == "", f"{key} expanded to {got[key]!r}"
    # The cap is the shipped 200, and it is what stops the loop: the
    # last expansion that fits still speaks.
    assert got["maxExpansions"] == 200
    assert got["fits"] == " ".join(["x"] * 199)
    assert got["spentBudget"] is True
    # The pack's own block reads back through the same path.
    assert got["fromPack"] == "Grey Hollow"
