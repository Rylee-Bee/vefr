"""The cooking ruleset contract - act 1's morning is pack-authored,
engine-resolved. These pins keep the resolution honest: orders must
reference real pantry ids, every ticket needs the customer's voice,
and the morning's headline choice must be a real choice."""

import copy

from vefr import maplab
from vefr.world import load_world

GOOD_BLOCK = {
    "pantry": [
        {"id": "egg", "label": "fried egg"},
        {"id": "salsa", "label": "red salsa"},
        {"id": "potato", "label": "crisp potato"},
    ],
    "tickets": [
        {
            "id": "t1",
            "customer": "the regular",
            "order": ["egg", "salsa"],
            "note": "The usual. Egg, and the red one that bites.",
            "thanks": "The regular eats standing up, already turning to go.",
            "kind_line": "The regular eats it anyway. Something is off and so is the morning; both are true.",
        },
        {
            "id": "t2",
            "customer": "a stranger",
            "order": ["potato", "egg"],
            "note": "Something warm. With the crisp thing in it, if you have it.",
        },
    ],
    "morning_length": 2,
    "headlines": [
        "FIRST TRUCK ON THE ROAD SERVES BREAKFAST AGAIN",
        "PLAYERS SEEN AT THE FLOODED POOL; SOMEONE HAS LEFT FLOWERS",
    ],
}


def _world_with_cooking(block):
    w = copy.deepcopy(load_world("sample-world"))
    act = w["acts"][0]
    act["ruleset"] = "cooking"
    act["cooking"] = block
    return w


def test_good_cooking_block_validates():
    errors = maplab.validate(_world_with_cooking(copy.deepcopy(GOOD_BLOCK)))
    assert not [e for e in errors if "cooking" in e or "pantry" in e
                or "ticket" in e or "headline" in e or "morning" in e], errors


def test_order_must_reference_pantry_ids():
    block = copy.deepcopy(GOOD_BLOCK)
    block["tickets"][0]["order"] = ["egg", "ghost-pepper"]
    errors = " ".join(maplab.validate(_world_with_cooking(block)))
    assert "unknown pantry ids" in errors


def test_every_ticket_needs_the_customers_voice():
    block = copy.deepcopy(GOOD_BLOCK)
    del block["tickets"][1]["note"]
    errors = " ".join(maplab.validate(_world_with_cooking(block)))
    assert "needs a note" in errors


def test_headline_choice_must_be_a_real_choice():
    block = copy.deepcopy(GOOD_BLOCK)
    block["headlines"] = ["ONLY ONE TRUTH TODAY"]
    errors = " ".join(maplab.validate(_world_with_cooking(block)))
    assert "headlines" in errors


def test_morning_length_bounds():
    block = copy.deepcopy(GOOD_BLOCK)
    block["morning_length"] = 9
    errors = " ".join(maplab.validate(_world_with_cooking(block)))
    assert "morning_length" in errors


def test_non_cooking_acts_are_unaffected():
    w = copy.deepcopy(load_world("sample-world"))
    w["acts"][0]["ruleset"] = "ambient"
    w["acts"][0]["cooking"] = {}
    errors = maplab.validate(w)
    assert not [e for e in errors if "cooking" in e], errors
