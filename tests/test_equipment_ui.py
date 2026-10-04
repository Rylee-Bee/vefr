"""Equipment, slice 3: the Bag "You" section in the real woven player (#217 track A, A3).

The pure engine is in place (A2); this slice pins the UI around it: the five slots,
the Equip/Take off buttons, the live line, the stat change, the swap, the clamp on
take-off, the potion refusal, the reload persistence, and the ghost-id drop. Each
test drives the panel through the DOM and the keyboard the way a player would.
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
HARNESS = ROOT / "tests" / "fixtures" / "equip_ui_harness.mjs"

# The second body thing the swap test needs; the base catalog only has the cloak.
COAT = {"coat-1": {"name": "a patched coat", "sprite": "cloak", "slot": "body", "mods": {"hp": 1}}}


def weave(dest, items=None, name="equip-test"):
    pack = mk.build(dest, items=items, name=name)
    out = dest / (name + ".html")
    out.write_text(cli.weave_html(pack), encoding="utf-8")
    return out


def run(html, steps, store=None, bag=None):
    # The hero starts with an empty bag; tests pre-seed what they need.
    base_store = {"vefr-bag-equip-test": json.dumps(bag or [])}
    if store:
        base_store.update(store)
    spec = json.dumps({"steps": steps, "store": base_store})
    result = subprocess.run(
        ["node", str(HARNESS), str(html), spec],
        capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def woven(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("equip-ui")
    # The base catalog has cloak-1 (body, +2 hp), bow-1 (hand, +1 atk),
    # ring-1 (charm, no mods) and potion-1 (heal=3). coat-1 is added for
    # the swap test (a second body thing).
    return weave(home, items=COAT)


# --- the panel: five slots, in order, each named ----------------------------

def test_the_five_slots_are_there_in_order_and_empty_ones_say_empty(woven):
    out = run(woven, [{"do": "openBag"}])
    final = out["final"]
    assert final["slotOrder"] == ["hand", "body", "head", "feet", "charm"]
    for sentence in final["slotSentences"]:
        # "Hand: empty", "Body: empty", ...
        assert sentence.endswith(": empty"), sentence


def test_an_empty_slot_draws_an_outline_not_an_image(woven):
    """An empty slot has an inline SVG outline, so no new art file is needed."""
    out = run(woven, [{"do": "openBag"}])
    final = out["final"]
    # The five rows must actually be there, or this test would pass on an
    # empty list and prove nothing.
    assert len(final["slotSentences"]) == 5, final["slotSentences"]
    for sentence in final["slotSentences"]:
        assert sentence.endswith(": empty"), sentence
    # Every empty slot draws the outline, and none of them an image.
    for slot, drawn in final["slotArt"].items():
        assert drawn == "svg", f"empty {slot} draws {drawn!r}, not an outline"
    # No buttons when every slot is empty.
    for slot, buttons in final["slotButtons"].items():
        assert buttons == [], f"{slot} has buttons when empty: {buttons}"


def test_a_worn_slot_draws_the_item_not_the_empty_outline(woven):
    """The outline is the *empty* signal, so a worn slot must not keep it."""
    out = run(woven, [
        {"do": "openBag"},
        {"do": "equip", "id": "cloak-1"},
    ], bag=["cloak-1"])
    art = out["final"]["slotArt"]
    # The fixture pack names a sprite for the cloak, so this is a real image.
    assert art["body"] == "img", f"body draws {art['body']!r}, not the item's sprite"
    # The four still-empty slots keep the outline.
    for slot in ("hand", "head", "feet", "charm"):
        assert art[slot] == "svg", f"{slot} should still be an empty outline"


# --- the bag row: Equip for slotted, not for a potion -----------------------

ALL_BAG = ["cloak-1", "bow-1", "ring-1", "potion-1"]


def test_a_slotted_thing_in_the_bag_gets_an_equip_button(woven):
    out = run(woven, [{"do": "openBag"}], bag=ALL_BAG)
    bag = {row["name"]: row["buttons"] for row in out["final"]["bagButtons"]}
    assert "Equip" in bag["a hooded cloak"]
    assert "Equip" in bag["a short bow"]
    assert "Equip" in bag["a plain ring"]
    # A potion is not slotted: no Equip button.
    assert "Equip" not in bag["a cloudy potion"]


# --- equipping --------------------------------------------------------------

def test_equipping_wears_it_and_the_slot_names_it(woven):
    out = run(woven, [{"do": "openBag"}, {"do": "equip", "id": "cloak-1"}], bag=ALL_BAG)
    final = out["final"]
    # The slot's sentence now names the item.
    body_idx = final["slotOrder"].index("body")
    assert final["slotSentences"][body_idx] == "Body: a hooded cloak"
    # A worn item is no longer in the bag list.
    assert "a hooded cloak" not in final["bagNames"]
    # The live line says what happened.
    assert "put on" in final["live"] and "hooded cloak" in final["live"]


def test_the_live_line_names_the_mods(woven):
    """'Health up by 2.' - the design's own example."""
    out = run(woven, [{"do": "openBag"}, {"do": "equip", "id": "cloak-1"}], bag=ALL_BAG)
    assert "Health up by 2" in out["final"]["live"]


def test_attack_and_max_health_change_by_the_worn_mods(woven):
    """Real numbers from heroAtk() / heroMax(), not just strings."""
    out = run(woven, [
        {"do": "snap", "tag": "before"},
        {"do": "openBag"},
        {"do": "equip", "id": "cloak-1"},   # +2 hp
        {"do": "snap", "tag": "cloak"},
        {"do": "equip", "id": "bow-1"},     # +1 atk
        {"do": "snap", "tag": "both"},
    ], bag=ALL_BAG)
    base = out["snaps"]["before"]
    cloak = out["snaps"]["cloak"]
    both = out["snaps"]["both"]
    # Base hero: hp=6, atk=2 (from the harness/engine fixture canon).
    assert base["heroMax"] == 6 and base["heroAtk"] == 2
    assert cloak["heroMax"] == 8 and cloak["heroAtk"] == 2
    assert both["heroMax"] == 8 and both["heroAtk"] == 3


# --- swap: equipping into a full slot ---------------------------------------

SWAP_BAG = ["cloak-1", "coat-1"]


def test_equipping_into_a_full_slot_swaps_and_names_what_came_off(woven):
    out = run(woven, [
        {"do": "openBag"},
        {"do": "equip", "id": "cloak-1"},       # body: cloak-1
        {"do": "equip", "id": "coat-1"},        # body: coat-1, cloak-1 -> bag
    ], bag=SWAP_BAG)
    final = out["final"]
    body_idx = final["slotOrder"].index("body")
    assert final["slotSentences"][body_idx] == "Body: a patched coat"
    # The outgoing cloak is back in the bag.
    assert "a hooded cloak" in final["bagNames"]
    # And the coat is no longer in the bag (it is worn).
    assert "a patched coat" not in final["bagNames"]
    # The live line names what came off.
    assert "hooded cloak" in final["live"]


# --- take off ---------------------------------------------------------------

def test_take_off_restores_the_numbers(woven):
    out = run(woven, [
        {"do": "openBag"},
        {"do": "equip", "id": "cloak-1"},
        {"do": "takeoff", "slot": "body"},
    ], bag=ALL_BAG)
    final = out["final"]
    body_idx = final["slotOrder"].index("body")
    assert final["slotSentences"][body_idx] == "Body: empty"
    assert final["heroMax"] == 6 and final["heroAtk"] == 2
    # The thing returns to the bag.
    assert "a hooded cloak" in final["bagNames"]
    assert final["slotButtons"]["body"] == []


def test_take_off_clamps_health_when_the_new_max_is_lower(woven):
    """Hero is at 7 with max 8 (cloak +2); taking the cloak off drops max to 6,
    so current is clamped to 6. The floor of clampHealth is 1, never a crash."""
    out = run(woven, [
        {"do": "openBag"},
        {"do": "equip", "id": "cloak-1"},       # max -> 8
        {"do": "setHp", "value": 7},            # current -> 7
        {"do": "takeoff", "slot": "body"},      # max -> 6; current clamped to 6
    ], bag=ALL_BAG)
    final = out["final"]
    assert final["heroMax"] == 6
    assert final["heroHp"] == 6
    assert "take off" in final["live"].lower()


# --- refusal: a potion cannot be equipped -----------------------------------

def test_a_potion_cannot_be_equipped_and_the_line_says_so_in_words(woven):
    # A potion has no slot, so no Equip button is drawn for it. The
    # test reaches the refusal path directly to pin the live line.
    out = run(woven, [
        {"do": "openBag"},
        {"do": "equip", "id": "potion-1", "direct": True},
    ], bag=ALL_BAG)
    final = out["final"]
    # The engine returns no-slot; the live line says it in words.
    assert "cannot be worn" in final["live"].lower()
    # And the slot is still empty.
    body_idx = final["slotOrder"].index("body")
    assert final["slotSentences"][body_idx] == "Body: empty"
    # The potion is still in the bag, untouched.
    assert "a cloudy potion" in final["bagNames"]
    # And no Equip button is drawn for it (only Use).
    potion_row = next(r for r in out["final"]["bagButtons"] if r["name"] == "a cloudy potion")
    assert "Equip" not in potion_row["buttons"]


# --- persistence across a reload --------------------------------------------

def test_state_survives_a_reload(woven):
    """Run once to equip, then run again with the saved storage pre-seeded.
    The same slots are still worn after the second boot."""
    first = run(woven, [
        {"do": "openBag"},
        {"do": "equip", "id": "cloak-1"},
        {"do": "equip", "id": "bow-1"},
    ], bag=ALL_BAG)
    saved = first["final"]["storage"]
    assert saved["equip"] == {"body": "cloak-1", "hand": "bow-1"}
    # Second run: pre-seed the same localStorage, then read the panel.
    store = {
        "vefr-equipped-equip-test": json.dumps(saved["equip"]),
    }
    second = run(woven, [{"do": "openBag"}], store=store, bag=saved["bag"])
    final = second["final"]
    body_idx = final["slotOrder"].index("body")
    hand_idx = final["slotOrder"].index("hand")
    assert final["slotSentences"][body_idx] == "Body: a hooded cloak"
    assert final["slotSentences"][hand_idx] == "Hand: a short bow"
    assert final["heroMax"] == 8 and final["heroAtk"] == 3


def test_a_saved_id_the_catalog_no_longer_has_is_dropped_on_load(woven):
    """Pre-seed storage with a ghost id; after boot the slot is empty, the
    ghost is gone, and nothing crashed."""
    store = {
        "vefr-equipped-equip-test": json.dumps({"body": "ghost-id", "charm": "ring-1"}),
    }
    out = run(woven, [{"do": "openBag"}], store=store, bag=[])
    final = out["final"]
    # The ghost was dropped; the ring is still worn.
    assert final["storage"]["equip"] == {"charm": "ring-1"}
    body_idx = final["slotOrder"].index("body")
    charm_idx = final["slotOrder"].index("charm")
    assert final["slotSentences"][body_idx] == "Body: empty"
    assert final["slotSentences"][charm_idx] == "Charm: a plain ring"
    # No jsdom errors from the cleanup.
    assert out["errors"] == []


# --- the frozen suites must still pass --------------------------------------

def test_the_frozen_declutter_and_quiet_ui_suites_still_pass():
    """Run the two neighbouring suites as a subprocess; their assertions are
    frozen and must hold against the new panel."""
    env = "PYTHONPYCACHEPREFIX=$(mktemp -d)"
    cmd = (
        f"cd {ROOT} && {env} .venv/bin/python -m pytest -q -p no:cacheprovider "
        "tests/test_declutter.py tests/test_quiet_ui.py"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr
