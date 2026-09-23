"""The desk loop, played end to end by the harness (pleasant-loop
protocol, mechanical half for Act 2)."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "desk_harness.mjs"
MAKE = ROOT / "tests" / "fixtures" / "make_desk_pack.py"


@pytest.fixture(scope="module")
def morning(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("desk-home")
    proc = subprocess.run(
        [sys.executable, str(MAKE), str(home)],
        capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    pack = Path(proc.stdout.strip())
    out = home / "desk.html"
    rc = cli.cmd_build_web(argparse_namespace(pack, out))
    assert rc == 0
    run = subprocess.run(
        ["node", str(HARNESS), str(out)],
        capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def argparse_namespace(pack: Path, out: Path):
    import argparse
    return argparse.Namespace(
        pack=str(pack), out=str(out), pool=4,
        with_bundle=False, from_live=None)


def _lines(morning):
    return {k: v for k, v in morning["log"]}


def test_the_desk_opens(morning):
    log = _lines(morning)
    assert log["headlines"] == 2
    assert "desk opens" in log["open"]


def test_a_whisper_is_judged_rightly(morning):
    log = _lines(morning)
    assert log["card"] is not None
    assert log["feed-cards"] == 1
    assert "rightly judged" in log["verdict-line"]
    kinds = [f.split(":")[0] for f in log["facts"]]
    assert kinds == ["confirmed" if log["card"]["is_true"] else "debunked"]


def test_printing_lands_on_the_wire(morning):
    log = _lines(morning)
    assert len(log["printed"]) == 1
    assert log["journal"] == ["desk_verdict", "printed"]


def test_verdict_buttons_lock_after_judging(morning):
    log = _lines(morning)
    assert log["buttons-disabled-after-verdict"] is True


def test_click_budget_stays_a_visit(morning):
    # enter + save + whisper + verdict + print = five clicks, whole loop
    assert morning["clicks"] <= 6, morning["clicks"]
