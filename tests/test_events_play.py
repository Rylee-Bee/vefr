"""Every observable event, played: the REAL woven file, driven in jsdom.

The harness (tests/fixtures/events_play_harness.mjs) weaves the events
fixture pack (make_events_pack.py: the sample town, one chest with a
drop, one enemy with a drop, one shopkeeper, one rule per observable
event) and performs each player action through the path a player
uses: Interact on the chest, walking onto a fallen drop, bumping the
rat, using a kept tool, trading, closing a book, turning the watch.

Pinned here: the chest fires `opens` AND `picks-up` through the one
interaction path; every acquisition path fires `picks-up`; `takes`
removes; a kept tool stays; and the two evidence panels render only
real records. Deterministic: the fixture is fixed.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli, maplab

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "events_play_harness.mjs"
MAKE = ROOT / "tests" / "fixtures" / "make_events_pack.py"


@pytest.fixture(scope="module")
def play(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("events-home")
    made = subprocess.run(
        [sys.executable, str(MAKE), str(home)],
        capture_output=True, text=True, timeout=120)
    assert made.returncode == 0, made.stderr
    pack = Path(made.stdout.strip())
    # the fixture itself must pass the validator: the events and ids
    # it exercises are the contract, so green here is part of the pin
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []
    out = home / "events.html"
    out.write_text(cli.weave_html(pack), encoding="utf-8")
    run = subprocess.run(
        ["node", str(HARNESS), str(out)],
        capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stderr + run.stdout
    return json.loads(run.stdout)


def test_every_step_of_the_journey_held(play):
    failed = [s["what"] for s in play["steps"] if not s["ok"]]
    assert play["allOk"], failed
    assert len(play["steps"]) >= 8


def test_the_chest_fires_opens_and_picks_up(play):
    fired = play["fired"]
    assert "the-chest-was-opened" in fired
    assert "the-pebble-taken" in fired


def test_every_acquisition_path_fires_picks_up(play):
    # chest contents, a fallen drop, and a purchase
    fired = play["fired"]
    assert "the-pebble-taken" in fired      # the chest
    assert "the-drop-taken" in fired        # the floor
    assert "the-buying" in fired            # the shop


def test_defeats_takes_and_the_kept_tool(play):
    fired = play["fired"]
    assert "the-rat-fell" in fired
    assert "the-key-turned" in fired
    assert "the-note-closed" in fired
    assert "the-watch-turned" in fired
    # `takes` removed the key the `starts` rule gave
    assert "brass-key" not in play["bag"]
    # the gold moved both ways through the shop
    assert play["gold"] == 5


def test_the_evidence_panels_show_only_real_records(play):
    assert play["nextRows"] >= 1
    assert play["whyRows"] >= 8
    assert any(e["place"] == "town" for e in play["next"])
