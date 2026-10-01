"""Build a small, hazard-free floor for the hero-motion tests.

One room, no residents, no monsters, no doors: the only thing that can
happen is the hero walking. That keeps the walk deterministic, so the
test can pin every facing and every tile.

    0  #########
    1  #.......#    hero starts at [1, 1]; the west and north walls
    2  #.......#    are one step away, the east and south walls are
    3  #.......#    a short walk away
    4  #########

Neutral engine-test canon only. The pack is a copy of the sample world
with its library, residents and enemies taken out.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

MAP = [
    "#########",
    "#.......#",
    "#.......#",
    "#.......#",
    "#########",
]

HERO_START = [1, 1]


def _legend() -> dict:
    return {
        ".": {"base": ["#212a20"]},
        "#": {"base": ["#2a2e33"], "solid": True},
    }


def build(dest: Path) -> Path:
    pack = dest / "worlds" / "motion-test"
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)

    # The sample's books sit on the sample's own map; this floor is its
    # own, so a book here would only ever open on a tile that means
    # nothing here.
    lib = pack / "library"
    if lib.exists():
        shutil.rmtree(lib)
    lib.mkdir()

    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["player"] = {"hp": 12, "atk": 2, "gold": 0,
                       "wake": {"region": "town", "at": HERO_START}}
    world_json.write_text(json.dumps(world), encoding="utf-8")

    act_dir = pack / "acts" / "act-1"
    act = json.loads((act_dir / "world.json").read_text(encoding="utf-8"))
    act["regions"] = ["town"]
    act["transitions"] = []
    act["speakers"] = {}
    (act_dir / "world.json").write_text(json.dumps(act), encoding="utf-8")

    region = act_dir / "town"
    region.mkdir(parents=True, exist_ok=True)
    (region / "map.md").write_text("\n".join(MAP) + "\n", encoding="utf-8")
    contract = {
        "tile": 32, "bg": "#131311", "hero_start": HERO_START,
        "sanctuary_tiles": ["."],
        "water_by_phase": {"dusk": "low", "dawn": "low"},
        "flood_tiles": [], "pois": {}, "legend": _legend(),
        "enemies": [],
    }
    (region / "contract.json").write_text(
        json.dumps(contract), encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))
