"""Build a growth fixture pack (sample world + one rat + a growth block).

Neutral engine-test canon only. `build(dest, growth=..., xp=..., rat_hp=...)`
copies the sample world, gives the hero hp 8 / atk 2, and puts ONE enemy
(`rat-1`, atk 1) one step west of the start tile, like make_events_pack.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

LEVELS = {"mode": "levels",
          "levels": {"xp": [0, 3, 6], "gain": {"hp": 2, "atk": 1}}}
PRACTICE = {"mode": "practice",
            "practice": {"atk": {"by": "strikes", "every": 1, "gain": 1, "cap": 1}}}


def build(dest: Path, growth=None, xp=None, rat_hp=2, name="growth-test") -> Path:
    pack = dest / "worlds" / name
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)

    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["name"] = name
    world["player"] = {"hp": 8, "atk": 2, "gold": 0}
    if growth is not None:
        world["growth"] = json.loads(json.dumps(growth))
    world_json.write_text(json.dumps(world), encoding="utf-8")

    contract_path = pack / "acts" / "act-1" / "town" / "contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    rat = {"id": "rat-1", "name": "the cellar rat", "at": [2, 4],
           "hp": rat_hp, "atk": 1}
    if xp is not None:
        rat["xp"] = xp
    contract["enemies"] = [rat]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
