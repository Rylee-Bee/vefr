"""Rolled loot in the real woven player (ADR 0017, T3 slice 1).

The engine side of this slice is pinned in `test_rolled_loot.py`: the
shape, the four refusals, the draw's determinism and the backward
compatibility proof. This file pins the half a player meets - the bag
panel and the HUD strip naming a thing and its rarity together the moment
it is picked up, the hidden traits in no part of the page at all, and the
instance kept as it was drawn rather than drawn again on the next load.

Drives the shipped player in jsdom through the real DOM, the way
`test_equipment_ui.py` does, and with reduced motion on: this slice owes
no animation, so the reveal must be the same sentence either way.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "rolled_loot_harness.mjs"
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_rolled_pack as mk  # noqa: E402

# The bag a floor drop leaves behind: a plain thing as the bare id it has
# always been, a rolled thing as the instance it was drawn as.
DRAWN = {"id": "cloudy-potion", "rarity": "rare",
         "traits": ["keen", "cold"], "identified": False}
BAG = [DRAWN, "pebble", {"id": "brass-ring", "rarity": "common",
                         "traits": ["keen"], "identified": False}]


def weave(dest):
    pack = mk.build(dest)
    out = dest / "rolled-test.html"
    out.write_text(cli.weave_html(pack), encoding="utf-8")
    return out


def run(html, steps, bag=BAG):
    spec = json.dumps({"steps": steps, "bag": bag})
    result = subprocess.run(["node", str(HARNESS), str(html), spec],
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr + result.stdout
    out = json.loads(result.stdout)
    assert out["errors"] == [], out["errors"]
    return out


@pytest.fixture(scope="module")
def woven(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    return weave(tmp_path_factory.mktemp("rolled-loot"))


def test_the_bag_names_the_thing_and_its_rarity_at_once(woven):
    """The reveal: "a cloudy potion (rare)" - both words, one line, no wait."""
    final = run(woven, [{"do": "openBag"}])["final"]
    names = final["bagNames"]
    assert "a cloudy potion (rare)" in names, names
    assert "a brass ring (common)" in names, names
    # A thing with no rarity is still just its own words - the label does
    # not grow empty parentheses for every plain drop in the game.
    assert "a grey pebble" in names, names
    assert not any(name.endswith("()") for name in names), names


def test_the_hidden_traits_are_in_no_part_of_the_page(woven):
    """Not hidden from the eye - absent. A reader of the DOM, a screen
    reader and the page source all get the rarity and no trait."""
    out = run(woven, [{"do": "openBag"}])
    final = out["final"]
    for word in ("keen", "cold"):
        assert word not in final["panelText"], final["panelText"]
        assert word not in final["strip"], final["strip"]
        assert all(word not in name for name in final["bagNames"])
    # The rarity, on the other hand, is everywhere it should be.
    assert "rare" in final["strip"], final["strip"]


def test_the_strip_says_the_rarity_to_a_screen_reader(woven):
    """The strip is pictures, so its own words carry the rarity."""
    final = run(woven, [{"do": "openBag"}])["final"]
    assert "a cloudy potion (rare)" in final["strip"], final["strip"]
    assert "a grey pebble" in final["strip"], final["strip"]


def test_the_instance_is_kept_as_it_was_drawn(woven):
    """A second load reads the same rarity and the same traits: the roll
    happened once, at the drop, and nothing re-draws it."""
    out = run(woven, [{"do": "openBag"}, {"do": "snap", "tag": "before"},
                      {"do": "reload"}, {"do": "openBag"}])
    assert out["final"]["bagNames"] == out["snaps"]["before"]["bagNames"]
    assert out["final"]["bag"] == BAG, out["final"]["bag"]
    assert out["final"]["bagNames"].count("a cloudy potion (rare)") == 1


def test_a_bag_saved_before_this_slice_still_reads(woven):
    """Bare ids only: every existing save is a list of strings, and it
    still is one - the same words, with nothing appended."""
    out = run(woven, [{"do": "openBag"}], bag=["pebble", "cloudy-potion"])
    final = out["final"]
    assert final["bagNames"] == ["a grey pebble", "a cloudy potion"]
    assert final["bag"] == ["pebble", "cloudy-potion"]