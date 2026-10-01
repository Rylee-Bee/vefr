"""The hero's facing and step motion, in the woven player.

The step motion lives in the woven single-file player (`web/packaged.html`
- the file a player actually opens), not in the studio's `index.html`, so
this executes the real woven file in jsdom (the same dev-only harness
pattern as `tests/fixtures/combat_harness.mjs`) and reads the player's own
`window.VEFR_MOTION` snapshot and its pure `window.VEFR_STEP_MOTION`
helper. Nothing here depends on Playwright; the browser half of this
coverage lives in `tests/browser/`.

A short walk is run twice - once with motion on, once with
`prefers-reduced-motion: reduce` - to prove four things:

  (a) the hero faces all four directions, and a REFUSED move (a wall on
      every side, reached at different points of the walk) still turns
      the hero;
  (b) reduced motion is the identity for every progress and direction;
  (c) a step's offsets stay inside one tile of travel, a `STEP_HOP` bob,
      a `STEP_LEAN` lean and a 0..`STEP_SQUASH` squash, even for progress
      outside 0..1 (which clamps instead of running away);
  (d) the game is untouched by the hop: the `window.VEFR_COMBAT` snapshot
      after the walk is identical whether the hop ran or not.

Skips gracefully if node isn't installed, like the other node-vm tests.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "motion_harness.mjs"
MAKE = ROOT / "tests" / "fixtures" / "make_motion_pack.py"

# The enemy-free fixture floor (see make_motion_pack.py): one open room,
# the hero in the north-west corner. Every expected tile below is pinned.
START_HERO = [1, 1]

# The walk the harness makes, in order: (key, facing, hero tile). The
# first two and the last two are refused by a wall; the rest walk.
WALK = [
    ("ArrowUp", "up", [1, 1]),         # refused by the north wall
    ("ArrowLeft", "left", [1, 1]),     # refused by the west wall
    ("ArrowDown", "down", [1, 2]),
    ("ArrowUp", "up", [1, 1]),
    ("ArrowRight", "right", [2, 1]),   # the probe step (first hop)
    ("ArrowRight", "right", [3, 1]),
    ("ArrowRight", "right", [4, 1]),
    ("ArrowRight", "right", [5, 1]),
    ("ArrowRight", "right", [6, 1]),
    ("ArrowRight", "right", [7, 1]),
    ("ArrowRight", "right", [7, 1]),   # refused by the east wall
    ("ArrowDown", "down", [7, 2]),
    ("ArrowDown", "down", [7, 3]),
    ("ArrowDown", "down", [7, 3]),     # refused by the south wall
]
BLOCKED = {0, 1, 10, 13}   # walk indices whose tile does not change


@pytest.fixture(scope="module")
def motion(tmp_path_factory):
    """Build the fixture floor, weave it, run the player, return the report."""
    if shutil.which("node") is None:
        pytest.skip("node not installed - this repo's engine tests never require it")
    home = tmp_path_factory.mktemp("motion-home")
    made = subprocess.run(
        [sys.executable, str(MAKE), str(home)],
        capture_output=True, text=True, timeout=120)
    assert made.returncode == 0, made.stderr
    pack = Path(made.stdout.strip())
    out = home / "motion.html"
    rc = cli.cmd_build_web(argparse.Namespace(
        pack=str(pack), out=str(out), pool=0,
        with_bundle=False, from_live=None))
    assert rc == 0, "cmd_build_web failed"
    run = subprocess.run(
        ["node", str(HARNESS), str(out)],
        capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def _moves(report, mode):
    return [(m["key"], m["facing"], m["hero"], m["animating"])
            for m in report[mode]["moves"]]


# ---- (a) facing, including a refused move ----


def test_the_walk_starts_where_the_fixture_says(motion):
    assert motion["active"]["startHero"] == START_HERO
    assert motion["reduced"]["startHero"] == START_HERO


def test_the_hero_faces_every_direction_it_tries(motion):
    for mode in ("active", "reduced"):
        faced = [facing for _, facing, _, _ in _moves(motion, mode)]
        assert faced == [step[1] for step in WALK], mode
        assert set(faced) == {"up", "down", "left", "right"}, mode


def test_a_refused_move_still_turns_the_hero(motion):
    # Every walk step lands where the fixture says, blocked or not.
    for mode in ("active", "reduced"):
        got = [(key, hero) for key, _, hero, _ in _moves(motion, mode)]
        assert got == [(key, hero) for key, _, hero in WALK], mode

    # The refused steps left the hero standing (the tile before and after
    # are the same) yet still changed the facing - a wall or the map edge
    # turns the hero exactly like an open step does.
    for mode in ("active", "reduced"):
        moves = motion[mode]["moves"]
        for i in BLOCKED:
            before = START_HERO if i == 0 else WALK[i - 1][2]
            assert moves[i]["hero"] == before == WALK[i][2], (mode, i)
            assert moves[i]["facing"] == WALK[i][1], (mode, i)


# ---- (b) reduced motion is the identity ----


def test_reduced_motion_returns_the_identity(motion):
    step = motion["active"]["step"]
    assert step["samples"] >= 160, "too few progress values were probed"
    assert step["identityViolations"] == []


# ---- (c) the offsets are bounded ----


def test_a_step_stays_inside_its_bounds(motion):
    step = motion["active"]["step"]
    t = step["tile"]
    assert step["boundViolations"] == []
    assert step["maxDx"] <= t
    # An upward step's hop rides on top of its travel, so the whole
    # vertical offset is one tile plus at most the hop.
    assert step["maxDy"] <= t * (1 + step["hop"]) + 1e-9
    assert step["maxBob"] <= t * step["hop"] + 1e-9
    assert step["maxLean"] <= step["leanLimit"]
    assert 0 <= step["maxSquash"] <= step["squashLimit"] + 1e-9


# ---- (d) the game is identical with and without the hop ----


def test_the_combat_snapshot_is_the_same_with_or_without_the_hop(motion):
    # The same walk, the same fight: animation never delays or changes
    # game state.
    assert motion["active"]["combat"] == motion["reduced"]["combat"]
    assert motion["active"]["hero"] == motion["reduced"]["hero"]


def test_the_hop_runs_but_never_moves_the_game(motion):
    active = motion["active"]
    reduced = motion["reduced"]

    # Motion on: an open step starts a hop; a refused step does not.
    for i, move in enumerate(active["moves"]):
        assert move["animating"] == (i not in BLOCKED), i

    # Reduced motion: no hop ever starts.
    assert all(not move["animating"] for move in reduced["moves"])
    assert reduced["animating"] is False

    # Settled, the drawn tile is the game's tile in both modes.
    assert active["drawn"] == active["hero"]
    assert reduced["drawn"] == reduced["hero"]

    # Under reduced motion the drawn tile is the new tile AT ONCE (the
    # first eastward step lands on [2, 1] with no tween); with motion on
    # it is still on its way there.
    assert reduced["motionProbe"] == [2, 1]
    assert abs(active["motionProbe"][0] - 2) + abs(active["motionProbe"][1] - 1) > 0.1
