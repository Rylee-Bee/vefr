"""The pleasant-loop protocol, mechanical half (owner directive:
"test regularly to see if it's actually a pleasant loop - I don't
wanna make a dud").

The kitchen harness EXECUTES the woven single-file player against a
stub DOM and plays one cooking morning end to end: read the rail,
wrap an order from the customer's spoken note, serve, miss on
purpose, set a ticket aside, print the morning page, sleep, wake.
These pins assert the loop actually looped - journal order, kind
beats on mistakes, the printed page, the click budget, and the
absence of timers. The felt half lives in the playtest notes pasted
per increment (VEFR-ACT1-SPEC-2026-09-22.md §9).
"""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "worlds" / "sample-world"
HARNESS = ROOT / "tests" / "fixtures" / "kitchen_harness.mjs"

COOKING = {
    "opening": "Day one after the quiet. The grill remembers heat before anyone does.",
    "pantry": [
        {"id": "egg", "label": "fried egg"},
        {"id": "salsa", "label": "red salsa"},
        {"id": "potato", "label": "crisp potato"},
        {"id": "cheese", "label": "melted cheese"},
    ],
    "tickets": [
        {
            "id": "t1", "customer": "the regular", "order": ["egg", "salsa"],
            "note": "The usual. Egg, and the red one that bites.",
            "thanks": "The regular eats standing up, already turning toward the day.",
            "kind_line": "The regular eats it anyway, nodding at something only they can see.",
        },
        {
            "id": "t2", "customer": "the scout", "order": ["potato", "egg", "cheese"],
            "note": "Something that survives a walk. Crisp thing, egg, the melt.",
            "thanks": "The scout wraps the last bite for the road, grinning.",
            "kind_line": "The scout laughs: tastes like a mistake I'd make again.",
        },
        {
            "id": "t3", "customer": "a stranger", "order": ["cheese"],
            "note": "Warm. Only warm. The melt, if the melt is kind today.",
        },
    ],
    "morning_length": 3,
    "byline": "by the morning truck",
    "headlines": [
        "FIRST TRUCK ON THE ROAD SERVES BREAKFAST AGAIN",
        "PLAYERS SEEN AT THE FLOODED POOL; SOMEONE HAS LEFT FLOWERS",
    ],
}


@pytest.fixture(scope="module")
def morning(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("kitchen-home")
    pack = home / "worlds" / "kitchen-test"
    shutil.copytree(SAMPLE, pack)
    act_json = pack / "acts" / "act-1" / "world.json"
    data = json.loads(act_json.read_text(encoding="utf-8"))
    data.update({"ruleset": "cooking", "tone": "warm", "floor": "costume",
                 "cooking": COOKING})
    act_json.write_text(json.dumps(data), encoding="utf-8")
    out = home / "kitchen.html"
    rc = cli.cmd_build_web(argparse.Namespace(
        pack=str(pack), out=str(out), pool=0,
        with_bundle=False, from_live=None))
    assert rc == 0
    proc = subprocess.run(
        ["node", str(HARNESS), str(out)],
        capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _lines(morning):
    return {k: v for k, v in morning["log"]}


def test_the_morning_loops(morning):
    log = _lines(morning)
    assert log["journal"] == [
        "ticket_served", "ticket_corrected", "ticket_set_aside",
        "headline_printed"]
    assert log["tickets"] == 3
    assert log["headlines-visible"] is True
    assert log["headline-count"] == 2
    assert log["page-visible"] is True


def test_kind_beats_not_slaps(morning):
    log = _lines(morning)
    assert log["serve1"] == COOKING["tickets"][0]["thanks"]
    assert log["serve2-wrong"] == COOKING["tickets"][1]["kind_line"]
    # the set-aside beat survives the morning ending into the page ask
    assert "no one hurries" in log["aside3"]
    assert "morning is over" in log["aside3"]


def test_the_page_reads_like_a_paper(morning):
    log = _lines(morning)
    page = log["page-text"]
    assert COOKING["byline"] in page
    assert COOKING["headlines"][1] in page
    assert "the regular was fed" in page
    assert "they ate it anyway" in page
    assert "waited behind the glass" in page


def test_click_budget_stays_a_visit(morning):
    clicks = morning["clicks"]
    assert clicks["t1"] <= 4, clicks
    assert clicks["t2"] <= 4, clicks


def test_no_timers_anywhere(morning):
    assert morning["setIntervalInTemplate"] is False


def test_sleep_wakes_a_fresh_rail(morning):
    log = _lines(morning)
    assert log["after-sleep"] == "the grill sleeps. the grill wakes."
    assert log["done-after-sleep"] == 0
