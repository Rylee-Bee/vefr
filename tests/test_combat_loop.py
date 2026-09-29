"""The combat loop, mechanical half (pleasant-loop protocol).

The combat harness EXECUTES the woven single-file player against a stub
DOM and plays the first fight end to end: bump the adjacent enemy, watch
it hit back, kill it and see it stay dead, watch a distant enemy inside
its sight step toward the hero, then take a fatal blow and wake whole at
the baked wake point. Deterministic: the fixture is fixed, so every
number here is pinned.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "combat_harness.mjs"
MAKE = ROOT / "tests" / "fixtures" / "make_combat_pack.py"

DEATH_LINE = "You wake in the temple. You lost nothing that mattered."


@pytest.fixture(scope="module")
def fight(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("combat-home")
    made = subprocess.run(
        [sys.executable, str(MAKE), str(home)],
        capture_output=True, text=True, timeout=120)
    assert made.returncode == 0, made.stderr
    pack = Path(made.stdout.strip())
    out = home / "combat.html"
    rc = cli.cmd_build_web(_args(pack, out))
    assert rc == 0
    run = subprocess.run(
        ["node", str(HARNESS), str(out)],
        capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def _args(pack: Path, out: Path):
    import argparse
    return argparse.Namespace(
        pack=str(pack), out=str(out), pool=0,
        with_bundle=False, from_live=None)


def _log(fight):
    return {k: v for k, v in fight["log"]}


def _by_id(snapshot):
    return {e["id"]: e for e in snapshot["enemies"]}


def test_the_fight_starts_where_the_fixture_says(fight):
    log = _log(fight)
    start = log["start"]
    assert start["region"] == "town"
    assert start["hero"] == {"hp": 3, "max": 3, "atk": 2, "at": [1, 1]}
    assert log["hp-line0"] == "3/3"
    rat = _by_id(start)["cellar-rat"]
    assert rat == {"id": "cellar-rat", "at": [2, 1], "hp": 4, "atk": 1,
                   "sight": 6, "alive": True}
    pale = _by_id(start)["pale-thing"]
    assert pale["at"] == [7, 1] and pale["atk"] == 2 and pale["sight"] == 6


def test_a_bump_attacks_and_the_answer_lands(fight):
    log = _log(fight)
    after = log["after-bump1"]
    # The hero did not move; the rat lost 2 hp and hit back for 1.
    assert after["hero"]["hp"] == 2
    assert after["hero"]["at"] == [1, 1]
    rat = _by_id(after)["cellar-rat"]
    assert rat["hp"] == 2 and rat["alive"] is True
    assert log["said-bump1"] == "a cellar rat hits you for 1."
    assert log["hp-line1"] == "2/3"


def test_a_killed_enemy_stays_dead(fight):
    log = _log(fight)
    after = log["after-bump2"]
    rat = _by_id(after)["cellar-rat"]
    assert rat["alive"] is False and rat["hp"] == 0
    assert "a cellar rat falls." in log["said-bump2"]
    assert json.loads(log["slain-after-kill"]) == ["cellar-rat"]


def test_an_enemy_in_sight_steps_toward_the_hero(fight):
    log = _log(fight)
    # Six tiles away at the start; one step per hero action, larger axis
    # first. Two hero actions bring it from x=7 to x=5.
    assert _by_id(log["after-bump1"])["pale-thing"]["at"] == [6, 1]
    assert _by_id(log["after-bump2"])["pale-thing"]["at"] == [5, 1]


def test_death_is_cozy_and_the_hero_wakes_whole(fight):
    log = _log(fight)
    after = log["after-death"]
    assert after["region"] == "town"
    assert after["hero"] == {"hp": 3, "max": 3, "atk": 2, "at": [1, 1]}
    assert log["hp-line-death"] == "3/3"
    assert log["said-death"] == DEATH_LINE
    # The fallen rat is still remembered; the other one is whole again.
    assert _by_id(after)["cellar-rat"]["alive"] is False
    assert _by_id(after)["pale-thing"] == {
        "id": "pale-thing", "at": [7, 1], "hp": 4, "atk": 2,
        "sight": 6, "alive": True}


def test_no_timers_anywhere(fight):
    assert fight["setIntervalInTemplate"] is False
