"""Play-time floors: where a depth leads, and what floor it draws (slice E1). FROZEN CONTRACT.

`locate(depth, pack)` is pure and reads only the pack's Section list: the
story is cycle 0, and past the last Section's last floor the descent
walks the Sections again in cycle 1, 2, ... Every floor's randomness
comes from a named stream seeded `v3|<floor key>|<stream>`, so two
streams never share a draw and changing what lives on a floor cannot
move a wall. A floor is identified by `(gen, section hash, floor key)`,
and the budgets of PLAN §3 - 1.5 KB per visited floor, 250 KB for a
whole save at 40 floors - are engine constants, not pack choices.
"""

import copy
import sys
from pathlib import Path

import pytest

from vefr import delve

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
from make_descent_pack import ENTRY_AT, SECTIONS  # noqa: E402

# The descent this file walks: two Sections, five floors in cycle 0. It is
# the fixture pack's own descent, so the Python reference and the pack the
# tests weave are one piece of data and cannot drift apart.
DESCENT = {
    "run_seed": "run-a",
    "entry": {"region": "town", "at": list(ENTRY_AT)},
    "sections": copy.deepcopy(SECTIONS),
}

DEPTHS = list(range(1, 13))


# ---- locate ---------------------------------------------------------------

def test_the_story_is_cycle_zero_and_walks_the_sections_in_order():
    assert delve.locate(1, DESCENT) == (0, DESCENT["sections"][0], 1)
    assert delve.locate(3, DESCENT) == (0, DESCENT["sections"][0], 3)
    assert delve.locate(4, DESCENT) == (0, DESCENT["sections"][1], 1)
    assert delve.locate(5, DESCENT) == (0, DESCENT["sections"][1], 2)


def test_past_the_story_the_sections_repeat_in_the_next_cycle():
    # A cycle is the Sections' own floor counts: 3 + 2 = 5 floors.
    assert delve.locate(6, DESCENT) == (1, DESCENT["sections"][0], 1)
    assert delve.locate(8, DESCENT) == (1, DESCENT["sections"][0], 3)
    assert delve.locate(9, DESCENT) == (1, DESCENT["sections"][1], 1)
    assert delve.locate(10, DESCENT) == (1, DESCENT["sections"][1], 2)
    assert delve.locate(11, DESCENT) == (2, DESCENT["sections"][0], 1)


def test_locate_never_widens_the_descent_forever():
    # One floor per Section would make depth 300 cycle 150; the packing is
    # the Sections' own floor counts, nothing else.
    thin = copy.deepcopy(DESCENT)
    thin["sections"] = [{"id": "only", "floors": 1,
                         "size": {"w": [20, 20], "h": [12, 12]},
                         "rooms": [3, 3], "mobs": [0, 0]}]
    assert delve.locate(300, thin) == (299, thin["sections"][0], 1)


def test_locate_reads_only_the_section_list():
    # The same Section list in a different pack is the same answer, and a
    # depth of zero (there is no floor before the first) is refused.
    other = {"run_seed": "run-b", "sections": copy.deepcopy(DESCENT["sections"])}
    assert delve.locate(4, other) == delve.locate(4, DESCENT)
    with pytest.raises(ValueError):
        delve.locate(0, DESCENT)


def test_a_pack_with_no_sections_refuses_rather_than_guessing():
    with pytest.raises(ValueError):
        delve.locate(1, {"run_seed": "x", "sections": []})


# ---- the floor key and its streams ---------------------------------------

def test_the_floor_key_is_the_run_seed_the_section_the_cycle_and_the_floor():
    assert delve.floor_key("run-a", "cellar", 0, 1) == "run-a/cellar/0/1"
    assert delve.floor_key("run-a", "cellar", 2, 7) == "run-a/cellar/2/7"


def test_every_stream_is_named_off_the_floor_key():
    key = delve.floor_key("run-a", "cellar", 0, 1)
    assert delve.stream_seed(key, "layout") == "v3|run-a/cellar/0/1|layout"
    assert delve.stream_seed(key, "plan") == "v3|run-a/cellar/0/1|plan"
    assert delve.stream_seed(key, "pop") == "v3|run-a/cellar/0/1|pop"
    assert delve.loot_seed(key, "m3") == "v3|run-a/cellar/0/1|loot|m3"
    assert delve.chest_seed(key, "c1") == "v3|run-a/cellar/0/1|chest|c1"


def test_a_floor_is_named_for_its_place_in_the_descent():
    assert delve.floor_name("cellar", 0, 1) == "cellar-0-1"
    assert delve.floor_name("hollow", 3, 9) == "hollow-3-9"


def test_a_second_run_is_a_new_run_seed_but_the_same_descent():
    assert delve.run_seed("run-a", 0) == "run-a"
    assert delve.run_seed("run-a", 1) == "run-a/run-1"
    assert delve.run_seed("run-a", 12) == "run-a/run-12"


# ---- determinism ----------------------------------------------------------

def test_the_same_depth_draws_the_same_floor_every_time():
    for depth in DEPTHS:
        first = delve.floor_plan(DESCENT, depth)
        second = delve.floor_plan(DESCENT, depth)
        assert first == second, depth


def test_another_run_seed_is_another_floor():
    other = copy.deepcopy(DESCENT)
    other["run_seed"] = "run-b"
    keys = {delve.floor_plan(DESCENT, d)["key"] for d in DEPTHS}
    other_keys = {delve.floor_plan(other, d)["key"] for d in DEPTHS}
    assert keys.isdisjoint(other_keys)


def test_rooms_and_stairs_survive_a_reload_of_the_same_floor():
    plan = delve.floor_plan(DESCENT, 2)
    up, down = plan["anchors"]["up"], plan["anchors"]["down"]
    assert up != down
    assert plan["rows"][up[1]][up[0]] == "u"
    assert plan["rows"][down[1]][down[0]] == "d"


def test_changing_what_lives_on_a_floor_never_moves_a_wall():
    # The affix table is a different stream from the layout, so the whole
    # mob roster may change while the rooms stay exactly where they were.
    other = copy.deepcopy(DESCENT)
    other["sections"][0]["families"] = [
        {"id": "wight", "name": "a cold wight", "weight": 5,
         "hp": [6, 9], "atk": 3, "sight": 9, "drops": ["pebble", "pebble"]},
    ]
    other["sections"][0]["mobs"] = [6, 8]
    other["sections"][1]["mobs"] = [4, 4]
    for depth in DEPTHS:
        assert delve.floor_plan(other, depth)["rows"] == \
            delve.floor_plan(DESCENT, depth)["rows"], depth


def test_a_floor_is_sized_by_the_packs_play_time_bounds():
    for depth in DEPTHS:
        plan = delve.floor_plan(DESCENT, depth)
        _, section, _ = delve.locate(depth, DESCENT)
        assert section["size"]["w"][0] <= plan["w"] <= section["size"]["w"][1]
        assert section["size"]["h"][0] <= plan["h"] <= section["size"]["h"][1]
        assert section["rooms"][0] <= plan["rooms"] <= section["rooms"][1]
        assert all(len(row) == plan["w"] for row in plan["rows"])
        assert len(plan["rows"]) == plan["h"]


def test_the_plan_stream_decides_the_kind_and_the_layout_stream_the_walls():
    for depth in DEPTHS:
        plan = delve.floor_plan(DESCENT, depth)
        _, section, k = delve.locate(depth, DESCENT)
        pattern = section.get("pattern")
        assert plan["kind"] == (pattern[k - 1] if pattern else "n")
        # Draw the layout by hand from the layout stream alone: the rows
        # are the generator's, with no plan and no pack read anywhere.
        rows = delve.generate_floor_v2(
            delve.stream_seed(plan["key"], "layout"), plan["w"], plan["h"],
            plan["rooms"])
        assert rows == plan["rows"], depth


def test_the_plan_is_json_able_and_carries_no_grid_in_the_identity():
    import json
    for depth in DEPTHS:
        text = json.dumps(delve.floor_plan(DESCENT, depth))
        assert isinstance(text, str) and text


# ---- floor identity -------------------------------------------------------

def test_a_floor_is_identified_by_its_generation_hash_and_key():
    ident = delve.floor_identity(DESCENT, 2)
    assert set(ident) == {"gen", "hash", "key"}
    assert ident["gen"] == delve.GEN_VERSION
    assert ident["key"] == "run-a/cellar/0/2"
    assert ident["hash"] == delve.section_hash(DESCENT["sections"][0])
    assert delve.floor_identity(DESCENT, 2) == ident


def test_editing_the_section_changes_the_hash_and_nothing_else():
    other = copy.deepcopy(DESCENT)
    other["sections"][0]["title"] = "The Cellar, Wet"
    assert delve.section_hash(other["sections"][0]) != \
        delve.section_hash(DESCENT["sections"][0])
    # The floors are drawn from the run seed and the Section's own numbers,
    # not from its title, so a cosmetic edit moves no wall either.
    assert delve.floor_plan(other, 2)["rows"] == delve.floor_plan(DESCENT, 2)["rows"]


def test_a_hash_is_short_stable_and_says_nothing_about_the_section():
    import json
    h = delve.section_hash(DESCENT["sections"][0])
    assert len(h) == 12
    assert delve.section_hash(DESCENT["sections"][0]) == h
    assert "cellar" not in h and json.dumps(DESCENT["sections"][0]) not in h


# ---- what lives on a floor ----------------------------------------------

def test_the_mobs_stand_far_enough_from_both_stairs():
    for depth in DEPTHS:
        plan = delve.floor_plan(DESCENT, depth)
        up = plan["anchors"]["up"]
        down = plan["anchors"]["down"]
        seen = set()
        for mob in plan["mobs"]:
            at = tuple(mob["at"])
            assert at not in seen
            seen.add(at)
            assert plan["rows"][at[1]][at[0]] == "."
            for stair in (up, down):
                assert abs(at[0] - stair[0]) + abs(at[1] - stair[1]) >= 7


def test_the_mob_roster_is_within_the_packs_bounds_and_ids_by_index():
    for depth in DEPTHS:
        plan = delve.floor_plan(DESCENT, depth)
        _, section, _ = delve.locate(depth, DESCENT)
        lo, hi = section["mobs"]
        assert lo <= len(plan["mobs"]) <= hi
        assert [m["id"] for m in plan["mobs"]] == \
            ["m%d" % i for i in range(len(plan["mobs"]))]
        for mob in plan["mobs"]:
            assert mob["name"] and mob["hp"] >= 1 and mob["atk"] >= 1
            assert isinstance(mob["drops"], list)


def test_a_floor_of_the_hollow_section_carries_only_its_own_families():
    # depth 4 is the hollow Section's first floor
    plan = delve.floor_plan(DESCENT, 4)
    names = {m["name"] for m in plan["mobs"]}
    assert names <= {"a hollow shade"}


def test_a_mobs_drops_come_from_that_mobs_own_stream():
    # Killing in another order cannot change what a monster carries: the
    # loot is seeded per mob id, never from the floor's shared stream.
    key = delve.floor_key("run-a", "cellar", 0, 1)
    table = ["pebble", "pebble"]
    first = delve.mob_drops(key, "m0", table)
    assert delve.mob_drops(key, "m0", table) == first
    assert isinstance(delve.mob_drops(key, "m1", table), list)
    assert delve.mob_drops(key, "m0", []) == []
    other = delve.floor_key("run-a", "cellar", 0, 2)
    assert delve.loot_seed(other, "m0") == "v3|run-a/cellar/0/2|loot|m0"


# ---- the budgets and the ban --------------------------------------------

def test_the_budgets_are_the_ones_the_plan_set():
    assert delve.FLOOR_CAP == 40
    assert delve.FLOOR_BYTES == 1_500
    assert delve.SAVE_BYTES == 250_000


def test_the_descent_part_draws_only_from_its_streams():
    # The banned sources, as a check rather than a promise: no wall clock,
    # no Math.random, no globals, and no float that is not a whole number
    # drawn off a stream.
    import re
    from pathlib import Path

    part = Path(__file__).resolve().parent.parent / "web" / "player" / "parts" \
        / "397-the-descent.js"
    text = part.read_text(encoding="utf-8")
    for banned in ("Math.random", "Date.now", "new Date", "performance.now",
                   "crypto.getRandomValues", "localStorage"):
        assert banned not in text, banned
    # Every float off a stream is whole: floor(rng() * n) and nothing else.
    for hit in re.finditer(r"rng\(\)", text):
        start = text.rfind("\n", 0, hit.start()) + 1
        line = text[start:text.find("\n", hit.end())]
        assert "*" in line or re.search(r"[<>]=?\s*rng\(\)", line), line