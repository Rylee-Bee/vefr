"""Locked doors and stairs (design/gates-and-guardians.md, build step 1). FROZEN CONTRACT.

A transition may carry `requires` and `locked_text`:
  "requires": {"item": "<item id>"}  or  {"flag": "<declared flag>"}   (exactly one key)
  "locked_text": "<one plain sentence, 1-200 chars>"   (optional; default "It will not open yet.")
Interact on a locked door or stair without the item (in the bag) or the flag (set) says the line and
stays put; with it the door opens as it always did. The item is never consumed in this slice.
A transition without `requires` behaves exactly as before. The lock is built; these tests pass.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli, maplab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_lock_pack as mk  # noqa: E402

HARNESS = ROOT / "tests" / "fixtures" / "lock_play_harness.mjs"
DEFAULT_LINE = "It will not open yet."
BAG = f"vefr-bag-{mk.NAME}"


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


def play(tmp_path, requires=None, locked_text=None, unlock_rule=False, store=None):
    pack = mk.build(tmp_path, requires=requires, locked_text=locked_text, unlock_rule=unlock_rule)
    html = tmp_path / "lock.html"
    html.write_text(cli.weave_html(pack), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(html), json.dumps({"store": store or {}})],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


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
    out = play(tmp_path, mk.RING, "The door is shut. Something below keeps the key.")
    assert out["errors"] == []
    assert out["regionBefore"] == "town" and out["regionAfter"] == "town"
    assert out["heroAfter"] == out["heroBefore"]
    assert out["narrator"] == "The door is shut. Something below keeps the key."


def test_the_default_line_when_locked_text_is_absent(tmp_path):
    out = play(tmp_path, mk.RING)
    assert out["regionAfter"] == "town" and out["narrator"] == DEFAULT_LINE


def test_the_item_in_the_bag_opens_the_door_and_stays_in_the_bag(tmp_path):
    out = play(tmp_path, mk.RING, "Shut.", store={BAG: json.dumps(["brass-ring"])})
    assert out["errors"] == []
    assert out["regionAfter"] == "cellar" and out["heroAfter"] == [1, 1]
    assert out["bag"] == ["brass-ring"]                          # kept, not consumed
    assert out["narrator"] != "Shut."


def test_a_flag_lock_stays_shut_until_the_flag_is_set(tmp_path):
    shut = play(tmp_path / "a", mk.GATE_FLAG, "Shut.", unlock_rule=False)
    assert shut["regionAfter"] == "town" and shut["narrator"] == "Shut."
    opened = play(tmp_path / "b", mk.GATE_FLAG, "Shut.", unlock_rule=True)
    assert opened["errors"] == [] and opened["regionAfter"] == "cellar"


def test_an_unlocked_door_still_goes_through(tmp_path):
    out = play(tmp_path, None)
    assert out["errors"] == []
    assert out["regionAfter"] == "cellar" and out["heroAfter"] == [1, 1]
