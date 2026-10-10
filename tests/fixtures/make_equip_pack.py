"""A neutral pack with wearable items, for the equipment tests (the #217 plan, track A).

`build(dest, items=..., name=...)` copies the sample world and merges `items` into its item catalog. The base
catalog adds a cloak (body, +2 health), a bow (hand, +1 attack), a ring (charm, no mods) and a potion (heal),
all neutral engine-test canon. The sample's own torch and chalked map stay.
"""

import base64
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

# The sample world ships no sprite table, so an item naming a `sprite`
# would never resolve and the Bag would fall back to a neutral dot. The
# bake (`cli._player_sprites`) only inlines a real image file that lives
# inside the pack, so the fixture writes one: a 1x1 transparent PNG per
# name. The equipment tests care that a worn slot draws an image, not what
# that image looks like. Neutral engine-test canon.
SPRITE_NAMES = ("cloak", "bow", "ring", "potion")
ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def build(dest: Path, items=None, replace=False, name="equip-test") -> Path:
    """`items` is merged into the base catalog (or replaces the whole catalog with replace=True).

    `replace=True` throws the sample's catalog away, and the sample's demo
    chest book goes with it: that book drops `torch` and `chalked-map`, and
    `vefr check` refuses a chest whose drops name no item the catalog
    declares (D114) - so a pack with no catalog beside it is a pack the
    check is right to say out loud, not a pack these tests should build.
    """
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
    if replace:
        (pack / "library" / "a-travellers-satchel.md").unlink()
    # Give the pack the four pictures its catalog names, so
    # `itemSpriteSrc` resolves and the equipment panel draws real art
    # instead of falling back to its neutral dot. The bake only inlines a
    # real image file inside the pack, so write the files.
    art = pack / "assets" / "equip-sprites"
    art.mkdir(parents=True, exist_ok=True)
    player = world.setdefault("player", {})
    sprites = player.setdefault("sprites", {})
    for name in SPRITE_NAMES:
        (art / f"{name}.png").write_bytes(ONE_PIXEL_PNG)
        sprites.setdefault(name, f"assets/equip-sprites/{name}.png")
    world_json.write_text(json.dumps(world), encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))
