"""Regions + door transitions: validation and the loader's region speakers.

A door is a tile you step on in one region that lands the hero in
another (an entry room, a floor below). `maplab.validate` checks the
door's shape and both tiles; the loader groups each act's speakers by
the region they name. Deterministic: no model calls anywhere.
"""

from __future__ import annotations

import json
from pathlib import Path

from vefr import maplab
from vefr.world import load_world

# Two maps: a town and a smaller entry room (a cottage). Both fit and
# both have open ground; '#' is solid, '.' is walkable.
TOWN_MAP = ["#####", "#...#", "#...#", "#...#", "#####"]
COTTAGE_MAP = ["#####", "#...#", "#####"]

TOWN_CONTRACT = {
    "tile": 32,
    "bg": "#131311",
    "hero_start": [1, 1],
    "legend": {".": {"base": ["#212a20"]},
               "#": {"base": ["#2a2e33"], "solid": True}},
    "sanctuary_tiles": ["."],
    "water_by_phase": {"dusk": "low", "dawn": "low"},
    "flood_tiles": [],
    "pois": {},
}
COTTAGE_CONTRACT = {
    "tile": 32,
    "bg": "#131311",
    "hero_start": [1, 1],
    "legend": {".": {"base": ["#212a20"]},
               "#": {"base": ["#2a2e33"], "solid": True}},
    "sanctuary_tiles": ["."],
    "water_by_phase": {"dusk": "low", "dawn": "low"},
    "flood_tiles": [],
    "pois": {},
}

# The good door: step on (2,3) in town, land on (1,1) in the cottage.
GOOD_DOOR = {"from": "town", "at": [2, 3], "to": "cottage", "to_at": [1, 1]}


def _make_pack(root: Path, *, transitions=None, speakers=None) -> Path:
    """A small two-region acts pack: town + cottage, joined by a door."""
    pack = root / "worlds" / "regions-test"
    (pack / "acts" / "act-1" / "town").mkdir(parents=True)
    (pack / "acts" / "act-1" / "cottage").mkdir(parents=True)
    (pack / "world.json").write_text(json.dumps({
        "name": pack.name,
        "title": "Regions Test",
        "phases": {"dusk": "quiet", "dawn": "warm"},
        "voices": {},
    }), encoding="utf-8")
    (pack / "acts" / "act-1" / "world.json").write_text(json.dumps({
        "id": "act-1",
        "title": "Regions Test",
        "regions": ["town", "cottage"],
        "speakers": speakers or {},
        "transitions": transitions if transitions is not None else [GOOD_DOOR],
    }), encoding="utf-8")
    for name, rows, contract in (
            ("town", TOWN_MAP, TOWN_CONTRACT),
            ("cottage", COTTAGE_MAP, COTTAGE_CONTRACT)):
        region = pack / "acts" / "act-1" / name
        (region / "map.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
        (region / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    return pack


def _errors(pack: Path) -> list[str]:
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def test_a_good_door_validates(tmp_path):
    """The door's tiles are walkable and both regions are declared."""
    assert _errors(_make_pack(tmp_path)) == []


def test_a_missing_target_region_is_named(tmp_path):
    """A door into an undeclared region is refused, naming the region."""
    pack = _make_pack(tmp_path, transitions=[{**GOOD_DOOR, "to": "cellar"}])
    errors = _errors(pack)
    assert any("cellar" in e and "not a declared region" in e for e in errors), errors


def test_a_door_off_the_map_is_named(tmp_path):
    """A door tile outside the `from` map is refused, naming the region."""
    pack = _make_pack(tmp_path, transitions=[{**GOOD_DOOR, "at": [99, 99]}])
    errors = _errors(pack)
    assert any("town" in e and "off the map" in e for e in errors), errors


def test_a_door_on_a_solid_tile_is_named(tmp_path):
    """A door on a wall is refused, naming the region and the tile."""
    pack = _make_pack(tmp_path, transitions=[{**GOOD_DOOR, "at": [0, 0]}])
    errors = _errors(pack)
    assert any("town" in e and "solid" in e and "(0,0)" in e for e in errors), errors


def test_a_landing_tile_off_the_map_is_named(tmp_path):
    """The landing tile must be inside the `to` map too."""
    pack = _make_pack(tmp_path, transitions=[{**GOOD_DOOR, "to_at": [9, 9]}])
    errors = _errors(pack)
    assert any("cottage" in e and "off the map" in e for e in errors), errors


def test_a_door_missing_a_key_is_refused(tmp_path):
    """Every door names from, to, at and to_at."""
    pack = _make_pack(tmp_path, transitions=[{"from": "town", "to": "cottage"}])
    errors = _errors(pack)
    assert any("missing" in e and "at" in e and "to_at" in e for e in errors), errors


def test_a_speaker_in_another_region_is_not_checked_against_the_town(tmp_path):
    """A region's speaker lives on that region's map.

    The validator checks only the first region's town, so a speaker placed
    in a room must not be judged by the town's geometry. This one stands on
    a wall in the town; with the region filter it is simply not the town's.
    """
    speakers = {
        "cook": {"name": "Cook", "at": [0, 0], "region": "cottage",
                 "voice_file": "voices/cook.md",
                 "seeds": {"dusk": "a", "dawn": "b"}},
    }
    pack = _make_pack(tmp_path, speakers=speakers)
    (pack / "voices").mkdir(exist_ok=True)
    (pack / "voices" / "cook.md").write_text("You are the cook.\n", encoding="utf-8")
    assert _errors(pack) == []


def test_the_loader_groups_speakers_by_region(tmp_path, monkeypatch):
    """Each region carries only its own speakers; the act keeps them all.

    A speaker with no `region` belongs to the act's first region.
    """
    speakers = {
        "keeper": {
            "name": "Keeper", "at": [1, 1], "region": "town",
            "voice_file": "voices/keeper.md",
            "seeds": {"dusk": "a", "dawn": "b"},
        },
        "cook": {
            "name": "Cook", "at": [1, 1], "region": "cottage",
            "voice_file": "voices/cook.md",
            "seeds": {"dusk": "c", "dawn": "d"},
        },
        "greeter": {
            "name": "Greeter", "at": [2, 2],
            "voice_file": "voices/greeter.md",
            "seeds": {"dusk": "e", "dawn": "f"},
        },
    }
    pack = _make_pack(tmp_path, speakers=speakers)
    monkeypatch.setenv("VEFR_HOME", str(tmp_path))
    load_world.cache_clear()
    try:
        act = load_world(pack.name)["acts"][0]
    finally:
        load_world.cache_clear()

    assert set(act["speakers"]) == {"keeper", "cook", "greeter"}
    assert set(act["regions"]["town"]["speakers"]) == {"keeper", "greeter"}
    assert set(act["regions"]["cottage"]["speakers"]) == {"cook"}


# --- region enemies: the combat contract's hazards ---

def _with_enemies(pack: Path, region: str, enemies: list) -> Path:
    p = pack / "acts" / "act-1" / region / "contract.json"
    contract = json.loads(p.read_text(encoding="utf-8"))
    contract["enemies"] = enemies
    p.write_text(json.dumps(contract), encoding="utf-8")
    return pack


def test_a_good_enemy_validates(tmp_path):
    """A named hazard on open ground with real numbers is accepted."""
    pack = _with_enemies(_make_pack(tmp_path), "town", [
        {"id": "a-rat", "name": "a rat", "at": [2, 2], "hp": 4, "atk": 1},
    ])
    assert _errors(pack) == []


def test_an_enemy_on_a_wall_is_named(tmp_path):
    pack = _with_enemies(_make_pack(tmp_path), "town", [
        {"id": "a-rat", "name": "a rat", "at": [0, 0], "hp": 4, "atk": 1},
    ])
    errors = _errors(pack)
    assert any("a rat" in e and "solid" in e and "(0,0)" in e for e in errors), errors


def test_an_enemy_off_the_map_is_named(tmp_path):
    pack = _with_enemies(_make_pack(tmp_path), "town", [
        {"id": "a-rat", "name": "a rat", "at": [99, 99], "hp": 4, "atk": 1},
    ])
    errors = _errors(pack)
    assert any("a rat" in e and "off the map" in e for e in errors), errors


def test_an_enemy_needs_positive_numbers(tmp_path):
    pack = _with_enemies(_make_pack(tmp_path), "town", [
        {"id": "a-rat", "name": "a rat", "at": [2, 2], "hp": 0, "atk": -1},
    ])
    errors = _errors(pack)
    assert any("a rat" in e and "positive hp" in e for e in errors), errors
    assert any("a rat" in e and "positive atk" in e for e in errors), errors


def test_an_enemy_needs_an_id_and_a_name(tmp_path):
    pack = _with_enemies(_make_pack(tmp_path), "town", [
        {"at": [2, 2], "hp": 4, "atk": 1},
    ])
    errors = _errors(pack)
    assert any("needs an id" in e for e in errors), errors
    assert any("needs a name" in e for e in errors), errors


def test_every_region_checks_its_own_enemies(tmp_path):
    """The second region's hazards are checked too, not just the first's."""
    pack = _with_enemies(_make_pack(tmp_path), "cottage", [
        {"id": "a-rat", "name": "a rat", "at": [9, 9], "hp": 4, "atk": 1},
    ])
    errors = _errors(pack)
    assert any("cottage" in e and "off the map" in e for e in errors), errors

