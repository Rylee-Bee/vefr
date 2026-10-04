"""The fog of war remembers explored tiles as a bitset (fog-bitset contract).

A region may declare `fog` in its contract; then the player draws only what
the hero has seen, a radius around them lights, and the rest of the memory
stays dark. What was explored is kept per region, per world:

  - Explored tiles save as one bit per tile of the region map, row-major:
    `index = y*width + x` with `width = map[0].length`, most significant bit
    first in each byte, encoded as base64 text. The key is
    `vefr-fog2-<world>-<region>`, written through `store()` - never raw
    localStorage.
  - On load, an old-format JSON array of `"x,y"` strings under
    `vefr-fog-<world>-<region>` converts: the new key is written and the old
    one removed, so no explored tile is lost in the move.
  - Play itself does not change. Walking still lights the tiles around the
    walker, and a reload still remembers the same tiles.
  - The player's preference sits on top of the pack's: fog off
    (`vefr-fogpref-<world>` = "off"), or a region with no `fog` in its
    contract, writes nothing at all.
  - A fully explored 128x96 region saves under 1.1 KB of base64.

Neutral fixtures only, played through tests/play_kit.py.
"""

import base64
import json
import shutil
from pathlib import Path

import pytest

import play_kit

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

# The two storage eras, and the player preference that outranks both.
FOG2 = "vefr-fog2-"
FOG_OLD = "vefr-fog-"
FOG_PREF = "vefr-fogpref-"

TOWN = "acts/act-1/town"
RADIUS = 3

# The default lock town, 11 wide by 7 tall - every fixture entity
# (rat, chest, speakers, door) stands inside it, away from the walks below.
TOWN_W, TOWN_H = 11, 7

# Test 4's own map: 13 wide by 7 tall, deliberately not square, so a bitset
# laid out with the width and the height swapped reads back wrong.
EDGE_W, EDGE_H = 13, 7
EDGE_MAP = [
    "#############",
    "#...........#",
    "#...........#",
    "#...........#",
    "#...........#",
    "#...........#",
    "#############",
]


def build(tmp_path, fog=True, rows=None):
    """A lock fixture pack whose town declares fog (radius 3) and wakes at
    [1, 1]; `rows` replaces the town's map with one of my own."""
    patch = None
    if fog:
        patch = {f"{TOWN}/contract.json": {"fog": {"radius": RADIUS}, "hero_start": [1, 1]}}
    pack = play_kit.pack(tmp_path, "lock", patch)
    if rows is not None:
        (Path(pack) / TOWN / "map.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return pack


def world_and_region(pack):
    """The pack's own world name and wake region - the two halves of every
    fog key - so no test hardcodes either."""
    data = json.loads((Path(pack) / "world.json").read_text(encoding="utf-8"))
    return data["name"], data["player"]["wake"]["region"]


def fog_keys(store, prefix):
    """Every key in the returned store under one fog prefix."""
    return sorted(k for k in store if k.startswith(prefix))


def only_fog2(store):
    """The one bitset key - asserts there is exactly one, so a missing key
    fails as a fog-bitset expectation rather than a lookup error."""
    keys = fog_keys(store, FOG2)
    assert len(keys) == 1, f"expected exactly one {FOG2} key, got {keys}"
    return keys[0]


def decode(value, width, height):
    """A bitset's value back to the set of (x, y) tiles it remembers:
    row-major, most significant bit first in each byte."""
    raw = base64.b64decode(value)
    assert len(raw) * 8 >= width * height, "the bitset is too short for this map"
    seen = set()
    for i in range(width * height):
        if raw[i >> 3] & (1 << (7 - (i & 7))):
            seen.add((i % width, i // width))
    return seen


def bitset(width, height, unset=()):
    """A bitset covering every tile of the map except `unset`, built the way
    the player writes it: one bit per tile, row-major, MSB first."""
    dropped = set(unset)
    bits = bytearray((width * height + 7) // 8)
    for y in range(height):
        for x in range(width):
            if (x, y) in dropped:
                continue
            i = y * width + x
            bits[i >> 3] |= 1 << (7 - (i & 7))
    return base64.b64encode(bytes(bits)).decode("ascii")


# --- player --------------------------------------------------------------------------------


def big_map(width, height):
    """A 128x96 room: solid border, floor everywhere inside."""
    floor = "#" + "." * (width - 2) + "#"
    return ["#" * width] + [floor] * (height - 2) + ["#" * width]


def test_a_fully_explored_region_saves_under_1_1_kb(tmp_path):
    w, h = 128, 96
    pack = build(tmp_path, rows=big_map(w, h))
    # What a radius-3 light at the hero's [1, 1] would add: the seeded
    # bitset leaves exactly those tiles off, so the player's own saveFog()
    # has new tiles to write when it lights them.
    lit = {
        (x, y)
        for y in range(1 - RADIUS, 1 + RADIUS + 1)
        for x in range(1 - RADIUS, 1 + RADIUS + 1)
        if 0 <= x < w and 0 <= y < h and (x - 1) ** 2 + (y - 1) ** 2 <= RADIUS * RADIUS
    }
    world, region = world_and_region(pack)
    out = play_kit.play(
        play_kit.weave(pack, tmp_path),
        {
            "store": {f"{FOG2}{world}-{region}": bitset(w, h, unset=lit)},
            "steps": ["begin", "walk:down", "wait:300"],
        },
    )
    assert out["errors"] == []
    value = out["store"].get(only_fog2(out["store"]))
    assert value is not None
    assert len(value.encode("utf-8")) < 1126


def test_explored_tiles_survive_a_reload(tmp_path):
    pack = build(tmp_path)
    html = play_kit.weave(pack, tmp_path)
    first = play_kit.play(html, {"steps": ["begin", "walk:down,down,right", "wait:300"]})
    assert first["errors"] == []
    key = only_fog2(first["store"])
    assert fog_keys(first["store"], FOG_OLD) == [], "the old JSON fog key is still written"
    seen = decode(first["store"][key], TOWN_W, TOWN_H)
    assert {(1, 2), (1, 3), (2, 3)} <= seen, "the walked tiles were not remembered"

    second = play_kit.play(
        html, {"store": first["store"], "steps": ["begin", "wait:300"]}
    )
    assert second["errors"] == []
    again = decode(second["store"][only_fog2(second["store"])], TOWN_W, TOWN_H)
    assert again == seen, "a reload did not remember the same tiles"


def test_an_old_json_array_converts_and_the_old_key_is_gone(tmp_path):
    pack = build(tmp_path)
    world, region = world_and_region(pack)
    old_key = f"{FOG_OLD}{world}-{region}"
    remembered = ["9,5", "10,2", "5,6"]   # far from the hero, outside any light
    out = play_kit.play(
        play_kit.weave(pack, tmp_path),
        {"store": {old_key: json.dumps(remembered)}, "steps": ["begin", "wait:300"]},
    )
    assert out["errors"] == []
    assert old_key not in out["store"], "the old JSON key survived the conversion"
    seen = decode(out["store"][only_fog2(out["store"])], TOWN_W, TOWN_H)
    assert {(9, 5), (10, 2), (5, 6)} <= seen, "the old array's tiles were lost"
    assert (1, 1) in seen, "the hero's own light was not remembered"


def test_an_edge_tile_on_a_non_square_map_round_trips(tmp_path):
    pack = build(tmp_path, rows=EDGE_MAP)
    html = play_kit.weave(pack, tmp_path)
    # Down the first column, across the clear row, then to [11, 5] -
    # beside the right edge and the bottom edge, past every fixture entity.
    route = ",".join(["down"] * 3 + ["right"] * 10 + ["down"])
    first = play_kit.play(
        html,
        {"steps": ["begin", "walk:" + route, "wait:300"]},
    )
    assert first["errors"] == []
    seen = decode(first["store"][only_fog2(first["store"])], EDGE_W, EDGE_H)
    assert (EDGE_W - 1, 5) in seen, "the right-edge tile was not lit"
    assert (11, EDGE_H - 1) in seen, "the bottom-edge tile was not lit"

    second = play_kit.play(
        html, {"store": first["store"], "steps": ["begin", "wait:300"]}
    )
    assert second["errors"] == []
    again = decode(second["store"][only_fog2(second["store"])], EDGE_W, EDGE_H)
    assert (EDGE_W - 1, 5) in again and (11, EDGE_H - 1) in again, (
        "the edge tiles did not survive the reload"
    )
    assert again == seen, "a reload did not remember the same tiles"


def test_fog_off_or_a_region_without_fog_writes_nothing(tmp_path):
    off = build(tmp_path / "off")
    world, _ = world_and_region(off)
    out = play_kit.play(
        play_kit.weave(off, tmp_path / "off"),
        {
            "store": {f"{FOG_PREF}{world}": "off"},
            "steps": ["begin", "walk:down", "wait:300"],
        },
    )
    assert out["errors"] == []
    assert fog_keys(out["store"], FOG2) == [], "fog off still wrote a bitset"
    assert fog_keys(out["store"], FOG_OLD) == [], "fog off still wrote a fog key"

    plain = build(tmp_path / "plain", fog=False)
    out2 = play_kit.play(
        play_kit.weave(plain, tmp_path / "plain"),
        {"steps": ["begin", "walk:down", "wait:300"]},
    )
    assert out2["errors"] == []
    assert fog_keys(out2["store"], FOG2) == [], "a region with no fog wrote a bitset"
    assert fog_keys(out2["store"], FOG_OLD) == [], "a region with no fog wrote a fog key"
