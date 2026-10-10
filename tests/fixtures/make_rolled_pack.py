"""A neutral pack whose loot is rolled (ADR 0017, T3 slice 1).

`build(dest, ...)` copies the sample world and writes three things on top:
a small `items` catalog with one plain thing, one fixed-rarity thing and
one rolled thing; a Blueprint whose cellar rat and pale moth carry those
ids; and a one-Section descent over the sample's own town.

Deliberately small, like every other fixture here: one Section, one floor
of play, two families. The point is that a pack CAN say this and the game
answers - not how big a rolled world is. Neutral engine-test canon only:
the things are a pebble, a ring and a cloudy potion.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

ENTRY_AT = [7, 5]          # the sample town's own threshold tile

# Three catalog entries, one per shape this slice added:
#   pebble    - the before picture: no rarity, no traits, no roll, so it
#               drops as the bare id it has always been;
#   brass-ring- a fixed rarity and a fixed trait, no roll, so it drops as
#               an instance that is never identified;
#   cloudy-potion - a roll: pack-chosen rarity names with whole weights,
#               a trait pool, a chance and a max.
ITEMS = {
    "pebble": {"name": "a grey pebble", "value": 1},
    "brass-ring": {"name": "a brass ring", "rarity": "common",
                   "traits": ["keen"]},
    "cloudy-potion": {
        "name": "a cloudy potion", "sprite": "potion", "heal": 3, "use": "drink",
        "roll": {
            "rarity": {"common": 60, "uncommon": 30, "rare": 10},
            "traits": ["keen", "brave", "swift", "cold"],
            "chance": 60,
            "max": 2,
        },
    },
}

BLUEPRINT = {
    "blueprint": 1,
    "families": {
        "rat": {"defaults": {"name": "a grey rat", "sprite": "rat", "hp": 4,
                             "atk": 2, "sight": 5, "drops": ["pebble"]}},
        "moth": {"defaults": {"name": "a pale moth", "sprite": "moth", "hp": 2,
                              "atk": 1, "sight": 3,
                              "drops": ["brass-ring", "cloudy-potion"]}},
    },
    "regions": {},
}

SECTIONS = [
    {
        "id": "cellar",
        "floors": 2,
        "size": {"w": [32, 36], "h": [24, 26]},
        "rooms": [6, 8],
        "fog": {"radius": 5},
        "families": [
            {"family": "rat", "weight": 2, "depth": [1, 2]},
            {"family": "moth", "weight": 1, "depth": [1, 2]},
        ],
    },
]

# The hero is patient, like the descent fixture's: these tests are about
# what a kill leaves behind, not about how long a fight takes.
PLAYER = {"hp": 40, "atk": 4, "gold": 0}


def build(dest: Path, items=None, descent=None) -> Path:
    """`items` replaces the catalog when given; `descent` replaces the block."""
    pack = dest / "worlds" / "rolled-test"
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)
    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["items"] = json.loads(json.dumps(ITEMS if items is None else items))
    world["player"] = dict(PLAYER, wake={"region": "town", "at": [3, 4]})
    if descent is None:
        descent = {
            "run_seed": "run-a",
            "entry": {"region": "town", "at": list(ENTRY_AT)},
            "sections": json.loads(json.dumps(SECTIONS)),
        }
    world["descent"] = descent
    # The catalog above replaces the sample's, so the pack can no longer
    # hand over what the inherited chest book promises: a chest that drops
    # ids world.json does not declare opens on nothing, which `vefr check`
    # refuses by name. Drop that book - this fixture's catalog is the
    # point of the test, and it means to be exactly the three shapes.
    (pack / "library" / "a-travellers-satchel.md").unlink()
    world_json.write_text(json.dumps(world), encoding="utf-8")
    # The Blueprint is a pack file beside world.json (ADR 0014): a Section
    # names a family by id, so the drops those families carry live here.
    # The lock beside it is the engine's own `vefr normalize`, run in
    # process, so the pack validates the way a pack that ships one does.
    (pack / "blueprint.json").write_text(json.dumps(BLUEPRINT), encoding="utf-8")
    from vefr import blueprint
    result = blueprint.normalize(pack, pack)
    assert not result.errors, result.errors
    return pack


def items_of(pack: Path) -> dict:
    """The pack's own item catalog, as the bake and the draw read it."""
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    return world.get("items") or {}


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))