"""Build the wall fixture pack for the monster-walking tests: one floor
where a monster can only reach the hero the long way round a wall, and
one open floor where two monsters who cannot see the hero drift toward
each other. Neutral engine-test canon only.

The town map is the whole point:

    0  ###########
    1  #.........#    the hero's corridor, and the door at [1, 1]
    2  #######.###    a wall, with the one doorway through it at [7, 2]
    3  #.........#
    4  #.........#
    5  #.........#
    6  ###########

The rat starts at [1, 3], under the wall, with the hero at [2, 1] -
straight above it, and every straight line out of its tile is wall. A
monster that walks in a straight line can never leave that pocket; the
only way to the hero is along the bottom corridor, through the doorway,
and back west. The hero is healthy enough to take a few blows and hurt
the rat enough to make it run, so one fight answers all three
questions: it comes round the wall, it hits, and it runs when hurt.

The cellar is one open room with the hero in one corner and two
monsters in the other, nine paces apart and well outside their own
sight: the only thing left for them to do is find each other.
"""

import base64
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

TOWN_MAP = [
    "###########",
    "#.........#",
    "#######.###",
    "#.........#",
    "#.........#",
    "#.........#",
    "###########",
]
CELLAR_MAP = [
    "###########",
    "#.........#",
    "#.........#",
    "#.........#",
    "###########",
]

# The rat is under the wall, three hp (so two hero hits leave it at one,
# badly hurt), one atk, and it can see the whole floor. The two in the
# cellar see almost nothing, so they never come looking for the hero.
TOWN_ENEMIES = [
    {"id": "far-rat", "name": "a far rat", "at": [1, 3],
     "hp": 3, "atk": 1, "sight": 6},
]
CELLAR_ENEMIES = [
    {"id": "gutter-hound", "name": "a gutter hound", "at": [6, 1],
     "hp": 4, "atk": 1, "sight": 2},
    {"id": "cold-crow", "name": "a cold crow", "at": [9, 1],
     "hp": 4, "atk": 1, "sight": 2},
]

# A 1x1 transparent PNG - enough for the bake to inline a sprite.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def _legend() -> dict:
    return {
        ".": {"base": ["#212a20"]},
        "#": {"base": ["#2a2e33"], "solid": True},
    }


def _write_region(region: Path, rows: list, enemies: list, hero_start: list) -> None:
    region.mkdir(parents=True, exist_ok=True)
    (region / "map.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    contract = {
        "tile": 32, "bg": "#131311", "hero_start": hero_start,
        "sanctuary_tiles": ["."],
        "water_by_phase": {"dusk": "low", "dawn": "low"},
        "flood_tiles": [], "pois": {}, "legend": _legend(),
    }
    if enemies:
        contract["enemies"] = enemies
    (region / "contract.json").write_text(
        json.dumps(contract), encoding="utf-8")


def build(dest: Path) -> Path:
    pack = dest / "worlds" / "wall-test"
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)

    # The sample's books sit on the sample's own map; this pack's floors
    # are its own, so a book here would only ever open on a tile that
    # means nothing here.
    lib = pack / "library"
    if lib.exists():
        shutil.rmtree(lib)
    lib.mkdir()

    # A hero with room to fight: enough health to be hit a few times
    # without waking, and two attack, so one good hit hurts.
    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["player"] = {
        "hp": 12, "atk": 2, "gold": 0,
        "sprites": {"rat": "sprites/rat.png"},
        "wake": {"region": "town", "at": [2, 1]},
    }
    world_json.write_text(json.dumps(world), encoding="utf-8")

    act_dir = pack / "acts" / "act-1"
    act = json.loads((act_dir / "world.json").read_text(encoding="utf-8"))
    act["regions"] = ["town", "cellar"]
    act["transitions"] = [
        {"from": "town", "at": [1, 1], "to": "cellar", "to_at": [1, 1]},
    ]
    # No residents on these floors: the fight is the whole fixture.
    act["speakers"] = {}
    (act_dir / "world.json").write_text(json.dumps(act), encoding="utf-8")

    _write_region(act_dir / "town", TOWN_MAP, TOWN_ENEMIES, [2, 1])
    _write_region(act_dir / "cellar", CELLAR_MAP, CELLAR_ENEMIES, [1, 1])

    sprites = pack / "sprites"
    sprites.mkdir(exist_ok=True)
    (sprites / "rat.png").write_bytes(_PNG)
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))
