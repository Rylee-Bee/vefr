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


# --- the save-aware pack (durable rule saves, docs/plans/durable-rule-saves-plan.md) ---
# Neutral canon again. `build_saves` makes a SECOND fixture, named per call, so the
# pack the other rules tests use is never touched.
SAVE_FLAGS = {"lit": "the torch is burning", "saw": "the keeper was seen"}
SAVE_CLAIMS = {"keeper-guards-gate": {"meaning": "the keeper guards the gate", "true": True},
               "extra-claim": {"meaning": "the gate is old", "true": True}}
SAVE_PEOPLE = {"keeper": {"believes": ["keeper-guards-gate"]}, "fisher": {"believes": []}}
SAVE_RULES = [
    {"id": "the-game-awakens", "when": {"starts": {}}, "once": True,
     "then": [{"set": "lit"}, {"say": "The rules are awake."}]},
    {"id": "hello", "when": {"starts": {}}, "once": False,
     "then": [{"say": "Hello again."}]},
    {"id": "keeper-is-near", "when": {"comes-near": {"who": "keeper", "distance": 3}}, "once": True,
     "then": [{"set": "saw"}, {"say": "Someone waits by the path."}]},
    {"id": "lit-keeper", "when": {"comes-near": {"who": "keeper", "distance": 3}}, "once": False,
     "if": [{"flag": "lit", "is": True}], "then": [{"say": "The torch lights the way."}]},
    {"id": "keeper-again", "when": {"comes-near": {"who": "keeper", "distance": 3}}, "once": False,
     "then": [{"say": "The keeper nods."}]},
    {"id": "gossip", "when": {"comes-near": {"who": "keeper", "distance": 3}}, "once": True,
     "then": [{"tells": {"who": "keeper", "claim": "keeper-guards-gate", "to": "fisher"}}]},
    {"id": "gift", "when": {"comes-near": {"who": "keeper", "distance": 3}}, "once": True,
     "then": [{"give": "torch"}]},
    {"id": "gift2", "when": {"comes-near": {"who": "keeper", "distance": 3}}, "once": True,
     "then": [{"give": "chalked-map"}]},
    {"id": "learn", "when": {"comes-near": {"who": "keeper", "distance": 3}}, "once": True,
     "then": [{"believes": {"who": "fisher", "claim": "extra-claim"}}]},
]


def build_saves(dest: Path, saves=None, name="rules-saves-a", variant="a") -> Path:
    """`variant="b"` is the changed pack: one rule (gift2, learn), one flag (saw), one claim
    (extra-claim) and one item (chalked-map) removed, and one rule (newcomer) added."""
    pack = build(dest)
    final = dest / "worlds" / name
    if final.exists():
        shutil.rmtree(final)
    shutil.move(str(pack), str(final))
    world_json = final / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["name"] = name
    flags, claims = dict(SAVE_FLAGS), json.loads(json.dumps(SAVE_CLAIMS))
    people = json.loads(json.dumps(SAVE_PEOPLE))
    rules = json.loads(json.dumps(SAVE_RULES))
    if variant == "b":
        flags.pop("saw")
        claims.pop("extra-claim")
        world["items"].pop("chalked-map", None)
        rules = [r for r in rules if r["id"] not in ("gift2", "learn")]
        for r in rules:
            r["then"] = [a for a in r["then"] if a != {"set": "saw"}]
        rules.append({"id": "newcomer", "when": {"comes-near": {"who": "keeper", "distance": 3}},
                      "once": True, "then": [{"say": "A new rule wakes."}]})
    # a second speaker (people must be speakers): a copy of the sample keeper, elsewhere on the map
    shutil.copy(final / "voices" / "keeper.md", final / "voices" / "fisher.md")
    world["voices"]["fisher"] = dict(world["voices"]["keeper"], file="voices/fisher.md")
    act_json = final / "acts" / "act-1" / "world.json"
    act = json.loads(act_json.read_text(encoding="utf-8"))
    act["speakers"]["fisher"] = dict(act["speakers"]["keeper"], name="The Fisher", at=[5, 6],
                                     voice_file="voices/fisher.md")
    act_json.write_text(json.dumps(act), encoding="utf-8")
    world.update({"flags": flags, "claims": claims, "people": people, "rules": rules})
    if saves is not None:
        world["saves"] = json.loads(json.dumps(saves))
    world_json.write_text(json.dumps(world), encoding="utf-8")
    return final


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))
