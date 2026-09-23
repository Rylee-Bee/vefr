"""Build the neutral desk fixture pack (sample-world + desk act) for
CI gates and local playtests. Neutral engine-test canon only."""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

DESK = {
    "opening": "The desk opens after the quiet. Rumors are the only wire left; judging them is the whole job.",
    "headlines": [
        "FIRST LIGHT OVER THE EMPTY MARKET",
        "TRAVELERS REPORT SONG AT THE FLOODED CROSSING",
    ],
}


def build(dest: Path) -> Path:
    pack = dest / "worlds" / "desk-test"
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)
    act_json = pack / "acts" / "act-1" / "world.json"
    data = json.loads(act_json.read_text(encoding="utf-8"))
    data.update({"ruleset": "desk", "tone": "deadpan", "desk": DESK})
    act_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return pack


if __name__ == "__main__":
    target = Path(sys.argv[1])
    print(str(build(target)))
