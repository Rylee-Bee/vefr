"""The studio's two shelves (web/js/features.js): "What this game uses" and "What VEFR can do".

The renderer is pure (like web/js/library.js): data in, an HTML string out, every word escaped.
The studio page loads it, `web/js/api.js` fetches `/api/features`, and an element with the id
`features-shelf` is where it is drawn.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def shelf():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    run = subprocess.run(["node", str(ROOT / "tests/fixtures/features_shelf_harness.mjs"),
                          str(ROOT / "web/js/features.js")],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr + run.stdout
    return json.loads(run.stdout)


def test_the_module_exists_and_labels_statuses(shelf):
    assert shelf["hasApi"] is True
    assert shelf["labels"] == ["Built", "Proposed", "Partly built", "weird"]


def test_a_pack_gets_its_own_shelf_first(shelf):
    html = shelf["withPack"]
    assert "What this game uses" in html and "What VEFR can do" in html
    assert html.index("What this game uses") < html.index("What VEFR can do")
    assert "cottage-of-the-breeze" in html
    assert "levels, 8 levels" in html                     # the detail of a used feature
    uses = html[html.index("What this game uses"):html.index("What VEFR can do")]
    assert "Levels, or learning by doing" in uses and "Reactions" not in uses


def test_proposed_things_are_labelled_not_hidden(shelf):
    html = shelf["withPack"]
    assert "On the way" in html and "Proposed" in html and "Partly built" in html


def test_without_a_pack_only_the_engine_shelf_shows(shelf):
    html = shelf["noPack"]
    assert "What this game uses" not in html and "What VEFR can do" in html


def test_words_are_escaped_and_empty_is_calm(shelf):
    assert "<b>album</b>" not in shelf["withPack"] and "&lt;b&gt;album&lt;/b&gt;" in shelf["withPack"]
    assert "<script" not in shelf["empty"]


def test_the_studio_loads_it_and_can_fetch_it():
    assert "features:" in (ROOT / "web/js/api.js").read_text(encoding="utf-8")
    assert "/api/features" in (ROOT / "web/js/api.js").read_text(encoding="utf-8")
    page = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "js/features.js" in page and 'id="features-shelf"' in page
