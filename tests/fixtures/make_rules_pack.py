"""Build the rules fixture pack (sample-world + two rules) for tests.

Neutral engine-test canon only: the sample's own town, one flag, one
claim, one person (the sample's keeper), and two rules - one on
`starts` (fires when Begin is pressed), one on `comes-near` (fires
when the hero walks up to a named place one step right of the start).
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

FLAGS = {"lit": "the torch is burning"}
CLAIMS = {"keeper-guards-gate": {"meaning": "the keeper guards the gate",
                                 "true": True}}
PEOPLE = {"keeper": {"believes": ["keeper-guards-gate"]}}

# One rule per event the harness drives. The walk lands the hero on a
# POI whose name is "keeper" - a thing a rule may name - so the
# comes-near payload matches with distance 0.
RULES = [
    {"id": "the-game-awakens",
     "when": {"starts": {}},
     "then": [{"set": "lit"},
              {"say": "The rules are awake."}],
     "once": True},
    {"id": "keeper-is-near",
     "when": {"comes-near": {"who": "keeper", "distance": 3}},
     "then": [{"say": "Someone waits by the path."}],
     "once": True},
]


def build(dest: Path) -> Path:
    pack = dest / "worlds" / "rules-test"
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)

    # The four catalog keys at the pack root - the one place load_pack,
    # the validator and the bake all read them from.
    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["flags"] = dict(FLAGS)
    world["claims"] = dict(CLAIMS)
    world["people"] = dict(PEOPLE)
    world["rules"] = [json.loads(json.dumps(r)) for r in RULES]
    world_json.write_text(json.dumps(world), encoding="utf-8")

    # A named place one step right of the hero's start: [3, 4] ->
    # [4, 4], a walkable 'p' tile in the sample's town map. The POI's
    # name is the keeper, so walking there fires the comes-near rule.
    contract_path = pack / "acts" / "act-1" / "town" / "contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    pois = dict(contract.get("pois") or {})
    pois["4,4"] = "keeper"
    contract["pois"] = pois
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))
