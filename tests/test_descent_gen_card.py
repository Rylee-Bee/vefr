"""The gen_version card: one Release 1 save shows it once, and play goes on.

Release 1 could not carry generated floors (PLAN §1, item 8), so a save
that predates them is offered one honest choice: start over, or keep
playing this world as it was. The card is keyed on `gen_version`, so it
is shown once and never again - and whichever way it is answered, the
game is playable afterwards. Acceptance 3 of the slice, in the real
woven player.
"""

import json
import shutil

import pytest

import play_kit
from vefr import delve

from test_descent_deltas import DOC_KEY, TOWN_HERO, WORLD, _go, TOWN

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

# What a Release 1 save looks like: the keys the shipped game wrote before
# generated floors existed, and no descent document at all.
RELEASE_1 = {
    "vefr-bag-" + WORLD: '["pebble"]',
    "vefr-gold-" + WORLD: "7",
    "vefr-hp-" + WORLD: "5",
    "vefr-fog2-%s-town" % WORLD: "kg==",
}

CARD = "text:#gen-card-title"
SEEN = "visible:#gen-card"


def _card_play(tmp_path, store=None, steps=None):
    html = play_kit.weave(play_kit.pack(tmp_path, "descent"), tmp_path)
    spec = {"steps": steps or ["begin", "wait:400"],
            "read": [CARD, SEEN, "exists:#gen-card-keep", "exists:#gen-card-over",
                     "VEFR_DESCENT.doc", "store"],
            "store": store or {}}
    return play_kit.play(html, spec)


def test_a_release_1_save_is_offered_the_card(tmp_path):
    play = _card_play(tmp_path, store=RELEASE_1)
    assert play["errors"] == [], play["errors"]
    assert play["reads"][SEEN] is True
    assert play["reads"][CARD].strip(), "the card must say something"


def test_keeping_the_old_save_hides_the_card_and_the_game_plays(tmp_path):
    play = _card_play(tmp_path, store=RELEASE_1,
                      steps=["begin", "wait:400", "click:#gen-card-keep",
                             "wait:150"])
    assert play["errors"] == [], play["errors"]
    assert play["reads"][SEEN] is False
    assert play["store"].get("vefr-bag-" + WORLD) == RELEASE_1["vefr-bag-" + WORLD]
    assert play["reads"]["VEFR_DESCENT.doc"]["card"] == delve.GEN_VERSION
    # And the town still walks: the game is playable after the card.
    steps = ["begin", "wait:400", "click:#gen-card-keep", "wait:150",
             _go(TOWN, TOWN_HERO, [7, 4]), "wait:100"]
    after = play_kit.play(play_kit.weave(play_kit.pack(tmp_path, "descent"), tmp_path),
                          {"steps": steps, "read": ["VEFR_COMBAT.hero.at"],
                           "store": play["store"]})
    assert after["errors"] == [], after["errors"]
    assert after["reads"]["VEFR_COMBAT.hero.at"] == [7, 4]


def test_starting_over_clears_the_old_save_and_the_card_never_returns(tmp_path):
    first = _card_play(tmp_path, store=RELEASE_1,
                       steps=["begin", "wait:400", "click:#gen-card-over",
                              "wait:200"])
    # Start over reloads the page, and jsdom cannot navigate: the console
    # says so and the store is still the cleared one, which is what this
    # test is about.
    assert "vefr-bag-" + WORLD not in first["store"], first["store"]
    assert first["reads"][SEEN] is False

    # Once the save has declared this generation, a reload says nothing.
    again = _card_play(tmp_path, store=first["store"])
    assert again["errors"] == [], again["errors"]
    assert again["reads"][SEEN] is False


def test_a_fresh_player_is_never_shown_a_card(tmp_path):
    play = _card_play(tmp_path)
    assert play["reads"][SEEN] is False, "no old save, nothing to offer"


def test_a_pack_with_no_descent_has_no_card_at_all(tmp_path):
    # The card lives in the static shell, beside every other dialog, so
    # what a pack without a descent must not do is show it.
    html = play_kit.weave(play_kit.pack(tmp_path, "interact"), tmp_path)
    play = play_kit.play(html, {"steps": ["begin", "wait:200"],
                                "read": ["exists:#gen-card", SEEN]})
    assert play["reads"]["exists:#gen-card"] is True, "the shell carries it"
    assert play["reads"][SEEN] is False


def test_the_card_is_keyed_on_the_generation_not_the_save(tmp_path):
    def doc(card):
        return json.dumps({"v": 1, "gen": delve.GEN_VERSION, "card": card,
                           "floors": {}, "order": [], "flags": {},
                           "run": 0, "seed": "descent-test-run"})

    older = _card_play(tmp_path, store=dict(RELEASE_1,
                                            **{DOC_KEY: doc(delve.GEN_VERSION - 1)}))
    assert older["reads"][SEEN] is True, "an older generation must be offered"

    same = _card_play(tmp_path, store=dict(RELEASE_1,
                                           **{DOC_KEY: doc(delve.GEN_VERSION)}))
    assert same["reads"][SEEN] is False, "this generation was already offered"