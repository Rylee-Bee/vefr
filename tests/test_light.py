"""The Light contract: a torch (radius/turns) or a one-shot reveal.

`maplab` pins the optional `light` field on an item so a broken torch is
a pack-authoring error, not a silent no-op in play. The bake carries
only a usable form, and the woven template is wired for the Bag use, the
HUD counter, and the announce-on-use lines.
"""

import copy
from pathlib import Path

import pytest

from vefr import cli, maplab
from vefr.world import load_world

TEMPLATE = Path(__file__).resolve().parents[1] / "web" / "packaged.html"


def _errors(items: dict) -> list[str]:
    w = copy.deepcopy(load_world("sample-world"))
    w["items"] = items
    return maplab.validate(w)


def test_the_radius_form_is_accepted():
    assert _errors({"torch": {"name": "a pitch torch",
                              "light": {"radius": 2, "turns": 6}}}) == []


def test_the_reveal_form_is_accepted():
    assert _errors({"map": {"name": "a chalked map",
                            "light": {"reveal": True}}}) == []


def test_items_with_no_light_are_untouched():
    assert _errors({
        "ring": {"name": "a plain ring", "value": 3},
        "potion": {"name": "a cloudy potion", "heal": 3, "use": "drink"},
    }) == []


@pytest.mark.parametrize("light", [
    {"radius": 0, "turns": 6},        # radius below range
    {"radius": 21, "turns": 6},       # radius above range
    {"radius": 2, "turns": 0},        # turns below range
    {"radius": 2, "turns": 1000},     # turns above range
    {"radius": "2", "turns": 6},      # radius not an integer
    {"radius": 2.5, "turns": 6},      # radius not an integer
    {"radius": True, "turns": 6},     # a bool is not an integer
    {"radius": 2, "turns": 6.5},      # turns not an integer
    {"radius": 2},                    # half a radius form
    {"turns": 6},                     # half a radius form
    {},                               # neither form
    {"reveal": False},                # reveal must be true to count
    {"reveal": "yes"},                # reveal not a bool
])
def test_a_bad_light_form_is_rejected(light):
    errors = _errors({"thing": {"name": "a thing", "light": light}})
    assert any("a thing" in e for e in errors), errors


def test_a_non_object_light_is_rejected():
    errors = _errors({"thing": {"name": "a thing", "light": "bright"}})
    assert any("a thing" in e and "object" in e for e in errors), errors


def test_the_bake_carries_only_usable_forms():
    """`_player_items` bakes a clean light; a broken one is left out, so
    the player never meets a torch that does nothing."""
    items = cli._player_items({"items": {
        "torch": {"name": "a pitch torch", "light": {"radius": 2, "turns": 6}},
        "map": {"name": "a chalked map", "light": {"reveal": True}},
        "ring": {"name": "a plain ring"},
        "junk": {"name": "junk", "light": {"radius": 0, "turns": 6}},
        "half": {"name": "half", "light": {"radius": 3}},
    }})
    assert items["torch"]["light"] == {"radius": 2, "turns": 6}
    assert items["map"]["light"] == {"reveal": True}
    assert "light" not in items["ring"]
    assert "light" not in items["junk"]
    assert "light" not in items["half"]


def test_the_woven_player_carries_the_light_hud():
    """The template ships the HUD counter and every announced line, so a
    woven file has them whether or not the pack names a light."""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="light-live"' in html
    assert "Turns of light: " in html
    assert "There is no dark here to light." in html
    assert "The whole place is laid out." in html
    assert "The torch catches: " in html
    assert "The light gutters out." in html
