"""E8a part 1: a Section's warden (ADR 0015).

The warden floor - the pattern's `warden` slot - puts the warden the Section names on the v3 warden anchor as
monster `w`, outside the area budget, with its family's stats. Defeating it sets the permanent story flag
`warden:<id>:c<cycle>`, and a warden whose flag is set is not spawned again: clearing the floor's kills (which a
town return does) cannot revive it. The key it carries and `yields` are part 2. The JS twin is held equal by
tests/test_descent_parity.py (its Blueprint descent ends on a warden floor).
"""
import copy
import json
import shutil

import pytest

from vefr import delve
import play_kit
from test_descent_deltas import DOC_KEY, TOWN, TOWN_HERO, _doc, _go, _go_fight, _play
from test_descent_floors import DESCENT
from test_descent_parity import BLUEPRINT

WARDEN = "cellar-boss"


def _descent(warden=WARDEN, blueprint=None, families=None):
    """The fixture descent whose first Section (three floors) ends on a warden floor."""
    descent = copy.deepcopy(DESCENT)
    cellar = descent["sections"][0]
    cellar["pattern"] = ["entry", "n", "warden"]
    if warden is not None:
        cellar["warden"] = warden
    if families is not None:
        for section in descent["sections"]:
            section["families"] = families
    if blueprint is not None:
        descent["blueprint"] = blueprint
    return descent


def _wardens(plan):
    return [m for m in plan["mobs"] if m.get("warden")]


# ---- the plan ------------------------------------------------------------

def test_the_warden_floor_puts_the_warden_on_its_anchor():
    plan = delve.floor_plan(_descent(), 3)
    (warden,) = _wardens(plan)
    assert warden["id"] == "w" and warden["family"] == WARDEN
    assert warden["at"] == plan["anchors"]["warden"]
    assert plan["warden"] == {"id": WARDEN, "flag": f"warden:{WARDEN}:c0"}


def test_only_the_warden_floor_has_one():
    descent = _descent()
    for depth in (1, 2, 4, 5):
        plan = delve.floor_plan(descent, depth)
        assert not _wardens(plan) and plan["warden"] is None, depth


def test_the_flag_names_the_cycle():
    plan = delve.floor_plan(_descent(), 8)          # cycle 1, the cellar's third floor
    assert plan["cycle"] == 1 and plan["warden"]["flag"] == f"warden:{WARDEN}:c1"


def test_a_section_that_names_no_warden_has_none_on_its_warden_floor():
    plan = delve.floor_plan(_descent(warden=None), 3)
    assert not _wardens(plan) and plan["warden"] is None


def test_the_warden_is_outside_the_budget_and_moves_no_other_monster():
    with_warden = delve.floor_plan(_descent(), 3)
    without = delve.floor_plan(_descent(warden=None), 3)
    anchor = with_warden["anchors"]["warden"]
    assert [m for m in with_warden["mobs"] if not m.get("warden")] == \
        [m for m in without["mobs"] if m["at"] != anchor]


def test_the_warden_has_its_familys_stats():
    plan = delve.floor_plan(_descent(warden="gutter-rat", blueprint=BLUEPRINT), 3)
    (warden,) = _wardens(plan)
    # gutter-rat extends rat and overrides only hp
    assert (warden["name"], warden["hp"], warden["atk"], warden["sight"]) == ("a grey rat", 9, 2, 5)
    assert warden["drops"] == ["pebble"]


# ---- in play (the woven player in jsdom) -----------------------------------

pytestmark_play = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

QUIET = _descent(families=[])          # nothing but the warden lives on these floors


def _down_to(depth):
    steps = ["begin", _go(TOWN, TOWN_HERO, QUIET["entry"]["at"]), "click:#interact", "wait:150"]
    for d in range(1, depth):
        plan = delve.floor_plan(QUIET, d)
        steps += [_go(plan, plan["anchors"]["up"], plan["anchors"]["down"]), "click:#interact", "wait:150"]
    return steps


@pytestmark_play
def test_beating_the_warden_sets_its_flag_and_it_stays_beaten(tmp_path):
    patch = {"world.json": {"descent": QUIET}}
    plan = delve.floor_plan(QUIET, 3)
    (warden,) = _wardens(plan)
    fought = _play(tmp_path, _down_to(3) + [_go_fight(plan, warden)] + ["wait:100"] * 6, patch=patch)
    assert fought["errors"] == [], fought["errors"]
    assert fought["reads"]["VEFR_COMBAT.region"] == plan["name"]
    doc = _doc(fought)
    assert doc["flags"].get(plan["warden"]["flag"]) is True, doc["flags"]

    # Wipe the floor's kills, as a town return does: the flag alone must keep it beaten.
    doc["floors"][plan["name"]]["kills"] = []
    store = dict(fought["store"])
    store[DOC_KEY] = json.dumps(doc)
    html = play_kit.weave(play_kit.pack(tmp_path / "again", "descent", patch=patch), tmp_path / "again")
    again = play_kit.play(html, {"steps": _down_to(3), "store": store,
                                 "read": ["VEFR_COMBAT.region", "VEFR_ENEMIES"]})
    assert again["errors"] == [], again["errors"]
    assert again["reads"]["VEFR_COMBAT.region"] == plan["name"]
    live = again["reads"]["VEFR_ENEMIES"][plan["name"]]
    assert all(e["id"] != "w" for e in live), live

    # And the control: with the flag cleared too, the same floor brings it back.
    doc["flags"].pop(plan["warden"]["flag"])
    store[DOC_KEY] = json.dumps(doc)
    control = play_kit.play(html, {"steps": _down_to(3), "store": store,
                                   "read": ["VEFR_ENEMIES"]})
    assert any(e["id"] == "w" for e in control["reads"]["VEFR_ENEMIES"][plan["name"]])
