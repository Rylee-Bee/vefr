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

import random

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


def _as_tile(value) -> tuple[int, int] | None:
    if (isinstance(value, (list, tuple)) and len(value) == 2
            and all(isinstance(v, (int, float)) for v in value)):
        return int(value[0]), int(value[1])
    return None


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
