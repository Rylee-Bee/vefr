"""Death and waking are events a rule can name (vefr #365).

Eleven events were typed in `shapes.EVENTS` and none of them was the
hero dying: `defeats` is the player killing something, and its mirror
did not exist. A pack could fake one with `enters`, which fires on
every arrival - so the narrator said "you wake in the cottage again"
to a player who had merely walked home, and death was
indistinguishable from a bug.

Two events close that: `falls` (the health bar reached zero; what did
it, and where) and `wakes` (where the hero woke up). Pinned here:

  - the two rows of the one table, with their payload and their refs;
  - `vefr check` accepting a rule and a sticker that name them, and
    naming the pointer when the payload's own keys are wrong - the way
    `defeats` does today;
  - the woven player raising both on one death, once each, carrying
    different places, with the narrator lines reaching the screen and
    the `enters` control NOT firing (the death is not an arrival).

The first two run on the Python side alone. The third plays the real
woven file in jsdom and is skipped where node is not installed.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli, maplab, shapes

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "death_events_harness.mjs"
MAKE = ROOT / "tests" / "fixtures" / "make_death_pack.py"

# One pack's worth of declared ids: a region, an enemy, a flag. Every
# sentence below is then about the payload, not about the pack.
KNOWN = {
    'items': set(),
    'people': set(),
    'places': {'town', 'cellar'},
    'pois': set(),
    'books': set(),
    'enemies': {'pit-rat'},
    'acts': set(),
    'phases': set(),
    'things': {'town', 'cellar', 'pit-rat'},
    'flags': {'fell'},
    'claims': set(),
}

FALLS = {'what': 'pit-rat', 'where': 'town'}
WAKES = {'where': 'cellar'}


# --- the table ------------------------------------------------------------

def test_the_table_carries_the_hero_dying_and_the_hero_waking():
    assert 'falls' in shapes.EVENTS and 'wakes' in shapes.EVENTS
    assert shapes.EVENTS['falls'] == (
        shapes.Key('what', 'ref', ref='enemy'),
        shapes.Key('where', 'ref', ref='place'))
    assert shapes.EVENTS['wakes'] == (shapes.Key('where', 'ref', ref='place'),)
    # The mirror of `defeats` sits beside it in the table, and both
    # validators read that one table, so neither names the vocabulary.
    assert maplab.RULE_EVENTS == tuple(shapes.EVENTS)
    assert maplab.RULE_EVENT_KEYS['falls'] == ('what', 'where')
    assert maplab.RULE_EVENT_KEYS['wakes'] == ('where',)


# --- vefr check -----------------------------------------------------------

def test_check_accepts_a_rule_and_a_sticker_naming_either_event():
    for when in (dict(falls=FALLS), dict(wakes=WAKES)):
        assert maplab._rule_event_errors('r', when, KNOWN) == [], when
        assert maplab._album_when_errors('s', when, KNOWN) == [], when


def test_a_wrong_key_of_the_new_events_is_named_at_its_pointer():
    # `falls` has two fields, so the sentence names the field the way
    # `uses-with`'s does; `wakes` has one, so it names the event alone.
    assert maplab._rule_event_errors('r', {'falls': {'what': 'pit-rat'}}, KNOWN) == [
        "rule 'r' when 'falls' needs key 'where'"]
    assert maplab._rule_event_errors(
        'r', {'falls': {'what': 'pit-rat', 'where': 'town', 'how': 'deep'}}, KNOWN) == [
            "rule 'r' when 'falls' has unknown key 'how'"]
    assert maplab._rule_event_errors(
        'r', {'falls': {'what': 'ghost', 'where': 'town'}}, KNOWN) == [
            "rule 'r' when 'falls' what names unknown enemy 'ghost'"]
    assert maplab._rule_event_errors(
        'r', {'falls': {'what': 'pit-rat', 'where': 'nowhere'}}, KNOWN) == [
            "rule 'r' when 'falls' where names unknown place 'nowhere'"]
    assert maplab._rule_event_errors('r', {'wakes': {'where': 'nowhere'}}, KNOWN) == [
        "rule 'r' when 'wakes' names unknown place 'nowhere'"]
    assert maplab._album_when_errors(
        's', {'falls': {'what': 'ghost', 'where': 'town'}}, KNOWN) == [
            "sticker 's' when 'falls' what names unknown enemy 'ghost'"]
    assert maplab._album_when_errors('s', {'wakes': {'where': 'nowhere'}}, KNOWN) == [
        "sticker 's' when 'wakes' names unknown place 'nowhere'"]


def test_a_rule_naming_either_event_survives_the_weave():
    # `_rule_bakes` is what decides whether a rule reaches the woven
    # player at all. An event the weave drops is an event that does not
    # exist for a pack, whatever the validator says.
    for when in ({'falls': FALLS}, {'wakes': WAKES}):
        rule = {'id': 'r', 'when': when, 'then': [{'set': 'fell'}]}
        assert cli._rule_bakes(rule), when


def test_the_fixture_pack_that_names_them_validates_clean(tmp_path):
    pack = _make_pack(tmp_path)
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []


# --- the woven player, played ---------------------------------------------

def _make_pack(root: Path) -> Path:
    made = subprocess.run([sys.executable, str(MAKE), str(root)],
                          capture_output=True, text=True, timeout=120)
    assert made.returncode == 0, made.stderr
    return Path(made.stdout.strip())


@pytest.fixture(scope="module")
def death(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("death-home")
    pack = _make_pack(home)
    out = home / "death.html"
    out.write_text(cli.weave_html(pack), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(out)],
                         capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stderr + run.stdout
    return {k: v for k, v in json.loads(run.stdout)['log']}


def test_the_harness_played_the_death_without_error(death):
    assert 'HARNESS-ERROR' not in death


def test_the_hero_dies_in_the_town_and_wakes_in_the_cellar(death):
    assert death['start-region'] == 'town'
    assert death['start-hero']['hp'] == 2
    assert death['end-region'] == 'cellar'
    # Cozy death is unchanged: full health again, nothing lost.
    assert death['end-hero']['hp'] == 2


def test_both_events_fired_once_each_and_no_others(death):
    # Before the fatal step neither had happened; the whole death is the
    # one step to the west. The engine seeds every DECLARED flag to false
    # at boot (`newState`, web/player/parts/445-rules-engine.js:56-58), so
    # "nothing had happened yet" is three falses, not an empty dict - and
    # it says anything at all only because the harness copies the live
    # flags object when it notes it.
    assert death['flags-before'] == {'fell': False, 'awoke': False,
                                     'arrived': False}
    after = death['flags-after']
    assert after['fell'] is True
    assert after['awoke'] is True
    # The control: a hero who dies where they stand walked through no
    # door, so `enters` never fired. This is the faked death ruled out.
    # `arrived` is declared, so it exists from boot and reads false; the
    # bite is that nothing flipped it true, which is why this reads the
    # flag itself rather than asking whether the key is there.
    assert after['arrived'] is False


def test_the_two_lines_reached_the_screen_in_order(death):
    said = death['said']
    assert 'The rat has you.' in said, said          # the `falls` line
    assert 'You come to in the cellar.' in said      # the `wakes` line
    assert said.index('The rat has you.') < said.index('You come to in the cellar.')
    # The waking line is the one still on screen; the Cozy line and the
    # pack's fall line each said their piece and moved on.
    assert death['said-line'] == 'You come to in the cellar.'


def test_each_event_carried_its_own_place(death):
    # The engine writes every `why` line in one established shape - the
    # rule id that fired, then the phrase the event builds
    # (`"rule '" + rule.id + "' fired: " + phrase`, then a full stop,
    # web/player/parts/445-rules-engine.js:333-335) - so this pins the
    # whole line as it stands. The two lines are the point: `falls`
    # carries the region the hero fell in and `wakes` the region they
    # woke in, so "town" and "cellar" must each appear on their own
    # line and neither may stand in for the other.
    why = {i: w for i, w in death['why']}
    assert why['the-hero-fell'] == \
        "rule 'the-hero-fell' fired: the hero fell in town to pit-rat."
    assert why['the-hero-woke'] == \
        "rule 'the-hero-woke' fired: the hero woke in cellar."