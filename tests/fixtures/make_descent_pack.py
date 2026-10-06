"""Build the neutral descent fixture pack (sample-world + a play-time descent).

Slice E1: floors sized by minutes to play them, generated at stair time
from a run seed. This fixture carries the pack's `descent` block - a run
seed, the entry tile in the town, and two Sections - over the sample
world's own town, so the generated floors are the only new thing in it.

Deliberately small: the floors are 32x24 to 36x26 with six to eight rooms,
because the play tests walk them tile by tile through the real player
and a 96x64 floor would take minutes per pass. That is as small as the one
Section contract allows - `SIZE` holds a width of 32 to 128 and a height
of 24 to 96, and `rooms` starts at 6. The engine's own size choices are
the pack's business, not the test's; the budgets are pinned with records
built for the large sizes in test_descent_deltas.py.

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

# The two Sections of the fixture descent, in the one Section contract
# (E4): `floors` is what `locate` walks, `size` and `rooms` are the
# play-time floor the plan stream draws from, and `families` names
# Blueprint families by id with a weight and a depth range - the Section
# carries no record of a family of its own, and how many monsters live on
# a floor is the generator's area budget, not a `mobs` key. Weights are
# on the family, never on the draw order, so a pack may list them in any
# order.
SECTIONS = [
    {
        "id": "cellar",
        "floors": 3,
        "size": {"w": [32, 36], "h": [24, 26]},
        "rooms": [6, 8],
        "fog": {"radius": 5},
        "pattern": ["entry", "landing", "warden"],
        "families": [
            {"family": "rat", "weight": 2, "depth": [1, 3]},
            {"family": "moth", "weight": 1, "depth": [1, 3]},
        ],
    },
    {
        "id": "hollow",
        "floors": 2,
        "size": {"w": [32, 34], "h": [24, 26]},
        "rooms": [6, 7],
        "fog": {"radius": 4},
        # No `pattern`: a Section that names none takes the engine's own,
        # and every floor here is an ordinary one. Naming two would force
        # three floors - two landings and a warden - on a Section the play
        # tests reach in two steps.
        "families": [
            {"family": "shade", "weight": 1, "depth": [1, 2]},
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