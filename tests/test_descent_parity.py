"""Play-time floors, R: the JavaScript twin answers exactly what Python answers.

The player is one static HTML file, so the descent is walked in the
browser and Python is only the reference. This replays `locate` and the
whole floor plan (size, rooms, rows, stairs, mobs, identity) for a dozen
depths and two runs through the REAL woven player in jsdom
(`window.VEFR_DESCENT`) and demands identical answers, in both
directions: nothing may be in one language and not the other.
"""

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from vefr import cli, delve
from test_descent_floors import DESCENT

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "descent_parity_harness.mjs"
DEPTHS = list(range(1, 13))
RUNS = [0, 1, 2]


@pytest.fixture(scope="module")
def replay(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("descent-parity")
    html = home / "p.html"
    html.write_text(cli.weave_html(ROOT / "worlds" / "sample-world"), encoding="utf-8")
    cases = home / "cases.json"
    cases.write_text(json.dumps({"descent": DESCENT, "depths": DEPTHS,
                                 "runs": RUNS}), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(html), str(cases)],
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr + run.stdout
    return json.loads(run.stdout)


def _canonical(value):
    return json.dumps(value, sort_keys=True)


def test_the_twin_exists(replay):
    assert replay["hasApi"] is True


def test_locate_matches_for_every_depth(replay):
    got = replay["located"]
    assert len(got) == len(DEPTHS)
    for depth, answer in zip(DEPTHS, got):
        cycle, section, k = delve.locate(depth, DESCENT)
        assert answer == [cycle, section["id"], k], depth


def test_the_whole_floor_matches_field_for_field(replay):
    got = replay["plans"]
    assert len(got) == len(DEPTHS) + len(RUNS)
    for depth, plan in zip(DEPTHS, got):
        want = delve.floor_plan(DESCENT, depth)
        assert _canonical(plan) == _canonical(want), depth


def test_a_second_run_is_another_floor_on_both_sides(replay):
    got = replay["plans"][len(DEPTHS):]
    for run, plan in zip(RUNS, got):
        descent = copy.deepcopy(DESCENT)
        want = delve.floor_plan(descent, 1, run=run)
        assert _canonical(plan) == _canonical(want), run


def test_the_plan_carries_no_grid_in_its_identity(replay):
    for plan in replay["plans"]:
        assert set(plan["identity"]) == {"gen", "hash", "key"}
        assert plan["name"] == plan["name"].lower()