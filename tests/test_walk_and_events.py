"""The first-walk rail's two new steps, and the two events that tick them.

T5 closes the player loop: paint, check, play here, put a person in, play
again. Two client-side events report the real actions -
`play_here` when the play pane is actually up, `character_placed` when a
character is written into the game for real - and the first walk grows a
step for each. A preview must never count as a placement.

The rail is declarative data (WALK_STEPS in web/app.js, rendered in that
order by walkRows), so the order is checked against that one list. The
event -> tick behaviour is executed for real: the node harness runs the
REAL workshop.js and characters.js with a stubbed DOM, fetch, sticker
reporter and first walk (tests/fixtures/walk_events_harness.mjs).

The two new stickers have no art yet: art is Rylee's to choose, so the
rules are parked behind `"disabled": true` / a `TODO(T5)` art note and
must be skipped, not broken.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from vefr import achievements as A

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DEFS_JSON = WEB / "achievements" / "achievements.json"
HARNESS = Path(__file__).resolve().parent / "fixtures" / "walk_events_harness.mjs"


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    """Never touch the real data dir."""
    monkeypatch.setattr(A, "_store", lambda: tmp_path / "achievements.json")


def _walk_step_ids():
    """The rail's own step ids, in the order it renders them."""
    src = (WEB / "app.js").read_text(encoding="utf-8")
    start = src.index("var WALK_STEPS = [")
    block = src[start:src.index("];", start)]
    return re.findall(r"id:\s*'([^']+)'", block)


def _rule_events(rule):
    events = []
    for key in ("count", "distinct", "burst"):
        if key in rule:
            events.append(rule[key][0])
    if "after" in rule:
        events.extend(rule["after"])
    return events


def test_the_walk_rail_has_the_two_new_steps_in_order():
    ids = _walk_step_ids()
    # The existing steps stay.
    for old in ("bell", "map", "chronicle", "folks", "hall"):
        assert old in ids, old
    # The two new ones exist and read paint -> play here -> put a person in.
    assert "play_here" in ids and "character_placed" in ids
    assert ids.index("play_here") < ids.index("character_placed")
    assert ids.index("map") < ids.index("play_here")
    assert ids.index("character_placed") < ids.index("hall")


def test_the_new_events_are_in_the_achievements_vocabulary():
    vocab = A.vocabulary(A.definitions())
    assert {"play_here", "character_placed"} <= vocab


@pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)
def test_play_and_place_tick_only_their_own_steps():
    result = subprocess.run(
        ["node", str(HARNESS), str(ROOT)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"walk/events harness failed:\n{result.stdout}\n{result.stderr}"
    line = next((ln for ln in result.stdout.splitlines() if ln.startswith("REPORT ")), None)
    assert line, result.stdout
    report = json.loads(line[len("REPORT "):])
    play, preview, put = report["afterPlay"], report["afterPreview"], report["afterPut"]

    # Play it here: the play_here event and its step, nothing else.
    assert "play_here" in play["events"]
    assert play["attempts"] == ["play_here"]
    assert "character_placed" not in play["events"]

    # The Keep preview is not a placement: no event, no tick.
    assert preview["events"] == [] and preview["attempts"] == []

    # Put in the game (a real write): character_placed and its step, nothing else.
    assert put["events"] == ["character_placed"]
    assert put["attempts"] == ["character_placed"]
    assert "play_here" not in put["events"]


def test_parked_sticker_rules_without_art_are_disabled_not_broken():
    raw = json.loads(DEFS_JSON.read_text(encoding="utf-8"))["achievements"]
    parked = [d for d in raw if d.get("disabled")]
    assert parked, "expected the T5 sticker rules to be parked behind disabled/todo_art"
    parked_events = {ev for d in parked for ev in _rule_events(d["rule"])}
    assert {"play_here", "character_placed"} <= parked_events
    # Art is Rylee's call: every parked rule names the TODO it waits on.
    assert all("TODO(T5)" in d.get("todo_art", "") for d in parked)

    disabled_ids = {d["id"] for d in parked}
    enabled_ids = {d["id"] for d in A.definitions()}
    assert disabled_ids.isdisjoint(enabled_ids), "a parked rule leaked into the live book"

    # Recording the events is accepted (no ValueError) and never earns the
    # parked stickers - the engine skips them instead of erroring.
    for event in ("play_here", "character_placed"):
        assert event in A.vocabulary(A.definitions())
        earned = {e["id"] for e in A.record(event)["earned"]}
        assert disabled_ids.isdisjoint(earned)

    # Nor do parked rules show up in the book or the Worlds album view.
    assert disabled_ids.isdisjoint({r["id"] for r in A.book()["achievements"]})
    assert disabled_ids.isdisjoint({s["id"] for s in A.room_view()["stickers"]})
