"""Read an external private pack; write evidence outside the public checkout."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess

from vefr import cli, maplab
from prototype import digest, expand, floor, lower, reachable, semantic

parser = argparse.ArgumentParser()
parser.add_argument("--pack", type=Path, required=True)
parser.add_argument("--region", required=True)
parser.add_argument("--sprite", required=True)
parser.add_argument("--rule", required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
pack = args.pack.resolve()
world = maplab.load_pack(pack)
assert not maplab.validate(world, pack)
root = json.loads((pack / "world.json").read_text())
region_path = next(pack.glob(f"acts/*/{args.region}/contract.json"))
region = json.loads(region_path.read_text())
originals = [e for e in region["enemies"] if e["sprite"] == args.sprite]
keys = ["name", "sprite", "hp", "atk", "xp"]
shared = {k: originals[0][k] for k in keys}
assert all(all(e[k] == shared[k] for k in keys) for e in originals)
families = {"observed-family": {"defaults": shared}}
instances = [{"id": e["id"], "family": "observed-family",
              "properties": {k: v for k, v in e.items() if k not in keys + ["id"]}} for e in originals]
normalized = expand(families, instances)
assert normalized == originals
adapted = deepcopy(world)
adapted["regions"][args.region]["enemies"] = normalized
assert not maplab.validate(adapted, pack)
rule = next(r for r in root["rules"] if r["id"] == args.rule)
source = semantic(rule)
lowered = lower(source)
assert lowered == rule
adapted = deepcopy(world)
adapted["rules"] = [lowered if r["id"] == args.rule else r for r in world["rules"]]
assert not maplab.rules_errors(adapted, pack)
bad = deepcopy(adapted)
bad["rules"][0]["then"] = [{"teleport-through-time": {}}]
unknown_errors = maplab.rules_errors(bad, pack)
assert unknown_errors
player = args.out / "private-player.html"
player.write_text(cli.weave_html(pack))
condition = rule["if"][0]["flag"]
result_flag = rule["then"][0]["set"]
event, data = next(iter(rule["when"].items()))
spec = {"player": str(player), "packs": [{**root, "rules": [r]} for r in (rule, lowered)],
        "condition": condition, "resultFlag": result_flag, "event": event, "data": data,
        "ruleId": args.rule, "line": rule["then"][1]["say"]["line"]}
(args.out / "comparison-input.json").write_text(json.dumps(spec, indent=2))
proc = subprocess.run(["node", str(Path(__file__).with_name("compare.mjs")), str(args.out / "comparison-input.json")],
                      capture_output=True, text=True, check=True)
(args.out / "rule-runtime.json").write_text(proc.stdout)
theme = {"generation": {"width": 30, "height": 20, "rooms": 8}, "props": ["pale-mark", "crate-mark"],
         "creatures": [{**shared, "id": "proof-creature"}],
         "required": ["reachable-stairs", "nonblocking-dressing"]}
generated = floor("language-proof-20261002", theme)
floor_world = deepcopy(world)
floor_world["regions"]["proof-floor"] = {**generated["contract"], "map": generated["rows"]}
assert not maplab.validate(floor_world, pack), maplab.validate(floor_world, pack)
assert generated == floor("language-proof-20261002", theme)
assert reachable(generated["rows"])[0]
changed = deepcopy(theme)
changed["props"].append("extra-mark")
assert floor("language-proof-20261002", changed)["rows"] == generated["rows"]
generated["provenance"]["engine_revision"] = "6943f13e60bdf8fd2922945e50cb053755c2566f"
generated["provenance"]["generator_source_sha256"] = digest(Path("src/vefr/delve.py").read_text())
evidence = {"family": {"original": originals, "semantic": {"families": families, "instances": instances},
                       "normalized": normalized, "validator": "pass", "repeated_properties_removed": (len(originals)-1)*len(keys)},
            "rule": {"original": rule, "semantic": source, "lowered": lowered, "validator": "pass",
                     "source_map": {"rule": f"world.json/rules/{args.rule}",
                                    "effects": [f"world.json/rules/{args.rule}/then/{i}" for i in range(len(rule["then"]))]},
                     "unknown_effect_validation": unknown_errors},
            "floor": {"theme": theme, "normalized": generated, "repeat_identical": True,
                      "layout_independent_of_dressing": True, "stairs_before_after": True,
                      "current_validator": "pass (extra isolated region; authored pack unchanged)",
                      "ending": "No authored ending room exists in inspected pack; synthetic pass-through tested separately"}}
(args.out / "private-evidence.json").write_text(json.dumps(evidence, indent=2))
print("real family exact equality + current validation: PASS")
print("real rule exact equality + validator + engine + DOM + reload comparison: PASS")
print("floor repeat/dressing independence/reachability: PASS")
