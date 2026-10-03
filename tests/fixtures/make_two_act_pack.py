"""A neutral two-act pack for the acts tests (docs: the #217 plan, track B).

`build(dest, act2=..., act1=..., world=..., hall_contract=...)` copies the sample world and adds `acts/act-2`
with one region, `hall` (a copy of the sample town's map and contract). The keyword dicts are merged into
act 2's `world.json`, act 1's `world.json`, the pack's `world.json`, and the hall's `contract.json`, so a test
breaks exactly one thing. Neutral engine-test canon only.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"


def _merge(path: Path, extra: dict | None) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(json.loads(json.dumps(extra or {})))
    path.write_text(json.dumps(data), encoding="utf-8")


def build(dest: Path, act2=None, act1=None, world=None, hall_contract=None, name="acts-test") -> Path:
    pack = dest / "worlds" / name
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)
    _merge(pack / "world.json", {"name": name, **(world or {})})

    acts = pack / "acts"
    hall = acts / "act-2" / "hall"
    shutil.copytree(acts / "act-1" / "town", hall)
    (acts / "act-2" / "world.json").write_text(json.dumps(
        {"id": "act-2", "title": "The Second Part", "regions": ["hall"], "speakers": {}, "transitions": []}),
        encoding="utf-8")
    _merge(acts / "act-2" / "world.json", act2)
    _merge(acts / "act-1" / "world.json", act1)
    _merge(hall / "contract.json", hall_contract)
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))
