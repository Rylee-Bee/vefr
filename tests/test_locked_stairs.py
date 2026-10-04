"""Locked doors and stairs (design/gates-and-guardians.md, build step 1). FROZEN CONTRACT.
Played through the shared tests/play_kit.py.

A transition may carry `requires` and `locked_text`:
  "requires": {"item": "<item id>"}  or  {"flag": "<declared flag>"}   (exactly one key)
  "locked_text": "<one plain sentence, 1-200 chars>"   (optional; default "It will not open yet.")
Interact on a locked door or stair without the item (in the bag) or the flag (set) says the line and
stays put; with it the door opens as it always did. The item is never consumed in this slice.
A transition without `requires` behaves exactly as before. The lock is built; these tests pass.
"""

import json
import sys
from pathlib import Path

import pytest

from vefr import maplab

import play_kit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_lock_pack as mk  # noqa: E402

DEFAULT_LINE = "It will not open yet."
BAG = f"vefr-bag-{mk.NAME}"
TO_DOOR = "walk:down,down,right,right,up,right,right,right,right,down,down,right,right"
SNAP_READS = ["VEFR_COMBAT.region", "VEFR_COMBAT.hero.at", "text:#combat-live"]


def _all_errors(tmp_path, requires, locked_text=None):
    pack = mk.build(tmp_path, requires=requires, locked_text=locked_text)
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def errors_for(tmp_path, requires, locked_text=None):
    """Errors beyond the interact fixture's own (it is built for play, not for a clean
    validation: two unrelated speaker voice-file errors)."""
    baseline = _all_errors(tmp_path / "base", None)
    extra = list(_all_errors(tmp_path / "x", requires, locked_text))
    for e in baseline:
        if e in extra:
            extra.remove(e)
    return extra


def build(tmp_path, requires=None, locked_text=None, unlock_rule=False):
    return play_kit.pack(tmp_path, "lock", requires=requires, locked_text=locked_text,
                         unlock_rule=unlock_rule)


def _run(html, store=None, interact=False):
    # A read is one snapshot at the end: the state before Interact and after
    # Interact are two runs over the same woven html.
    steps = ["begin", TO_DOOR] + (["key:e", "wait:200"] if interact else [])
    return play_kit.play(html, {"steps": steps, "read": SNAP_READS, "store": store or {}})


# --- validator -------------------------------------------------------------------------------

def test_a_transition_without_requires_is_unchanged(tmp_path):
    assert errors_for(tmp_path, None) == []


@pytest.mark.parametrize("requires", [mk.RING, mk.GATE_FLAG])
def test_a_valid_lock_passes(tmp_path, requires):
    assert errors_for(tmp_path, requires, "The door is shut.") == []


@pytest.mark.parametrize("requires,needle", [
    ("brass-ring", "requires"), ([], "requires"), ({}, "requires"),
    ({"item": "brass-ring", "flag": "gate-open"}, "requires"),
    ({"item": 7}, "requires"), ({"flag": ""}, "requires"),
    ({"item": "no-such-item"}, "no-such-item"), ({"flag": "never-declared"}, "never-declared"),
    ({"item": "brass-ring", "level": 3}, "requires"),
])
def test_a_bad_lock_is_one_plain_sentence(tmp_path, requires, needle):
    errors = errors_for(tmp_path, requires)
    assert len(errors) == 1 and needle in errors[0]


@pytest.mark.parametrize("text", ["", 5, ["x"], "x" * 201])
def test_a_bad_locked_text_is_one_plain_sentence(tmp_path, text):
    errors = errors_for(tmp_path, mk.RING, text)
    assert len(errors) == 1 and "locked_text" in errors[0]


# --- played in the real woven file -------------------------------------------------------------

def test_a_locked_door_stays_shut_and_says_the_line(tmp_path):
    html = play_kit.weave(build(tmp_path, mk.RING, "The door is shut. Something below keeps the key."),
                          tmp_path)
    before = _run(html)
    after = _run(html, interact=True)
    assert after["errors"] == []
    assert before["reads"]["VEFR_COMBAT.region"] == "town"
    assert after["reads"]["VEFR_COMBAT.region"] == "town"
    assert after["reads"]["VEFR_COMBAT.hero.at"] == before["reads"]["VEFR_COMBAT.hero.at"]
    assert after["reads"]["text:#combat-live"] == "The door is shut. Something below keeps the key."


def test_the_default_line_when_locked_text_is_absent(tmp_path):
    html = play_kit.weave(build(tmp_path, mk.RING), tmp_path)
    after = _run(html, interact=True)
    assert after["reads"]["VEFR_COMBAT.region"] == "town"
    assert after["reads"]["text:#combat-live"] == DEFAULT_LINE


def test_the_item_in_the_bag_opens_the_door_and_stays_in_the_bag(tmp_path):
    html = play_kit.weave(build(tmp_path, mk.RING, "Shut."), tmp_path)
    out = _run(html, store={BAG: json.dumps(["brass-ring"])}, interact=True)
    assert out["errors"] == []
    assert out["reads"]["VEFR_COMBAT.region"] == "cellar"
    assert out["reads"]["VEFR_COMBAT.hero.at"] == [1, 1]
    assert json.loads(out["store"][BAG]) == ["brass-ring"]                # kept, not consumed
    assert out["reads"]["text:#combat-live"] != "Shut."


def test_a_flag_lock_stays_shut_until_the_flag_is_set(tmp_path):
    shut = _run(play_kit.weave(build(tmp_path / "a", mk.GATE_FLAG, "Shut.", unlock_rule=False),
                               tmp_path / "a"), interact=True)
    assert shut["reads"]["VEFR_COMBAT.region"] == "town"
    assert shut["reads"]["text:#combat-live"] == "Shut."
    opened = _run(play_kit.weave(build(tmp_path / "b", mk.GATE_FLAG, "Shut.", unlock_rule=True),
                                 tmp_path / "b"), interact=True)
    assert opened["errors"] == [] and opened["reads"]["VEFR_COMBAT.region"] == "cellar"


def test_an_unlocked_door_still_goes_through(tmp_path):
    html = play_kit.weave(build(tmp_path), tmp_path)
    out = _run(html, interact=True)
    assert out["errors"] == []
    assert out["reads"]["VEFR_COMBAT.region"] == "cellar"
    assert out["reads"]["VEFR_COMBAT.hero.at"] == [1, 1]
