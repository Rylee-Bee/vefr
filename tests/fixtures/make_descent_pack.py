"""Build the neutral descent fixture pack (sample-world + a play-time descent).

Slice E1: floors sized by minutes to play them, generated at stair time
from a run seed. This fixture carries the pack's `descent` block - a run
seed, the entry tile in the town, and two Sections - over the sample
world's own town, so the generated floors are the only new thing in it.

Deliberately small: the floors are 28x20 to 36x24 with five to eight rooms,
because the play tests walk them tile by tile through the real player
and a 96x64 floor would take minutes per pass. The engine's own size
choices are the pack's business, not the test's; the budgets are pinned
with records built for the large sizes in test_descent_deltas.py.

Neutral engine-test canon only: the hazards are named creatures and the
places are a town and a cellar, exactly as the other fixtures are.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

# The sample town's own threshold tile. The hero wakes at [3, 4] and
# walks four tiles to stand on it; the descent's entry is that tile.
ENTRY_AT = [7, 5]

# The two Sections of the fixture descent. `floors` is what `locate`
# walks; `size` and `rooms` are the play-time floor the plan stream
# draws from; `mobs` is how many live on it. Weights are on the family,
# never on the draw order, so a pack may list them in any order.
SECTIONS = [
    {
        "id": "cellar",
        "title": "The Cellar",
        "floors": 3,
        "size": {"w": [28, 36], "h": [20, 24]},
        "rooms": [6, 8],
        "mobs": [1, 2],
        "fog": {"radius": 5},
        "pattern": ["entry", "n", "warden"],
        "families": [
            {"id": "rat", "name": "a cellar rat", "weight": 2,
             "hp": [1, 2], "atk": 1, "sight": 4, "drops": ["pebble"]},
            {"id": "moth", "name": "a pale moth", "weight": 1,
             "hp": [1, 1], "atk": 1, "sight": 4, "drops": []},
        ],
    },
    {
        "id": "hollow",
        "title": "The Hollow",
        "floors": 2,
        "size": {"w": [28, 32], "h": [20, 22]},
        "rooms": [5, 7],
        "mobs": [1, 2],
        "fog": {"radius": 4},
        "pattern": ["entry", "n"],
        "families": [
            {"id": "shade", "name": "a hollow shade", "weight": 1,
             "hp": [1, 2], "atk": 1, "sight": 4, "drops": []},
        ],
    },
]

ITEMS = {
    "pebble": {"name": "a grey pebble", "value": 1},
}

# The hero is patient on purpose: the play tests walk into monsters on
# the way to the stair, and a wake at the town's own start would end the
# descent halfway. Health is not what this slice is testing.
PLAYER = {"hp": 40, "atk": 4, "gold": 0}


def build(dest: Path, descent=None) -> Path:
    pack = dest / "worlds" / "descent-test"
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)

    world_json = pack / "world.json"
    world = json.loads(world_json.read_text(encoding="utf-8"))
    world["items"] = ITEMS
    world["player"] = dict(PLAYER, wake={"region": "town", "at": [3, 4]})
    if descent is None:
        descent = {
            # The same run seed the Python-side tests walk, so a plan
            # computed in Python is the floor the woven player draws.
            "run_seed": "run-a",
            "entry": {"region": "town", "at": list(ENTRY_AT)},
            "sections": SECTIONS,
        }
    world["descent"] = descent
    world_json.write_text(json.dumps(world), encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))