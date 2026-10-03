"""Equipment, slice 1: the pack fields `slot` and `mods` (the #217 plan, track A, A1). FROZEN CONTRACT.

An item may carry `slot` (exactly one of hand, body, head, feet, charm) and, only with a slot, `mods`
(an object with only atk and hp, each a whole number 0 to 9, bools refused). A slotted item may carry `value`
but not heal, light or use (a worn thing is not drunk or lit); an item named by a door's `requires.item` may
not have a slot (a key is not worn). Items without a slot are unchanged. The bake (`_player_items`) carries
`slot` and `mods` only when they are valid. Strict xfail until the validator and bake work lands (A1); the
pins that pass now guard it. The engine and UI tests (A2, A3) come with their slices.
"""

import json
import sys
from pathlib import Path

import pytest

from vefr import cli, maplab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_equip_pack as mk  # noqa: E402
import make_lock_pack as lockmk  # noqa: E402

SLOTS = ("hand", "body", "head", "feet", "charm")
needs_a1 = pytest.mark.xfail(strict=True, reason="equipment pack fields (A1) not built yet")


def errors_of(pack):
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def only(tmp_path, **item):
    """Validate the base pack plus one extra item `x`; return the errors."""
    return errors_of(mk.build(tmp_path, items={"x": {"name": "a thing", **item}}))


def named(errors, *needles):
    return any(all(n in e for n in needles) for e in errors)


# --- pins that pass today and must keep passing --------------------------------------------------

def test_a_pack_without_slots_is_unchanged(tmp_path):
    pack = mk.build(tmp_path, items={}, replace=True)
    assert errors_of(pack) == []
    assert maplab.load_pack(pack)["items"] == json.loads((pack / "world.json").read_text())["items"]


def test_load_pack_carries_items_and_a_bad_light_on_an_acts_pack_is_reported(tmp_path):
    assert "items" in maplab.load_pack(mk.build(tmp_path / "a"))
    bad = mk.build(tmp_path / "b", items={"torch": {"name": "a torch", "light": {"radius": 99, "turns": 6}}})
    assert named(errors_of(bad), "torch")


@pytest.mark.parametrize("slot", SLOTS)
@pytest.mark.parametrize("mods", [{}, {"atk": 0}, {"hp": 9, "atk": 9}])
def test_a_valid_slot_and_mods_pass(tmp_path, slot, mods):
    assert only(tmp_path, slot=slot, mods=mods) == []


def test_the_base_catalog_validates(tmp_path):
    assert errors_of(mk.build(tmp_path)) == []


# --- what A1 adds --------------------------------------------------------------------------------

@needs_a1
@pytest.mark.parametrize("slot", ["belt", "", 3, ["hand"], None, "Hand"])
def test_a_bad_slot_is_one_plain_sentence_naming_the_item_and_slot(tmp_path, slot):
    errors = only(tmp_path, slot=slot)
    assert len(errors) == 1 and named(errors, "a thing", "slot")


@needs_a1
@pytest.mark.parametrize("mods", [{"speed": 1}, {"atk": 10}, {"atk": -1}, {"hp": 1.5}, {"atk": True}, [1], "atk"])
def test_bad_mods_are_named(tmp_path, mods):
    errors = only(tmp_path, slot="hand", mods=mods)
    assert len(errors) == 1 and named(errors, "a thing", "mods")


@needs_a1
def test_mods_without_a_slot_are_named(tmp_path):
    errors = only(tmp_path, mods={"atk": 1})
    assert len(errors) == 1 and named(errors, "a thing", "mods", "slot")


@needs_a1
@pytest.mark.parametrize("field,value", [("heal", 3), ("light", {"radius": 2, "turns": 6}), ("use", "drink")])
def test_a_slot_cannot_combine_with_heal_light_or_use(tmp_path, field, value):
    errors = only(tmp_path, slot="hand", **{field: value})
    assert len(errors) == 1 and named(errors, "a thing", "slot", field)


def test_a_slot_may_combine_with_value_and_keep(tmp_path):
    assert only(tmp_path, slot="charm", value=3, keep=True) == []


@needs_a1
def test_a_door_key_cannot_be_worn(tmp_path):
    pack = lockmk.build(tmp_path, requires=lockmk.RING)
    world_json = pack / "world.json"
    world = json.loads(world_json.read_text())
    world["items"]["brass-ring"]["slot"] = "charm"
    world_json.write_text(json.dumps(world))
    baseline = errors_of(lockmk.build(tmp_path / "base", requires=lockmk.RING))
    new = [e for e in errors_of(pack) if e not in baseline]
    assert len(new) == 1 and named(new, "brass-ring", "slot", "key")


def test_a_slotted_item_that_is_not_a_key_is_fine_next_to_a_locked_door(tmp_path):
    pack = lockmk.build(tmp_path, requires=lockmk.RING)
    world_json = pack / "world.json"
    world = json.loads(world_json.read_text())
    world["items"]["cloak-1"] = {"name": "a cloak", "slot": "body", "mods": {"hp": 1}}
    world_json.write_text(json.dumps(world))
    baseline = errors_of(lockmk.build(tmp_path / "base", requires=lockmk.RING))
    assert [e for e in errors_of(pack) if e not in baseline] == []


@needs_a1
def test_the_bake_carries_slot_and_mods_only_when_valid():
    world = {"items": {
        "good": {"name": "a cloak", "slot": "body", "mods": {"hp": 2}},
        "bad-slot": {"name": "a belt", "slot": "belt", "mods": {"hp": 1}},
        "bad-mods": {"name": "a bow", "slot": "hand", "mods": {"atk": 10}},
        "plain": {"name": "a torch"},
    }}
    baked = cli._player_items(world)
    assert baked["good"]["slot"] == "body" and baked["good"]["mods"] == {"hp": 2}
    assert "slot" not in baked["bad-slot"] and "mods" not in baked["bad-slot"]
    assert baked["bad-mods"].get("slot") == "hand" and "mods" not in baked["bad-mods"]
    assert "slot" not in baked["plain"] and "mods" not in baked["plain"]
