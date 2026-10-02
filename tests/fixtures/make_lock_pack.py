"""The locked-door fixture (design/gates-and-guardians.md, build step 1).

`build(dest, requires=..., locked_text=..., unlock_rule=...)` is make_interact_pack's
town with its one door (town [9, 3] -> cellar) given an optional `requires` lock.
Neutral engine-test canon only. The key item is `brass-ring`; the flag is `gate-open`.
`unlock_rule=True` adds a rule that sets `gate-open` when Begin is pressed.
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import make_interact_pack as base  # noqa: E402

NAME = "lock-test"
RING = {"item": "brass-ring"}
GATE_FLAG = {"flag": "gate-open"}


def build(dest: Path, requires=None, locked_text=None, unlock_rule=False, name=NAME) -> Path:
    made = base.build(dest)
    pack = dest / "worlds" / name
    if pack.exists():
        shutil.rmtree(pack)
    shutil.move(str(made), str(pack))

    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["name"] = name
    if requires is not None and "flag" in (requires if isinstance(requires, dict) else {}):
        world["flags"] = {"gate-open": "the gate has been opened"}
        world["claims"], world["people"] = {}, {}
        world["rules"] = ([{"id": "open-the-gate", "when": {"starts": {}}, "once": True,
                            "then": [{"set": "gate-open"}]}] if unlock_rule else [])
    world_json.write_text(json.dumps(world), encoding="utf-8")

    act_json = pack / "acts" / "act-1" / "world.json"
    act = json.loads(act_json.read_text(encoding="utf-8"))
    door = dict(base.DOOR)
    if requires is not None:
        door["requires"] = json.loads(json.dumps(requires))
    if locked_text is not None:
        door["locked_text"] = locked_text
    act["transitions"] = [door]
    act_json.write_text(json.dumps(act), encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]), requires=RING)))
