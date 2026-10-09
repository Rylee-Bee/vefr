"""A drop that hands the player nothing is said out loud (D114, 2026-10-08).

Four keys reached a 2026-10-08 game as chests whose `drops` no item in the
pack's catalog could answer. Each one validated green, and each one was a
run that could not be finished: the woven player drops an id the catalog
does not hold, and the bag refuses one (`bagAdd`), so the chest opens and
the player takes nothing.

Two shapes are checked, and both are the `drops` line the author wrote: a
line that names no id at all, and ids that resolve to no item. A book with
no `drops` line is not one of them - it holds its note and nothing else,
which is a thing a pack may mean - so it is left alone. The warden's
`carries` gets the same treatment for the same reason: an item the pack
declares with no `name` is not an item the bag can hold, so beating the
warden hands over nothing.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

from vefr import maplab
from vefr.library import parse_book, validate_books

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
import make_descent_pack  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "worlds" / "sample-world"

ITEMS = {"cellar-key": {"name": "a wax key", "keep": True},
         "torch": {"name": "a pitch torch"},
         "nameless": {"sprite": "gem"}}


def book(book_id, **front):
    """One library book, written the way a pack writes one."""
    lines = [f"title: A {book_id}", "found: map", "at: [3, 3]", "kind: note"]
    lines += [f"{k.replace('_', '-')}: {v}" for k, v in front.items()]
    return parse_book("---\n" + "\n".join(lines) + "\n---\nA page.\n", book_id)


def chest_errors(*books, items=ITEMS):
    return validate_books(list(books), items=items)


# ---- a chest that holds something -------------------------------------------------

def test_a_chest_that_names_a_declared_item_is_fine():
    assert chest_errors(book("a-chest", chest="yes", drops="cellar-key, torch")) == []


def test_a_chest_may_name_a_comma_separated_list_with_spaces():
    assert chest_errors(book("a-chest", chest="yes", drops=" torch , cellar-key ")) == []


# ---- a chest that opens on nothing ------------------------------------------------

def test_a_chest_whose_drops_no_item_answers_for_is_refused():
    assert chest_errors(book("a-chest", chest="yes", drops="cellar-key")) == []   # good first
    assert chest_errors(book("a-chest", chest="yes", drops="brass-key")) == [
        "library book 'a-chest': the chest holds nothing - its drops name no item "
        "world.json declares"]


def test_a_chest_with_a_drops_line_and_no_id_in_it_is_refused():
    assert chest_errors(book("a-chest", chest="yes", drops="")) == [
        "library book 'a-chest': the chest holds nothing - its 'drops' line names "
        "no item"]


def test_the_one_id_a_chest_names_that_nothing_declares_is_named_alone():
    assert chest_errors(book("a-chest", chest="yes", drops="torch, brass-key")) == [
        "library book 'a-chest': drop 'brass-key' is not an item world.json declares"]


def test_an_item_the_pack_declares_with_no_name_is_no_item():
    # `weave` drops such an entry from the catalog it bakes and `bagAdd`
    # refuses an id that catalog does not hold, so the chest opens on
    # nothing however plainly the pack lists the id.
    assert chest_errors(book("a-chest", chest="yes", drops="nameless")) == [
        "library book 'a-chest': the chest holds nothing - its drops name no item "
        "world.json declares"]


def test_each_bad_chest_is_said_in_one_line():
    books = [book("a-chest", chest="yes", drops="brass-key"),
             book("b-chest", chest="yes", drops="copper-key")]
    assert len(chest_errors(*books)) == 2


# ---- what is deliberately not refused ----------------------------------------------

def test_a_chest_with_no_drops_line_holds_its_note_and_is_left_alone():
    assert chest_errors(book("a-note-in-a-chest", chest="yes")) == []


def test_a_book_that_is_not_a_chest_is_not_read_for_drops():
    assert chest_errors(book("a-shelf-book", drops="brass-key")) == []


def test_a_caller_with_no_catalog_has_nothing_to_read_the_drops_against():
    # `items=None` is "this pack was not checked against a catalog", which
    # is not the same as "this pack's catalog is empty".
    assert validate_books([book("a-chest", chest="yes", drops="brass-key")]) == []
    assert chest_errors(book("a-chest", chest="yes", drops="brass-key"), items={}) == [
        "library book 'a-chest': the chest holds nothing - its drops name no item "
        "world.json declares"]


# ---- the gate `vefr check` runs ----------------------------------------------------

def test_vefr_check_refuses_a_pack_that_ships_the_empty_chest(tmp_path):
    pack = tmp_path / "worlds" / "empty-chest"
    shutil.copytree(SAMPLE, pack)
    (pack / "library" / "the-locked-cupboard.md").write_text(
        "---\ntitle: The Locked Cupboard\nfound: map\nat: [6, 6]\nkind: note\n"
        "chest: yes\ndrops: cellar-key\n---\nA key behind a door.\n", encoding="utf-8")
    said = maplab.validate(maplab.load_pack(pack), pack_dir=pack)
    assert said == ["library book 'the-locked-cupboard': the chest holds nothing - "
                    "its drops name no item world.json declares"]


def test_the_pack_the_engine_ships_still_checks_green(tmp_path):
    pack = make_descent_pack.build(tmp_path)
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []


def test_a_pack_that_declares_no_catalog_at_all_drops_nothing(tmp_path):
    # The half of the bug a pack hits by forgetting the catalog rather
    # than the id: no `items` block means nothing for the bag to take.
    pack = tmp_path / "worlds" / "no-catalog"
    shutil.copytree(SAMPLE, pack)
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    del world["items"]
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")
    (pack / "library" / "the-locked-cupboard.md").write_text(
        "---\ntitle: The Locked Cupboard\nfound: map\nat: [6, 6]\nkind: note\n"
        "chest: yes\ndrops: cellar-key\n---\nA key behind a door.\n", encoding="utf-8")
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == [
        "library book 'a-travellers-satchel': the chest holds nothing - its drops "
        "name no item world.json declares",
        "library book 'the-locked-cupboard': the chest holds nothing - its drops "
        "name no item world.json declares"]


# ---- the warden's own key, ADR 0015 check 3 ----------------------------------------

KEY = "cellar-key"
WARDEN = {"family": "cellar-king", "carries": KEY}


def _pack(where, item):
    where.mkdir()
    (where / "world.json").write_text(json.dumps({"items": {KEY: item} if item else {}}))
    return where.resolve()


def test_the_wardens_key_must_be_an_item_the_bag_can_hold(tmp_path):
    good = _pack(tmp_path / "good", {"name": "a wax key", "keep": True})
    assert maplab._warden_key_errors(good, {"id": "c", "warden": WARDEN}, "s") == []
    nameless = _pack(tmp_path / "nameless", {"sprite": "key", "keep": True})
    assert maplab._warden_key_errors(nameless, {"id": "c", "warden": WARDEN}, "s") == [
        "s: /warden/carries 'cellar-key' is declared with no name, so it is not an "
        "item the bag can hold; give it a name"]
    missing = _pack(tmp_path / "missing", None)
    assert maplab._warden_key_errors(missing, {"id": "c", "warden": WARDEN}, "s") == [
        "s: /warden/carries 'cellar-key' is not an item world.json declares"]


@pytest.mark.parametrize("flag", ["yes", "true", "1", "Yes"])
def test_every_spelling_of_the_chest_flag_is_read(flag):
    # A refused chest proves the flag was read at all: a book the engine
    # does not draw as a chest is not read for drops at all.
    assert chest_errors(book("a-chest", chest=flag, drops="brass-key")) == [
        "library book 'a-chest': the chest holds nothing - its drops name no item "
        "world.json declares"]


def test_a_flag_the_engine_does_not_read_is_not_a_chest():
    assert chest_errors(book("a-chest", chest="maybe", drops="brass-key")) == []