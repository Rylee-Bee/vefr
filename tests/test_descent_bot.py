"""Acceptance 4: three generated floors, played end to end through the player.

The player-level proof is the Cottage bot, in the private pack's
`tests/playthrough/`, which this clone cannot run. This is the
engine-side equivalent the slice plan asks for instead: the REAL woven
file in jsdom, a scripted player who walks out of the town and down three
floors that were never baked, using nothing but the pad and the Interact
button - the same path a person takes.

The descent here has nothing living on it, so that the walk a test
performs is the walk the generator drew and not a detour around a fight;
the fight on a generated floor is proved in test_descent_deltas.py.
"""

import copy
import json
import shutil

import pytest

import play_kit
from vefr import delve

from test_descent_deltas import DOC_KEY, _descend, _doc, _go
from test_descent_floors import DESCENT

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

FLOORS = 3


def _quiet_descent():
    """The fixture's own descent with nothing living on the floors."""
    descent = copy.deepcopy(DESCENT)
    for section in descent["sections"]:
        # No family, no monster: the count is generator policy, so the old
        # `mobs: [0, 0]` here was never read, and the walk passed only because
        # no v2 monster stood on it (a v3 floor put one there, 2026-10-09).
        section["families"] = []
    return descent


def _patch(built):
    """A pack whose descent is the quiet one (play_kit's merge replaces lists)."""
    return {"world.json": {"descent": _quiet_descent()}}


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("descent-bot")
    pack = play_kit.pack(home, "descent", patch=_patch(None))
    html = play_kit.weave(pack, home)
    # Down three floors, and then the third one is walked to its stair and
    # back: a floor the hero only stood on has not been played.
    last = delve.floor_plan(_quiet_descent(), FLOORS)
    steps = _descend(FLOORS, avoid_mobs=False)
    steps.append(_go(last, last["anchors"]["up"], last["anchors"]["down"]))
    steps.append(_go(last, last["anchors"]["down"], last["anchors"]["up"]))
    play = play_kit.play(html, {"steps": steps,
                                "read": ["VEFR_COMBAT.region",
                                         "VEFR_DESCENT.floor", "store"]})
    return steps, play


def test_the_bot_played_the_three_floors_without_a_single_error(run):
    _steps, play = run
    assert play["errors"] == [], play["errors"]
    assert play["reads"]["VEFR_COMBAT.region"] == "cellar-0-%d" % FLOORS


def test_all_three_floors_are_remembered_and_were_walked(run):
    _steps, play = run
    doc = _doc(play)
    assert doc["order"] == ["cellar-0-1", "cellar-0-2", "cellar-0-3"], doc["order"]
    for depth in range(1, FLOORS + 1):
        record = doc["floors"]["cellar-0-%d" % depth]
        assert record["n"] == depth
        assert record["fog"], "floor %d was walked but nothing was kept" % depth
        assert record["kills"] == []
    # The hero arrived on each floor at its up-stair and walked to the
    # down-stair, so each floor's memory is a real walk and not one tile.
    for depth in range(1, FLOORS + 1):
        plan = delve.floor_plan(_quiet_descent(), depth)
        assert _lit(plan, doc["floors"]["cellar-0-%d" % depth]["fog"],
                    plan["anchors"]["down"]), depth


def test_three_generated_floors_are_three_different_floors(run):
    _steps, play = run
    plans = [delve.floor_plan(_quiet_descent(), d)
             for d in range(1, FLOORS + 1)]
    assert len({p["key"] for p in plans}) == FLOORS
    assert len({tuple(p["rows"]) for p in plans}) == FLOORS


def test_the_bot_left_a_save_a_person_can_keep(run):
    _steps, play = run
    raw = play["store"][DOC_KEY]
    assert len(raw.encode("utf-8")) <= delve.SAVE_BYTES
    doc = json.loads(raw)
    assert doc["card"] == delve.GEN_VERSION
    assert doc["seed"] == _quiet_descent()["run_seed"]


def _lit(plan, fog, tile):
    """Whether the explored bitset says the hero saw this tile."""
    import base64
    raw = base64.b64decode(fog)
    i = tile[1] * plan["w"] + tile[0]
    return bool(raw[i >> 3] & (1 << (7 - (i & 7))))