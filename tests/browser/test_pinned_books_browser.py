"""Pinned books in Chromium: the woven game puts them where Python says, finds them, and moves them on a new run.

Weaves the neutral descent fixture with two books pinned to its first generated floor, enters that
floor through the descent's own arrival path, and reads the library back: each book lies on the
tile `delve.place_books` gives for run 0, stepping on the plain one finds it, and after "New
descent" both lie where Python gives for run 1. Runs in its own process (the suite's session
`browser` fixture holds the sync API in this one) and skips without Chromium, failing instead
when VEFR_BROWSER_REQUIRED=1.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures"))
import make_descent_pack  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

_PLAY = r"""
import json, sys
from pathlib import Path
from vefr import cli
try:
    from playwright.sync_api import sync_playwright
except Exception:
    print("NO-BROWSER"); sys.exit(0)
pack = Path(sys.argv[1]); html = pack.parent / "pins.html"
html.write_text(cli.weave_html(pack), encoding="utf-8")
JS = '''() => {
  const D = window.VEFR_DESCENT;
  const at = (id) => { const b = (window.VEFR_LIBRARY || []).find((x) => x.id === id); return b ? b.at : null; };
  D.enterDescentFloor(1);
  const run0 = {letter: at("a-letter"), candle: at("b-candle")};
  libraryOnTile(run0.candle[0], run0.candle[1], D.floorName("cellar", 0, 1));
  const found = bookIsFound("b-candle");
  D.startRun();
  D.enterDescentFloor(1);
  return {run0: run0, found: found, run1: {letter: at("a-letter"), candle: at("b-candle")}};
}'''
with sync_playwright() as p:
    try:
        browser = p.chromium.launch()
    except Exception:
        print("NO-BROWSER"); sys.exit(0)
    page = browser.new_page()
    page.goto(html.resolve().as_uri())
    page.click("#ts-enter")
    page.wait_for_timeout(500)
    print(json.dumps(page.evaluate(JS)))
    browser.close()
"""


def _book(pack, name, place, chest=False):
    folder = pack / "library"
    folder.mkdir(exist_ok=True)
    extra = "chest: yes\n" if chest else ""
    (folder / f"{name}.md").write_text(
        f"---\ntitle: {name}\nfound: map\nregion: cellar-0-1\nplace: {place}\n{extra}kind: note\n---\nA page.\n",
        encoding="utf-8")


def test_the_woven_game_places_finds_and_moves_pinned_books_as_python_does(tmp_path):
    from vefr import delve, maplab

    pack = make_descent_pack.build(tmp_path)
    _book(pack, "a-letter", "near-up", chest=True)
    _book(pack, "b-candle", "near-down")
    r = subprocess.run([sys.executable, "-c", _PLAY, str(pack)], capture_output=True, text=True,
                       cwd=ROOT, timeout=240)
    assert r.returncode == 0, r.stderr
    if r.stdout.strip() == "NO-BROWSER":
        if os.environ.get("VEFR_BROWSER_REQUIRED") == "1":
            pytest.fail("Chromium is required here and is not installed")
        pytest.skip("Chromium isn't installed; run: uv run playwright install chromium")
    seen = json.loads(r.stdout.strip().splitlines()[-1])

    descent = delve.descent_of(maplab.load_pack(pack), pack)
    books = [{"id": "a-letter", "place": "near-up"}, {"id": "b-candle", "place": "near-down"}]
    for run in (0, 1):
        want = delve.place_books(delve.floor_plan(descent, 1, run), books)
        got = seen[f"run{run}"]
        assert (got["letter"], got["candle"]) == (want["a-letter"], want["b-candle"]), run
    assert seen["found"] is True
    assert seen["run0"] != seen["run1"]
