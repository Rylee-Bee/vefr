"""The pop-stage cap sweep: ADR 0014's "Hard caps", as properties.

A SIBLING of `tests/test_floor_v3_properties.py`, not a replacement. That file
owns the floor GEOMETRY - one component, up to down, loops, the fun-at-scale
numbers, plan-stage determinism. This file owns the POP: the monsters, elites
and groups the pop stage draws, and nothing else. The caps under test are the
"Hard caps" list of `docs/adr/0014-elites-and-groups.md`:

- 36 monsters, plus the warden;
- 2 lone elites;
- 3 groups;
- 4 members per group;
- 1 elite-led group per 8 rooms, and at least 1 when the Section's
  `per_floor` low bound asks for one;
- every spawn at least `STAIR_CLEAR` (7) tiles from both stairs, and a
  leader never in a vault, a hall or a secret room;
- a minion within Chebyshev 2 of its leader.

Like the model file, this one re-derives what it needs from the FloorPlan
ALONE: the plan carries no graph and no room roles beyond the shape word, so
the room of a named tile, the rooms that are secret and the walkable set are
all read back off `rows`, `rooms`, `secrets` and `anchors` here. A cap that
cannot be checked from those four keys is a cap the FloorPlan does not
promise, and the one place that bites (a leader in a corridor that only
serves a hall) is called out in the comment on the leader-placement property.

**Seeds: an explicit list, not `hypothesis`, for the property sweep.**
A seed is a string, and shrinking a string does not lead to a simpler FLOOR -
a four-character seed is no easier to reason about than a twelve-character
one, so a shrunk counterexample teaches nothing that a rerun does not. What a
fixed list buys instead is reproducibility at the moment it matters: the pop
stage is written against this file, so a failure has to be re-runnable by
name (`caps-137`, `128x96`, `infested`) with no hypothesis database in the
way, and the same list of 200 seeds is what ADR 0014's acceptance asks for
("the caps hold over 200 seeds x sizes, including 128x96"). So the sweep is
`SEED_COUNT * 4 sizes * 4 kinds = 3200` floors per pack, and every floor is
generated exactly once for the session and cached.

`hypothesis` is used where it does earn its place: the drawn-pack test at the
end, which draws the whole accepted `elites` / `groups` space rather than the
three packs the list uses, so "the caps hold" becomes a statement about every
pack the validator takes and not only about the packs written down here.

**Omens.** There is no omen mechanism in the tree yet - that is E10, and
nothing here invents one. The stand-in for "with omens on" is the STRICTEST
pack the validator accepts: `elites.per_floor`, `groups.per_floor` and
`groups.minions` all at the top the ADR allows (2, 3 and 3), with the group
leaders elite, which is the shape an omen that adds groups or promotes a
leader would push the caps towards. Two strictness settings are swept: a full
range at the cap (`[0, 2]`, `[0, 3]`, `[1, 3]`), which samples the whole legal
range, and a worst case pinned at the cap (`[2, 2]`, `[3, 3]`, `[3, 3]`),
where every floor is the most crowded floor the pack can ask for. If the caps
survive both, they survive any omen E10 can layer on top that only asks for
more.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import json

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vefr import delve_v3
from vefr import shapes


# The four sizes of PLAN.md section 3, each with its room quota, and the four
# floor kinds. The same lists `test_floor_v3_properties.py` sweeps, so a floor
# key that fails in one file can be replayed in the other.
SIZES = [  # (w, h, rooms)
    (48, 32, 16), (64, 48, 18), (96, 64, 24), (128, 96, 32),
]
FLOOR_KINDS = ["normal", "treasure", "infested", "hub"]
SEED_COUNT = 200
SEEDS = [f"caps-{i}" for i in range(SEED_COUNT)]

# Determinism is a property of the floor key, and the sweep already covers the
# key space with 200 seeds, so a subset proves the same thing: 25 seeds x 4
# sizes x 4 kinds is 400 independent pairs. The model file argues the same way
# for the plan stage.
DET_SEEDS = SEEDS[:25]

# The caps, as the numbers ADR 0014 writes them. Named here rather than read
# off the generator, so a generator that lowers a constant cannot quietly
# lower the bar with it.
POP_CAP = 36  # monsters, the warden aside
LONE_ELITE_CAP = 2
GROUP_CAP = 3
MEMBER_CAP = 4
ROOMS_PER_ELITE_GROUP = 8

# The pop stage's own spacing rule, read off the generator so the sweep and
# the stage cannot disagree about which number is 7.
STAIR_CLEAR = delve_v3.STAIR_CLEAR
# ADR 0014: "Minions stand within Chebyshev 2 of the leader."
LEADER_REACH = 2

# Every key a FloorPlan spawn may carry, closed by ADR 0014. A spawn that
# grows an eighth key is a shape change, not a detail.
SPAWN_KEYS = frozenset({"id", "family", "at", "elite", "group", "leader", "warden"})

WALKABLE = frozenset(".ud")

# The counters the closing report quotes.
STATS: dict[str, int] = {"floors": 0, "v2": 0, "leaders_in_rooms": 0}


# ------------------------------------------------------------- the packs
# Affix records, valid by `shapes.check_section`: a whole number of hundredths
# for the multipliers, `{name}` in the label, and only the keys the affix shape
# closes over.
AFFIXES = [
    {"id": "broad", "label": "Broad {name}", "hp": 1.5, "atk": 1.0, "xp": 1.5,
     "scale": 1.3, "extra_drops": 1},
    {"id": "quick", "label": "Quick {name}", "hp": 1.0, "atk": 1.25, "xp": 1.0,
     "sight": 1, "scale": 1.1},
    {"id": "gilded", "label": "Gilded {name}", "hp": 1.25, "atk": 1.0, "xp": 1.5,
     "sight": 2, "scale": 1.0, "extra_drops": 2},
]

# The Section packs the sweep runs, as `(label, elites, groups, minions)`. The
# only difference between the strict pack and the worst case is whether each
# range is a range or pinned at the cap, and both are swept: a range at the cap
# samples the whole legal space, while a range pinned at the cap makes every
# floor the most crowded floor the pack can ask for.
PACK_BLOCKS = [
    # The everyday pack: what a Section would really ship. `leader: "elite"`
    # is what makes the "at least one elite-led group" half of the
    # elite-led-group property bite - a pack that asks for elite-led groups
    # and a floor that carries none is a floor that spent nothing.
    ("base", [1, 2], [1, 2], [2, 3]),
    # The strictest pack the validator accepts, over its whole range: 2
    # elites, 3 groups, 3 minions (so 4 members counting the leader).
    ("strict", [0, 2], [0, 3], [1, 3]),
    # The same, pinned at the cap, so every floor is the worst draw.
    ("worst", [2, 2], [3, 3], [3, 3]),
]
PACK_LABELS = [label for label, _, _, _ in PACK_BLOCKS]


def _pack(label: str, rooms: int) -> dict:
    """A valid Section pack for one sweep pack and one size's room quota.

    A distinct `id` per label, so `base-normal` and `strict-normal` are
    different floors from the same seed: the section id is part of the floor
    key, and two packs of one id would collide.
    """
    for name, elites, groups, minions in PACK_BLOCKS:
        if name == label:
            break
    else:  # pragma: no cover - a typo in PACK_BLOCKS, not a floor's fault
        raise KeyError(label)
    return {
        "section": 1,
        "id": f"range-{label}",
        "rooms": [rooms, rooms],
        "families": [
            {"family": "grunt", "weight": 5, "depth": [1, 6]},
            {"family": "flyer", "weight": 3, "depth": [1, 9]},
            {"family": "shell", "weight": 2, "depth": [3, 9]},
        ],
        "elites": {"per_floor": elites, "affixes": [a["id"] for a in AFFIXES]},
        "groups": {
            "per_floor": groups,
            "minions": minions,
            "leader": "elite",
            "same_family": True,
            "wake": "all",
            "leash": 6,
        },
        "loot": {"tier": 1},
        "pois": ["the low arch", "the flooded step", "the barred stair"],
        "warden": "sentry",
        "vault": "strongroom",
    }


@lru_cache(maxsize=None)
def _cached_pack(label: str, rooms: int) -> dict:
    """The pack, built once per (label, rooms) and handed out as a copy."""
    return _pack(label, rooms)


def _pack_for(label: str, rooms: int) -> dict:
    """A private copy of a pack, so a generator that mutates it cannot poison
    the cache."""
    return copy.deepcopy(_cached_pack(label, rooms))


@lru_cache(maxsize=None)
def _floor(label: str, seed: str, w: int, h: int, kind: str, rooms: int) -> dict:
    """One v3 floor, generated once per key and reused by every test."""
    return delve_v3.generate_floor_v3(
        seed, (w, h), _pack_for(label, rooms), kind
    )


# ------------------------------------------------------- reading a plan back
# Everything below reads the FloorPlan alone. The plan carries no graph, so a
# room of a named tile is a rectangle test against `rooms` and a secret room
# is a room whose centre tile the plan lists in `secrets`.


def _walkable_tiles(plan: dict) -> set[tuple[int, int]]:
    """Every tile of the grid the hero can stand on."""
    rows = plan["rows"]
    return {
        (x, y)
        for y in range(plan["h"])
        for x in range(plan["w"])
        if rows[y][x] in WALKABLE
    }


def _flood(plan: dict, start: tuple[int, int]) -> set[tuple[int, int]]:
    """Every walkable tile 4-connected to `start`."""
    rows, w, h = plan["rows"], plan["w"], plan["h"]
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            if rows[ny][nx] in WALKABLE and (nx, ny) not in seen:
                seen.add((nx, ny))
                stack.append((nx, ny))
    return seen


@lru_cache(maxsize=None)
def _reachable(label: str, seed: str, w: int, h: int, kind: str, rooms: int) -> frozenset:
    """The up-component of one floor, cached: the flood is the expensive half
    of the reachability property and one property needs all of them."""
    plan = _floor(label, seed, w, h, kind, rooms)
    return frozenset(_flood(plan, tuple(plan["anchors"]["up"])))


def _cheb(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Chebyshev distance: the number of diagonal steps between two tiles."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _stair_gap(tile: tuple[int, int], plan: dict) -> int:
    """How far `tile` is from the nearer of the two stairs, in Chebyshev steps.

    The pop stage's rule is "at least `STAIR_CLEAR` from BOTH stairs", which is
    the same as "at least `STAIR_CLEAR` from the nearer of the two", so one
    number answers it.
    """
    up = tuple(plan["anchors"]["up"])
    down = tuple(plan["anchors"]["down"])
    return min(_cheb(tile, up), _cheb(tile, down))


def _rooms_containing(plan: dict, tile: tuple[int, int]) -> list[int]:
    """The rooms whose rectangle holds `tile`, in `rooms` order.

    Usually one. Two only if two rectangles overlap, which the layout stage
    does not do, so a caller that gets a list rather than an index handles
    both without assuming.
    """
    return [
        index
        for index, room in enumerate(plan["rooms"])
        if room[0] <= tile[0] < room[0] + room[2]
        and room[1] <= tile[1] < room[1] + room[3]
    ]


def _secret_rooms(plan: dict) -> set[int]:
    """The rooms the plan turned into secret rooms.

    The graph stage writes a secret as the CENTRE tile of the room it turned,
    so the room holding a listed tile is the secret room. A secret tile that
    names no room would contribute nothing here, and a room named twice would
    contribute once; neither can happen on a floor that validated, and
    neither is worth an exception.
    """
    rooms: set[int] = set()
    for tile in plan["secrets"]:
        rooms.update(_rooms_containing(plan, tuple(tile)))
    return rooms


def _groups_of(spawns: list[dict]) -> dict[str, list[dict]]:
    """The spawns of each group id, in draw order; a spawn with no group is
    not a member of anything."""
    groups: dict[str, list[dict]] = {}
    for spawn in spawns:
        gid = spawn.get("group")
        if gid is not None:
            groups.setdefault(gid, []).append(spawn)
    return groups


def _leaders(spawns: list[dict]) -> list[dict]:
    """Every spawn that calls itself a leader.

    A leader is a spawn whose `leader` key is `True`. ADR 0014 closes the key
    to "appears only as `true`", so a spawn carrying `leader: false` is not a
    leader and is not a leader for any purpose here - the key-closure property
    is where that is reported.
    """
    return [spawn for spawn in spawns if spawn.get("leader") is True]


def _leader(members: list[dict]) -> dict | None:
    """The leader among one group's members, or None when it names none.

    A group with members and no leader is a broken group: its members have
    nothing to stand next to and nothing to wake with, so the callers below
    report it rather than skipping the group.
    """
    for spawn in members:
        if spawn.get("leader") is True:
            return spawn
    return None


def _elite_led(groups: dict[str, list[dict]]) -> list[str]:
    """The group ids led by an elite, in id order.

    ADR 0014: "a group with a member whose `leader is True` and whose `elite`
    is non-null". The leader is the member, so a group whose leader carries an
    affix is elite-led.
    """
    led = []
    for gid in sorted(groups):
        leader = _leader(groups[gid])
        if leader is not None and leader.get("elite") is not None:
            led.append(gid)
    return led


def _is_elite(spawn: dict) -> bool:
    """Does this spawn carry an affix?"""
    return spawn.get("elite") is not None


def _is_warden(spawn: dict) -> bool:
    """Is this spawn the warden? ADR 0015 puts the warden outside the budget,
    so it is the one spawn the 36-monster cap does not count."""
    return bool(spawn.get("warden"))


def _monsters(spawns: list[dict]) -> list[dict]:
    """The spawns the 36 cap counts: everything but the warden."""
    return [spawn for spawn in spawns if not _is_warden(spawn)]


def _offending_numbers(value, path: str = "spawn"):
    """Every (path, value) in a spawn that is a number but not an `int`.

    `bool` is a subclass of `int`, so `type(value) is int` is the test: a
    flag is not a number, and a float is not a whole number. A float anywhere
    in a FloorPlan would break the save-deltas rule of PLAN.md section 2, so
    this is worth a property of its own.
    """
    if value is None or isinstance(value, (str, bool)):
        return []
    if isinstance(value, (int, float)):
        return [] if type(value) is int else [(path, value)]
    if isinstance(value, (list, tuple)):
        return [
            found
            for index, item in enumerate(value)
            for found in _offending_numbers(item, f"{path}[{index}]")
        ]
    return []


# --------------------------------------------------------------- the harness


def _where(label: str, seed: str, w: int, h: int, kind: str) -> str:
    """The (pack, seed, size, kind) stamp every failure message carries."""
    return f"pack={label} seed={seed} size={w}x{h} kind={kind}"


def _cases() -> list[tuple[int, int, int, str]]:
    """The 16 (w, h, rooms, kind) cases of the base-pack sweep."""
    return [
        (w, h, rooms, kind)
        for w, h, rooms in SIZES
        for kind in FLOOR_KINDS
    ]


def _all_cases() -> list[tuple[str, int, int, int, str]]:
    """Every pack label over the 16 cases: the strict sweep of the caps."""
    return [
        (label, w, h, rooms, kind)
        for label in PACK_LABELS
        for w, h, rooms in SIZES
        for kind in FLOOR_KINDS
    ]


def _case_ids() -> list[str]:
    """Readable ids for the 16 base-pack cases: `128x96-32-infested`."""
    return [f"{w}x{h}-{rooms}-{kind}" for w, h, rooms, kind in _cases()]


def _all_case_ids() -> list[str]:
    """The same, with the pack label in front."""
    return [
        f"{label}-{w}x{h}-{rooms}-{kind}" for label, w, h, rooms, kind in _all_cases()
    ]


# -------------------------------------------------------------- the caps
# Every property below walks the seed list of its case, generated once and
# cached, and fails with the floor key and the numbers in plain words. A floor
# with `gen != 3` is v2 geometry - the fallback, which carries no monsters at
# all - so every property skips it and the fallback test in the model file
# measures it.


@pytest.mark.parametrize("label, w, h, rooms, kind", _all_cases(),
                         ids=_all_case_ids())
def test_pop_is_at_most_thirty_six_mons(label, w, h, rooms, kind):
    """The 36-monster cap, warden aside: the floor never carries more.

    Swept over every pack, not just the base one, because this is the cap an
    omen would break first: "Crowded" adds a group, and a group is four
    monsters the budget never reserved.
    """
    seen = 0
    for seed in SEEDS:
        plan = _floor(label, seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            continue
        seen += 1
        monsters = _monsters(plan["spawns"])
        wardens = [s for s in plan["spawns"] if _is_warden(s)]
        if len(wardens) > 1:
            pytest.fail(
                f"{_where(label, seed, w, h, kind)}: {len(wardens)} warden spawns, "
                "at most 1 outside the budget"
            )
        if len(monsters) > POP_CAP:
            pytest.fail(
                f"{_where(label, seed, w, h, kind)}: {len(monsters)} monsters, "
                f"{POP_CAP} allowed"
            )
    STATS["floors"] += seen


@pytest.mark.parametrize("w, h, rooms, kind", _cases(), ids=_case_ids())
def test_at_most_two_lone_elites(w, h, rooms, kind):
    """A lone elite - an affix and no group - is at most two per floor."""
    label = "base"
    for seed in SEEDS:
        plan = _floor(label, seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            continue
        lone = [s for s in plan["spawns"] if _is_elite(s) and s.get("group") is None]
        if len(lone) > LONE_ELITE_CAP:
            pytest.fail(
                f"{_where(label, seed, w, h, kind)}: {len(lone)} lone elites "
                f"({', '.join(s['id'] for s in lone)}), {LONE_ELITE_CAP} allowed"
            )


@pytest.mark.parametrize("w, h, rooms, kind", _cases(), ids=_case_ids())
def test_at_most_three_groups(w, h, rooms, kind):
    """No floor carries a fourth group id."""
    label = "base"
    for seed in SEEDS:
        plan = _floor(label, seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            continue
        groups = _groups_of(plan["spawns"])
        if len(groups) > GROUP_CAP:
            pytest.fail(
                f"{_where(label, seed, w, h, kind)}: {len(groups)} groups "
                f"({', '.join(sorted(groups))}), {GROUP_CAP} allowed"
            )


@pytest.mark.parametrize("w, h, rooms, kind", _cases(), ids=_case_ids())
def test_at_most_four_members_per_group(w, h, rooms, kind):
    """A group is at most four members, its leader counted."""
    label = "base"
    for seed in SEEDS:
        plan = _floor(label, seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            continue
        for gid, members in _groups_of(plan["spawns"]).items():
            if len(members) > MEMBER_CAP:
                pytest.fail(
                    f"{_where(label, seed, w, h, kind)}: group {gid} has "
                    f"{len(members)} members "
                    f"({', '.join(m['id'] for m in members)}), {MEMBER_CAP} allowed"
                )


@pytest.mark.parametrize("w, h, rooms, kind", _cases(), ids=_case_ids())
def test_elite_led_groups_scale_with_the_room_count(w, h, rooms, kind):
    """One elite-led group per 8 rooms, and at least one when asked for.

    The cap is `max(1, rooms // 8)`. The floor half of the property is the
    Section's demand: this pack sets `groups.per_floor` low bound to 1 and
    `leader: "elite"`, so a floor that could carry an elite-led group and
    carries none is a floor that dropped a draw the pack paid for. A floor
    "could carry one" when it has a walkable tile at least `STAIR_CLEAR` from
    both stairs - a leader has to stand somewhere, and a floor with no such
    tile has nowhere to put it.
    """
    label = "base"
    pack = _cached_pack(label, rooms)
    asks_for = (
        pack["groups"]["per_floor"][0] >= 1
        and pack["groups"].get("leader") == "elite"
    )
    measured = 0
    for seed in SEEDS:
        plan = _floor(label, seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            continue
        groups = _groups_of(plan["spawns"])
        led = _elite_led(groups)
        room_count = len(plan["rooms"])
        allowed = max(1, room_count // ROOMS_PER_ELITE_GROUP)
        where = _where(label, seed, w, h, kind)
        if len(led) > allowed:
            pytest.fail(
                f"{where}: {len(led)} elite-led groups ({', '.join(led)}) over "
                f"{room_count} rooms, {allowed} allowed"
            )
        if asks_for:
            clear = [
                tile for tile in _walkable_tiles(plan)
                if _stair_gap(tile, plan) >= STAIR_CLEAR
            ]
            if clear:
                measured += 1
                if not led:
                    pytest.fail(
                        f"{where}: the pack asks for a group led by an elite and "
                        f"the floor carries none over {room_count} rooms and "
                        f"{len(clear)} tiles clear of both stairs"
                    )
    # A case that measured nothing said nothing, which is not a pass.
    assert measured or not asks_for, (
        f"pack {label} asks for an elite-led group and no floor of this case "
        "could carry one, so the demand was never measured"
    )


@pytest.mark.parametrize("w, h, rooms, kind", _cases(), ids=_case_ids())
def test_minions_stay_within_two_of_their_leader(w, h, rooms, kind):
    """Every minion is within Chebyshev 2 of its group's leader tile.

    A member whose group names no leader has nothing to be within 2 of, so it
    is reported here as the failure it is rather than skipped.
    """
    label = "base"
    for seed in SEEDS:
        plan = _floor(label, seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            continue
        where = _where(label, seed, w, h, kind)
        for gid, members in _groups_of(plan["spawns"]).items():
            leader = _leader(members)
            if leader is None:
                pytest.fail(
                    f"{where}: group {gid} has {len(members)} members "
                    f"({', '.join(m['id'] for m in members)}) and no leader, so "
                    "no member can be within 2 of one"
                )
            here = tuple(leader["at"])
            for spawn in members:
                if spawn is leader:
                    continue
                away = _cheb(tuple(spawn["at"]), here)
                if away > LEADER_REACH:
                    pytest.fail(
                        f"{where}: minion {spawn['id']} at {spawn['at']} is "
                        f"{away} tiles from its leader {leader['id']} at "
                        f"{here}, {LEADER_REACH} allowed"
                    )


@pytest.mark.parametrize("w, h, rooms, kind", _cases(), ids=_case_ids())
def test_every_spawn_clears_both_stairs_and_stands_on_floor(w, h, rooms, kind):
    """Every spawn is on a walkable tile and at least 7 tiles from both stairs.

    The distance is Chebyshev, the same measure `STAIR_CLEAR` is written in.
    "From both stairs" is checked as "from the nearer of the two", which is
    the same statement and one number.
    """
    label = "base"
    for seed in SEEDS:
        plan = _floor(label, seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            continue
        rows = plan["rows"]
        for spawn in plan["spawns"]:
            tile = tuple(spawn["at"])
            x, y = tile
            if not (0 <= x < plan["w"] and 0 <= y < plan["h"]):
                pytest.fail(
                    f"{_where(label, seed, w, h, kind)}: spawn {spawn['id']} is "
                    f"at {tile}, off the {plan['w']}x{plan['h']} grid"
                )
            if rows[y][x] not in WALKABLE:
                pytest.fail(
                    f"{_where(label, seed, w, h, kind)}: spawn {spawn['id']} at "
                    f"{tile} stands on {rows[y][x]!r}, which is not walkable"
                )
            gap = _stair_gap(tile, plan)
            if gap < STAIR_CLEAR:
                pytest.fail(
                    f"{_where(label, seed, w, h, kind)}: spawn {spawn['id']} at "
                    f"{tile} is {gap} tiles from the nearest stair "
                    f"(up {plan['anchors']['up']}, down {plan['anchors']['down']}), "
                    f"{STAIR_CLEAR} required"
                )


@pytest.mark.parametrize("w, h, rooms, kind", _cases(), ids=_case_ids())
def test_leaders_stay_out_of_halls_vaults_and_secrets(w, h, rooms, kind):
    """A leader is never in a room the plan named a hall or a vault, and never
    in a secret room.

    WHAT IS DERIVABLE, and what is not. `rooms` carries a shape word per room
    and the graph stage names the warden room `"hall"` and the vault room
    `"vault"` in it, so a leader standing inside a room rectangle is checked
    against those two words. `secrets` carries the centre tile of each room
    the floor turned secret, so a secret room is the room holding a listed
    tile, and the check covers every tile of that room, not just its centre.

    THE GAP, stated rather than papered over: a leader standing in a CORRIDOR
    is in no room, so neither rule bites - and the plan carries no corridor
    list, so a corridor that runs only to the warden hall reads as an
    ordinary corridor. The FloorPlan does not promise a leader is out of a
    hall; it promises the leader is not IN one. What is asserted is the whole
    of what the plan can answer, and the reachability property below still
    holds every leader on a tile the hero can walk to.
    """
    label = "base"
    measured = 0
    for seed in SEEDS:
        plan = _floor(label, seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            continue
        secrets = _secret_rooms(plan)
        where = _where(label, seed, w, h, kind)
        for spawn in _leaders(plan["spawns"]):
            tile = tuple(spawn["at"])
            for index in _rooms_containing(plan, tile):
                measured += 1
                shape = plan["rooms"][index][4]
                if shape in ("hall", "vault"):
                    pytest.fail(
                        f"{where}: leader {spawn['id']} at {tile} is in room "
                        f"{index}, which the plan named {shape!r}"
                    )
                if index in secrets:
                    pytest.fail(
                        f"{where}: leader {spawn['id']} at {tile} is in room "
                        f"{index}, which the plan turned into a secret room"
                    )
    STATS["leaders_in_rooms"] += measured


@pytest.mark.parametrize("w, h, rooms, kind", _cases(), ids=_case_ids())
def test_spawn_keys_are_closed_and_the_numbers_are_whole(w, h, rooms, kind):
    """A spawn carries only the seven keys ADR 0014 closes over, `leader` only
    ever as `true`, and every number is an `int` and never a `float`.

    A `leader: false` is a real failure, not a style question: ADR 0014 says
    the key "appears only as `true`", so a false is a key the plan never
    promised. `warden` is a flag, not a number, and is the one key allowed to
    hold a bool.
    """
    label = "base"
    for seed in SEEDS:
        plan = _floor(label, seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            continue
        where = _where(label, seed, w, h, kind)
        for spawn in plan["spawns"]:
            extra = sorted(set(spawn) - SPAWN_KEYS)
            if extra:
                pytest.fail(
                    f"{where}: spawn {spawn['id']} carries the key(s) "
                    f"{extra}, which are not in {sorted(SPAWN_KEYS)}"
                )
            for key in ("id", "family", "at"):
                if key not in spawn:
                    pytest.fail(f"{where}: spawn {spawn['id']} has no {key!r} key")
            if "leader" in spawn and spawn["leader"] is not True:
                pytest.fail(
                    f"{where}: spawn {spawn['id']} carries leader="
                    f"{spawn['leader']!r}, which is only ever true"
                )
            if "warden" in spawn and not isinstance(spawn["warden"], bool):
                pytest.fail(
                    f"{where}: spawn {spawn['id']} carries warden="
                    f"{spawn['warden']!r}, which is a yes or a no"
                )
            for path, value in _offending_numbers(spawn):
                pytest.fail(
                    f"{where}: spawn {spawn['id']} carries {path}={value!r} of "
                    f"type {type(value).__name__}, which is not a whole int"
                )


@pytest.mark.parametrize("w, h, rooms, kind", _cases(), ids=_case_ids())
def test_spawn_ids_are_unique_and_gapless(w, h, rooms, kind):
    """Monster ids are `m0, m1, ...` in draw order with no gap and no repeat,
    and group ids are `g0, g1, ...` the same way.

    Gapless matters because a killed id is what the save keeps: an id that
    skipped a number would make a floor's slain list ambiguous to read back.
    """
    label = "base"
    for seed in SEEDS:
        plan = _floor(label, seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            continue
        where = _where(label, seed, w, h, kind)
        ids = [spawn["id"] for spawn in plan["spawns"]]
        if len(set(ids)) != len(ids):
            repeated = sorted({i for i in ids if ids.count(i) > 1})
            pytest.fail(f"{where}: ids repeat: {repeated}")
        if ids != [f"m{i}" for i in range(len(ids))]:
            pytest.fail(
                f"{where}: the ids are {ids[:8]}{'...' if len(ids) > 8 else ''}, "
                f"not m0..m{len(ids) - 1} in draw order"
            )
        gids = [gid for gid in _groups_of(plan["spawns"])]
        want = [f"g{i}" for i in range(len(gids))]
        if sorted(gids) != want:
            pytest.fail(
                f"{where}: the group ids are {sorted(gids)}, not {want}"
            )


@pytest.mark.parametrize("w, h, rooms, kind", _cases(), ids=_case_ids())
def test_the_whole_pop_is_reachable_from_up(w, h, rooms, kind):
    """Every spawn - plain, elite, group leader and minion alike - is in the
    up-component.

    The model file proves this for its own packs; it is repeated here because
    the caps are what put a minion near a leader and an elite off the stairs,
    and a cap change that sealed a room off would show here and nowhere else.
    """
    label = "base"
    for seed in SEEDS:
        plan = _floor(label, seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            continue
        reach = _reachable(label, seed, w, h, kind, rooms)
        for spawn in plan["spawns"]:
            if tuple(spawn["at"]) not in reach:
                pytest.fail(
                    f"{_where(label, seed, w, h, kind)}: spawn {spawn['id']} at "
                    f"{spawn['at']} is not reachable from the up-stair at "
                    f"{plan['anchors']['up']}"
                )


# -------------------------------------------- the packs themselves, and E10


@pytest.mark.parametrize("label", PACK_LABELS)
def test_the_sweep_packs_are_ones_the_validator_accepts(label):
    """Every pack this file sweeps passes `shapes.check_section`.

    It has to: the strictest-pack property below claims to prove the caps for
    the strictest pack the ACCEPTED, and a pack the validator refuses proves
    nothing. The affix list is handed over too, so the affix ids the elites
    name are defined rather than merely well shaped.
    """
    rooms = SIZES[-1][2]
    pack = _pack_for(label, rooms)
    problems = shapes.check_section(pack, affixes=[dict(a) for a in AFFIXES])
    assert problems == [], [p.sentence for p in problems]
    # And the claim the docstring makes about "the maximum the ADR allows".
    if label in ("strict", "worst"):
        assert pack["elites"]["per_floor"][1] <= 2
        assert pack["groups"]["per_floor"][1] <= 3
        assert pack["groups"]["minions"][1] <= 3


@pytest.mark.parametrize("label", ["strict", "worst"])
def test_the_strictest_packs_are_the_omens_stand_in(label):
    """The strictest pack asks for the most the ADR allows, and is at the cap.

    This is the omen-free stand-in, and it is only a stand-in if it really is
    the worst pack: `elites.per_floor` and `groups.per_floor` top out at the
    hard caps, `minions` tops out at 3 (so four members counting the leader),
    and the group leaders are elite, which is the shape an omen that promotes
    a leader would push towards. Real omens are E10; nothing here models one.
    """
    pack = _cached_pack(label, SIZES[0][2])
    assert pack["elites"]["per_floor"][1] == 2, "the ADR caps lone elites at 2"
    assert pack["groups"]["per_floor"][1] == 3, "the ADR caps groups at 3"
    assert pack["groups"]["minions"][1] == 3, "the ADR caps a group at 4 members"
    assert pack["groups"]["leader"] == "elite"
    if label == "worst":
        assert pack["elites"]["per_floor"] == [2, 2]
        assert pack["groups"]["per_floor"] == [3, 3]
        assert pack["groups"]["minions"] == [3, 3]


def test_determinism_same_seed_twice():
    """The same pack, seed, size and kind give a byte-identical canonical plan.

    A subset of the sweep, and one that is not a subset of the cases: the
    floor key is what determinism is a property of, so 25 seeds x 4 sizes x 4
    kinds over the base pack is 400 independent pairs. The canonical form is
    the same `json.dumps(..., sort_keys=True)` the model file compares, so a
    plan that differs only in key order still counts as equal.
    """
    for w, h, rooms in SIZES:
        for kind in FLOOR_KINDS:
            for seed in DET_SEEDS:
                first = delve_v3.generate_floor_v3(
                    seed, (w, h), _pack_for("base", rooms), kind
                )
                second = delve_v3.generate_floor_v3(
                    seed, (w, h), _pack_for("base", rooms), kind
                )
                a = json.dumps(first, sort_keys=True)
                b = json.dumps(second, sort_keys=True)
                if a != b:
                    pytest.fail(
                        f"{_where('base', seed, w, h, kind)}: two draws of one "
                        "floor key differ"
                    )


# The strategies, built once: a `[lo, hi]` pair each, drawn inside the bounds
# `shapes` accepts and sorted, so the pack the sweep builds is one the
# validator takes. The bounds are the shape's, not the ADR's prose: elites 0-2,
# groups 0-3, minions 1-3.
def _pair(lo: int, hi: int):
    return st.lists(st.integers(min_value=lo, max_value=hi), min_size=2,
                    max_size=2).map(sorted)


PACK_BLOCK_STRATEGY = st.fixed_dictionaries({
    "elites": _pair(0, 2),
    "groups": _pair(0, 3),
    "minions": _pair(1, 3),
    "same_family": st.booleans(),
})
SEED_STRATEGY = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
                        min_size=1, max_size=10)


@pytest.mark.parametrize("w, h, rooms", SIZES, ids=[f"{w}x{h}-{r}" for w, h, r in SIZES])
@settings(max_examples=40, deadline=None, derandomize=True,
          suppress_health_check=[HealthCheck.too_slow])
@given(blocks=PACK_BLOCK_STRATEGY, kind=st.sampled_from(FLOOR_KINDS),
       seed=SEED_STRATEGY)
def test_caps_hold_for_any_pack_the_validator_accepts(w, h, rooms, blocks, kind, seed):
    """The caps hold over the whole accepted pack space, drawn by hypothesis.

    The seed list proves the caps for three packs; this proves them for every
    pack the validator takes, which is the stronger statement and the one any
    omen has to live inside. `hypothesis` draws the three blocks, the floor
    kind and the seed, `derandomize` keeps the run reproducible, and every
    cap is checked with the same numbers the sweep above uses.

    The pack is a deep copy with the drawn blocks written into it, and its id
    carries the blocks so two packs never share a floor key.
    """
    pack = _pack_for("base", rooms)
    pack["elites"]["per_floor"] = blocks["elites"]
    pack["groups"]["per_floor"] = blocks["groups"]
    pack["groups"]["minions"] = blocks["minions"]
    pack["groups"]["same_family"] = blocks["same_family"]
    pack["id"] = (
        f"range-drawn-{blocks['elites']}-{blocks['groups']}"
        f"-{blocks['minions']}-{blocks['same_family']}"
    )
    problems = shapes.check_section(pack, affixes=[dict(a) for a in AFFIXES])
    assert problems == [], [p.sentence for p in problems]
    plan = delve_v3.generate_floor_v3(seed, (w, h), pack, kind)
    if plan["gen"] != 3:
        STATS["v2"] += 1
        return
    where = _where("drawn", seed, w, h, kind)
    spawns = plan["spawns"]
    groups_of = _groups_of(spawns)
    led = _elite_led(groups_of)
    allowed = max(1, len(plan["rooms"]) // ROOMS_PER_ELITE_GROUP)
    lone = [s for s in spawns if _is_elite(s) and s.get("group") is None]
    assert len(_monsters(spawns)) <= POP_CAP, (
        f"{where}: {len(_monsters(spawns))} monsters, {POP_CAP} allowed"
    )
    assert len(lone) <= LONE_ELITE_CAP, f"{where}: {len(lone)} lone elites"
    assert len(groups_of) <= GROUP_CAP, f"{where}: {len(groups_of)} groups"
    for gid, members in groups_of.items():
        assert len(members) <= MEMBER_CAP, (
            f"{where}: group {gid} has {len(members)} members, {MEMBER_CAP} allowed"
        )
        leader = _leader(members)
        assert leader is not None, f"{where}: group {gid} names no leader"
        for spawn in members:
            if spawn is not leader:
                away = _cheb(tuple(spawn["at"]), tuple(leader["at"]))
                assert away <= LEADER_REACH, (
                    f"{where}: minion {spawn['id']} is {away} tiles from its "
                    f"leader, {LEADER_REACH} allowed"
                )
    assert len(led) <= allowed, (
        f"{where}: {len(led)} elite-led groups over {len(plan['rooms'])} rooms, "
        f"{allowed} allowed"
    )
    for spawn in spawns:
        gap = _stair_gap(tuple(spawn["at"]), plan)
        assert gap >= STAIR_CLEAR, (
            f"{where}: spawn {spawn['id']} at {spawn['at']} is {gap} tiles from "
            f"the nearest stair, {STAIR_CLEAR} required"
        )
    STATS["floors"] += 1


def test_sweep_counters():
    """The counts the closing report quotes, printed from the finished sweep."""
    total = 0
    v2 = 0
    for label in PACK_LABELS:
        for w, h, rooms in SIZES:
            for kind in FLOOR_KINDS:
                for seed in SEEDS:
                    total += 1
                    if _floor(label, seed, w, h, kind, rooms)["gen"] != 3:
                        v2 += 1
    print(
        f"\ncaps: {total} floors over {len(PACK_LABELS)} packs and "
        f"{SEED_COUNT} seeds, {total - v2} v3, {v2} v2, "
        f"{STATS['floors']} floors measured by a property, "
        f"{STATS['v2']} v2 floors in the drawn-pack sweep"
    )
    assert total == SEED_COUNT * len(PACK_LABELS) * len(SIZES) * len(FLOOR_KINDS)
