"""Synthetic acts-shape pack for the Blueprint tests (neutral engine canon only).

`build(dest, legacy=..., blueprint=...)` copies the sample world, adds one item
(`shell`), and makes two extra region directories (`cave-2`, `cave-3`) by
copying the sample town. With `legacy=True` the two caves carry hand-written
`enemies` equal to what STD_BLUEPRINT expands to. With `blueprint=` the given
dict is written to `blueprint.json` at the pack root. No real pack content.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

STD_BLUEPRINT = {
    "blueprint": 1,
    "families": {
        "beetle": {"defaults": {"name": "a beetle", "sprite": "beetle",
                                "hp": 3, "atk": 1, "xp": 2}},
        "deep-beetle": {"extends": "beetle", "defaults": {"hp": 4}},
        "moth": {"defaults": {"name": "a moth", "sprite": "moth",
                              "hp": 2, "atk": 1, "xp": 1, "sight": 3}},
    },
    "regions": {
        "act-1/cave-2": {"enemies": [
            {"id": "b1", "family": "beetle", "at": [3, 4]},
            {"id": "b2", "family": "beetle", "at": [6, 4],
             "properties": {"drops": ["shell"]}},
            {"id": "m1", "family": "moth", "at": [4, 2]},
            {"id": "odd1", "family": "beetle", "at": [5, 5],
             "properties": {"hp": 9}},
        ]},
        "act-1/cave-3": {"enemies": [
            {"id": "d1", "family": "deep-beetle", "at": [3, 4]},
            {"id": "d2", "family": "deep-beetle", "at": [6, 4]},
        ]},
    },
}

# What STD_BLUEPRINT must expand to, hand-written in the emitted key order
# (id, name, sprite, at, hp, atk, xp, sight, drops).
STD_LEGACY = {
    "act-1/cave-2": [
        {"id": "b1", "name": "a beetle", "sprite": "beetle", "at": [3, 4],
         "hp": 3, "atk": 1, "xp": 2},
        {"id": "b2", "name": "a beetle", "sprite": "beetle", "at": [6, 4],
         "hp": 3, "atk": 1, "xp": 2, "drops": ["shell"]},
        {"id": "m1", "name": "a moth", "sprite": "moth", "at": [4, 2],
         "hp": 2, "atk": 1, "xp": 1, "sight": 3},
        {"id": "odd1", "name": "a beetle", "sprite": "beetle", "at": [5, 5],
         "hp": 9, "atk": 1, "xp": 2},
    ],
    "act-1/cave-3": [
        {"id": "d1", "name": "a beetle", "sprite": "beetle", "at": [3, 4],
         "hp": 4, "atk": 1, "xp": 2},
        {"id": "d2", "name": "a beetle", "sprite": "beetle", "at": [6, 4],
         "hp": 4, "atk": 1, "xp": 2},
    ],
}


def build(dest: Path, legacy=False, blueprint=None, name="blueprint-test") -> Path:
    pack = dest / "worlds" / name
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)

    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["name"] = name
    world["items"]["shell"] = {"name": "a spiral shell"}
    world_json.write_text(json.dumps(world), encoding="utf-8")

    town = pack / "acts" / "act-1" / "town"
    for cave in ("cave-2", "cave-3"):
        shutil.copytree(town, pack / "acts" / "act-1" / cave)
        path = pack / "acts" / "act-1" / cave / "contract.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["enemies"] = (json.loads(json.dumps(STD_LEGACY[f"act-1/{cave}"]))
                               if legacy else [])
        path.write_text(json.dumps(contract), encoding="utf-8")

    if blueprint is not None:
        (pack / "blueprint.json").write_text(json.dumps(blueprint), encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(build(Path(sys.argv[1]), legacy=True, blueprint=STD_BLUEPRINT))
