"""A neutral pack with wearable items, for the equipment tests (the #217 plan, track A).

`build(dest, items=..., name=...)` copies the sample world and merges `items` into its item catalog. The base
catalog adds a cloak (body, +2 health), a bow (hand, +1 attack), a ring (charm, no mods) and a potion (heal),
all neutral engine-test canon. The sample's own torch and chalked map stay.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

BASE_ITEMS = {
    "cloak-1": {"name": "a hooded cloak", "sprite": "cloak", "slot": "body", "mods": {"hp": 2}},
    "bow-1": {"name": "a short bow", "sprite": "bow", "slot": "hand", "mods": {"atk": 1}},
    "ring-1": {"name": "a plain ring", "sprite": "ring", "slot": "charm", "value": 3},
    "potion-1": {"name": "a cloudy potion", "sprite": "potion", "heal": 3, "use": "drink", "value": 4},
}


def build(dest: Path, items=None, replace=False, name="equip-test") -> Path:
    """`items` is merged into the base catalog (or replaces the whole catalog with replace=True)."""
    pack = dest / "worlds" / name
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)
    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["name"] = name
    catalog = {} if replace else {**world.get("items", {}), **json.loads(json.dumps(BASE_ITEMS))}
    catalog.update(json.loads(json.dumps(items or {})))
    world["items"] = catalog
    world_json.write_text(json.dumps(world), encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))
