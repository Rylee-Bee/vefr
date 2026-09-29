"""Build the neutral combat fixture pack (sample-world + a small fight)
for tests and local playtests. Neutral engine-test canon only: the
hazard is a named creature, the places are a town and a cellar."""

import base64
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

TOWN_MAP = [
    "#########",
    "#.......#",
    "#.......#",
    "#.......#",
    "#.......#",
    "#########",
]
CELLAR_MAP = [
    "#####",
    "#...#",
    "#####",
]

# One enemy stands next to the hero's start (bump to attack); the other
# waits across the room inside its sight (it walks in). The rat carries
# a drop; the pale thing does not.
TOWN_ENEMIES = [
    {"id": "cellar-rat", "name": "a cellar rat", "at": [2, 1],
     "hp": 4, "atk": 1, "sprite": "rat", "drops": ["cloudy-potion"]},
    {"id": "pale-thing", "name": "a pale thing", "at": [7, 1],
     "hp": 4, "atk": 2, "sight": 6},
]

# The item catalog: what a drop names and what the bag shows. Both have a
# sprite so the marker and the bag draw a picture, not a dot.
ITEMS = {
    "cloudy-potion": {"name": "a cloudy potion", "sprite": "potion"},
    "brass-ring": {"name": "a plain brass ring", "sprite": "ring"},
}

# A chest book at [1, 2], below the hero's start, holding a note and two
# items. A chest is used, not stepped on, so it never interrupts the walk
# to the fight.
CHEST_BOOK = (
    "---\ntitle: A Cellar Cache\nfound: map\nat: [1, 2]\n"
    "chest: yes\ndrops: cloudy-potion, brass-ring\nkind: note\n---\n"
    "A note left for whoever came down.\n"
)

# A 1x1 transparent PNG - enough for the bake to inline a sprite.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def _legend() -> dict:
    return {
        ".": {"base": ["#212a20"]},
        "#": {"base": ["#2a2e33"], "solid": True},
    }


def _write_region(region: Path, rows: list, enemies: list) -> None:
    region.mkdir(parents=True, exist_ok=True)
    (region / "map.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    contract = {
        "tile": 32, "bg": "#131311", "hero_start": [1, 1],
        "sanctuary_tiles": ["."],
        "water_by_phase": {"dusk": "low", "dawn": "low"},
        "flood_tiles": [], "pois": {}, "legend": _legend(),
    }
    if enemies:
        contract["enemies"] = enemies
    (region / "contract.json").write_text(
        json.dumps(contract), encoding="utf-8")


def build(dest: Path) -> Path:
    pack = dest / "worlds" / "combat-test"
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)

    # Engine-test canon only: the sample's books lie on the sample's own
    # map, so they are not the fixture's. The fixture's own chest holds
    # the note and the items its `drops` names.
    lib = pack / "library"
    if lib.exists():
        shutil.rmtree(lib)
    lib.mkdir()
    (lib / "cellar-cache.md").write_text(CHEST_BOOK, encoding="utf-8")

    # The hero's numbers, its pictures, and the wake point.
    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["items"] = ITEMS
    world["player"] = {
        "hp": 3, "atk": 2,
        "sprites": {"rat": "sprites/rat.png",
                    "potion": "sprites/potion.png",
                    "ring": "sprites/ring.png"},
        "wake": {"region": "town", "at": [1, 1]},
    }
    world_json.write_text(json.dumps(world), encoding="utf-8")

    # A two-region act: the town (with the fight) and an empty cellar.
    act_dir = pack / "acts" / "act-1"
    act = json.loads((act_dir / "world.json").read_text(encoding="utf-8"))
    act["regions"] = ["town", "cellar"]
    act["transitions"] = [
        {"from": "town", "at": [5, 4], "to": "cellar", "to_at": [1, 1]},
    ]
    (act_dir / "world.json").write_text(json.dumps(act), encoding="utf-8")

    _write_region(act_dir / "town", TOWN_MAP, TOWN_ENEMIES)
    _write_region(act_dir / "cellar", CELLAR_MAP, [])

    sprites = pack / "sprites"
    sprites.mkdir(exist_ok=True)
    (sprites / "rat.png").write_bytes(_PNG)
    (sprites / "potion.png").write_bytes(_PNG)
    (sprites / "ring.png").write_bytes(_PNG)
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))
