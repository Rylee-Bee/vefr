"""The three findings of the vefr#308 second-family review, one test each.

Not a frozen contract: this file is the review pass. Each test here is
one finding, written to fail on the head it reviews:

1. the save was trimmed by the documented order but the trim could stop
   before the byte budget, so `store.setJSON` wrote over `SAVE_BYTES`;
2. returning to town cleared kills and chests but left the floor drops,
   so one Section reset in two halves;
3. Start over cleared the storage, swallowed a refusal and reloaded, so
   the player was told a fresh start over a save that was still there.

The first and the third need a storage of their own, so they run
through `descent_review_harness.mjs` against the REAL woven player: the
byte budget is proved on what the player's own `saveDoc` leaves in
storage, and Start over is proved against a storage that refuses one
remove the way a full or private-mode browser does. The second is a
walk, so it is played through the shared play kit the way the frozen
lifecycle tests are.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import play_kit
from vefr import delve

from test_descent_deltas import _descend, _doc, _json_store, _play
from test_descent_floors import DESCENT

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "descent_review_harness.mjs"
WORLD = "descent-test"
DOC_KEY = "vefr-descent-" + WORLD

# One of the keys a Release 1 save wrote and a save from this generation
# never does: its presence is what makes the descent offer the card.
OLD_SAVE_KEY = "vefr-bag-" + WORLD


def _record(i, drops=0, fog=""):
    name = "cellar-0-1-%d" % i
    return name, {
        "g": delve.GEN_VERSION,
        "h": delve.section_hash(DESCENT["sections"][0]),
        "k": "%s/cellar/0/%d" % (DESCENT["run_seed"], i + 1),
        "n": i + 1, "s": "cellar", "kills": [], "chests": [], "secrets": [],
        "drops": [{"at": [10, 10], "item": "pebble"} for _ in range(drops)],
        "fog": fog,
    }


def _doc_of(records, flags=None):
    doc = {"v": 1, "gen": delve.GEN_VERSION, "run": 0, "seed": DESCENT["run_seed"],
           "order": [], "floors": {}, "flags": flags or {}, "card": delve.GEN_VERSION}
    for name, record in records:
        doc["floors"][name] = record
        doc["order"].append(name)
    return doc


def _bytes(value):
    """The count `saveDoc` itself makes: `JSON.stringify(value).length`."""
    return len(json.dumps(value, separators=(",", ":")))


def _run(tmp_path, cases):
    html = play_kit.weave(play_kit.pack(tmp_path, "descent"), tmp_path)
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(html), str(path)],
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr + run.stdout
    out = json.loads(run.stdout)
    assert out["hasApi"] is True
    return out


# ---- finding 1: the trim must not stop before the budget -----------------

# Forty floors, each 250 dropped items and a small bitset: over the byte
# budget, under the 40-floor count cap, so the count cap is not what the
# byte budget can lean on.
FAT = _doc_of([_record(i, drops=250, fog="f" * 700) for i in range(40)])


def test_a_save_over_the_byte_budget_is_never_stored_over_it(tmp_path):
    # Nothing can be refused here: the bitsets go first, and the oldest
    # floors go whole after them, until what is left fits.
    assert _bytes(FAT) > delve.SAVE_BYTES
    got = _run(tmp_path, {"mode": "budget", "seedDoc": _doc_of([_record(0)]),
                          "docs": [FAT]})["results"][0]
    assert got["storedBytes"] <= delve.SAVE_BYTES, got["storedBytes"]
    # The second review round changed this line and nothing else here. A
    # floor record is now fitted to FLOOR_BYTES on write (that round's
    # finding 6), and 40 records of 1.5 KB is 60 KB - inside SAVE_BYTES -
    # so the whole-save trim no longer has to drop floors here, and asking
    # it to would be asking for the budget to be violated per floor to keep
    # a test's shape. What this test still proves is the point it was
    # written for: the save that lands is inside the byte budget and
    # nothing was refused. The order of sacrifice itself is pinned by the
    # frozen test in tests/test_descent_deltas.py, which drives `trimDoc`
    # directly.
    assert got["maxFloorBytes"] <= delve.FLOOR_BYTES, got["maxFloorBytes"]
    assert got["storedFloors"] == delve.FLOOR_CAP, got["storedFloors"]
    assert got["order"][-1] == FAT["order"][-1], "the newest floor is kept"
    kept = got["storedFloors"]
    assert got["order"] == FAT["order"][len(FAT["order"]) - kept:], \
        "what is given up is the oldest, first"
    assert got["refusal"] in (None, ""), "it fit, so nothing was refused"


def test_a_save_that_nothing_can_shrink_is_refused_and_says_so(tmp_path):
    # The only thing left to give up is the world's own story memory,
    # which is never given up - so this write is refused, and said.
    huge = _doc_of([_record(0)], flags={"a-flag-nobody-reads": "x" * 300000})
    seed = _doc_of([_record(0)], flags={"marker": "the old save"})
    got = _run(tmp_path, {"mode": "budget", "seedDoc": seed,
                          "docs": [huge]})["results"][0]
    assert got["given"] > delve.SAVE_BYTES
    assert got["storedFloors"] == 1, "nothing was written"
    assert got["storedFlags"] == {"marker": "the old save"}, \
        "the save that was already there is still whole, and is not over budget"
    assert got["returnedBytes"] == -1, "saveDoc refused, it did not write"
    refusal = got["refusal"] or ""
    assert len(refusal) > 20 and "save" in refusal.lower(), \
        "a save that cannot be stored says so in plain words"


# ---- finding 2: the reset is one contract --------------------------------

def test_returning_to_town_clears_the_drops_with_the_kills_and_the_chests(tmp_path):
    # A CONTRACT test, not a regression test, and the coordinator says so in the
    # PR body: this also passes against the pre-fix head 2aba3c4. The pre-fix
    # `returnToTown` really did clear kills and chests and leave `drops` alone -
    # but a floor record's drops do not survive a save round trip at all, for a
    # floor the hero entered and for one they did not, so the observable end
    # state is the same either way and nothing here can distinguish them.
    #
    # What the fix buys is that the reset is one contract in one place rather than
    # three arrays that happen to be cleared today. Keep the assertion - it pins
    # the state we want to hold - but do not read it as proof the finding was real.
    # Whether floor drops should survive a save round trip is a separate question,
    # and this slice does not answer it.
    # Two sessions, because that is what they are: the save remembers the
    # floor, not where the hero stood.
    first = _play(tmp_path, _descend(1))
    assert first["errors"] == [], first["errors"]
    doc = _doc(first)
    doc["floors"]["cellar-0-1"]["drops"] = [{"at": [10, 10], "item": "pebble"}]

    home = _play(tmp_path, _descend(1) + ["click:#interact", "wait:200"],
                 store=_json_store(doc))
    assert home["reads"]["VEFR_COMBAT.region"] == "town"
    record = _doc(home)["floors"]["cellar-0-1"]
    assert record["kills"] == [] and record["chests"] == []
    assert record["drops"] == [], \
        "returning to town resets the Section; what was dropped on it goes too"
    assert record["fog"], "the explored bitset is kept"


# ---- finding 3: Start over must not lie about a cleared save -------------

def _release_one_store():
    """A Release 1 save: an old bag, and a descent doc that never carried
    the card, so the player is offered the choice."""
    old = _doc_of([_record(0)])
    old["card"] = 1
    return {DOC_KEY: json.dumps(old), OLD_SAVE_KEY: "[]"}


def test_start_over_says_so_when_the_browser_will_not_clear_the_save(tmp_path):
    # The descent's own save is the key the storage refuses to remove, so
    # this is the finding exactly: the old game survives the reload.
    got = _run(tmp_path, {"mode": "startover", "store": _release_one_store(),
                          "blockKey": DOC_KEY})
    assert got["offered"]["cardHidden"] is False, "the card was offered"
    assert got["returned"] is False, "start over did not go through"
    after = got["after"]
    assert after["cardHidden"] is False, \
        "the card stays up: the player has lost nothing yet"
    assert DOC_KEY in after["left"], "the save the browser refused is still there"
    assert OLD_SAVE_KEY not in after["left"], "the keys it would remove, it did"
    said = after["line"] or ""
    assert "clear" in said.lower() and "save" in said.lower(), \
        f"a clear that failed is named in plain words, not swallowed: {said!r}"


def test_start_over_still_reloads_when_the_storage_lets_it(tmp_path):
    got = _run(tmp_path, {"mode": "startover", "store": _release_one_store(),
                          "blockKey": None})
    assert got["returned"] is True
    assert got["after"]["left"] == [], "every vefr- key was removed"
