"""E8b part 1: the vault door (ADR 0015).

The warden floor's vault stamp has one door - the socket its corridor came in by. In play it is shut (`+`, solid)
until the Section's warden is beaten, says who holds the key when bumped, and opens in place the moment the warden
falls: the same floor, so nothing respawns. On a later visit the warden's flag keeps it open. The plan's own rows
never carry the door; both languages agree on the plan's `vault` record (tests/test_descent_parity.py).
"""
import copy
import json
import shutil
from pathlib import Path

import pytest

import play_kit
from vefr import delve, stamps
from test_descent_deltas import TOWN, TOWN_HERO, _go, _go_fight, _path
from test_descent_floors import DESCENT

STAMPS = Path(__file__).resolve().parent / "fixtures" / "stamps"
RECORDS = json.loads(json.dumps(stamps.load(STAMPS)))


def _descent(warden="cellar-boss"):
    out = copy.deepcopy(DESCENT)
    cellar = out["sections"][0]
    cellar.update({"pattern": ["entry", "n", "warden"], "stamps": ["cellar"], "vault": "vault-cellar"})
    if warden:
        cellar["warden"] = warden
    for section in out["sections"]:
        section["families"] = []           # nothing but the warden lives here
    return out


def test_the_warden_floor_has_a_vault_and_no_other_floor_does():
    descent = {**_descent(), "stamps": RECORDS}
    assert delve.floor_plan(descent, 1)["vault"] is None
    plan = delve.floor_plan(descent, 3)
    vault = plan["vault"]
    assert vault["stamp"] == "vault-cellar" and vault["flag"] == "warden:cellar-boss:c0"
    x, y = vault["door"]
    assert plan["rows"][y][x] == ".", "the plan's rows never carry the shut door"
    assert all(vault[k] for k in ("note", "chest", "home"))


def test_with_no_warden_the_vault_is_not_locked():
    plan = delve.floor_plan({**_descent(warden=None), "stamps": RECORDS}, 3)
    assert plan["vault"]["flag"] is None


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_door_is_shut_until_the_warden_falls_then_opens_in_place(tmp_path):
    descent = _descent()
    pack = play_kit.pack(tmp_path / "pack", "descent", patch={"world.json": {"descent": descent}})
    shutil.copytree(STAMPS, Path(pack) / "stamps")
    html = play_kit.weave(pack, tmp_path)
    woven = {**descent, "stamps": RECORDS}
    plan = delve.floor_plan(woven, 3)
    door, home = plan["vault"]["door"], plan["vault"]["home"]
    (warden,) = [m for m in plan["mobs"] if m.get("warden")]
    down = ["begin", _go(TOWN, TOWN_HERO, descent["entry"]["at"]), "click:#interact", "wait:150"]
    for d in (1, 2):
        p = delve.floor_plan(woven, d)
        down += [_go(p, p["anchors"]["up"], p["anchors"]["down"]), "click:#interact", "wait:150"]
    to_door = _path(plan, plan["anchors"]["up"], door, [warden["at"]])
    assert to_door, "no way to the vault door"
    region = f"VEFR_REGIONS.{plan['name']}.map"

    # Session one: bump the shut door (stay outside), then beat the warden; the door opens at once.
    bump = down + ["walk:" + ",".join(to_door), "wait:100"]
    shut = play_kit.play(html, {"steps": bump, "read": [region, "VEFR_COMBAT.hero"]})
    assert shut["errors"] == [], shut["errors"]
    assert shut["reads"][region][door[1]][door[0]] == "+"
    assert shut["reads"]["VEFR_COMBAT.hero"]["at"] != door, "the hero walked through a shut door"

    fight = down + [_go_fight(plan, warden)] + ["wait:100"] * 6
    opened = play_kit.play(html, {"steps": fight, "read": [region, "store"]})
    assert opened["errors"] == [], opened["errors"]
    assert opened["reads"][region][door[1]][door[0]] == "."

    # Session two, from that save: the flag keeps the door open, and the hero walks through to the vault.
    inside = _path(plan, plan["anchors"]["up"], home, [warden["at"]])
    walked = play_kit.play(html, {"steps": down + ["walk:" + ",".join(inside), "wait:100"],
                                  "store": opened["store"], "read": [region, "VEFR_COMBAT.hero"]})
    assert walked["errors"] == [], walked["errors"]
    assert walked["reads"][region][door[1]][door[0]] == "."
    assert walked["reads"]["VEFR_COMBAT.hero"]["at"] == home
