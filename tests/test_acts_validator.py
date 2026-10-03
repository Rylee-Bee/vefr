"""The validator covers EVERY act of an acts-shape pack (the #217 plan, track B, slice B1). FROZEN CONTRACT.

Today `maplab.load_pack` builds its unified dict from the first act only and does not carry `items` or `acts`,
so `norns validate` never runs the per-act law checks, the item catalog checks, or any check on act 2's regions,
doors, enemies and locks. These tests pin the fix: every problem in any act is named, and the message says
WHICH act ("act 'act-2' ..."). These all pass now.
"""

import sys
from pathlib import Path


from vefr import maplab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_two_act_pack as mk  # noqa: E402


def errors_of(pack):
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def named(errors, *needles):
    return any(all(n in e for n in needles) for e in errors)


def door(**kw):
    return {"from": "hall", "at": [4, 4], "to": "hall", "to_at": [3, 4], **kw}


# --- pins that pass today and must keep passing ------------------------------------------------

def test_the_sample_world_still_validates():
    assert errors_of(ROOT / "worlds" / "sample-world") == []


def test_the_two_act_fixture_validates(tmp_path):
    assert errors_of(mk.build(tmp_path)) == []


# --- act law fields -----------------------------------------------------------------------------

def test_a_bad_floor_on_act_one_of_an_acts_pack_is_named(tmp_path):
    errors = errors_of(mk.build(tmp_path, act1={"floor": "bogus"}))
    assert named(errors, "act 'act-1'", "floor")


def test_act_two_law_fields_are_checked_and_name_act_two(tmp_path):
    assert named(errors_of(mk.build(tmp_path / "a", act2={"tone": "frantic"})), "act 'act-2'", "tone")
    assert named(errors_of(mk.build(tmp_path / "b", act2={"verbs": "talk"})), "act 'act-2'", "verbs")


# --- act 2's regions, doors, enemies and locks, against act 2's own regions -----------------------

def test_an_act_two_door_to_an_undeclared_region_is_named(tmp_path):
    errors = errors_of(mk.build(tmp_path, act2={"transitions": [door(to="nowhere")]}))
    assert named(errors, "act 'act-2'", "nowhere")


def test_an_act_two_door_into_act_one_is_refused_doors_stay_inside_their_act(tmp_path):
    errors = errors_of(mk.build(tmp_path, act2={"transitions": [door(to="town", to_at=[3, 4])]}))
    assert named(errors, "act 'act-2'", "town", "inside")


def test_an_act_two_enemy_on_a_wall_is_named(tmp_path):
    enemy = {"id": "wall-rat", "name": "a rat", "at": [0, 0], "hp": 1, "atk": 1}
    errors = errors_of(mk.build(tmp_path, hall_contract={"enemies": [enemy]}))
    assert named(errors, "hall", "wall-rat")


def test_an_act_two_lock_naming_an_unknown_item_is_named(tmp_path):
    errors = errors_of(mk.build(tmp_path, act2={"transitions": [door(requires={"item": "no-such-item"})]}))
    assert named(errors, "no-such-item")


def test_a_valid_act_two_door_and_lock_pass(tmp_path):
    ok = door(requires={"item": "torch"}, locked_text="The hall door is shut.")
    assert errors_of(mk.build(tmp_path, act2={"transitions": [ok]})) == []


# --- the item catalog on an acts-shape pack ---------------------------------------------------------

def test_the_item_catalog_is_checked_on_an_acts_pack(tmp_path):
    bad = {"items": {"torch": {"name": "a torch", "light": {"radius": 99, "turns": 6}}}}
    errors = errors_of(mk.build(tmp_path, world=bad))
    assert named(errors, "torch")
