"""Build the neutral kitchen fixture pack (sample-world + cooking act)
at a target directory, for CI gates (a11y, visual) and local playtests.

The canon here is deliberately NEUTRAL engine-test fiction - the same
block tests/test_kitchen_loop.py pins. Burrito Journalism's real canon
lives in its own repo and its own PRs.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

COOKING = {
    "opening": "Day one after the quiet. The grill remembers heat before anyone does.",
    "byline": "by the morning truck",
    "pantry": [
        {"id": "egg", "label": "fried egg"},
        {"id": "salsa", "label": "red salsa"},
        {"id": "potato", "label": "crisp potato"},
        {"id": "cheese", "label": "melted cheese"},
    ],
    "tickets": [
        {
            "id": "t1", "customer": "the regular", "order": ["egg", "salsa"],
            "note": "The usual. Egg, and the red one that bites.",
            "thanks": "The regular eats standing up, already turning toward the day.",
            "kind_line": "The regular eats it anyway, nodding at something only they can see.",
        },
        {
            "id": "t2", "customer": "the scout", "order": ["potato", "egg", "cheese"],
            "note": "Something that survives a walk. Crisp thing, egg, the melt.",
            "thanks": "The scout wraps the last bite for the road, grinning.",
            "kind_line": "The scout laughs: tastes like a mistake I'd make again.",
        },
        {
            "id": "t3", "customer": "a stranger", "order": ["cheese"],
            "note": "Warm. Only warm. The melt, if the melt is kind today.",
        },
    ],
    "morning_length": 3,
    "headlines": [
        "FIRST TRUCK ON THE ROAD SERVES BREAKFAST AGAIN",
        "TRAVELERS SEEN AT THE FLOODED CROSSING; SOMEONE HAS LEFT FLOWERS",
    ],
}


def build(dest: Path) -> Path:
    pack = dest / "worlds" / "kitchen-test"
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)
    act_json = pack / "acts" / "act-1" / "world.json"
    data = json.loads(act_json.read_text(encoding="utf-8"))
    data.update({
        "ruleset": "cooking", "tone": "warm", "floor": "costume",
        "cooking": COOKING,
    })
    act_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return pack


if __name__ == "__main__":
    target = Path(sys.argv[1])
    pack = build(target)
    print(str(pack))
