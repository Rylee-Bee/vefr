"""The `complete-act` rule action (Cottage release 1, plan V1). FROZEN CONTRACT.
Played through the shared tests/play_kit.py.

A pack can end a story beat with one rule action: {"complete-act": "<act id>"}.
  - validator: the value must be a string naming an act the pack declares; anything else is one plain
    sentence naming the rule (and, for an unknown act, the act id).
  - engine: the pure rules engine accepts the action (a rule using it is not skipped as malformed).
  - player: it opens an end card on the overlay surface: element #act-end, role=dialog, aria-modal,
    labelled by a heading, with the buttons "Keep exploring" and "Start over"; focus lands on
    "Keep exploring". Interact (E) continues = closes the card. It does NOT advance acts.
    window.VEFR_ACT_COMPLETE = {act, shown} is the harness snapshot.
  - once per save: with saves.rules=persist a reload does not show the card again.
  - a pack that never uses the action plays exactly as before (the card stays hidden).
Neutral fixtures only: VEFR is public.
"""

import shutil

import pytest

from vefr import maplab

import play_kit

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

END_RULE = {"id": "the-end", "when": {"starts": {}}, "once": True,
            "then": [{"complete-act": "act-1"}]}

# The kit reads one synchronous snapshot, so the end card before and after
# Interact is two runs over the same woven html.
ACT = "VEFR_ACT_COMPLETE"
PRESENT = "exists:#act-end"
VISIBLE = "visible:#act-end"
DIALOG = 'exists:#act-end[role="dialog"][aria-modal="true"]'
LABELLED = "exists:#act-end[aria-labelledby]"
TITLE = "exists:#act-end-title"
CARD_TEXT = "text:#act-end"
KEEP_TEXT = "text:#act-end-keep"
KEEP_FOCUS = "exists:#act-end-keep:focus"
CARD_READS = [ACT, PRESENT, VISIBLE, DIALOG, LABELLED, TITLE, CARD_TEXT, KEEP_TEXT, KEEP_FOCUS]


def build(tmp_path, rules=None, persist=False):
    world = {"flags": {}, "claims": {}, "people": {},
             "rules": rules if rules is not None else []}
    if persist:
        world["saves"] = {"rules": "persist", "legacy": "fresh"}
    return play_kit.pack(tmp_path, "lock", {"world.json": world})


def extra_errors(tmp_path, rules):
    bpack = build(tmp_path / "b")
    base = maplab.validate(maplab.load_pack(bpack), pack_dir=bpack)
    pack = build(tmp_path / "x", rules)
    got = maplab.validate(maplab.load_pack(pack), pack_dir=pack)
    return [e for e in got if e not in base]


def rule(value):
    return {"id": "the-end", "when": {"starts": {}}, "then": [{"complete-act": value}]}


# --- validator -------------------------------------------------------------------------------

def test_a_declared_act_is_accepted(tmp_path):
    assert extra_errors(tmp_path, [rule("act-1")]) == []


def test_an_unknown_act_is_named(tmp_path):
    errs = extra_errors(tmp_path, [rule("act-9")])
    assert any("the-end" in e and "act-9" in e for e in errs), errs


@pytest.mark.parametrize("bad", [7, True, None, {"act": "act-1"}, ["act-1"]])
def test_a_non_string_value_is_refused(tmp_path, bad):
    errs = extra_errors(tmp_path, [rule(bad)])
    assert any("the-end" in e and "complete-act" in e for e in errs), errs


# --- engine and player -------------------------------------------------------------------------

def play(tmp_path, rules, persist=False, store=None, press=False):
    html = play_kit.weave(build(tmp_path, rules, persist), tmp_path)
    steps = ["begin"] + (["key:e", "wait:200"] if press else [])
    return play_kit.play(html, {"steps": steps, "read": CARD_READS, "store": store or {}})


def test_the_end_card_opens_accessibly(tmp_path):
    out = play(tmp_path, [END_RULE])
    assert out["errors"] == []
    assert out["reads"][ACT] == {"act": "act-1", "shown": True}
    assert out["reads"][PRESENT] is True and out["reads"][VISIBLE] is True
    assert out["reads"][DIALOG] is True
    assert out["reads"][LABELLED] is True and out["reads"][TITLE] is True
    assert "Keep exploring" in out["reads"][CARD_TEXT] and "Start over" in out["reads"][CARD_TEXT]
    assert "Keep exploring" in out["reads"][KEEP_TEXT]
    assert out["reads"][KEEP_FOCUS] is True


def test_interact_closes_the_card_and_does_not_advance(tmp_path):
    html = play_kit.weave(build(tmp_path, [END_RULE]), tmp_path)
    before = play_kit.play(html, {"steps": ["begin"], "read": [VISIBLE]})
    after = play_kit.play(html, {"steps": ["begin", "key:e", "wait:200"],
                                 "read": [PRESENT, VISIBLE]})
    assert before["reads"][VISIBLE] is True
    assert not (after["reads"][PRESENT] and after["reads"][VISIBLE])
    assert after["errors"] == []


def test_once_per_save_survives_a_reload(tmp_path):
    first = play(tmp_path / "one", [END_RULE], persist=True)
    assert first["reads"][VISIBLE] is True
    second = play(tmp_path / "two", [END_RULE], persist=True, store=first["store"])
    assert not (second["reads"][PRESENT] and second["reads"][VISIBLE])
    assert second["reads"][ACT] is None


def test_a_pack_without_the_action_has_no_card(tmp_path):
    out = play(tmp_path, [])
    assert not out["reads"][VISIBLE]  # the dialog exists hidden, like the reader and trade
    assert out["reads"][ACT] is None
    assert out["errors"] == []
