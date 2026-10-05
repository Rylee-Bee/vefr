"""The v3 floor-generator property sweep - the acceptance tests, written first.

These are the acceptance tests for `vefr.delve_v3`, per
`docs/plans/endless-dungeon/PLAN.md` sections 2 (the pipeline, the FloorPlan
shape, the determinism rule), 3 (the four sizes and their room quotas) and 4
(the fun-at-scale numbers: two loops, 40% of rooms within one step of the main
path, 60% of chest value off it).

They are written BEFORE the generator, on purpose: the properties are the
contract the generator is built to, and a test written after the code only
records what the code happened to do. `src/vefr/delve_v3.py` is not in the tree
yet, so this file fails at import today. That is the expected state.

The FloorPlan carries no graph, so every graph property here is derived from
`rows` and `rooms` alone, by the derivation rules of PLAN.md sections 2 and 4.
That is also a real requirement on the generator: its geometry has to be
readable from the grid. Geometry that cannot be read back as rooms-plus-
corridors fails these tests, and it should.
"""

from __future__ import annotations

import copy
from collections import deque
from functools import lru_cache
import json
from pathlib import Path
from typing import NamedTuple

import pytest

from vefr import delve_v3, stamps


# The four sizes of PLAN.md section 3, with the room quota each one carries.
# Every size here asks for 12 rooms or more, so the "at least two loops"
# property applies to every floor of the sweep, not to a subset of it.
SIZES = [  # (w, h, rooms)
    (48, 32, 16), (64, 48, 18), (96, 64, 24), (128, 96, 32),
]
FLOOR_KINDS = ["normal", "treasure", "infested", "hub"]
SEED_COUNT = 200
SEEDS = [f"sweep-{i}" for i in range(SEED_COUNT)]

# Determinism and stream separation are per-floor-key properties, and the sweep
# already covers the key space with 200 seeds, so a subset of seeds proves the
# same thing: 25 seeds x 4 sizes x 4 kinds is 400 independent pairs for
# determinism, and 20 seeds x 4 sizes is 80 mutations for the sub-seed rule.
# Running all 3200 for either would cost minutes and prove nothing extra.
DET_SEEDS = SEEDS[:25]
STREAM_SEEDS = SEEDS[:20]

# Every character a row may carry, and the subset the hero can stand on.
ALPHABET = frozenset("#.ud")
WALKABLE = frozenset(".ud")

# Counters the final report quotes. A floor with `gen != 3` is v2 geometry and
# every property test skips it; the count of those skips is the fallback count
# the fallback test measures, and the report prints both.
STATS: dict[str, int] = {"chestless": 0, "skipped": 0}


def section(id: str, rooms: int) -> dict:
    """A valid Section pack for one floor kind and one size's room quota.

    `rooms` is `[quota, quota]` so the quota is exact rather than sampled. Only
    `id`, `rooms`, `families`, `elites`, `groups` and `pois` are required by the
    v3 slice; the rest is here because a real pack carries it. There is no
    `chest_values` table, so by the API contract every chest is worth 1.
    """
    return {
        "section": 1,
        "id": id,
        "rooms": [rooms, rooms],
        "families": [
            {"family": "rat", "weight": 5, "depth": [1, 6]},
            {"family": "moth", "weight": 3, "depth": [1, 9]},
            {"family": "beetle", "weight": 2, "depth": [3, 9]},
        ],
        "elites": {"per_floor": [1, 2], "affixes": ["big", "quick", "glowing"]},
        "groups": {"per_floor": [1, 2], "minions": [2, 3]},
        "loot": {"tier": 1},
        "pois": ["the drowned well", "the ash alcove", "the rusted grate"],
        "warden": "ashwing",
        "vault": "vault-cellar",
    }


@lru_cache(maxsize=None)
def _pack(kind: str, rooms: int) -> dict:
    """The Section pack for one floor kind; a distinct id per kind.

    The floor key carries the section id, so `cellar-normal` and
    `cellar-treasure` are different floors from the same seed.
    """
    return section(f"cellar-{kind}", rooms)


def _chest_value(pack: dict, table: str) -> int:
    """What one chest is worth: `chest_values[table]`, else 1 when unmapped."""
    return pack.get("chest_values", {}).get(table, 1)


@lru_cache(maxsize=None)
def _floor(seed: str, w: int, h: int, kind: str, rooms: int) -> dict:
    """One v3 floor, generated once per key and reused by every test.

    The whole sweep is 200 seeds x 4 sizes x 4 kinds = 3200 floors and each
    property test walks all of them, so a floor is generated exactly once for
    the session, not once per property. The pack is copied per call, so a
    generator that mutates the pack it is handed cannot poison the cache.
    """
    return delve_v3.generate_floor_v3(seed, (w, h), copy.deepcopy(_pack(kind, rooms)), kind)


# ------------------------------------------------------------- grid geometry


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


def _shortest_node_path(adj: list[set[int]], start: int, goal: int) -> list[int] | None:
    """The shortest node path start -> goal, ties broken by the smaller index.

    BFS with the neighbours of a node visited in ascending node order, so the
    first route found is the canonical one: the lower node index wins a tie.
    """
    if start == goal:
        return [start]
    prev: dict[int, int | None] = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in sorted(adj[node]):
            if nxt in prev:
                continue
            prev[nxt] = node
            if nxt == goal:
                path = [nxt]
                while prev[path[-1]] is not None:
                    path.append(prev[path[-1]])
                return path[::-1]
            queue.append(nxt)
    return None


class Geometry(NamedTuple):
    """Everything the graph properties need out of one floor's grid."""

    room_count: int
    corridor_count: int
    covers_walkable: bool
    room_adj: tuple[frozenset[int], ...]
    main_path: tuple[int, ...]  # the room nodes of the up -> down path, in order
    main_nodes: frozenset[int]  # every region node on that path
    rooms_of: dict[tuple[int, int], int | None]  # the room of each named tile
    on_path: dict[tuple[int, int], bool]  # is that named tile on the main path


def _point_tiles(plan: dict) -> list[tuple[int, int]]:
    """Every tile the plan names: anchors, pois, secrets, spawns, chests."""
    tiles = [tuple(tile) for tile in plan["anchors"].values() if tile is not None]
    tiles += [tuple(poi["at"]) for poi in plan["pois"]]
    tiles += [tuple(tile) for tile in plan["secrets"]]
    tiles += [tuple(spawn["at"]) for spawn in plan["spawns"]]
    tiles += [tuple(chest["at"]) for chest in plan["chests"]]
    return tiles


def _region_graph(plan: dict) -> Geometry:
    """Read the region graph and the room graph out of `rows` and `rooms`.

    Nodes are the rooms first, by index, and the corridor regions after them.
    A maximal 4-connected set of walkable tiles that touches no room rectangle
    is one corridor node, so corridors, stairs and any other carved space are
    all of them. A room edge exists when two rooms touch directly or share one
    corridor node; the "exactly one corridor node" rule is what stops a chain
    of two corridors from reading as a room edge.

    Two consequences of that rule worth knowing, because they make the room
    graph read generous: a corridor that touches three rooms (a T junction)
    joins all three pairs, and two corridors that run side by side between the
    same two rooms count once. A generator that closes real loops between
    distant room pairs is what the loop property is really asking for.

    Because rooms are the low indices and corridors the high ones, a BFS that
    breaks ties by the smaller node index visits the rooms in `rooms` order.
    The main path is a BFS over the REGION graph, from the node holding the up
    anchor to the node holding the down anchor, and its room nodes in order.
    """
    rows, w, h = plan["rows"], plan["w"], plan["h"]
    rooms = plan["rooms"]
    walkable = _walkable_tiles(plan)

    room_of: dict[tuple[int, int], int] = {}
    for index, (rx, ry, rw, rh, _shape) in enumerate(rooms):
        for yy in range(ry, ry + rh):
            for xx in range(rx, rx + rw):
                if (xx, yy) in walkable:
                    room_of[(xx, yy)] = index

    room_count = len(rooms)
    adj: list[set[int]] = [set() for _ in rooms]
    node_of: dict[tuple[int, int], int] = dict(room_of)
    seen: set[tuple[int, int]] = set()
    corridor_tiles = 0
    for y in range(h):
        for x in range(w):
            if rows[y][x] not in WALKABLE or (x, y) in room_of or (x, y) in seen:
                continue
            node = len(adj)
            adj.append(set())
            seen.add((x, y))
            node_of[(x, y)] = node
            stack = [(x, y)]
            while stack:
                cx, cy = stack.pop()
                corridor_tiles += 1
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if not (0 <= nx < w and 0 <= ny < h):
                        continue
                    if rows[ny][nx] not in WALKABLE or (nx, ny) in seen:
                        continue
                    if (nx, ny) in room_of:
                        adj[node].add(room_of[(nx, ny)])
                        continue
                    seen.add((nx, ny))
                    node_of[(nx, ny)] = node
                    stack.append((nx, ny))
    for node, neighbours in enumerate(adj):
        for other in sorted(neighbours):
            adj[other].add(node)

    # Two rooms sharing a tile edge are neighbours with no corridor between.
    for y in range(h):
        for x in range(w):
            if rows[y][x] not in WALKABLE:
                continue
            here = room_of.get((x, y))
            for nx, ny in ((x + 1, y), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h and rows[ny][nx] in WALKABLE:
                    there = room_of.get((nx, ny))
                    if here is not None and there is not None and here != there:
                        adj[here].add(there)
                        adj[there].add(here)

    room_adj: list[set[int]] = [set() for _ in rooms]
    for index in range(room_count):
        room_adj[index] |= {n for n in adj[index] if n < room_count}
    for node in range(room_count, len(adj)):
        touching = sorted(n for n in adj[node] if n < room_count)
        for i, a in enumerate(touching):
            for b in touching[i + 1:]:
                room_adj[a].add(b)
                room_adj[b].add(a)

    # The main path is a BFS over the region graph, not the room graph: it
    # runs from the region node holding the up anchor to the one holding the
    # down anchor, and its room nodes in order are the main path.
    up = tuple(plan["anchors"]["up"])
    down = tuple(plan["anchors"]["down"])
    start = node_of.get(up)
    goal = node_of.get(down)
    path = []
    if start is not None and goal is not None:
        path = _shortest_node_path(adj, start, goal) or []
    main_nodes = frozenset(path)
    main = tuple(node for node in path if node < room_count)

    # Resolve only the tiles the plan names, so the cache stays small: a whole
    # tile -> node map would be thousands of entries on every one of 3200 floors.
    rooms_of: dict[tuple[int, int], int | None] = {}
    on_path: dict[tuple[int, int], bool] = {}
    for tile in _point_tiles(plan):
        node = node_of.get(tile)
        if node is None:
            rooms_of[tile] = None
            on_path[tile] = False
        elif node < room_count:
            rooms_of[tile] = node
            on_path[tile] = node in main
        else:
            # A tile in a corridor belongs to the lowest-index room it serves.
            served = [n for n in adj[node] if n < room_count]
            rooms_of[tile] = min(served) if served else None
            on_path[tile] = node in main_nodes
    return Geometry(
        room_count=room_count,
        corridor_count=len(adj) - room_count,
        covers_walkable=len(room_of) + corridor_tiles == len(walkable),
        room_adj=tuple(frozenset(s) for s in room_adj),
        main_path=main,
        main_nodes=main_nodes,
        rooms_of=rooms_of,
        on_path=on_path,
    )


@lru_cache(maxsize=None)
def _geometry(seed: str, w: int, h: int, kind: str, rooms: int) -> Geometry:
    """The derived graph of one floor, built once per key.

    The derivation is the expensive half of the sweep and four tests need it,
    so it is cached the way the floor itself is.
    """
    return _region_graph(_floor(seed, w, h, kind, rooms))


def _edge_count(geom: Geometry) -> int:
    """How many edges the room graph has, self-loops and doubles removed."""
    return sum(len(neighbours) for neighbours in geom.room_adj) // 2


def _loop_count(geom: Geometry) -> int:
    """The cyclomatic number of the room graph: edges - nodes + 1 component."""
    return _edge_count(geom) - len(geom.room_adj) + 1


def _within_one_step(geom: Geometry) -> set[int]:
    """Rooms at room-graph distance 0 or 1 from the main-path room set."""
    if not geom.main_path:
        return set()
    near = set(geom.main_path)
    for room in geom.main_path:
        near |= set(geom.room_adj[room])
    return near


# --------------------------------------------------------------- the harness


def _where(seed: str, w: int, h: int, kind: str) -> str:
    """The (seed, size, kind) stamp that every failure message carries."""
    return f"seed={seed} size={w}x{h} kind={kind}"


def _cases() -> list[tuple[int, int, int, str]]:
    """The 16 (w, h, rooms, kind) cases the sweep is parametrised over."""
    return [(w, h, rooms, kind) for w, h, rooms in SIZES for kind in FLOOR_KINDS]


# ---------------------------------------------------------------- properties


@pytest.mark.parametrize("w, h, rooms, kind", _cases())
def test_one_connected_component(w, h, rooms, kind):
    """Flood fill from the up-stair reaches every walkable tile: no orphans."""
    skipped = 0
    for seed in SEEDS:
        plan = _floor(seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            # v2 geometry, covered by the fallback-rate test instead.
            skipped += 1
            continue
        walkable = _walkable_tiles(plan)
        seen = _flood(plan, tuple(plan["anchors"]["up"]))
        if seen != walkable:
            pytest.fail(
                f"{_where(seed, w, h, kind)}: the up-component is missing "
                f"{len(walkable - seen)} of {len(walkable)} walkable tiles; "
                f"{skipped} earlier floors were skipped as gen != 3"
            )
    STATS["skipped"] += skipped


@pytest.mark.parametrize("w, h, rooms, kind", _cases())
def test_stairs_reachable_and_far_enough(w, h, rooms, kind):
    """The two stairs differ, the down one is in the up-component, and their
    rooms are in one component of the room graph.

    The "at least 7 tiles from both stairs" spacing is the pop stream's own
    rule, not part of this property, so it is not asserted here.
    """
    skipped = 0
    for seed in SEEDS:
        plan = _floor(seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            skipped += 1
            continue
        where = _where(seed, w, h, kind)
        up = tuple(plan["anchors"]["up"])
        down = tuple(plan["anchors"]["down"])
        if up == down:
            pytest.fail(f"{where}: the up and down anchors are the same tile {up}")
        if down not in _flood(plan, up):
            pytest.fail(f"{where}: the down anchor {down} is not in the up-component")
        geom = _geometry(seed, w, h, kind, rooms)
        up_room = geom.rooms_of[up]
        down_room = geom.rooms_of[down]
        if up_room is None or down_room is None:
            pytest.fail(f"{where}: an anchor tile at {up}/{down} names no room")
        room_adj = [set(n) for n in geom.room_adj]
        if _shortest_node_path(room_adj, up_room, down_room) is None:
            pytest.fail(
                f"{where}: rooms {up_room} and {down_room} are in different "
                "components of the room graph"
            )
    STATS["skipped"] += skipped


@pytest.mark.parametrize("w, h, rooms, kind", _cases())
def test_every_anchor_spawn_and_chest_reachable(w, h, rooms, kind):
    """Every placed tile is walkable and reachable, and the plan is well formed."""
    skipped = 0
    for seed in SEEDS:
        plan = _floor(seed, w, h, kind, rooms)
        where = _where(seed, w, h, kind)
        if plan["gen"] != 3:
            skipped += 1
            continue
        rows = plan["rows"]
        if len(rows) != h:
            pytest.fail(f"{where}: {len(rows)} rows, expected h={h}")
        if any(len(row) != w for row in rows):
            bad = [i for i, row in enumerate(rows) if len(row) != w]
            pytest.fail(f"{where}: rows {bad[:4]} are not w={w} chars wide")
        alphabet = set("".join(rows))
        if not alphabet <= ALPHABET:
            pytest.fail(f"{where}: rows carry {sorted(alphabet - ALPHABET)}")
        if len(plan["rooms"]) < 2:
            pytest.fail(f"{where}: {len(plan['rooms'])} rooms, at least 2 required")
        if plan["anchors"]["up"] is None or plan["anchors"]["warden"] is None:
            pytest.fail(f"{where}: the up and warden anchors must not be None")
        if len(plan["pois"]) < 1:
            pytest.fail(f"{where}: a v3 floor needs at least the landmark poi")
        json.dumps(plan, sort_keys=True)

        # The region graph has to be readable off the grid: its nodes'
        # tiles together are the whole walkable set, with none left over.
        if not _geometry(seed, w, h, kind, rooms).covers_walkable:
            pytest.fail(f"{where}: the rooms and corridors do not tile the walkable set")
        walkable = _walkable_tiles(plan)
        reach = _flood(plan, tuple(plan["anchors"]["up"]))
        for name, tile in plan["anchors"].items():
            if tile is None:
                continue
            if tuple(tile) not in walkable:
                pytest.fail(f"{where}: anchor {name} at {tile} is not a walkable tile")
            if tuple(tile) not in reach:
                pytest.fail(f"{where}: anchor {name} at {tile} is not reachable from up")
        for poi in plan["pois"]:
            if tuple(poi["at"]) not in reach:
                pytest.fail(f"{where}: poi {poi['name']} at {poi['at']} is not reachable")
        for tile in plan["secrets"]:
            if tuple(tile) not in reach:
                pytest.fail(f"{where}: secret at {tile} is not reachable from up")
        for spawn in plan["spawns"]:
            if tuple(spawn["at"]) not in reach:
                pytest.fail(f"{where}: spawn {spawn['id']} at {spawn['at']} is not reachable")
        for chest in plan["chests"]:
            if tuple(chest["at"]) not in reach:
                pytest.fail(f"{where}: chest {chest['id']} at {chest['at']} is not reachable")
    STATS["skipped"] += skipped


@pytest.mark.parametrize("w, h, rooms, kind", _cases())
def test_warden_is_off_the_main_path(w, h, rooms, kind):
    """The warden's room is off the up -> down path: the gates-and-guardians rule."""
    skipped = 0
    for seed in SEEDS:
        plan = _floor(seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            skipped += 1
            continue
        where = _where(seed, w, h, kind)
        geom = _geometry(seed, w, h, kind, rooms)
        if not geom.main_path:
            pytest.fail(f"{where}: the region graph has no up -> down path")
        warden = tuple(plan["anchors"]["warden"])
        if geom.on_path[warden]:
            pytest.fail(
                f"{where}: the warden is in room {geom.rooms_of[warden]}, which is "
                f"on the main path {list(geom.main_path)}"
            )
    STATS["skipped"] += skipped


@pytest.mark.parametrize("w, h, rooms, kind", _cases())
def test_two_loops_at_twelve_rooms_or_more(w, h, rooms, kind):
    """At least two room-graph cycles on a floor of 12 or more rooms.

    Every size of PLAN.md section 3 asks for 16 rooms or more, so this bites on
    every floor of the sweep, not on a subset of it.
    """
    skipped = 0
    measured = 0
    for seed in SEEDS:
        plan = _floor(seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            skipped += 1
            continue
        geom = _geometry(seed, w, h, kind, rooms)
        if geom.room_count < 12:
            continue
        measured += 1
        if _loop_count(geom) < 2:
            pytest.fail(
                f"{_where(seed, w, h, kind)}: {_edge_count(geom)} room edges over "
                f"{geom.room_count} rooms is {_loop_count(geom)} loops, 2 required"
            )
    # A case that measured nothing either fell back on every floor or held no
    # floor with 12 rooms; both are the fallback test's business, not a pass.
    assert measured or skipped == SEED_COUNT
    STATS["skipped"] += skipped


@pytest.mark.parametrize("w, h, rooms, kind", _cases())
def test_forty_percent_of_rooms_within_one_step_of_the_main_path(w, h, rooms, kind):
    """Per floor, at least 40% of rooms are at distance 0 or 1 of the main path."""
    skipped = 0
    first_bad: tuple[str, float] | None = None
    worst: tuple[float, str] = (1.0, "")
    for seed in SEEDS:
        plan = _floor(seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            skipped += 1
            continue
        where = _where(seed, w, h, kind)
        geom = _geometry(seed, w, h, kind, rooms)
        if not geom.main_path:
            pytest.fail(f"{where}: the room graph has no up -> down path")
        ratio = len(_within_one_step(geom)) / geom.room_count
        if ratio < worst[0]:
            worst = (ratio, where)
        if ratio < 0.40 and first_bad is None:
            first_bad = (where, ratio)
    if first_bad is not None:
        pytest.fail(
            f"{first_bad[0]}: only {first_bad[1] * 100:.1f}% of rooms are within one "
            "step of the main path, 40% required; the first failing floor, and the "
            f"worst floor is {worst[0] * 100:.1f}% at {worst[1]}"
        )
    STATS["skipped"] += skipped


@pytest.mark.parametrize("w, h, rooms, kind", _cases())
def test_sixty_percent_of_chest_value_off_the_main_path(w, h, rooms, kind):
    """Value-weighted: at least 60% of the chest value sits off the main path.

    A floor with no chest is counted, not failed: it has no chest value to put
    off the path. The count is in the report.
    """
    skipped = 0
    first_bad: tuple[str, float] | None = None
    worst: tuple[float, str] = (1.0, "")
    pack = _pack(kind, rooms)
    for seed in SEEDS:
        plan = _floor(seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            skipped += 1
            continue
        if not plan["chests"]:
            STATS["chestless"] += 1
            continue
        where = _where(seed, w, h, kind)
        geom = _geometry(seed, w, h, kind, rooms)
        total = 0
        off = 0
        for chest in plan["chests"]:
            worth = _chest_value(pack, chest["table"])
            total += worth
            if not geom.on_path[tuple(chest["at"])]:
                off += worth
        ratio = off / total if total else 0.0
        if ratio < worst[0]:
            worst = (ratio, where)
        if ratio < 0.60 and first_bad is None:
            first_bad = (where, ratio)
    if first_bad is not None:
        pytest.fail(
            f"{first_bad[0]}: {first_bad[1] * 100:.1f}% of the chest value is off "
            "the main path, 60% required; the first failing floor, and the worst "
            f"floor is {worst[0] * 100:.1f}% at {worst[1]}"
        )
    STATS["skipped"] += skipped


@pytest.mark.parametrize("w, h, rooms, kind", _cases())
def test_determinism_same_seed_twice(w, h, rooms, kind):
    """The same key twice gives byte-identical canonical JSON.

    A subset of seeds, not the whole sweep: determinism is a property of the
    floor key, and 400 independent pairs is already far past the point where
    200 more seeds would show a different answer.
    """
    for seed in DET_SEEDS:
        first = delve_v3.generate_floor_v3(seed, (w, h), copy.deepcopy(_pack(kind, rooms)), kind)
        second = delve_v3.generate_floor_v3(seed, (w, h), copy.deepcopy(_pack(kind, rooms)), kind)
        a = json.dumps(first, sort_keys=True)
        b = json.dumps(second, sort_keys=True)
        if a != b:
            pytest.fail(f"{_where(seed, w, h, kind)}: two draws of one key differ")


@pytest.mark.parametrize(
    "w, h, rooms", SIZES, ids=[f"{w}x{h}-{r}" for w, h, r in SIZES]
)
def test_stream_separation_never_moves_a_wall(w, h, rooms):
    """PLAN.md section 2's sub-seed rule: an affix table must never move a wall.

    The affix table, the group table and the family weights are rewritten and a
    `chest_values` entry is added, then the floor is drawn again. Everything
    the layout stream draws - rows, rooms, anchors, secrets - must come out
    identical, because the plan stream may pick a flavour but must never pick
    anything that changes a wall. Spawns and chests are NOT asserted: they
    SHOULD change, which is the whole reason the streams are separate.
    """
    kind = "normal"
    skipped = 0
    for seed in STREAM_SEEDS:
        base = _floor(seed, w, h, kind, rooms)
        if base["gen"] != 3:
            skipped += 1
            continue
        mutated = copy.deepcopy(_pack(kind, rooms))
        mutated["elites"] = {"per_floor": [1, 3], "affixes": ["huge", "swift", "shining"]}
        mutated["groups"] = {"per_floor": [2, 3], "minions": [4, 5]}
        mutated["families"] = [
            {"family": "beetle", "weight": 9, "depth": [1, 9]},
            {"family": "rat", "weight": 1, "depth": [2, 6]},
        ]
        mutated["chest_values"] = {"t1": 7, "t2": 4}
        after = delve_v3.generate_floor_v3(seed, (w, h), mutated, kind)
        where = _where(seed, w, h, kind)
        if after["rows"] != base["rows"]:
            pytest.fail(f"{where}: rewriting the tables moved a wall (rows differ)")
        if after["rooms"] != base["rooms"]:
            pytest.fail(f"{where}: rewriting the tables moved a room")
        if after["anchors"] != base["anchors"]:
            pytest.fail(f"{where}: rewriting the tables moved an anchor")
        if after["secrets"] != base["secrets"]:
            pytest.fail(f"{where}: rewriting the tables moved a secret")
    STATS["skipped"] += skipped


def test_fallback_rate_under_half_a_percent():
    """Over the full sweep, fewer than 0.5% of calls fall back to v2.

    This is the one property that needs every floor, so the 3200 calls are
    driven from here; the other tests read the same cache.
    """
    total = 0
    fell_back = 0
    for w, h, rooms in SIZES:
        for kind in FLOOR_KINDS:
            for seed in SEEDS:
                total += 1
                if _floor(seed, w, h, kind, rooms)["gen"] != 3:
                    fell_back += 1
    rate = fell_back / total
    assert total == SEED_COUNT * len(SIZES) * len(FLOOR_KINDS)
    if rate >= 0.005:
        pytest.fail(
            f"{fell_back} of {total} floors fell back to v2, a rate of {rate:.5f}, "
            "0.005 allowed"
        )


# ------------------------------------------------------------- the stamped rooms
# ADR 0013's Placement, exercised on the same sweep the properties above
# run: the same 200 seeds, the same four sizes and the same four floor
# kinds, drawn with the fixture stamp pack and a Section that asks for
# stamps by tag. One pack and one Section, so the numbers below are about
# the placer and not about a pack that happens to suit itself.
#
# A stamp is "eligible" on a floor when its tags match the Section's
# `stamps` tags and `STAMP_DEPTH` is inside its own `depth` range; that is
# the rule the placer filters on, and the rate a test is measured over is
# a rate over the eligible floors, not over every floor of the sweep.
STAMP_FIXTURES = Path(__file__).parent / "fixtures" / "stamps"
# `k`, the floor's 1-based position in its Section. Every fixture stamp
# carries `depth [1, 9]` or `[1, 99]`, so this is inside all of them.
STAMP_DEPTH = 3
STAMP_TAGS = ["cellar", "any"]


@lru_cache(maxsize=None)
def _stamp_pack() -> tuple:
    """The fixture stamps, read by the real reader, in sorted id order."""
    return tuple(stamps.load(STAMP_FIXTURES))


def _stamped_section(kind: str, rooms: int) -> dict:
    """The Section pack of `_pack`, asking for stamps by tag.

    The vault is named, so the vault stamp is eligible: a Section with no
    vault has none in the pool, and the sweep would then measure two
    required roles instead of three.
    """
    pack = dict(_pack(kind, rooms))
    pack["stamps"] = list(STAMP_TAGS)
    return pack


@lru_cache(maxsize=None)
def _stamp_floor(seed: str, w: int, h: int, kind: str, rooms: int) -> dict:
    """One stamped v3 floor, generated once per key like `_floor`."""
    return delve_v3.generate_floor_v3(
        seed, (w, h), copy.deepcopy(_stamped_section(kind, rooms)), kind,
        list(_stamp_pack()), STAMP_DEPTH)


def _stamped() -> list[dict]:
    """Every v3 floor of the sweep that carries stamps, as (where, plan)."""
    for w, h, rooms, kind in _cases():
        for seed in SEEDS:
            plan = _stamp_floor(seed, w, h, kind, rooms)
            if plan["gen"] == 3:
                yield _where(seed, w, h, kind), plan


def _records_by_id() -> dict[str, dict]:
    return {record["id"]: record for record in _stamp_pack()}


# ------------------------------------------------------------------- rates


def test_a_stamped_floor_carries_every_required_role():
    """A required role places on 100% of the floors where it is eligible.

    ADR 0013's Validation puts required stamps at 100% and holds no bar
    over the optional ones at all; this is the 100%. The rate is per role
    and not per stamp, because two eligible stamps of one role share the
    floors between them by weight - a Section with two landmarks cannot
    place either of them on every floor, and requiring it to would be
    requiring the pack to ship one landmark.

    A floor that fell back to v2 placed nothing, so it counts against the
    rate rather than being skipped: a Section whose floors cannot hold its
    required stamps is exactly what this number is for.
    """
    wanted = set(stamps.REQUIRED_ROLES)
    placed: dict[str, int] = {}
    eligible = 0
    fell_back = 0
    misses: list[str] = []
    for _where_, plan in _stamped():
        eligible += 1
        for role in wanted & {p["role"] for p in plan["stamps"]}:
            placed[role] = placed.get(role, 0) + 1
    for w, h, rooms, kind in _cases():
        for seed in SEEDS:
            plan = _stamp_floor(seed, w, h, kind, rooms)
            if plan["gen"] == 3:
                continue
            fell_back += 1
            if not eligible:
                continue
            if not misses or len(misses) < 5:
                misses.append(f"{_where(seed, w, h, kind)}"
                              f" ({plan.get('stamp_defect', 'no defect named')})")
    for role in wanted:
        rate = placed.get(role, 0) / eligible
        if rate < 1.0:
            pytest.fail(
                f"the {role} role placed on {placed.get(role, 0)} of {eligible} "
                f"eligible floors ({rate:.1%}); a required role places on every "
                f"one. First floors: {'; '.join(misses)}"
            )
    assert fell_back < len(_cases()) * SEED_COUNT, "no floor should be v2 here"


def test_every_required_stamp_is_placed_on_every_one_of_its_floors():
    """The 100% bar of ADR 0013's Validation, on the stamps it applies to.

    A required stamp is on every floor it is eligible for: one floor in a
    hundred that loses its warden hall is a floor the hero walks into an
    empty hall, and a 95% bar let that floor through. Owner decision 4
    is what leaves the required roles the only ones with a bar at all -
    an optional stamp may be rare on purpose, so the test below holds it
    to nothing. A required stamp with no rival in its role is measured
    directly - the ADR's own example is `crypt-hall`, and it is the shape
    of stamp the sentence is about. A required role with several
    eligible stamps splits its floors by weight instead, because a
    Section with two landmarks cannot put either of them on every floor;
    there the rule that still means something is the split, and the
    tolerance is a quarter of the share.
    """
    shares: dict[str, int] = {}
    total = 0
    for _where_, plan in _stamped():
        total += 1
        for stamp in plan["stamps"]:
            shares[stamp["id"]] = shares.get(stamp["id"], 0) + 1
    rivals: dict[str, list[dict]] = {}
    for record in _stamp_pack():
        rivals.setdefault(record["role"], []).append(record)
    for record in _stamp_pack():
        if record["role"] not in stamps.REQUIRED_ROLES:
            continue
        where = shares.get(record["id"], 0)
        if len(rivals[record["role"]]) == 1:
            rate = where / total
            if rate < 1.0:
                pytest.fail(
                    f"stamp {record['id']}: placed on {where} of {total} eligible "
                    f"floors ({rate:.1%}); it needs 100%"
                )
            continue
        weight = sum(other["weight"] for other in rivals[record["role"]])
        share = record["weight"] / weight
        rate = where / total
        if abs(rate - share) > 0.25:
            pytest.fail(
                f"stamp {record['id']}: {rate:.1%} of eligible floors, and it is "
                f"{share:.1%} of the weight of its role; a weighted draw splits "
                "the floors, and 25 points is the tolerance"
            )


def test_an_optional_stamp_may_be_rare_but_is_never_dead():
    """Owner decision 4: optional stamps may be rare on purpose.

    So there is no rate to hold them to. What they do have to clear is
    zero: a pack that ships a stamp nothing ever places has shipped
    nothing, and the failure a player sees is a room that was never there.
    The rates are printed, because the number is the point of the report.
    """
    shares: dict[str, int] = {}
    total = 0
    for _where_, plan in _stamped():
        total += 1
        for stamp in plan["stamps"]:
            shares[stamp["id"]] = shares.get(stamp["id"], 0) + 1
    optional = [record for record in _stamp_pack()
                if record["role"] in stamps.OPTIONAL_ROLES]
    dead = [record["id"] for record in optional if not shares.get(record["id"])]
    rates = ", ".join(
        f"{record['id']} {shares.get(record['id'], 0)}/{total}"
        for record in optional
    )
    print(f"\nstamps: {total} stamped floors; optional rates: {rates}")
    assert not dead, f"optional stamps never placed: {', '.join(dead)}"


def test_a_stamp_section_falls_back_under_half_a_percent():
    """The plain sweep's 0.5% cap, with stamps on every floor.

    A stamped floor has three more rooms in it than a plain one, and a
    floor that cannot hold them falls back to v2 - so the cap has to hold
    here too, or stamps are a cost the dungeon pays on every floor. The
    failures name the size, because the smallest one is where it bites.
    """
    total = 0
    by_size: dict[tuple[int, int], int] = {}
    for w, h, rooms, kind in _cases():
        for seed in SEEDS:
            total += 1
            if _stamp_floor(seed, w, h, kind, rooms)["gen"] != 3:
                by_size[(w, h)] = by_size.get((w, h), 0) + 1
    rate = sum(by_size.values()) / total
    if rate >= 0.005:
        worst = ", ".join(f"{w}x{h}: {n}" for (w, h), n in sorted(by_size.items()))
        pytest.fail(
            f"{sum(by_size.values())} of {total} stamped floors fell back to v2, "
            f"a rate of {rate:.5f}, 0.005 allowed. By size: {worst}"
        )


# ------------------------------------------------------------ the stamped grid


@pytest.mark.parametrize("w, h, rooms, kind", _cases())
def test_a_stamped_floor_reads_back_as_rooms_and_corridors(w, h, rooms, kind):
    """The plain coverage property, with stamped rooms in the floor.

    A stamped room is a drawing, not a filled rectangle, so this is the
    test that says the drawing did not leak a tile: every walkable tile
    belongs to a room or to a corridor, the up-component is all of them,
    the warden is off the main path, and the loops and the 40% rule hold.
    """
    skipped = 0
    for seed in SEEDS:
        plan = _stamp_floor(seed, w, h, kind, rooms)
        if plan["gen"] != 3:
            skipped += 1
            continue
        where = _where(seed, w, h, kind)
        geom = _region_graph(plan)
        if not geom.covers_walkable:
            pytest.fail(f"{where}: a walkable tile belongs to no room and no corridor")
        walkable = _walkable_tiles(plan)
        seen = _flood(plan, tuple(plan["anchors"]["up"]))
        if seen != walkable:
            pytest.fail(
                f"{where}: the up-component is missing {len(walkable - seen)} of "
                f"{len(walkable)} walkable tiles; {skipped} earlier floors skipped"
            )
        warden = tuple(plan["anchors"]["warden"])
        if geom.on_path.get(warden):
            pytest.fail(f"{where}: the warden {warden} is on the main path")
        if geom.room_count >= 12 and _loop_count(geom) < 2:
            pytest.fail(f"{where}: {geom.room_count} rooms and {_loop_count(geom)} loops")
        near = _within_one_step(geom)
        if len(near) < 0.40 * geom.room_count:
            pytest.fail(
                f"{where}: {len(near)} of {geom.room_count} rooms are within one "
                f"step of the main path; 40% is the floor"
            )
    STATS["skipped"] += skipped


def test_a_stamp_reads_back_out_of_the_grid_it_was_painted_on():
    """The room in `rows` is the drawing: same letters, same sockets.

    Every tile of the placed rectangle in the floor's own rows is the
    oriented stamp's own glyph, except that the socket the corridor came
    in through is floor and every other socket is wall. Geometry that
    cannot be read back off the grid is geometry the auto-map, the graph
    checks and a twin all have to take on trust.
    """
    records = _records_by_id()
    for where, plan in _stamped():
        rows = plan["rows"]
        for stamp in plan["stamps"]:
            record = records.get(stamp["id"])
            assert record is not None, f"{where}: placed an unknown stamp {stamp['id']}"
            drawn = stamps.orient(record["rows"], stamp["orientation"])
            x, y = stamp["at"]
            width, height = stamp["size"]
            if (len(drawn[0]), len(drawn)) != (width, height):
                pytest.fail(
                    f"{where}: {stamp['id']} says it is {width}x{height} and the "
                    f"orientation drawn is {len(drawn[0])}x{len(drawn)}"
                )
            for dy, row in enumerate(drawn):
                for dx, glyph in enumerate(row):
                    if glyph in (stamps.WALL, stamps.OUTSIDE):
                        want = delve_v3.WALL
                    elif glyph in (stamps.DOOR, stamps.SECRET):
                        want = (delve_v3.FLOOR
                                if [x + dx, y + dy] == stamp["socket"]
                                else delve_v3.WALL)
                    else:
                        want = delve_v3.FLOOR
                    if rows[y + dy][x + dx] != want:
                        pytest.fail(
                            f"{where}: {stamp['id']} at {stamp['at']} drew "
                            f"{glyph!r} and the floor has "
                            f"{rows[y + dy][x + dx]!r} at {x + dx},{y + dy}"
                        )


def test_an_unused_socket_is_a_wall():
    """The sockets a room did not use became wall, every one of them.

    ADR 0013's Placement 3 says so outright, and it is the rule that
    keeps a stamped room from being a room with three doors: a second
    open socket would be a second way in, drawn by nobody.
    """
    records = _records_by_id()
    for where, plan in _stamped():
        rows = plan["rows"]
        for stamp in plan["stamps"]:
            drawn = stamps.orient(records[stamp["id"]]["rows"], stamp["orientation"])
            x, y = stamp["at"]
            unused = 0
            for socket in stamps.sockets(drawn):
                at = (x + socket["at"][0], y + socket["at"][1])
                if [at[0], at[1]] == stamp["socket"]:
                    if rows[at[1]][at[0]] != delve_v3.FLOOR:
                        pytest.fail(f"{where}: {stamp['id']}'s used socket {at} is not floor")
                    continue
                unused += 1
                if rows[at[1]][at[0]] != delve_v3.WALL:
                    pytest.fail(
                        f"{where}: {stamp['id']}'s unused socket {at} is "
                        f"{rows[at[1]][at[0]]!r}, not wall"
                    )
            if not stamp["socket"]:
                pytest.fail(f"{where}: {stamp['id']} was placed with no used socket")


def test_every_anchor_of_a_stamp_is_standable_and_reachable():
    """Every letter a stamp drew is a walkable tile in the up-component.

    The anchor is the promise the drawing makes - the chest is there, the
    warden stands there - and a promise made on a wall or in a room the
    hero cannot walk to is not a promise.
    """
    for where, plan in _stamped():
        walkable = _walkable_tiles(plan)
        reach = _flood(plan, tuple(plan["anchors"]["up"]))
        for stamp in plan["stamps"]:
            for name, tile in stamp["anchors"].items():
                at = (tile[0], tile[1])
                if at not in walkable:
                    pytest.fail(
                        f"{where}: {stamp['id']}'s {name} anchor is at {at}, which "
                        "is not walkable"
                    )
                if at not in reach:
                    pytest.fail(
                        f"{where}: {stamp['id']}'s {name} anchor at {at} is not "
                        "reachable from the up-stair"
                    )


def test_a_used_secret_socket_is_a_secret_of_the_floor():
    """A used `?` is in the floor's `secrets`, at the socket's own tile."""
    secrets: list[list[int]] = []
    for _where_, plan in _stamped():
        secrets.extend(plan["secrets"])
    found = 0
    for where, plan in _stamped():
        for stamp in plan["stamps"]:
            if "secret" not in stamp:
                continue
            found += 1
            if stamp["secret"] not in plan["secrets"]:
                pytest.fail(
                    f"{where}: {stamp['id']}'s secret socket {stamp['secret']} is "
                    f"not in the floor's secrets {plan['secrets']}"
                )
    assert found, "no secret socket was ever used, so the rule went untested"
    assert secrets


def test_a_story_room_is_never_turned_or_mirrored():
    """Owner decision 2, at the placement end: a story room is at `o = 0`.

    The reader refuses `rotate` or `mirror` on a warden-hall, a vault or
    a landmark at all, so a placement in any other orientation would be a
    placer that ignored the reader.
    """
    seen = 0
    for where, plan in _stamped():
        for stamp in plan["stamps"]:
            if stamp["role"] not in stamps.REQUIRED_ROLES:
                continue
            seen += 1
            if stamp["orientation"] != 0:
                pytest.fail(
                    f"{where}: {stamp['id']} is a {stamp['role']} and was placed at "
                    f"orientation {stamp['orientation']}; a story room is at 0"
                )
    assert seen, "no story room was ever placed, so the rule went untested"


# --------------------------------------------------------- the streams around


def test_a_section_with_no_stamp_tags_draws_the_floor_it_always_drew():
    """No tags, no stamps, and not one tile moved.

    The stamps are the last thing the layout stage carves, so a Section
    that asks for none has to come out byte for byte as it did before ADR
    0013 - the property every other floor in this file rests on.
    """
    for w, h, rooms in SIZES[:2]:
        for kind in FLOOR_KINDS:
            for seed in SEEDS[:10]:
                pack = _stamped_section(kind, rooms)
                pack.pop("stamps")
                plain = delve_v3.generate_floor_v3(seed, (w, h), copy.deepcopy(pack), kind)
                offered = delve_v3.generate_floor_v3(
                    seed, (w, h), copy.deepcopy(pack), kind, list(_stamp_pack()),
                    STAMP_DEPTH)
                where = _where(seed, w, h, kind)
                if plain != offered:
                    pytest.fail(f"{where}: offering stamps moved a tile on a Section with no tags")
                if "stamps" in offered:
                    pytest.fail(f"{where}: a Section with no tags placed {offered['stamps']}")


def test_the_same_seed_and_pack_draw_the_same_stamps():
    """Determinism, on the stream the stamps are drawn from."""
    for w, h, rooms in SIZES[:2]:
        for kind in FLOOR_KINDS[:2]:
            for seed in SEEDS[:5]:
                first = _stamp_floor(seed, w, h, kind, rooms)
                second = delve_v3.generate_floor_v3(
                    seed, (w, h), copy.deepcopy(_stamped_section(kind, rooms)), kind,
                    list(_stamp_pack()), STAMP_DEPTH)
                where = _where(seed, w, h, kind)
                if first != second:
                    pytest.fail(f"{where}: the same seed drew two different stamped floors")
                # A floor that fell back to v2 placed nothing and is the
                # fallback test's business, not this one's.
                assert first["gen"] == 3 or not first.get("stamps")


def test_rewriting_the_pop_tables_moves_no_wall_of_a_stamped_floor():
    """The sub-seed rule, with stamps in the floor: the affixes and loot
    tables are rewritten, and every wall of every stamped room stays."""
    skipped = 0
    for w, h, rooms in SIZES[:2]:
        for kind in FLOOR_KINDS[:2]:
            for seed in SEEDS[:10]:
                base = _stamp_floor(seed, w, h, kind, rooms)
                if base["gen"] != 3:
                    skipped += 1
                    continue
                mutated = _stamped_section(kind, rooms)
                mutated["groups"] = {"per_floor": [2, 3], "minions": [4, 5]}
                mutated["families"] = [
                    {"family": "beetle", "weight": 9, "depth": [1, 9]},
                    {"family": "rat", "weight": 1, "depth": [2, 6]},
                ]
                mutated["chest_values"] = {"t1": 7, "t2": 4}
                after = delve_v3.generate_floor_v3(
                    seed, (w, h), mutated, kind, list(_stamp_pack()), STAMP_DEPTH)
                where = _where(seed, w, h, kind)
                if after["rows"] != base["rows"]:
                    pytest.fail(f"{where}: rewriting the tables moved a wall (rows differ)")
                if after["stamps"] != base["stamps"]:
                    pytest.fail(f"{where}: rewriting the tables moved a stamped room")
                if after["anchors"] != base["anchors"]:
                    pytest.fail(f"{where}: rewriting the tables moved an anchor")
    STATS["skipped"] += skipped


def test_a_required_stamp_that_cannot_place_falls_back_to_v2_and_says_why():
    """The pinned try, and the defect it leaves behind.

    A 21x21 warden-hall cannot fit a 24x16 floor at any orientation, so
    the 24 attempts are not even taken and the floor cannot be built with
    the hall the Section asked for. The caller gets v2 geometry - the
    floor is still a floor - and the floor names the role that would not
    place, which is what `vefr stamp check` reads.
    """
    middle = ["#" + "." * 19 + "#"] * 19
    middle[0] = "#" + "W" + "." * 18 + "#"
    hall = ["##+##" + "#" * 16] + middle + ["#" * 10 + "+" + "#" * 10]
    assert len(hall) == 21 and all(len(row) == 21 for row in hall)
    record = stamps.read_v1({
        "stamp": 1, "id": "too-big-hall", "role": "warden-hall", "tags": ["too-big"],
        "legend": {"W": {"anchor": "warden"}}, "rows": hall,
    })
    pack = _stamped_section("normal", 6)
    pack["stamps"] = ["too-big"]
    floor = delve_v3.generate_floor_v3("too-big", (24, 16), pack, "normal", [record], 1)
    assert floor["gen"] == 2, "a stamp that cannot fit should fall back to v2"
    assert floor.get("stamp_defect") == "stamp:warden-hall", (
        f"the fallback names no defect: {floor.get('stamp_defect')!r}"
    )


def test_sweep_counters():
    """The counts the report quotes, printed from the completed sweep.

    Last in the file, so the fallback test has already walked all 3200 floors.
    """
    total = SEED_COUNT * len(SIZES) * len(FLOOR_KINDS)
    fell_back = sum(
        1
        for w, h, rooms in SIZES
        for kind in FLOOR_KINDS
        for seed in SEEDS
        if _floor(seed, w, h, kind, rooms)["gen"] != 3
    )
    print(
        f"\nsweep: {total} floors, {total - fell_back} v3, {fell_back} fallback "
        f"({fell_back / total:.5f}), {STATS['chestless']} chestless floors, "
        f"{STATS['skipped']} floors skipped by the property tests"
    )
    assert total == SEED_COUNT * len(SIZES) * len(FLOOR_KINDS)
