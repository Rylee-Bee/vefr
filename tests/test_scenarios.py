"""Scenarios (ADR 0016, slice P2): a pack names a game state and the dev tools open it.

Cottage Release 1 needed 1,651 keypresses to photograph one deep room (#260). A
scenario is the Player Driver's Session Capsule written by hand: the player's own
save keys plus where the hero stands. These tests pin the shape, the checks
against the pack, the save keys a scenario writes (and that they are the keys the
player itself reads), and the dev tools' refusals before any browser opens. The
browser half is tests/browser/test_scenarios_browser.py.
"""

import json
import re
import sys
from pathlib import Path

import pytest

from vefr import delve, devtools, maplab, scenarios

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
import make_descent_pack  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "web" / "player" / "parts"

# A wearable item beside the fixture's pebble, so `equipped` has something to hold.
STAFF = {"name": "an oak staff", "slot": "hand"}


@pytest.fixture
def pack(tmp_path):
    pack = make_descent_pack.build(tmp_path)
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    world["items"]["oak-staff"] = STAFF
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")
    return pack


def put(pack, name, data):
    folder = pack / "scenarios"
    folder.mkdir(exist_ok=True)
    (folder / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


def problems(pack):
    return scenarios.errors(maplab.load_pack(pack), pack)


# ---------------------------------------------------------------- a pack without scenarios

def test_a_pack_with_no_scenarios_checks_exactly_as_before(pack):
    w = maplab.load_pack(pack)
    assert scenarios.errors(w, pack) == []
    assert maplab.validate(w, pack_dir=pack) == []


# ---------------------------------------------------------------- good scenarios

def test_a_region_scenario_and_a_depth_scenario_are_good(pack):
    put(pack, "town-rich", {"note": "a full purse in town", "start": {"region": "town", "at": [3, 4]},
                            "gold": 120, "bag": ["pebble", "pebble"], "equipped": {"hand": "oak-staff"},
                            "xp": 40, "hp": 12})
    put(pack, "floor-four", {"start": {"depth": 4}})
    assert problems(pack) == []
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []


# ---------------------------------------------------------------- the shape

@pytest.mark.parametrize("data, says", [
    ({}, "scenario must hold a start"),
    ({"start": {"depth": 2}, "mood": "x"}, "unknown key 'mood'"),
    ({"start": {"depth": 2}, "gold": -1}, "scenario.gold must be between 0"),
    ({"start": {"depth": 2}, "bag": "pebble"}, "scenario.bag must be a list"),
    ({"start": {"depth": 0}}, "start.depth must be between 1"),
    ({"start": {"region": "town", "at": [1]}}, "must be an [x, y] tile"),
])
def test_the_shape_is_refused_with_a_sentence(pack, data, says):
    put(pack, "bad", data)
    found = problems(pack)
    assert any(says in p for p in found), found
    assert all(p.startswith("scenarios/bad.json: ") for p in found)


# ---------------------------------------------------------------- the start

@pytest.mark.parametrize("start, says", [
    ({"region": "town", "depth": 2}, "a region or a depth, not both"),
    ({}, "a region or a depth, not both and not neither"),
    ({"depth": 2, "at": [3, 4]}, "start.at goes with a region"),
    ({"region": "attic"}, "'attic' is not a region of this pack; it has town"),
    ({"region": "town", "at": [40, 4]}, "is outside town (12x10 tiles)"),
    ({"region": "town", "at": [0, 0]}, "is not a tile the hero can stand on in town"),
])
def test_a_start_the_pack_cannot_play_is_refused(pack, start, says):
    put(pack, "bad", {"start": start})
    found = problems(pack)
    assert any(says in p for p in found), found


def test_a_depth_needs_a_descent(pack):
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    del world["descent"]
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")
    put(pack, "deep", {"start": {"depth": 3}})
    assert any("needs a descent" in p for p in problems(pack))


# ---------------------------------------------------------------- the items

@pytest.mark.parametrize("extra, says", [
    ({"bag": ["pebble", "lantern"]}, "scenario.bag[1] 'lantern' is not an item this pack defines"),
    ({"equipped": {"tail": "oak-staff"}}, "slot 'tail' is not a slot"),
    ({"equipped": {"hand": "lantern"}}, "scenario.equipped.hand 'lantern' is not an item"),
    ({"equipped": {"head": "oak-staff"}}, "'oak-staff' is worn on the hand slot"),
    ({"equipped": {"hand": "pebble"}}, "'pebble' is worn on no slot"),
])
def test_items_the_pack_does_not_have_or_cannot_wear_are_refused(pack, extra, says):
    put(pack, "bad", {"start": {"depth": 1}, **extra})
    found = problems(pack)
    assert any(says in p for p in found), found


# ---------------------------------------------------------------- the files

def test_a_file_that_is_not_a_scenario_is_named(pack):
    put(pack, "Upper-Case", {"start": {"depth": 1}})
    (pack / "scenarios" / "notes.txt").write_text("x", encoding="utf-8")
    found = problems(pack)
    assert any(p.startswith("scenarios/Upper-Case.json: ") and "is not a scenario name" in p for p in found), found
    assert "scenarios/notes.txt: a scenario is a .json file" in found


def test_an_unreadable_scenario_is_a_sentence_not_a_crash(pack):
    (pack / "scenarios").mkdir()
    (pack / "scenarios" / "broken.json").write_text("{not json", encoding="utf-8")
    assert len(problems(pack)) == 1


# ---------------------------------------------------------------- the save keys

def test_storage_writes_the_players_own_keys_in_its_own_formats(pack):
    w = maplab.load_pack(pack)
    keys = scenarios.storage(w, {"start": {"depth": 2}, "gold": 120, "bag": ["pebble"],
                                 "equipped": {"hand": "oak-staff"}, "xp": 40, "hp": 12})
    name = "descent-test"
    assert scenarios.world_name(w) == name
    assert keys["vefr-gold-" + name] == "120"
    assert json.loads(keys["vefr-bag-" + name]) == ["pebble"]
    assert json.loads(keys["vefr-equipped-" + name]) == {"hand": "oak-staff"}
    assert json.loads(keys["vefr-growth-" + name]) == {"xp": 40, "counts": {}}
    assert keys["vefr-hp-" + name] == "12"
    doc = json.loads(keys["vefr-descent-" + name])
    assert doc == {"v": 1, "gen": delve.GEN_VERSION, "run": 0, "seed": "run-a", "order": [],
                   "floors": {}, "flags": {}, "card": delve.GEN_VERSION}


def test_storage_writes_only_what_the_scenario_names(pack):
    w = maplab.load_pack(pack)
    assert set(scenarios.storage(w, {"start": {"depth": 1}})) == {"vefr-descent-descent-test"}
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    del world["descent"]
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")
    plain = maplab.load_pack(pack)
    assert scenarios.storage(plain, {"start": {"region": "town"}, "gold": 3}) == {"vefr-gold-descent-test": "3"}


# ---------------------------------------------------------------- the twin: the player's own source

def _parts_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(PARTS.glob("*.js")))


def test_every_key_a_scenario_writes_is_one_the_player_reads():
    text = _parts_text()
    for prefix in [*scenarios.KEYS.values(), scenarios.DESCENT_KEY]:
        assert f"'{prefix}'" in text, f"no player part names the save key {prefix!r}"


def test_the_descent_document_version_is_the_players():
    source = (PARTS / "397-the-descent.js").read_text(encoding="utf-8")
    assert int(re.search(r"var DOC_VERSION = (\d+);", source).group(1)) == scenarios.DESCENT_DOC_VERSION
    assert int(re.search(r"var GEN_VERSION = (\d+);", source).group(1)) == delve.GEN_VERSION


def test_a_planted_save_carries_the_current_generation_so_no_old_save_card_opens(pack):
    # The descent offers its one-time generation card to any save holding one of these
    # Release 1 keys without a current document; a scenario must never look like that.
    source = (PARTS / "397-the-descent.js").read_text(encoding="utf-8")
    card_keys = re.findall(r"'(vefr-[a-z]+-)'", source[source.index("var CARD_KEYS"):][:200])
    assert {"vefr-bag-", "vefr-gold-", "vefr-hp-"} <= set(card_keys)
    keys = scenarios.storage(maplab.load_pack(pack), {"start": {"depth": 1}, "gold": 5, "bag": ["pebble"], "hp": 9})
    assert json.loads(keys["vefr-descent-descent-test"])["card"] == delve.GEN_VERSION


# ---------------------------------------------------------------- the dev tools refuse before a browser opens

def test_look_with_a_scenario_needs_a_pack(capsys):
    assert devtools.look(html="x.html", scenario="deep") == 2
    assert "--scenario needs --pack" in capsys.readouterr().err


def test_look_refuses_an_invalid_scenario_with_the_checks_sentences(pack, capsys):
    put(pack, "bad", {"start": {"region": "attic"}})
    assert devtools.look(pack=pack, scenario="bad") == 2
    assert "'attic' is not a region of this pack" in capsys.readouterr().err


def test_probe_refuses_a_scenario_the_pack_does_not_have(pack, capsys):
    put(pack, "deep", {"start": {"depth": 2}})
    assert devtools.probe(pack=pack, scenario="shallow") == 2
    assert "has no scenario 'shallow'; it has deep" in capsys.readouterr().err


def test_scenario_boot_carries_the_keys_the_start_and_the_world(pack):
    put(pack, "deep", {"start": {"depth": 2}, "gold": 7})
    boot, problems_ = devtools.scenario_boot(pack, "deep")
    assert problems_ is None
    assert boot["start"] == {"depth": 2}
    assert boot["world"] == "descent-test"
    assert boot["storage"]["vefr-gold-descent-test"] == "7"
