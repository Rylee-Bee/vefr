"""Random floors, R2: the JavaScript twin draws exactly the rows Python draws.

The player is one static HTML file, so a run's floors are drawn in the browser. Python is the
reference; this replays 50 floors and a set of random streams through the REAL woven player
in jsdom (`window.VEFR_DELVE.prng` and `.generateFloorV2`) and demands identical results.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from vefr import cli, delve

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "floor_v2_parity_harness.mjs"

SIZES = [(30, 20, 8), (48, 32, 10), (20, 20, 3), (64, 64, 16), (40, 28, 9)]
SEEDS = ["a", "cottage", "run-0001:floor-1", "run-0001:floor-2", "Ünïcode ☕", "", "x" * 40,
         "seed-7", "seed-8", "9"]


@pytest.fixture(scope="module")
def replay(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("parity")
    html = home / "p.html"
    html.write_text(cli.weave_html(ROOT / "worlds" / "sample-world"), encoding="utf-8")
    floors = [{"seed": s, "width": w, "height": h, "rooms": r}
              for s in SEEDS for (w, h, r) in SIZES]
    prng = [{"seed": s, "count": 40} for s in SEEDS]
    cases = home / "cases.json"
    cases.write_text(json.dumps({"prng": prng, "floors": floors}), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(html), str(cases)],
                         capture_output=True, text=True, timeout=240)
    assert run.returncode == 0, run.stderr + run.stdout
    return floors, prng, json.loads(run.stdout)


def test_the_twin_exists(replay):
    assert replay[2]["hasApi"] is True


def test_the_streams_match(replay):
    _, prng, out = replay
    assert len(out["prng"]) == len(prng) == len(SEEDS)     # a missing twin must not pass by checking nothing
    for case, got in zip(prng, out["prng"]):
        rng = delve.prng(case["seed"])
        assert got == [rng() for _ in range(case["count"])], case["seed"]


def test_the_floors_match_row_for_row(replay):
    floors, _, out = replay
    assert len(out["floors"]) == len(floors) == len(SEEDS) * len(SIZES) == 50
    for case, rows in zip(floors, out["floors"]):
        want = delve.generate_floor_v2(case["seed"], case["width"], case["height"], case["rooms"])
        assert rows == want, case
