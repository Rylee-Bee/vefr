"""delve - the deterministic dungeon-floor generator.

The engine owns the *shape* of a generated floor; the story owns what
the floor means. `generate_floor` draws one floor from a seed using
rectangular rooms joined by L-corridors, marks the up-stair and the
down-stair, and guarantees a single connected cave with the two stairs
reachable from each other. `contract` writes the region contract.json a
generated floor needs, and `LEGEND` is the shared symbol -> tile table.

Everything here is rules-only and deterministic. The only randomness is
`random.Random(seed)` - never the global `random`, and never the clock -
so the same `(seed, width, height, rooms)` always draws the same rows.

Stair distance: `generate_floor` tries to place the down-stair at least
`MIN_STAIR_DISTANCE` (10) Manhattan tiles from the up-stair, so a floor
feels like a walk. If a layout cannot satisfy that after many tries it
relaxes to the widest pair it found rather than fail; the caller can
measure the pair it got.

This slice generates floors once, at build time, from a seed
(`norns delve`). Per-playthrough generation is a later slice.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

# How far apart the two stairs should be, in Manhattan tiles. The
# generator keeps the widest pair it can find when a layout is too
# small to satisfy this.
MIN_STAIR_DISTANCE = 10

# The symbols a generated floor uses. `#` is solid; the rest are
# walkable. Every symbol points at a tile the studio's archive already
# ships (web/art/tiles/dungeon-*.webp), so a woven floor reads as stone
# instead of flat colour.
LEGEND = {
    "#": {"base": ["#20242b"], "solid": True, "tile": "dungeon-wall"},
    ".": {"base": ["#1a1d22"], "tile": "dungeon-floor"},
    "u": {"base": ["#2b2f38"], "tile": "dungeon-stairs-up"},
    "d": {"base": ["#2b2f38"], "tile": "dungeon-stairs-down"},
}

# A generated floor is deep ground: near-black, lit only by the stairs.
BG = "#0d0f12"
HERO_COLOR = "#e8e5df"
SPEAKER_COLOR = "#8b939c"
SPEAKER_HEAD = "#d8d5df"

# How many times the stair picker samples before it relaxes the minimum.
_STAIR_ATTEMPTS = 500


def _to_int32(value: int) -> int:
    """The low 32 bits of `value`, read as JavaScript's signed 32-bit int."""
    value &= 0xFFFFFFFF
    if value >= 0x80000000:
        value -= 0x100000000
    return value


def _imul(a: int, b: int) -> int:
    """JavaScript's `Math.imul`: a 32-bit signed multiply (low 32 bits)."""
    return _to_int32((a & 0xFFFFFFFF) * (b & 0xFFFFFFFF))


def _ushr(value: int, bits: int) -> int:
    """JavaScript's unsigned right shift `>>>`, on a 32-bit word."""
    return (value & 0xFFFFFFFF) >> bits


def prng(seed: str):
    """A JavaScript-compatible random stream: floats in [0, 1).

    The string is hashed by its UTF-16 code units (exactly what
    JavaScript's `charCodeAt` reads, so an astral character is two
    units) with xmur3, and the resulting 32-bit state feeds mulberry32.
    Only 32-bit integer maths is used, so a JavaScript twin that runs
    the same code returns the identical stream. The returned closure is
    stateful: every call yields the next float and advances the state.
    """
    units = seed.encode("utf-16-le")
    codes = [units[i] | (units[i + 1] << 8) for i in range(0, len(units), 2)]
    h = _to_int32(1779033703 ^ len(codes))
    for code in codes:
        h = _imul(h ^ code, 3432918353)
        h = _to_int32((h << 13) | _ushr(h, 19))
    h = _imul(h ^ _ushr(h, 16), 2246822507)
    h = _imul(h ^ _ushr(h, 13), 3266489909)
    state = _to_int32(h ^ _ushr(h, 16))

    def next_float() -> float:
        nonlocal state
        state = _to_int32(state + 0x6D2B79F5)
        t = _imul(state ^ _ushr(state, 15), 1 | state)
        t = _to_int32((t + _imul(t ^ _ushr(t, 7), 61 | t)) ^ t)
        return _ushr(t ^ _ushr(t, 14), 0) / 4294967296

    return next_float


def _center(room: tuple[int, int, int, int]) -> tuple[int, int]:
    x, y, w, h = room
    return x + w // 2, y + h // 2


def _overlaps(a: tuple[int, int, int, int],
              b: tuple[int, int, int, int], pad: int) -> bool:
    """True when two room rectangles touch or sit closer than `pad`.

    Kept apart by at least one wall so rooms read as separate chambers
    instead of one merged blob.
    """
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ((ax - pad) < (bx + bw) and (bx - pad) < (ax + aw)
            and (ay - pad) < (by + bh) and (by - pad) < (ay + ah))


def _carve_room(grid: list[list[str]], room: tuple[int, int, int, int]) -> None:
    x, y, w, h = room
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            grid[yy][xx] = "."


def _carve_h(grid: list[list[str]], x0: int, x1: int, y: int) -> None:
    for x in range(min(x0, x1), max(x0, x1) + 1):
        grid[y][x] = "."


def _carve_v(grid: list[list[str]], x: int, y0: int, y1: int) -> None:
    for y in range(min(y0, y1), max(y0, y1) + 1):
        grid[y][x] = "."


def _carve_corridor(rng: random.Random, grid: list[list[str]],
                    a: tuple[int, int], b: tuple[int, int]) -> None:
    """An L-shaped corridor from `a` to `b` (order chosen at random)."""
    ax, ay = a
    bx, by = b
    if rng.random() < 0.5:
        _carve_h(grid, ax, bx, ay)
        _carve_v(grid, bx, ay, by)
    else:
        _carve_v(grid, ax, ay, by)
        _carve_h(grid, ax, bx, by)


def _place_rooms(rng: random.Random, grid: list[list[str]],
                 width: int, height: int,
                 count: int) -> list[tuple[int, int, int, int]]:
    """Carve up to `count` non-touching rooms; return the ones placed.

    A layout with little room may place fewer than `count`; the carved
    rooms are always internally connected by the caller's corridors.
    """
    placed: list[tuple[int, int, int, int]] = []
    max_w = max(3, min(9, width - 2))
    max_h = max(3, min(7, height - 2))
    for _ in range(count * 30):
        if len(placed) >= count:
            break
        w = rng.randint(3, max_w)
        h = rng.randint(3, max_h)
        x = rng.randint(1, width - 1 - w)
        y = rng.randint(1, height - 1 - h)
        room = (x, y, w, h)
        if any(_overlaps(room, other, 1) for other in placed):
            continue
        _carve_room(grid, room)
        placed.append(room)
    if not placed:
        # The interior is at least 3x3 (the caller enforces the sizes),
        # so this never fires in practice - kept so a floor always has
        # ground to stand on.
        _carve_room(grid, (1, 1, 3, 3))
        placed.append((1, 1, 3, 3))
    return placed


def _pick_stairs(rng: random.Random,
                 floors: list[tuple[int, int]]) -> tuple[tuple[int, int],
                                                         tuple[int, int]]:
    """Two distinct floor tiles for `u` and `d`.

    Samples pairs, keeping the widest; returns as soon as a pair meets
    `MIN_STAIR_DISTANCE`. A layout too small to satisfy it relaxes to
    the widest pair found.
    """
    if len(floors) < 2:
        raise ValueError("a floor needs at least two walkable tiles for stairs")
    best: tuple[tuple[int, int], tuple[int, int]] | None = None
    best_dist = -1
    for _ in range(_STAIR_ATTEMPTS):
        a, b = rng.sample(floors, 2)
        dist = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if dist > best_dist:
            best, best_dist = (a, b), dist
        if dist >= MIN_STAIR_DISTANCE:
            return a, b
    assert best is not None
    return best


def _rand_range(rng, lo: int, hi: int) -> int:
    """A whole number in [lo, hi] (both inclusive) from one `prng` draw.

    Written as `lo + floor(rng() * (hi - lo + 1))` so a JavaScript twin
    using `Math.floor` gets the identical number.
    """
    return lo + int(rng() * (hi - lo + 1))


def _place_rooms_v2(rng, grid: list[list[str]], width: int, height: int,
                    count: int) -> list[tuple[int, int, int, int]]:
    """The `prng` twin of `_place_rooms`; see the v2 draw order below."""
    placed: list[tuple[int, int, int, int]] = []
    max_w = max(3, min(9, width - 2))
    max_h = max(3, min(7, height - 2))
    for _ in range(count * 30):
        if len(placed) >= count:
            break
        w = _rand_range(rng, 3, max_w)
        h = _rand_range(rng, 3, max_h)
        x = _rand_range(rng, 1, width - 1 - w)
        y = _rand_range(rng, 1, height - 1 - h)
        room = (x, y, w, h)
        if any(_overlaps(room, other, 1) for other in placed):
            continue
        _carve_room(grid, room)
        placed.append(room)
    if not placed:
        _carve_room(grid, (1, 1, 3, 3))
        placed.append((1, 1, 3, 3))
    return placed


def _carve_corridor_v2(rng, grid: list[list[str]],
                       a: tuple[int, int], b: tuple[int, int]) -> None:
    """The `prng` twin of `_carve_corridor` (one draw picks the bend)."""
    ax, ay = a
    bx, by = b
    if rng() < 0.5:
        _carve_h(grid, ax, bx, ay)
        _carve_v(grid, bx, ay, by)
    else:
        _carve_v(grid, ax, ay, by)
        _carve_h(grid, ax, bx, by)


def _pick_stairs_v2(rng,
                    floors: list[tuple[int, int]]) -> tuple[tuple[int, int],
                                                           tuple[int, int]]:
    """The `prng` twin of `_pick_stairs` (two draws pick two tiles)."""
    if len(floors) < 2:
        raise ValueError("a floor needs at least two walkable tiles for stairs")
    n = len(floors)
    best: tuple[tuple[int, int], tuple[int, int]] | None = None
    best_dist = -1
    for _ in range(_STAIR_ATTEMPTS):
        i = int(rng() * n)
        j = int(rng() * (n - 1))
        if j >= i:
            j += 1
        a, b = floors[i], floors[j]
        dist = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if dist > best_dist:
            best, best_dist = (a, b), dist
        if dist >= MIN_STAIR_DISTANCE:
            return a, b
    assert best is not None
    return best


def generate_floor(seed: str, width: int = 30, height: int = 20,
                   rooms: int = 8) -> list[str]:
    """Draw one dungeon floor from `seed` as `height` rows of `width`.

    The rows use only `#` (wall), `.` (floor), `u` (up-stair) and `d`
    (down-stair). The border is solid wall; the interior is rooms joined
    by corridors, so every floor tile is reachable from every other and
    the two stairs are reachable from each other. The down-stair is
    placed at least `MIN_STAIR_DISTANCE` Manhattan tiles from the
    up-stair when the layout allows; otherwise the widest pair found is
    used (see the module docstring).

    Deterministic: `random.Random(seed)` is the only source of
    randomness, so identical inputs always return identical rows.
    Raises `ValueError` when `width` or `height` is smaller than 5 or
    `rooms` is smaller than 1.
    """
    if width < 5 or height < 5:
        raise ValueError("width and height must each be at least 5")
    if rooms < 1:
        raise ValueError("rooms must be at least 1")

    rng = random.Random(seed)
    grid = [["#"] * width for _ in range(height)]
    placed = _place_rooms(rng, grid, width, height, rooms)
    for a, b in zip(placed, placed[1:]):
        _carve_corridor(rng, grid, _center(a), _center(b))

    floors = [(x, y) for y in range(height) for x in range(width)
              if grid[y][x] == "."]
    up, down = _pick_stairs(rng, floors)
    grid[up[1]][up[0]] = "u"
    grid[down[1]][down[0]] = "d"
    return ["".join(row) for row in grid]


# generate_floor_v2 - the exact order of draws. A JavaScript twin must
# follow this line for line; `rng()` is one call of `prng(seed)`, and a
# whole number `rand(lo, hi)` is `lo + floor(rng() * (hi - lo + 1))`.
#
#  1. Validate: width and height must each be >= 5, and rooms >= 1;
#     otherwise raise ValueError (same messages as generate_floor).
#  2. rng = prng(seed). Build a `height` x `width` grid of "#".
#  3. max_w = max(3, min(9, width - 2));
#     max_h = max(3, min(7, height - 2)).
#  4. Rooms: repeat at most `rooms * 30` times, breaking early once
#     `rooms` rooms are placed. Each attempt draws, in this order:
#       w = rand(3, max_w);
#       h = rand(3, max_h);
#       x = rand(1, width - 1 - w);
#       y = rand(1, height - 1 - h).
#     The rectangle (x, y, w, h) is discarded if it overlaps any
#     already-placed room with pad 1 (no further draws that attempt);
#     otherwise carve it to "." and append it. If no room was placed,
#     carve (1, 1, 3, 3) and use that as the only room.
#  5. Corridors: for each consecutive pair of placed rooms (0->1, 1->2,
#     ..., n-2->n-1), take their centres cx = x + w // 2, cy = y + h // 2
#     (integer floor) and draw once:
#       if rng() < 0.5: carve horizontal from a.cx to b.cx at a.cy, then
#                       vertical from a.cy to b.cy at b.cx;
#       else:           carve vertical from a.cy to b.cy at a.cx, then
#                       horizontal from a.cx to b.cx at b.cy.
#     Every carve is inclusive of both endpoints and writes ".".
#  6. floors = every "." tile in row-major order: for y = 0..height-1,
#     then for x = 0..width-1.
#  7. Stairs: if len(floors) < 2 raise ValueError("a floor needs at
#     least two walkable tiles for stairs"). Otherwise repeat at most
#     _STAIR_ATTEMPTS (500) times:
#       n = len(floors);
#       i = floor(rng() * n);
#       j = floor(rng() * (n - 1));
#       if j >= i then j = j + 1            (so i != j);
#       a = floors[i]; b = floors[j];
#       dist = |a.x - b.x| + |a.y - b.y|.
#     Keep the pair with the largest dist seen so far (a strictly
#     greater dist replaces it; a tie keeps the earlier pair). Return
#     the first pair with dist >= MIN_STAIR_DISTANCE (10). If none
#     reaches it in 500 attempts, return the widest pair found.
#  8. Write "u" at the first stair and "d" at the second; return the
#     rows as strings.
def generate_floor_v2(seed: str, width: int = 30, height: int = 20,
                      rooms: int = 8) -> list[str]:
    """Draw one floor from `seed` using only the shared `prng`.

    Same shape as `generate_floor` (rooms joined by L-corridors, a solid
    wall border, one `u` and one `d` far apart when the layout allows,
    every walkable tile connected) but built entirely from `prng(seed)`,
    so a JavaScript twin draws identical rows. Raises `ValueError` for
    the same bad sizes as `generate_floor`. The draw order is the
    numbered comment above this function.
    """
    if width < 5 or height < 5:
        raise ValueError("width and height must each be at least 5")
    if rooms < 1:
        raise ValueError("rooms must be at least 1")

    rng = prng(seed)
    grid = [["#"] * width for _ in range(height)]
    placed = _place_rooms_v2(rng, grid, width, height, rooms)
    for a, b in zip(placed, placed[1:]):
        _carve_corridor_v2(rng, grid, _center(a), _center(b))

    floors = [(x, y) for y in range(height) for x in range(width)
              if grid[y][x] == "."]
    up, down = _pick_stairs_v2(rng, floors)
    grid[up[1]][up[0]] = "u"
    grid[down[1]][down[0]] = "d"
    return ["".join(row) for row in grid]


def _as_tile(value) -> tuple[int, int] | None:
    if (isinstance(value, (list, tuple)) and len(value) == 2
            and all(isinstance(v, (int, float)) for v in value)):
        return int(value[0]), int(value[1])
    return None


# ---- the descent: play-time floors (PLAN §2, rows E1) ----
#
# A descent is sized by minutes to play it, not by tiles. The pack's
# `descent` block names the run and the Sections; `locate` says which
# Section a depth is in; the floor for that depth is drawn here, from a
# run seed and nothing else. Everything below is pure: the same depth
# always draws the same floor, in Python and in the JavaScript twin
# beside it (web/player/parts/395-the-descent.js).

# The generation this descent draws. It rides in every floor's identity,
# in the save (so a save from a different generation is offered the
# start-over card once), and in the seed of every stream: `v3|<key>|...`.
GEN_VERSION = 3
STREAM_VERSION = "v3"

# The save budgets of PLAN §3, and the cap that keeps them.
FLOOR_CAP = 40
FLOOR_BYTES = 1_500
SAVE_BYTES = 250_000

# What a Section gets when it says nothing. A floor defaults to a size a
# person can play in one sitting (PLAN §1, item 1), and a pack that wants
# a different number of minutes writes it.
DEFAULT_SIZE = {"w": (48, 64), "h": (32, 44)}
DEFAULT_ROOMS = (12, 18)
DEFAULT_MOBS = (2, 5)
DEFAULT_FOG_RADIUS = 5
DEFAULT_FAMILY = "a stranger in the dark"

# A monster stands at least this far from both stairs, so arriving and
# leaving are never a fight the hero did not choose (the shipped spacing
# rule).
MOB_SPACING = 7


def _range_of(section: dict, key: str, default: tuple[int, int]) -> tuple[int, int]:
    """A Section's `[lo, hi]` pair for `key`, or the engine's default."""
    value = section.get(key) if isinstance(section, dict) else None
    if (isinstance(value, (list, tuple)) and len(value) == 2
            and all(isinstance(v, int) and not isinstance(v, bool) for v in value)
            and value[0] <= value[1]):
        return int(value[0]), int(value[1])
    return default


def _size_range(section: dict, axis: str) -> tuple[int, int]:
    size = section.get('size')
    value = size.get(axis) if isinstance(size, dict) else None
    if (isinstance(value, (list, tuple)) and len(value) == 2
            and all(isinstance(v, int) and not isinstance(v, bool) for v in value)
            and value[0] <= value[1] and value[0] >= 5):
        return int(value[0]), int(value[1])
    return DEFAULT_SIZE[axis]


def _floors_of(section: dict) -> int:
    value = section.get('floors') if isinstance(section, dict) else None
    if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
        return value
    raise ValueError("every Section needs a whole number of floors, at least 1")


def _sections(pack) -> list[dict]:
    """The Section records a pack's descent carries, in pack order.

    Accepts the pack itself (a dict with a `descent` block), the block on
    its own, or the bare list of Sections, so a caller holding any of the
    three gets the same answer. A Section named by id rather than written
    out is refused: reading `sections/<id>.json` is the loader's job (the
    weave does it), not this function's.
    """
    block = pack
    if isinstance(pack, dict) and isinstance(pack.get('descent'), dict):
        block = pack['descent']
    listed = block.get('sections') if isinstance(block, dict) else block
    if not isinstance(listed, list) or not listed:
        raise ValueError("a descent needs a list of Sections")
    sections: list[dict] = []
    for entry in listed:
        if not isinstance(entry, dict):
            raise ValueError("every Section must be a record with an id and "
                             "its number of floors")
        if not isinstance(entry.get('id'), str) or not entry['id']:
            raise ValueError("every Section needs an id")
        sections.append(entry)
    return sections


def descent_of(pack, pack_dir=None) -> dict:
    """The pack's `descent` block, or `{}` when it declares none.

    A Section may be written out in the block or named by id and kept in
    `sections/<id>.json` beside the pack (`pack_dir`); the named ones are
    read here so every caller - the validator, the bake, the tests - sees
    the same resolved list of records.

    An id is pack data, so it goes through the same `_inside` guard
    (`cli._inside`) every other name out of a pack goes through before it
    touches the filesystem: an id like `../x` or `/etc/x` is refused in a
    sentence rather than read and baked.
    """
    block = pack.get('descent') if isinstance(pack, dict) else None
    if not isinstance(block, dict):
        return {}
    listed = block.get('sections')
    if not isinstance(listed, list):
        return block
    from .cli import _inside  # here, not at the top: cli imports this module

    base = os.path.realpath(str(pack_dir)) if pack_dir is not None else None
    sections = []
    for entry in listed:
        if not isinstance(entry, str):
            sections.append(entry)
            continue
        where = f'sections/{entry}.json'
        if base is None:
            raise ValueError(f"the Section {entry!r} is named but there is "
                             f"no pack to read {where} from")
        target = _inside(base, 'sections', f'{entry}.json')
        if target is None:
            raise ValueError(f"the Section {entry!r} is named but {where} "
                             f"would leave the pack")
        try:
            data = json.loads(Path(target).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raise ValueError(f"the Section {entry!r} is named but "
                             f"{where} could not be read")
        if not isinstance(data, dict):
            raise ValueError(f"{where} must be a Section record")
        sections.append({'id': entry, **data})
    return {**block, 'sections': sections}


def locate(depth: int, pack) -> tuple[int, dict, int]:
    """Where a depth leads: `(cycle, section, k)`, and nothing else.

    The story is cycle 0: depth 1 is the first floor of the first Section,
    and the Sections are walked in pack order. Past the last floor of the
    last Section the descent begins again in cycle 1, the Sections in the
    same order, so a descent is endless without any of it being special.

    Pure: the answer is read off the pack's Section list and the depth
    alone. A depth below 1, or a pack with no Sections, is refused rather
    than guessed at.
    """
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
        raise ValueError("depth must be a whole number of at least 1")
    sections = _sections(pack)
    counts = [_floors_of(s) for s in sections]
    cycle, within = divmod(depth - 1, sum(counts))
    for section, count in zip(sections, counts):
        if within < count:
            return cycle, section, within + 1
        within -= count
    raise ValueError("depth is outside this descent")   # unreachable


def floor_name(section_id: str, cycle: int, k: int) -> str:
    """The region name a floor plays under: stable across reloads.

    The name says where the floor is in the descent and nothing about
    which run drew it, so two runs reuse the names and the identity
    triple - not the name - is what tells their floors apart.
    """
    return f'{section_id}-{cycle}-{k}'


def floor_key(run_seed: str, section_id: str, cycle: int, k: int) -> str:
    """The key every one of a floor's streams is seeded from."""
    return f'{run_seed}/{section_id}/{cycle}/{k}'


def stream_seed(key: str, stream: str) -> str:
    """One named stream of one floor: `v3|<floor key>|<stream>`.

    A separate stream per stage, so changing what a floor carries - an
    affix table, a loot roll, a chest - can never move a wall (PLAN §8's
    sub-seed rule).
    """
    return f'{STREAM_VERSION}|{key}|{stream}'


def loot_seed(key: str, mob_id: str) -> str:
    """A monster's own loot stream: the kill order cannot change a drop."""
    return stream_seed(key, f'loot|{mob_id}')


def chest_seed(key: str, chest_id: str) -> str:
    """A chest's own stream, for the day the chest is opened."""
    return stream_seed(key, f'chest|{chest_id}')


def run_seed(base: str, run: int = 0) -> str:
    """The run seed of a run: the pack's own for the first, counted after."""
    run = 0 if not isinstance(run, int) or isinstance(run, bool) else max(0, run)
    return base if run == 0 else f'{base}/run-{run}'


def _canonical(value) -> str:
    """A Section's content as the bytes both languages hash.

    Keys in order, no spaces, and a number written the way both languages
    write one: a whole number as a whole number, anything else in its
    shortest round-trip form. Every key of a record is written, including
    one whose value is null - which is what makes two Sections that differ
    only in a null and an absent key hash differently, as they should.
    The JavaScript twin (web/player/parts/395-the-descent.js) has the same
    function, and the parity harness is what proves they agree.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_canonical(v) for v in value) + "]"
    if isinstance(value, dict):
        parts = []
        for key in sorted(value, key=str):
            parts.append(json.dumps(str(key), ensure_ascii=False) + ":"
                         + _canonical(value[key]))
        return "{" + ",".join(parts) + "}"
    return "null"


def _hash12(text: str) -> str:
    """Two 32-bit FNV-style lanes over the UTF-8 bytes, as twelve hex.

    Small, exact and identical in both languages, which is all a digest
    has to be: the only question asked of it is "is this the same Section
    as last time?".
    """
    h1 = 2166136261
    h2 = 3335557771
    for i, byte in enumerate(text.encode("utf-8")):
        h1 = ((h1 ^ byte) * 16777619) & 0xFFFFFFFF
        h2 = ((h2 ^ ((byte + i) & 255)) * 2246822519) & 0xFFFFFFFF
    return f"{h1:08x}{h2:08x}"[:12]


def section_hash(section: dict) -> str:
    """A short, stable digest of a Section's own content.

    Half of a floor's identity. Editing a Section changes the hash, which
    is how a save learns that the floor it remembers is no longer the
    floor it would draw.
    """
    return _hash12(_canonical(section))


def _run_seed_of(descent, run: int) -> str:
    block = descent
    if isinstance(descent, dict) and isinstance(descent.get('descent'), dict):
        block = descent['descent']
    base = block.get('run_seed') if isinstance(block, dict) else None
    if not isinstance(base, str) or not base:
        raise ValueError("a descent needs a run seed")
    return run_seed(base, run)


def floor_identity(descent, depth: int, run: int = 0) -> dict:
    """`(gen, section hash, floor key)`: what makes this floor this floor."""
    cycle, section, k = locate(depth, descent)
    key = floor_key(_run_seed_of(descent, run), section['id'], cycle, k)
    return {'gen': GEN_VERSION, 'hash': section_hash(section), 'key': key}


def mob_drops(key: str, mob_id: str, table) -> list[str]:
    """What one monster carries, drawn from that monster's own stream.

    `table` is the monster family's list of drop ids. One draw off
    `v3|<key>|loot|<mob id>`, so two monsters never share a roll and the
    order monsters are killed in cannot change what they drop.
    """
    ids = [i for i in table if isinstance(i, str) and i] if isinstance(table, list) else []
    if not ids:
        return []
    rng = prng(loot_seed(key, mob_id))
    return [ids[int(rng() * len(ids))]]


def plan_floor(key: str, section: dict, k: int) -> dict:
    """The floor's plan: how big it is, and what kind of floor it is.

    Draws from `v3|<key>|plan` only, in this order: width, height, rooms.
    The kind is the Section's own pattern at position `k` - pack data,
    not a draw - so the pattern may be edited without moving a wall.
    """
    w_lo, w_hi = _size_range(section, 'w')
    h_lo, h_hi = _size_range(section, 'h')
    r_lo, r_hi = _range_of(section, 'rooms', DEFAULT_ROOMS)
    rng = prng(stream_seed(key, 'plan'))
    w = _rand_range(rng, w_lo, w_hi)
    h = _rand_range(rng, h_lo, h_hi)
    rooms = _rand_range(rng, max(1, r_lo), max(1, r_hi))
    pattern = section.get('pattern')
    kind = 'n'
    if isinstance(pattern, list) and 1 <= k <= len(pattern) \
            and isinstance(pattern[k - 1], str):
        kind = pattern[k - 1]
    return {'kind': kind, 'w': w, 'h': h, 'rooms': rooms}


def _stairs_of(rows: list[str]) -> tuple[tuple[int, int], tuple[int, int]]:
    up = down = None
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == 'u' and up is None:
                up = (x, y)
            elif ch == 'd' and down is None:
                down = (x, y)
    if up is None or down is None:
        raise ValueError("the generator drew no stairs")
    return up, down


def _families_of(section: dict) -> list[dict]:
    """The Section's families, sorted by id: a draw may not depend on
    the order the pack happened to write them in."""
    listed = section.get('families')
    if not isinstance(listed, list):
        return []
    families = [f for f in listed if isinstance(f, dict) and f.get('id')]
    return sorted(families, key=lambda f: f['id'])


def mobs_at(key: str, section: dict, rows: list[str],
            up: tuple[int, int], down: tuple[int, int]) -> list[dict]:
    """Who lives on this floor, drawn from `v3|<key>|pop`.

    A floor's monsters are placed on floor tiles at least `MOB_SPACING`
    from both stairs, one per tile, in a fixed order: the count first,
    then for each monster its tile, its family, its health, its reach and
    its drops (the drops from that monster's own loot stream). A floor
    too small to hold them all carries as many as fit, never fewer than
    none.
    """
    rng = prng(stream_seed(key, 'pop'))
    lo, hi = _range_of(section, 'mobs', DEFAULT_MOBS)
    count = _rand_range(rng, max(0, lo), max(0, hi))
    families = _families_of(section)
    pool: list[dict] = []
    for family in families:
        weight = family.get('weight')
        weight = weight if isinstance(weight, int) and not isinstance(weight, bool) \
            and 0 < weight <= 99 else 1
        pool.extend([family] * weight)
    candidates = [(x, y) for y, row in enumerate(rows) for x, ch in enumerate(row)
                  if ch == '.' and abs(x - up[0]) + abs(y - up[1]) >= MOB_SPACING
                  and abs(x - down[0]) + abs(y - down[1]) >= MOB_SPACING]
    mobs: list[dict] = []
    for i in range(count):
        if not candidates or not pool:
            break
        at = candidates.pop(int(rng() * len(candidates)))
        family = pool[int(rng() * len(pool))]
        hp_lo, hp_hi = _range_of(family, 'hp', (1, 1))
        hp = _rand_range(rng, max(1, hp_lo), max(1, hp_hi))
        atk = family.get('atk')
        atk = atk if isinstance(atk, int) and not isinstance(atk, bool) else 1
        sight = family.get('sight')
        sight = sight if isinstance(sight, int) and not isinstance(sight, bool) else 6
        drops = family.get('drops')
        mobs.append({
            'id': f'm{i}', 'family': family['id'],
            'name': family.get('name') or DEFAULT_FAMILY,
            'at': [at[0], at[1]], 'hp': max(1, hp), 'atk': max(1, atk),
            'sight': max(1, sight),
            'drops': mob_drops(key, f'm{i}', drops),
        })
    return mobs


def floor_plan(descent, depth: int, run: int = 0) -> dict:
    """The whole floor at `depth`, JSON-able and drawn from the run seed.

    The plan stream says how big the floor is, the layout stream carves
    it, and the pop stream fills it - three streams that never share a
    draw. The identity triple rides along so the save can tell this floor
    from the floor it drew last time.
    """
    cycle, section, k = locate(depth, descent)
    key = floor_key(_run_seed_of(descent, run), section['id'], cycle, k)
    plan = plan_floor(key, section, k)
    rows = generate_floor_v2(stream_seed(key, 'layout'), plan['w'], plan['h'],
                             plan['rooms'])
    up, down = _stairs_of(rows)
    fog = section.get('fog')
    radius = fog.get('radius') if isinstance(fog, dict) else None
    radius = radius if isinstance(radius, int) and not isinstance(radius, bool) \
        else DEFAULT_FOG_RADIUS
    return {
        'name': floor_name(section['id'], cycle, k),
        'key': key,
        'identity': {'gen': GEN_VERSION, 'hash': section_hash(section),
                     'key': key},
        'depth': depth, 'cycle': cycle, 'section': section['id'], 'k': k,
        'kind': plan['kind'], 'w': plan['w'], 'h': plan['h'],
        'rooms': plan['rooms'], 'rows': rows,
        'anchors': {'up': [up[0], up[1]], 'down': [down[0], down[1]]},
        'mobs': mobs_at(key, section, rows, up, down),
        'fog': {'radius': max(1, radius)},
    }


def contract(width: int, height: int, hero_at,
             down_at=None) -> dict:
    """The region contract.json for one generated floor.

    `hero_at` is the up-stair tile `[x, y]` - the hero lands there when
    stepping down from the floor above - and `down_at` is the down-stair
    tile `[x, y]` (the way on). For convenience `hero_at` may instead be
    a mapping with `up`/`down` keys or a pair of tiles, in which case the
    down tile is read from it.

    Returns the same shape an authored region's contract.json uses:
    `legend`, `pois` + `poi_text` for the stairs, `hero_start`, `tile`,
    `bg` and the character colours. A generated floor marks no sanctuary
    (a floor is not a safe town) and no water.
    """
    up = down = None
    if isinstance(hero_at, dict):
        up = _as_tile(hero_at.get("up"))
        down = _as_tile(hero_at.get("down"))
    elif (isinstance(hero_at, (list, tuple)) and len(hero_at) == 2
            and all(_as_tile(v) is not None for v in hero_at)):
        up = _as_tile(hero_at[0])
        down = _as_tile(hero_at[1])
    else:
        up = _as_tile(hero_at)
    if down_at is not None:
        down = _as_tile(down_at)

    for tile in (up, down):
        if tile is None:
            continue
        x, y = tile
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f"stair tile {tile} is outside the {width}x{height} floor")

    pois: dict[str, str] = {}
    poi_text: dict[str, str] = {}
    if up is not None:
        key = f"{up[0]},{up[1]}"
        pois[key] = "the stair up"
        poi_text[key] = "Steps climb back toward the day."
    if down is not None:
        key = f"{down[0]},{down[1]}"
        pois[key] = "the stair down"
        poi_text[key] = "Steps drop into the dark."

    return {
        "tile": 32,
        "bg": BG,
        "hero_start": list(up) if up is not None else [1, 1],
        "legend": {k: dict(v) for k, v in LEGEND.items()},
        "pois": pois,
        "poi_text": poi_text,
        "sanctuary_tiles": [],
        "water_by_phase": {},
        "flood_tiles": [],
        "watch": {},
        "hero_color": HERO_COLOR,
        "speaker_color": SPEAKER_COLOR,
        "speaker_head": SPEAKER_HEAD,
    }
