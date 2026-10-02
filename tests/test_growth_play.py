"""Growth, T3: played in the real woven file (jsdom). Levels: the rat's xp
becomes a level with a plain line. Practice: striking teaches attack, with no
experience shown. Fixture: tests/fixtures/make_growth_pack.py."""

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
HARNESS = ROOT / "tests" / "fixtures" / "growth_play_harness.mjs"


def play(tmp_path, mode, **build):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    out = tmp_path / f"{mode}.html"
    out.write_text(cli.weave_html(mk.build(tmp_path, **build)), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(out), mode],
                         capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stderr + run.stdout
    return json.loads(run.stdout)


def test_levels_mode_awards_xp_and_levels_up(tmp_path):
    r = play(tmp_path, "levels", growth=mk.LEVELS, xp=3, rat_hp=2)
    failed = [s["what"] for s in r["steps"] if not s["ok"]]
    assert r["allOk"] and len(r["steps"]) >= 7, failed


def test_practice_mode_grows_by_striking(tmp_path):
    r = play(tmp_path, "practice", growth=mk.PRACTICE, rat_hp=6)
    failed = [s["what"] for s in r["steps"] if not s["ok"]]
    assert r["allOk"] and len(r["steps"]) >= 5, failed
