"""E7.2b: the v3 pop stage - elites, linked groups, and the closed spawn.

ADR 0014 is the contract. "Pop stage" fixes the budget and the placement
rules, "Hard caps" fixes the ceilings, "Draw order" fixes the order the
stream is consumed in, and "FloorPlan spawn keys (closed)" fixes the
shape of a spawn. This file is the unit-level reading of those clauses
for one floor at a time.

The property sweep in `tests/test_floor_v3_properties.py` is the other
half of the acceptance and is not extended here: it answers the same
questions over 200 seeds x 4 sizes x 4 kinds, where this file answers
them over a handful of floors with the numbers spelled out, so a failure
here says WHICH clause broke rather than only that one did.

Nothing here mocks the generator and nothing pokes at a private name:
every assertion reads a `FloorPlan` and the pack that produced it, the
way a caller does. The one exception is the draw count, which no
`FloorPlan` carries; that one test wraps `vefr.delve_v3.prng` and counts
the calls the pop stream made, because "the count is a statement of its
own" is a claim about draws and nothing else can see it.

Run with:

    bash tests/run.sh tests/test_elite_groups_pop.py
"""

from __future__ import annotations

import copy
import json
from collections import deque

import pytest

from vefr import delve_v3


# Two of the four sizes of PLAN.md section 3. 64x48 is the candidate
# default and is the one that carries enough free tiles for a floor with
# two elites, two full groups and the randoms after them; 48x32 is the
# baseline and is the tight end of the budget clamp.
SIZES = [(48, 32, 16), (64, 48, 18)]
SEEDS = [f"pop-{index}" for index in range(8)]

# The closed spawn keys of ADR 0014, all eight and nothing else. The
# `hp`/`atk`/`xp` a brief once asked for are NOT in the set below: the
# ADR closes the keys, and a spawn that carried one would pass this
# check. `warden` is in the ADR's list and is deliberately NOT in the
# set below either: ADR 0015 owns the warden and no spawn may carry
# the key until one exists.
SPAWN_KEYS = {
    "id", "family", "at", "elite", "group", "leader", "leash", "warden",
}

# The room shapes ADR 0014 names a stamp room by, as the graph stage
# writes them into `rooms[i][4]`.
STAMP_ROOMS = ("hall", "vault")

WALKABLE = frozenset(".ud")


def pack(**over) -> dict:
    """A Section pack for the pop stage, with the keys the ADR names.

    `elites.per_floor` and `groups.per_floor` default to asking for one
    of each so a floor without an override carries an elite and a group;
    a test that wants neither says so. `groups.leader` defaults to
    `normal` and `same_family` to `false`, which are the generator's
    defaults for a pack that names neither.

    The `affixes` list is the pack root's `affixes.json` handed to the
    generator beside the Section: the pop stage reads it on the `pop`
    stream and nowhere else, and it is what turns an affix ID into the
    record `vefr.mob_stats` scales the base by.

    The family entries carry a `hp`, `atk` and `xp`, which is how a pack
    that resolves its families through a Blueprint hands the resolved
    base to the pop stage. A family entry without them still draws; its
    stats come back at mob_stats' own floor of 1.
    """
    base = {
        "section": 1,
        "id": "cellar-normal",
        "rooms": [16, 16],
        "families": [
            {"family": "rat", "weight": 5, "hp": 8, "atk": 3, "xp": 4},
            {"family": "moth", "weight": 3, "hp": 5, "atk": 2, "xp": 3},
            {"family": "beetle", "weight": 2, "hp": 12, "atk": 4, "xp": 6},
        ],
        "elites": {"per_floor": [1, 1], "affixes": ["big"]},
        "groups": {"per_floor": [1, 1], "minions": [2, 3]},
        "affixes": [
            {"id": "big", "label": "Big {name}", "hp": 1.5, "xp": 1.5, "scale": 1.3},
            {"id": "quick", "label": "Quick {name}", "atk": 1.2, "xp": 1.2, "sight": 1},
        ],
        "curve": {"hp": [1.0, 1.0], "atk": [1.0, 1.0]},
        "loot": {"tier": 1},
        "pois": ["the drowned well"],
        "warden": "ashwing",
    }
    base.update(over)
    return base


def floor(seed: str = "pop-0", size: tuple[int, int] = (64, 48),
          kind: str = "normal", **over) -> dict:
    """One v3 floor of one pack, deep-copied in so the pack is never shared."""
    return delve_v3.generate_floor_v3(seed, size, copy.deepcopy(pack(**over)), kind)


# ------------------------------------------------------------- the fixtures


def _room_of(plan: dict, tile) -> int:
    """The index of the room rectangle a tile stands in, or -1."""
    for index, room in enumerate(plan["rooms"]):
        if (room[0] <= tile[0] < room[0] + room[2]
                and room[1] <= tile[1] < room[1] + room[3]):
            return index
    return -1


def _secret_rooms(plan: dict) -> set[int]:
    """The rooms PLAN.md section 2 turned into secret rooms."""
    return {_room_of(plan, tuple(tile)) for tile in plan["secrets"]} - {-1}


def _stamp_rooms(plan: dict) -> set[int]:
    """The rooms the graph stage named a hall or a vault."""
    return {index for index, room in enumerate(plan["rooms"])
            if room[4] in STAMP_ROOMS}


def _chebyshev(a, b) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _walkable(plan: dict) -> set[tuple[int, int]]:
    return {
        (x, y)
        for y in range(plan["h"])
        for x in range(plan["w"])
        if plan["rows"][y][x] in WALKABLE
    }


def _corridor_run(plan: dict, start) -> set[tuple[int, int]]:
    """The 4-connected run of corridor tiles holding `start`."""
    rows, w, h = plan["rows"], plan["w"], plan["h"]
    start = (start[0], start[1])
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx < w and 0 <= ny < h) or (nx, ny) in seen:
                continue
            if rows[ny][nx] in WALKABLE and _room_of(plan, (nx, ny)) < 0:
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def _spawns(plan: dict) -> list[dict]:
    return plan["spawns"]


def _leaders(plan: dict) -> list[dict]:
    return [spawn for spawn in _spawns(plan) if spawn.get("leader") is True]


def _lone_elites(plan: dict) -> list[dict]:
    return [spawn for spawn in _spawns(plan)
            if "elite" in spawn and "group" not in spawn]


def _groups(plan: dict) -> list[str]:
    """The group ids in first-appearance order, which is `g<n>` order."""
    seen: list[str] = []
    for spawn in _spawns(plan):
        group = spawn.get("group")
        if group is not None and group not in seen:
            seen.append(group)
    return seen


# ------------------------------------------------------------ the draw order


def test_ids_are_m0_in_draw_order():
    """`m<n>` follows the draw order, and the first draw is `m0`.

    The counter follows the draws and nothing else, so the ids of one
    floor are `m0` up to `m{n-1}` with no gap and no repeat, in the order
    the spawns are listed.
    """
    for w, h, rooms in SIZES:
        for seed in SEEDS:
            plan = floor(seed, (w, h), **{"rooms": [rooms, rooms]})
            ids = [spawn["id"] for spawn in _spawns(plan)]
            assert ids == [f"m{index}" for index in range(len(ids))], (
                f"{seed} {w}x{h}: ids are {ids[:8]}..., not m0.. in order"
            )


def test_group_ids_are_g0_in_draw_order():
    """`g<n>` numbers the groups in the order they were drawn."""
    for w, h, rooms in SIZES:
        for seed in SEEDS:
            plan = floor(seed, (w, h), **{"rooms": [rooms, rooms]})
            groups = _groups(plan)
            assert groups == [f"g{index}" for index in range(len(groups))], (
                f"{seed} {w}x{h}: group ids are {groups}"
            )


def test_elites_then_groups_then_randoms():
    """The ADR's draw order, read straight off the spawn list.

    ADR 0014 "Draw order" is 1. elites, 2. groups, 3. randoms, and the
    ids are the draw order. So a pack that pins itself to two elites and
    two groups must read as: two `elite` spawns with no `group`, then a
    run of grouped spawns holding two leaders, then a run of randoms
    with neither key.

    The size of the middle run is NOT asserted. ADR 0014 caps a group at
    four members and does not promise it four: a leader that lands in a
    one-tile-wide corridor has two tiles within reach of itself and not
    one more, and a group that stops at what its leader can hold is the
    cap working, not the draw order breaking.
    """
    for w, h, rooms in SIZES:
        for seed in SEEDS:
            plan = floor(seed, (w, h), **{
                "rooms": [rooms, rooms],
                "elites": {"per_floor": [2, 2], "affixes": ["big", "quick"]},
                "groups": {"per_floor": [2, 2], "minions": [3, 3]},
            })
            spawns = _spawns(plan)
            lone = spawns[:2]
            assert all("elite" in s and "group" not in s for s in lone), (
                f"{seed} {w}x{h}: the first two draws are {lone}"
            )
            kinds = ["elite" if "elite" in s else
                     "group" if "group" in s else "random" for s in spawns]
            # One run of each, in the ADR's order, with nothing after a
            # run but the next run and nothing before the first.
            runs = [kinds[0]] + [b for a, b in zip(kinds, kinds[1:]) if a != b]
            assert runs == ["elite", "group", "random"], (
                f"{seed} {w}x{h}: the spawn list runs {runs}, not "
                "elites then groups then randoms"
            )
            grouped = [s for s in spawns if "group" in s]
            assert sum(1 for s in grouped if s.get("leader") is True) == 2, (
                f"{seed} {w}x{h}: two groups, two leaders expected in {grouped}"
            )
            assert len(_groups(plan)) == 2, f"{seed} {w}x{h}: {_groups(plan)}"


def test_elite_count_is_drawn_even_with_no_affix_table(monkeypatch):
    """The count is a statement of its own: one draw, whatever its value.

    ADR 0014 fixes the count at `rand(elite_lo, elite_hi)`, and the stage
    comment says why it is made BEFORE the loop: a pack with an elite
    count and no affix table has to consume the same count draw a pack
    with a table does, or the two streams part and a rewritten affix
    table would move a tile. A count written inside the `range()` call
    would read as "the count is only drawn when there are affixes".

    So the three packs below differ ONLY in `elites.per_floor` - [0,0],
    [1,1] and [2,2] - and all three name no affix at all. Identical draw
    counts are the claim: the count is drawn whatever it comes out as,
    and a pack with no table places nothing after it. A generator that
    wrote the count as `range(_rand(...) if affixes else 0)` would cost
    [0,0] one draw fewer than the other two and this fails.
    """
    def pop_draws(elites: dict) -> int:
        real = delve_v3.prng
        seen = 0

        def counting(key: str):
            nonlocal seen
            seed = real(key)
            if not key.endswith("|pop"):
                return seed

            def wrapped() -> float:
                nonlocal seen
                seen += 1
                return seed()

            return wrapped

        monkeypatch.setattr(delve_v3, "prng", counting)
        plan = delve_v3.generate_floor_v3(
            "pop-draws", (64, 48),
            copy.deepcopy(pack(elites=elites, **{"groups": {"per_floor": [0, 0],
                                                             "minions": [2, 3]}})),
            "normal",
        )
        return seen, [s for s in plan["spawns"] if "elite" in s]

    none, no_elites = pop_draws({"per_floor": [0, 0], "affixes": []})
    one, still_none = pop_draws({"per_floor": [1, 1], "affixes": []})
    two, never_two = pop_draws({"per_floor": [2, 2], "affixes": []})
    assert one == none == two, (
        f"the elite count cost {none}, {one} and {two} draws for [0,0], "
        "[1,1] and [2,2]: it is one draw whatever it comes out as"
    )
    assert not (no_elites or still_none or never_two), (
        "a pack with an elite count and no affix table places no elite"
    )


def test_a_minion_that_is_never_placed_costs_no_draw(monkeypatch):
    """A family is drawn when a minion is placed, not when one is asked for.

    With `same_family: false` each minion draws its own family, and the
    draw used to be taken BEFORE the tile was found. A leader whose box
    has no free tile left - the box is Chebyshev 2 of the leader in its
    own room or corridor region, so a leader standing in a corridor
    between two rooms runs out early - then spent a family draw on a
    minion that was never written to the plan, and every draw after it
    landed one step out of place.

    The floor below is that floor: seed `pop-12` at 64x48 draws three
    minions for `g0` and places two of them, so one placement fails. The
    draw count is then re-derived from the plan rather than read off the
    generator - one elite count, one group count, the group's minion
    count and the leader's family, one family per minion PLACED, one per
    random placed, the chest count and one table per chest - and the two
    have to agree.

    The second half is what the wasted draw did to the floor, and it is
    why this is a bug and not a curiosity: the chest count is drawn off
    the same stream, so one family too many made this floor carry two
    chests instead of four, and every chest table after it one step out.
    A minion that could not be placed changed what a hero finds on the
    other side of the floor.
    """
    section = pack(elites={"per_floor": [0, 0], "affixes": []},
                   groups={"per_floor": [1, 1], "minions": [3, 3],
                           "same_family": False})

    real = delve_v3.prng
    seen = 0

    def counting(key: str):
        nonlocal seen
        seed = real(key)
        if not key.endswith("|pop"):
            return seed

        def wrapped() -> float:
            nonlocal seen
            seen += 1
            return seed()

        return wrapped

    monkeypatch.setattr(delve_v3, "prng", counting)
    # The floor key changed, every floor was redrawn, and pop-12 at 64x48 no
    # longer has the shape this test is about. It needs two halves at once:
    # two of g0's three minions placed and one that could not be, AND four
    # chests - one wasted family draw would have taken two of them away. No
    # seed at 64x48 has that shape any more; pop-13 at 48x32 does. Neither the
    # assertions nor the pins move.
    plan = delve_v3.generate_floor_v3(
        "pop-13", (48, 32), copy.deepcopy(section), "normal")
    assert plan["gen"] == 3, "the fixture is a v3 floor, or it proves nothing"

    members = [s for s in _spawns(plan) if s.get("group") == "g0"]
    placed = [m for m in members if not m.get("leader")]
    randoms = [s for s in plan["spawns"]
               if "group" not in s and "elite" not in s]
    assert len(placed) == 2, (
        "the fixture needs a minion that could not be placed: g0 asks for "
        f"3 and placed {len(placed)}"
    )
    expected = 1 + 1 + 2 + len(placed) + len(randoms) + 1 + len(plan["chests"])
    assert seen == expected, (
        f"the pop stream spent {seen} draws and the floor accounts for "
        f"{expected}: {1} elite count, {1} group count, "
        f"{2} for the minion count and the leader's family, "
        f"{len(placed)} for the minions placed, {len(randoms)} for the "
        f"randoms placed, {1} chest count and {len(plan['chests'])} chest "
        f"tables"
    )
    assert len(plan["chests"]) == 4, (
        f"this floor carries {len(plan['chests'])} chests: a wasted family "
        "draw moved the chest count and took two of them away"
    )


def test_a_leader_that_is_never_placed_costs_no_draw(monkeypatch):
    """Same rule, one loop up: a leader's family is drawn when it is led.

    The minion fix above settled the tile before the family. The two
    loops that had not been changed are the group leader and the random,
    and both drew before their tile: a leader's family (and its affix,
    where the group is led by an elite) and a random's family. The leader
    is the one that reaches it easily, because the leader pool is
    `clear` less the vault, hall and secret rooms, and a minion standing
    a tile or two from its own leader spends the same pool - so a floor
    with three groups asked for and a leader pool of three tiles runs
    out at `g1` and never gets there.

    The floor below is that floor: `pop-18` at 22x15 asks for three
    groups and is led once. The group's own minion count is still drawn
    before its leader is placed - a count is a statement of its own, the
    same way the elite count and the group count are, and ADR 0014 lists
    it ahead of the leader's tile - so the group that never formed spent
    exactly one draw and not one more.

    What the wasted draw did is on the second half of the assertion. The
    chest count comes off the same pop stream, so one family too many
    made this floor carry THREE chests instead of two, and a hero found a
    third one that the floor key does not put there. The draw count is
    re-derived from the plan rather than read off the generator, so the
    two have to agree.
    """
    section = pack(groups={"per_floor": [3, 3], "minions": [1, 1],
                           "same_family": True})

    real = delve_v3.prng
    seen = 0

    def counting(key: str):
        nonlocal seen
        seed = real(key)
        if not key.endswith("|pop"):
            return seed

        def wrapped() -> float:
            nonlocal seen
            seen += 1
            return seed()

        return wrapped

    monkeypatch.setattr(delve_v3, "prng", counting)
    # pop-45, not pop-18: the redraw gave pop-18 a floor that staffs its second
    # group, so there is no unstaffed group left to measure. At 22x15 this seed
    # leaves exactly g0 led while the pack asks for three.
    plan = delve_v3.generate_floor_v3(
        "pop-45", (22, 15), copy.deepcopy(section), "normal")
    assert plan["gen"] == 3, "the fixture is a v3 floor, or it proves nothing"

    lone = _lone_elites(plan)
    led = _groups(plan)
    randoms = [s for s in _spawns(plan) if "group" not in s and "elite" not in s]
    assert led == ["g0"], (
        "the fixture needs groups the floor could not staff: the pack asks "
        f"for 3 and the floor carries {led}"
    )
    expected = (1                      # the elite count, drawn before its loop
                + 2 * len(lone)        # a family and an affix per elite placed
                + 1                     # the group count, drawn before its loop
                + 2                     # g0: its minion count, then its leader
                + 1                     # g1: its minion count, and no leader
                + len(randoms)         # a family per random placed
                + 1 + len(plan["chests"]))
    assert seen == expected, (
        f"the pop stream spent {seen} draws and the floor accounts for "
        f"{expected}: {1} elite count, {2 * len(lone)} for the {len(lone)} "
        f"elite(s) placed, {1} group count, {2} for the minion count and the "
        f"family of the one group that was led, {1} for the minion count of "
        f"the group that was not, {len(randoms)} for the randoms placed, "
        f"{1} chest count and {len(plan['chests'])} chest tables"
    )
    # Three, not two: the seed moved with the floor after the key change and
    # this floor carries one more chest. A real pin rather than decoration:
    # chest term FROM the plan, so it cannot catch a wrong count by itself.
    assert len(plan["chests"]) == 3, (
        f"this floor carries {len(plan['chests'])} chests: a wasted leader "
        "family draw moved the chest count and added one"
    )


# --------------------------------------------------------------- hard caps


@pytest.mark.parametrize("w, h, rooms", SIZES)
def test_hard_caps_hold(w, h, rooms):
    """ADR 0014's ceilings, on a pack that asks past every one of them.

    The pack asks for 5 elites, 5 groups of 5, and an elite-led group,
    which is outside what the pack validator would accept. The
    generator does not validate: it caps, and a cap that is hit "stops
    further draws of that kind - it does not raise, and it does not fail
    the floor". So a floor still comes back, with 36 monsters at most,
    2 lone elites, 3 groups and 4 members in each.
    """
    for seed in SEEDS:
        plan = floor(seed, (w, h), **{
            "rooms": [rooms, rooms],
            "elites": {"per_floor": [5, 5], "affixes": ["big", "quick"]},
            "groups": {"per_floor": [5, 5], "minions": [4, 5],
                       "leader": "elite", "same_family": True},
        })
        spawns = _spawns(plan)
        assert len(spawns) <= 36, f"{seed} {w}x{h}: {len(spawns)} monsters"
        assert len(_lone_elites(plan)) <= 2, (
            f"{seed} {w}x{h}: {len(_lone_elites(plan))} lone elites"
        )
        assert len(_groups(plan)) <= 3, f"{seed} {w}x{h}: {len(_groups(plan))} groups"
        for group in _groups(plan):
            members = [s for s in spawns if s.get("group") == group]
            assert len(members) <= 4, (
                f"{seed} {w}x{h}: group {group} has {len(members)} members"
            )
            assert sum(1 for s in members if s.get("leader") is True) == 1, (
                f"{seed} {w}x{h}: group {group} has {members}"
            )
        elite_led = [
            group for group in _groups(plan)
            if any(s.get("group") == group and "elite" in s for s in spawns)
        ]
        rooms_in_floor = len(plan["rooms"])
        assert len(elite_led) <= max(1, rooms_in_floor // 8), (
            f"{seed} {w}x{h}: {len(elite_led)} elite-led groups over "
            f"{rooms_in_floor} rooms"
        )


@pytest.mark.parametrize("w, h, rooms", SIZES)
def test_a_small_floor_is_filled_from_the_budget(w, h, rooms):
    """The budget is the count, and the randoms fill what the elites and
    the groups left of it.

    `budget = clamp(walkable // 30, 4, 36)`. The floor under test names
    no elite and no group, so the randoms carry the whole budget and the
    spawn count is it exactly - which also pins that the count is not a
    draw of its own.
    """
    for seed in SEEDS:
        plan = floor(seed, (w, h), **{
            "rooms": [rooms, rooms],
            "elites": {"per_floor": [0, 0], "affixes": ["big"]},
            "groups": {"per_floor": [0, 0], "minions": [2, 3]},
        })
        walkable = len(_walkable(plan))
        budget = min(36, max(4, walkable // 30))
        assert len(_spawns(plan)) == budget, (
            f"{seed} {w}x{h}: {walkable} walkable tiles is a budget of {budget}, "
            f"and {len(_spawns(plan))} spawns came back"
        )


# --------------------------------------------------------------- placement


@pytest.mark.parametrize("w, h, rooms", SIZES)
def test_leaders_stand_clear_of_both_stairs(w, h, rooms):
    """A leader is at least STAIR_CLEAR (7) from both stairs, Chebyshev."""
    assert delve_v3.STAIR_CLEAR == 7, "the ADR's number for a leader is 7"
    for seed in SEEDS:
        plan = floor(seed, (w, h), **{"rooms": [rooms, rooms]})
        stairs = [tuple(plan["anchors"][name]) for name in ("up", "down")]
        for leader in _leaders(plan):
            for stair in stairs:
                assert _chebyshev(leader["at"], stair) >= delve_v3.STAIR_CLEAR, (
                    f"{seed} {w}x{h}: leader {leader['id']} at {leader['at']} is "
                    f"{_chebyshev(leader['at'], stair)} from {stair}"
                )


@pytest.mark.parametrize("w, h, rooms", SIZES)
def test_leaders_are_never_in_a_vault_hall_or_secret_room(w, h, rooms):
    """The placement rule's other half: a stamp room and a secret room
    are spoken for, and a leader stands in neither."""
    for seed in SEEDS:
        plan = floor(seed, (w, h), **{
            "rooms": [rooms, rooms],
            "elites": {"per_floor": [2, 2], "affixes": ["big", "quick"]},
            "groups": {"per_floor": [3, 3], "minions": [2, 3],
                       "leader": "elite", "same_family": True},
        })
        blocked = _stamp_rooms(plan) | _secret_rooms(plan)
        for leader in _leaders(plan):
            room = _room_of(plan, leader["at"])
            assert room not in blocked, (
                f"{seed} {w}x{h}: leader {leader['id']} at {leader['at']} is in "
                f"room {room} ({plan['rooms'][room][4] if room >= 0 else 'corridor'})"
            )


@pytest.mark.parametrize("w, h, rooms", SIZES)
def test_minions_stay_within_two_tiles_of_their_leader(w, h, rooms):
    """Chebyshev 2, and not the 4 the stage used to search.

    ADR 0014 "Placement": "Minions stand within Chebyshev 2 of the
    leader, in the same room or corridor region." Both halves are
    checked here - the straight line AND the region, because a floor
    with a wall inside 4 tiles would satisfy the first and break the
    second.
    """
    for seed in SEEDS:
        plan = floor(seed, (w, h), **{"rooms": [rooms, rooms]})
        by_group: dict[str, dict] = {}
        for spawn in _spawns(plan):
            if spawn.get("leader") is True:
                by_group[spawn["group"]] = spawn
        assert by_group, f"{seed} {w}x{h}: no group leader to check"
        for group, leader in by_group.items():
            region = _region_of(plan, leader["at"])
            for spawn in _spawns(plan):
                if spawn.get("group") != group or spawn.get("leader") is True:
                    continue
                assert _chebyshev(spawn["at"], leader["at"]) <= 2, (
                    f"{seed} {w}x{h}: {spawn['id']} at {spawn['at']} is "
                    f"{_chebyshev(spawn['at'], leader['at'])} from its leader "
                    f"{leader['id']} at {leader['at']}"
                )
                assert _region_of(plan, spawn["at"]) == region, (
                    f"{seed} {w}x{h}: {spawn['id']} at {spawn['at']} is in a "
                    f"different region from its leader at {leader['at']}"
                )


def _region_of(plan: dict, tile) -> tuple:
    """The room or corridor region a tile belongs to, as one hashable."""
    room = _room_of(plan, tile)
    if room >= 0:
        return ("room", room)
    return ("corr",) + tuple(sorted(_corridor_run(plan, tile)))

# ---------------------------------------------------------------- the shape


@pytest.mark.parametrize("w, h, rooms", SIZES)
def test_spawn_keys_are_closed(w, h, rooms):
    """A spawn carries only the ADR's keys, and carries the three always
    ones. `leader` appears as `true` and as nothing else, and `warden` -
    which ADR 0015 owns - is never written.
    """
    for seed in SEEDS:
        plan = floor(seed, (w, h), **{"rooms": [rooms, rooms]})
        for spawn in _spawns(plan):
            keys = set(spawn)
            assert keys <= SPAWN_KEYS, f"{seed}: spawn {spawn} has keys {keys - SPAWN_KEYS}"
            assert {"id", "family", "at"} <= keys, f"{seed}: spawn {spawn} is missing a key"
            assert "leader" not in spawn or spawn["leader"] is True, (
                f"{seed}: leader is {spawn['leader']!r}, and is only ever true or absent"
            )
            assert "warden" not in keys, f"{seed}: {spawn} carries a warden key"


# --------------------------------------------------------------- the leash


@pytest.mark.parametrize("w, h, rooms", SIZES)
def test_the_configured_leash_rides_on_every_group_member(w, h, rooms):
    """ADR 0014's "Section `groups`" names a `leash`, and it has to reach
    the spawn or the pack wrote it for nothing.

    The player reads `leash` off a baked spawn record and asks any member
    of a group for it (part 420's `groupLeash`), and a spawn that carries
    no `leash` reads as the player's own default of 6. So a Section that
    wrote `leash: 11` and got spawns without the key had eleven tiles of
    leash asked for and six used, with nothing anywhere saying so.

    Every member carries it, not just the leader: `groupLeash` falls back
    to any member's record precisely so a pack that writes the leash once
    is not asked to write it four times, and a key only on the leader
    would make that fallback dead.
    """
    for seed in SEEDS:
        plan = floor(seed, (w, h), **{
            "rooms": [rooms, rooms],
            "groups": {"per_floor": [2, 2], "minions": [2, 3], "leash": 11},
        })
        members = [spawn for spawn in _spawns(plan) if "group" in spawn]
        assert members, f"{seed}: the floor carried no group to put a leash on"
        assert len(_groups(plan)) == 2, f"{seed}: the floor carried one group, not two"
        for spawn in members:
            assert spawn.get("leash") == 11, (
                f"{seed}: {spawn['id']} of group {spawn['group']} carries "
                f"leash {spawn.get('leash')!r}, and the Section wrote 11"
            )


@pytest.mark.parametrize("w, h, rooms", SIZES)
def test_a_section_that_names_no_leash_writes_none(w, h, rooms):
    """The other half of the same clause, and the reason the key rides
    along only when the Section named one: a pack that writes no leash
    gets the player's own default, and baking the default onto every
    spawn would change the exact bytes a pack that never asked for a
    leash has always baked.

    A leash outside the closed range ADR 0014 writes is treated the same
    way - `vefr.shapes` refuses one at validation, and a generator handed
    one anyway has no number to carry.
    """
    for leash in (None, 2, 13, 6.5, True, "6"):
        for seed in SEEDS:
            groups = {"per_floor": [1, 1], "minions": [2, 3]}
            if leash is not None:
                groups["leash"] = leash
            plan = floor(seed, (w, h), **{"rooms": [rooms, rooms], "groups": groups})
            for spawn in _spawns(plan):
                assert "leash" not in spawn, (
                    f"{seed}: a Section whose leash is {leash!r} put "
                    f"{spawn.get('leash')!r} on {spawn['id']}"
                )


@pytest.mark.parametrize("w, h, rooms", SIZES)
def test_every_number_in_a_spawn_is_a_whole_number(w, h, rooms):
    """`at` is a pair of whole-number tile indices, and no `True` posing as a 1.

    `type(x) is int` is the whole assertion and it is not a
    paraphrase of `isinstance`: `True` is an `int` in Python and would
    sail through the looser spelling, and a float that happens to hold
    a whole value would too. A tile index that arrives as either is a
    number the JSON twin would not round-trip the same way.

    The stats are not checked here because they are not here. ADR 0014
    closes the spawn keys at `id, family, at, elite, group, leader,
    warden`, so a spawn carries no `hp`, `atk` or `xp` to be whole:
    `vefr.mob_stats` is reached by the balance report, and the numbers
    it produces are proved whole there (E10), not here.
    """
    for seed in SEEDS:
        plan = floor(seed, (w, h), **{"rooms": [rooms, rooms]})
        for spawn in _spawns(plan):
            assert type(spawn["at"][0]) is int and type(spawn["at"][1]) is int
            for value in spawn["at"]:
                assert type(value) is int, (
                    f"{seed}: {spawn['id']} at {spawn['at']} holds a "
                    f"{type(value).__name__}, and `at` is a pair of tile indices"
                )


# ------------------------------------------------------- the stream contract


def test_the_elite_and_group_tables_never_move_a_wall():
    """PLAN.md section 2's sub-seed rule, at unit level.

    The affix table, the group table and the family weights are
    rewritten and the floor is drawn again. `rows`, `rooms`, `anchors`
    and `secrets` have to come out identical; `spawns` SHOULD change,
    which is the whole reason the streams are apart. The frozen sweep
    proves this over 3200 floors; this one proves the spawn tables are
    read on the pop stream and nowhere else, and it says so out loud when
    it fails.
    """
    for w, h, rooms in SIZES:
        for seed in SEEDS[:4]:
            base = floor(seed, (w, h), **{"rooms": [rooms, rooms]})
            mutated = floor(seed, (w, h), **{
                "rooms": [rooms, rooms],
                "elites": {"per_floor": [2, 2], "affixes": ["quick", "big", "big"]},
                "groups": {"per_floor": [3, 3], "minions": [3, 3],
                           "same_family": True, "leader": "elite"},
                "families": [
                    {"family": "beetle", "weight": 9, "hp": 12, "atk": 4, "xp": 6},
                    {"family": "rat", "weight": 1, "hp": 8, "atk": 3, "xp": 4},
                ],
                "affixes": [{"id": "quick", "label": "Quick {name}", "atk": 1.4}],
            })
            where = f"{seed} {w}x{h}"
            assert mutated["rows"] == base["rows"], f"{where}: a table moved a wall"
            assert mutated["rooms"] == base["rooms"], f"{where}: a table moved a room"
            assert mutated["anchors"] == base["anchors"], f"{where}: a table moved an anchor"
            assert mutated["secrets"] == base["secrets"], f"{where}: a table moved a secret"
            assert mutated["spawns"] != base["spawns"], (
                f"{where}: rewriting the tables changed nothing on the pop stream, "
                "so they are probably not being read at all"
            )


@pytest.mark.parametrize("w, h, rooms", SIZES)
def test_the_same_key_twice_is_the_same_floor(w, h, rooms):
    """`delve.prng` is the only source of randomness, so it holds here too."""
    for seed in SEEDS[:3]:
        first = floor(seed, (w, h), **{"rooms": [rooms, rooms]})
        second = floor(seed, (w, h), **{"rooms": [rooms, rooms]})
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True), (
            f"{seed} {w}x{h}: two draws of one floor key differ"
        )
