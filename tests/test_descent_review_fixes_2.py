"""Round 3's descent finding: one floor key, one floor - across two sessions.

PLAN §2's identity rule says a floor is `(gen version, section content
hash, floor_key)` and every stream is named off that key, so the same key
draws the same floor, always. What the earlier tests never looked at is
what the SAVE has to remember about that floor: the monsters. The frozen
reload test compares grid rows and never reads the enemies snapshot, so a
floor whose monsters came back wrong after a reload passed it.

Both tests here are played through the REAL woven player in jsdom, in two
sessions with one save handed back in between, because that is what a
reload is:

1. the same floor key must draw the same monsters, same ids and same
   tiles, in a session that has the save and in one that does not;
2. a monster killed on a generated floor must still be dead when that
   save is handed to the next session - and the monsters that were never
   fought are still there.

The second is the round-2 assertion, kept because it is the property the
first one exists to protect: a kill list cannot be honoured by a session
that does not put the monster back.

Neither test reads the monsters out of the save. A session that is handed
a save reads it, plays it and walks on; what it is given is the browser's
own storage, which is the only thing a reload really hands back.
"""

import shutil

import pytest

import play_kit
from vefr import delve

from test_descent_deltas import TOWN, TOWN_HERO, _doc, _go
from test_descent_floors import DESCENT

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

# The snapshot both sessions are compared through: what is on the floor,
# who is on which tile, and who is standing. Read the same way, at the
# same moment in the same walk, in both sessions.
READS = ["VEFR_COMBAT.region", "VEFR_COMBAT.enemies",
         "VEFR_DESCENT.floor", "VEFR_DESCENT.doc", "store"]

PLAN = delve.floor_plan(DESCENT, 1)
MOB = PLAN["mobs"][0]


def _play(tmp_path, steps, store=None):
    """One session: weave the descent pack, plant `store` as the browser's
    own storage, and play `steps`."""
    html = play_kit.weave(play_kit.pack(tmp_path, "descent"), tmp_path)
    spec = {"steps": steps, "read": list(READS)}
    if store:
        spec["store"] = store
    return play_kit.play(html, spec)


def _enter():
    """Begin, walk out of the town and down the first stair. The hero
    arrives on the floor's own up-stair and goes no further, so the walk
    is the same in every session and nothing in it is a fight."""
    return ["begin", _go(TOWN, TOWN_HERO, DESCENT["entry"]["at"]),
            "click:#interact", "wait:150", "wait:200"]


def _roster(play):
    """The live roster: which monster, which tile, still standing.
    `VEFR_COMBAT.enemies` is the harness's window onto the fight, and it
    is the thing this finding was read off."""
    return [(e["id"], tuple(e["at"]), e["alive"])
            for e in play["reads"]["VEFR_COMBAT.enemies"]]


def _drawn(play):
    """The floor as it was drawn, before anyone walked on it: the key
    every monster came from, and the monsters themselves."""
    floor = play["reads"]["VEFR_DESCENT.floor"]
    return (floor["key"], [(m["id"], tuple(m["at"]), m["hp"]) for m in floor["mobs"]])


def test_two_sessions_one_save_draw_the_same_floor(tmp_path):
    first = _play(tmp_path, _enter())
    assert first["errors"] == [], first["errors"]
    assert first["reads"]["VEFR_COMBAT.region"] == "cellar-0-1"
    assert _roster(first), "the floor drew no monsters at all, so nothing here is proved"

    # The same floor key, the same save handed back in by the browser.
    again = _play(tmp_path, _enter(), store=first["store"])
    assert again["errors"] == [], again["errors"]
    assert again["reads"]["VEFR_COMBAT.region"] == "cellar-0-1"
    assert _drawn(again) == _drawn(first), \
        "the same floor key drew a different floor the second time"
    assert _roster(again) == _roster(first), \
        "the same floor key put the monsters on other tiles the second time"
    assert _drawn(again)[0] == delve.floor_key(
        DESCENT["run_seed"], "cellar", 0, 1), "the floor key moved, which is not the finding"


def test_a_monster_killed_on_a_generated_floor_stays_killed_after_a_reload(tmp_path):
    # The fight, planned against the very floor the generator drew. The
    # hero walks up the floor into the monster and bumps it, which is how
    # a fight starts in this game; the hero is atk 4 and this monster has
    # one hit point, so the bump is the whole fight.
    steps = ["begin", _go(TOWN, TOWN_HERO, DESCENT["entry"]["at"]),
             "click:#interact", "wait:150",
             _go(PLAN, PLAN["anchors"]["up"], MOB["at"],
                 [m["at"] for m in PLAN["mobs"] if m["at"] != MOB["at"]])]
    steps += ["wait:100"] * 8
    fought = _play(tmp_path, steps)
    assert fought["errors"] == [], fought["errors"]
    assert fought["reads"]["VEFR_COMBAT.region"] == "cellar-0-1"
    dead = [e for e in fought["reads"]["VEFR_COMBAT.enemies"] if not e["alive"]]
    assert [e["id"] for e in dead] == [MOB["id"]], \
        "the fight did not happen, so nothing after it is proved"
    assert _doc(fought)["floors"]["cellar-0-1"]["kills"] == [MOB["id"]], \
        "the save does not remember the kill, so the next session cannot honour it"

    # The next session, with that save handed back in. The hero walks in
    # and stops on the up-stair; it does not go looking for a fight, so
    # the floor it finds is the floor the save is about.
    again = _play(tmp_path, _enter(), store=fought["store"])
    assert again["errors"] == [], again["errors"]
    assert again["reads"]["VEFR_COMBAT.region"] == "cellar-0-1"
    drawn = again["reads"]["VEFR_DESCENT.floor"]["mobs"]
    assert [m["id"] for m in drawn] == [m["id"] for m in PLAN["mobs"]], \
        "the floor itself changed across the reload; that is a different finding"
    standing = {e["id"]: e for e in again["reads"]["VEFR_COMBAT.enemies"]}
    assert MOB["id"] in standing, "the floor does not hold the monster that was killed"
    assert standing[MOB["id"]]["alive"] is False, \
        "a monster killed on a generated floor is standing again after a reload"
    assert _doc(again)["floors"]["cellar-0-1"]["kills"] == [MOB["id"]], \
        "the save forgot the kill on the way back in"