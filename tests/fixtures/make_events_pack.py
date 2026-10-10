"""Build the events fixture pack (sample world + one of everything).

Neutral engine-test canon only: the sample's own town, one chest with
a drop, one enemy with a drop, one shopkeeper, and one rule per
observable event the player performs - `opens`, `picks-up`, `defeats`,
`uses-with`, `buys`, `sells`, `reads`, `phase-changes` - plus a
`takes` action and a `point-to` hint. Each rule sets its own flag so
the harness can see exactly which facts the world noticed.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

FLAGS = {
    "lit": "the game began",
    "opened": "the chest was opened",
    "got-it": "the pebble was picked up",
    "got-drop": "the fallen drop was picked up",
    "won": "the rat was defeated",
    "used-key": "the key was used on the place",
    "bought": "something was bought",
    "sold": "something was sold",
    "read-it": "the note was read and closed",
    "turned": "the watch turned",
}
CLAIMS = {"keeper-guards-gate": {"meaning": "the keeper guards the gate",
                                 "true": True}}
PEOPLE = {"keeper": {"believes": ["keeper-guards-gate"]}}

RULES = [
    {"id": "the-game-awakens", "when": {"starts": {}},
     "then": [{"set": "lit"}, {"give": "brass-key"},
              {"point-to": "town"}], "once": True},
    {"id": "the-chest-was-opened", "when": {"opens": {"what": "the-fixture-note"}},
     "then": [{"set": "opened"}], "once": True},
    {"id": "the-pebble-taken", "when": {"picks-up": {"what": "shiny-pebble"}},
     "then": [{"set": "got-it"}], "once": True},
    {"id": "the-drop-taken", "when": {"picks-up": {"what": "cloudy-potion"}},
     "then": [{"set": "got-drop"}], "once": True},
    {"id": "the-rat-fell", "when": {"defeats": {"what": "rat-1"}},
     "then": [{"set": "won"}, {"takes": "brass-key"}], "once": True},
    {"id": "the-key-turned", "when": {"uses-with": {"item": "brass-key",
                                                   "with": "keeper"}},
     "then": [{"set": "used-key"}], "once": True},
    {"id": "the-buying", "when": {"buys": {"what": "cloudy-potion"}},
     "then": [{"set": "bought"}], "once": True},
    {"id": "the-selling", "when": {"sells": {"what": "cloudy-potion"}},
     "then": [{"set": "sold"}], "once": True},
    {"id": "the-note-closed", "when": {"reads": {"what": "the-fixture-note"}},
     "then": [{"set": "read-it"}], "once": True},
    {"id": "the-watch-turned", "when": {"phase-changes": {"to": "dawn"}},
     "then": [{"set": "turned"}], "once": True},
]


def build(dest: Path) -> Path:
    pack = dest / "worlds" / "events-test"
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)

    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["flags"] = dict(FLAGS)
    world["claims"] = dict(CLAIMS)
    world["people"] = dict(PEOPLE)
    world["rules"] = [json.loads(json.dumps(r)) for r in RULES]
    # Beside the sample's own catalog, not over it: the pack keeps the
    # sample's demo chest book, whose drops the catalog has to declare
    # (`vefr check` refuses a chest that opens on nothing).
    world["items"] = {**(world.get("items") or {}), **{
        "brass-key": {"name": "a brass key", "use": "turn", "keep": True},
        "cloudy-potion": {"name": "a cloudy potion", "value": 5,
                          "heal": 2, "use": "drink"},
        "shiny-pebble": {"name": "a shiny pebble", "value": 3},
    }}
    world["player"] = {"hp": 8, "atk": 2, "gold": 5}
    world_json.write_text(json.dumps(world), encoding="utf-8")

    # The town contract: a chest on the hero's own start tile, one
    # enemy one step west, the keeper made a shopkeeper, and a named
    # place at [4,4] whose label is "keeper" - the tile the hero uses
    # the kept tool on (the same spot the rules fixture names).
    contract_path = pack / "acts" / "act-1" / "town" / "contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    pois = dict(contract.get("pois") or {})
    pois["4,4"] = "keeper"
    contract["pois"] = pois
    contract["enemies"] = [
        # hp 2 and hero atk 2: one bump ends it. The wound-flee rule
        # (a rat at a third of hp steps away) would make this a chase;
        # fight mechanics are pinned by test_combat_loop, not here.
        {"id": "rat-1", "name": "the cellar rat", "at": [2, 4],
         "hp": 2, "atk": 1, "drops": ["cloudy-potion"]},
    ]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    # One chest book on the hero's start tile, holding the pebble.
    lib = pack / "library" / "the-fixture-note.md"
    lib.write_text(
        "---\n"
        "title: The Fixture Note\n"
        "found: map\n"
        "at: [3, 4]\n"
        "kind: note\n"
        "chest: yes\n"
        "drops: shiny-pebble\n"
        "---\n"
        "A note left in a chest on the exact tile where the game begins.\n",
        encoding="utf-8",
    )

    # The keeper becomes the shopkeeper (one per region, first named).
    act_json = pack / "acts" / "act-1" / "world.json"
    act = json.loads(act_json.read_text(encoding="utf-8"))
    act["speakers"]["keeper"]["shop"] = "true"
    act_json.write_text(json.dumps(act), encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
