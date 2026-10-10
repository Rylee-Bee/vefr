"""Build the death fixture pack (sample world + one death, one waking).

Neutral engine-test canon only: the sample's own town, one enemy that
kills the hero in a single blow, a second region the hero wakes in, and
the two rules a story needs for a death - one on `falls`, one on
`wakes` (vefr #365). Nothing else changes, and neither rule can be
faked with `enters`: `enters` fires on every arrival, `falls` fires
once, when the health reaches zero.

Each rule sets its own flag so the harness can see exactly which fact
the world noticed, and each says one line so the harness can see the
narrator heard it.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

FLAGS = {
    "fell": "the hero's health reached zero",
    "awoke": "the hero woke after falling",
    "arrived": "the hero arrived in the town (the `enters` control, and the "
               "one a death must not be mistaken for)",
}

RULES = [
    {"id": "the-hero-fell", "when": {"falls": {"what": "pit-rat",
                                                "where": "town"}},
     "then": [{"set": "fell"}, {"say": "The rat has you."}], "once": True},
    {"id": "the-hero-woke", "when": {"wakes": {"where": "cellar"}},
     "then": [{"set": "awoke"}, {"say": "You come to in the cellar."}],
     "once": True},
    # The control, and the whole point of #365: the death is NOT an
    # arrival. `enters` fires only on a door, and a hero who dies where
    # they stand has walked through no door, so this flag must still be
    # false when the hero wakes. A pack that faked the death with
    # `enters` would say its line here.
    {"id": "the-town-arrival", "when": {"enters": {"place": "town"}},
     "then": [{"set": "arrived"}], "once": True},
]

# A plain empty room: the hero wakes here, so `wakes.where` is a
# different place from `falls.where`.
CELLAR_MAP = [
    "#####",
    "#...#",
    "#####",
]

ITEMS = {
    "brass-key": {"name": "a brass key", "use": "turn", "keep": True},
}


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
    pack = dest / "worlds" / "death-test"
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)

    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["flags"] = dict(FLAGS)
    world["items"] = dict(ITEMS)
    world["rules"] = [json.loads(json.dumps(r)) for r in RULES]
    # hp 2 against an atk-2 rat: one blow is the whole health bar, so
    # the harness reaches the death in a single step. The rat's 9 hp
    # keeps the hero from winning first - the fixture is about dying.
    world["player"] = {
        "hp": 2, "atk": 2, "gold": 5,
        "wake": {"region": "cellar", "at": [1, 1]},
    }
    # The catalog above replaces the sample's, so the pack can no longer
    # hand over what the inherited chest book promises: a chest that drops
    # ids world.json does not declare opens on nothing, which `vefr check`
    # refuses by name. This catalog is here to serve the rat's one drop,
    # not to carry a chest, so that book goes.
    (pack / "library" / "a-travellers-satchel.md").unlink()
    world_json.write_text(json.dumps(world), encoding="utf-8")

    act_dir = pack / "acts" / "act-1"
    act_json = act_dir / "world.json"
    act = json.loads(act_json.read_text(encoding="utf-8"))
    act["regions"] = ["town", "cellar"]
    act_json.write_text(json.dumps(act), encoding="utf-8")

    # One tile west of the hero's start [3, 4], so one step left is the
    # bump that empties the health bar.
    contract_path = act_dir / "town" / "contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["enemies"] = [
        {"id": "pit-rat", "name": "the pit rat", "at": [2, 4],
         "hp": 9, "atk": 2, "drops": ["brass-key"]},
    ]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    _write_region(act_dir / "cellar", CELLAR_MAP, [])
    return pack


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))