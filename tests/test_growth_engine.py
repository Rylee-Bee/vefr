"""Growth, T2: the pure maths, played inside the real woven file.
Numbers are pinned in design/growth.md; the harness prints, this asserts."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
import make_growth_pack as mk  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "growth_engine_harness.mjs"


@pytest.fixture(scope="module")
def r(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("growth-engine")
    out = home / "g.html"
    out.write_text(cli.weave_html(mk.build(home, growth=mk.LEVELS, xp=3)),
                   encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(out)],
                         capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stderr + run.stdout
    return json.loads(run.stdout)


def test_engine_exists(r):
    assert r["hasEngine"] is True


def test_level_from_xp_table(r):
    assert r["levelFor"] == [1, 1, 2, 2, 3, 4]


def test_level_stats(r):
    assert r["statsLevels"][0] == {"level": 1, "hp": 0, "atk": 0}
    assert r["statsLevels"][1] == {"level": 3, "hp": 4, "atk": 2}


def test_award(r):
    one = r["awardOne"]
    assert one["state"]["xp"] == 13 and one["level"] == 2
    assert one["levelsGained"] == 1 and one["grew"] == {"hp": 2, "atk": 1}
    two = r["awardTwo"]
    assert two["state"]["xp"] == 28 and two["level"] == 3
    assert two["levelsGained"] == 2 and two["grew"] == {"hp": 4, "atk": 2}
    for k in ("awardZero", "awardNeg"):
        assert r[k]["state"]["xp"] == 8 and r[k]["levelsGained"] == 0
        assert r[k]["grew"] == {"hp": 0, "atk": 0}


def test_practice_stats_and_cap(r):
    assert r["statsPractice"]["atk"] == 2 and r["statsPractice"]["hp"] == 1
    assert r["statsPractice"]["level"] is None
    assert r["statsCapped"]["atk"] == 2          # cap holds at 100 strikes


def test_practice_bump_grows_every_third_strike(r):
    assert r["bumps"] == [[], [], [{"stat": "atk", "gain": 1}]]
    assert r["bumpState"]["counts"]["strikes"] == 3


def test_bump_ignores_other_modes_and_unknown_kinds(r):
    assert r["bumpLevelsMode"]["grown"] == []
    assert r["bumpLevelsMode"]["state"] == {"xp": 0, "counts": {}}
    assert r["bumpUnknown"]["grown"] == []


def test_no_growth_and_bad_state_are_harmless(r):
    assert r["nullStats"] == {"level": None, "hp": 0, "atk": 0}
    assert r["nullAward"]["state"]["xp"] == 5 and r["nullAward"]["levelsGained"] == 0
    assert r["badState"] == {"level": 1, "hp": 0, "atk": 0}
    assert r["nullState"] == {"level": 1, "hp": 0, "atk": 0}


def test_a_short_table_clamps(r):
    assert r["shortTable"] == {"level": 2, "hp": 1, "atk": 0}
