"""Equipment, slice 2: the equip state and the stat maths as pure functions (#217 track A, A2). FROZEN CONTRACT.

`window.VEFR_EQUIP_ENGINE` in the real woven player is pure: given a base, the pack's item catalog and
what is worn, it answers the numbers, and it moves a `{slot: itemId}` state around without touching
storage, the clock, the DOM or a model. The numbers are the design's (`design/equipment.md`, "The
rules"): attack is base `atk` plus the sum of worn `mods.atk`, max health is base `hp` plus worn
`mods.hp`, and taking something off clamps current health to the new max, never below 1.

  statsFor(base, items, equipped) -> {hp, atk}   base plus every worn mod
  equip(state, items, slot, itemId) -> {state, swapped, reason}
  unequip(state, slot) -> {state, removed}
  clean(state, items) -> state                  a saved state the catalog no longer matches
  clampHealth(hp, maxHp) -> number

`equip` refuses an item with no slot, a slot the item does not fit, an id the catalog lacks, and an id
that is already worn somewhere (a duplicate is impossible). A refused equip returns the state it was
given. Equipping into a full slot returns the previous wearer in `swapped` so the bag can take it
back. Nothing is ever written into the caller's state object.

This is the tests-first half: strict xfail until the engine lands (A2). The Bag panel, the buttons and
the live line (A3) come with their own slice.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
import make_equip_pack as mk  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "equip_engine_harness.mjs"

needs_a2 = pytest.mark.xfail(strict=True, reason="equipment engine (A2) not built yet")

OK = "ok"
# The plain reasons a refusal names, kept short: the live line is built from them in A3.
NOT_AN_ITEM = "not-an-item"
NO_SLOT = "no-slot"
WRONG_SLOT = "wrong-slot"
BAD_SLOT = "bad-slot"
WORN = "worn"


@pytest.fixture(scope="module")
def r(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("equip-engine")
    out = home / "e.html"
    out.write_text(cli.weave_html(mk.build(home)), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(out)],
                         capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stderr + run.stdout
    return json.loads(run.stdout)


# --- the engine exists ------------------------------------------------------------------------------

@needs_a2
def test_the_pure_engine_is_in_the_woven_file(r):
    assert r["hasEngine"] is True


# --- the stat sums -----------------------------------------------------------------------------------

@needs_a2
def test_nothing_worn_changes_nothing(r):
    assert r["statsNone"] == {"hp": 6, "atk": 2}


@needs_a2
def test_each_worn_mod_adds_to_the_base(r):
    assert r["statsCloak"] == {"hp": 8, "atk": 2}      # +2 hp
    assert r["statsRingOnly"] == {"hp": 6, "atk": 2}    # a keepsake with no mods
    assert r["statsAll"] == {"hp": 8, "atk": 3}         # cloak +2 hp, bow +1 atk, ring nothing


@needs_a2
def test_a_worn_id_the_catalog_lost_contributes_nothing(r):
    assert r["statsGhost"] == {"hp": 6, "atk": 2}


@needs_a2
def test_malformed_arguments_read_as_no_gear_and_never_crash(r):
    assert r["statsNoBase"] == {"hp": 0, "atk": 0}
    assert r["statsNoItems"] == {"hp": 6, "atk": 2}
    assert r["statsBadState"] == {"hp": 6, "atk": 2}
    assert r["statsNoHp"] == {"hp": 6, "atk": 2}        # no base hp, the cloak's +2 lands on 0


# --- equip -------------------------------------------------------------------------------------------

@needs_a2
def test_equipping_into_a_free_slot_wears_it(r):
    assert r["equipEmpty"] == {
        "state": {"body": "cloak-1"}, "swapped": None, "reason": OK}


@needs_a2
def test_equipping_into_a_full_slot_hands_the_old_wearer_back(r):
    assert r["equipSwap"] == {
        "state": {"body": "ring-1"}, "swapped": "cloak-1", "reason": OK}


@needs_a2
def test_the_slot_must_be_the_items_own_slot(r):
    assert r["equipWrongSlot"] == {
        "state": {}, "swapped": None, "reason": WRONG_SLOT}
    assert r["equipBadSlot"] == {
        "state": {}, "swapped": None, "reason": BAD_SLOT}


@needs_a2
def test_an_item_with_no_slot_cannot_be_worn(r):
    assert r["equipPotion"] == {
        "state": {}, "swapped": None, "reason": NO_SLOT}


@needs_a2
def test_an_id_the_catalog_lacks_cannot_be_worn(r):
    assert r["equipGhost"] == {
        "state": {}, "swapped": None, "reason": NOT_AN_ITEM}
    assert r["equipNoArgs"] == {
        "state": {}, "swapped": None, "reason": NOT_AN_ITEM}
    assert r["equipNoCatalog"] == {
        "state": {}, "swapped": None, "reason": NOT_AN_ITEM}


@needs_a2
def test_a_duplicate_is_impossible(r):
    # Already in its own slot: nothing changes.
    assert r["equipTwice"] == {
        "state": {"body": "cloak-1"}, "swapped": None, "reason": WRONG_SLOT}
    # Worn, and asked for a slot it does not fit: still refused.
    assert r["equipElsewhere"] == {
        "state": {"body": "cloak-1"}, "swapped": None, "reason": WRONG_SLOT}


@needs_a2
def test_equipping_never_writes_into_the_callers_state(r):
    assert r["equipPureInput"] == {"body": "cloak-1"}
    assert r["equipPure"]["state"] == {"body": "cloak-1", "charm": "ring-1"}


# --- unequip -----------------------------------------------------------------------------------------

@needs_a2
def test_taking_off_returns_the_thing_that_was_worn(r):
    assert r["unequipWorn"] == {"state": {"charm": "ring-1"}, "removed": "cloak-1"}


@needs_a2
def test_taking_off_nothing_is_not_an_error(r):
    assert r["unequipEmpty"] == {"state": {"body": "cloak-1"}, "removed": None}
    assert r["unequipBadSlot"] == {"state": {"body": "cloak-1"}, "removed": None}
    assert r["unequipNothing"] == {"state": {}, "removed": None}


# --- a saved state the catalog no longer matches -----------------------------------------------------

@needs_a2
def test_clean_drops_only_what_no_longer_fits(r):
    assert r["cleanOk"] == {"body": "cloak-1", "charm": "ring-1"}
    assert r["cleanGhost"] == {"charm": "ring-1"}       # the id is gone
    assert r["cleanWrongSlot"] == {}                     # the cloak is not a hand thing
    assert r["cleanUnslotted"] == {}                     # a potion cannot be worn
    assert r["cleanBadShape"] == {}                      # a non-string id, an unknown slot
    assert r["cleanNoArgs"] == {}


# --- the health clamp --------------------------------------------------------------------------------

@needs_a2
def test_taking_off_a_thing_that_lowered_max_health_clamps(r):
    assert r["clampLower"] == 5      # 10 health, a new max of 5
    assert r["clampSame"] == 5


@needs_a2
def test_a_bigger_max_never_heals_and_the_floor_is_one(r):
    assert r["clampHigher"] == 5     # a smaller max does not top the hero up
    assert r["clampFloor"] == 1      # a max of 0 still leaves 1
    assert r["clampDead"] == 1       # never below 1
    assert r["clampJunk"] == [1, 1, 1]   # junk in, 1 out, never a crash
