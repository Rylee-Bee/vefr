"""Blueprint format 2: things (ADR 0010, slice B1) - one record per thing,
expanded into an `items` entry and one appended drop.

`things` is a list at the TOP level of the file, not a region key, because
one thing is not in one place: it is either in the pack from the start (no
`from`) or carried by one enemy instance in any region the Blueprint owns.
Format 3's `places` stayed a region key because a place is a tile in that
region and nowhere else.

What is frozen here, in the order the plan's B1 bullet lists it:

- the registry reads format 2, `TOP_KEYS` gains `things`, and `THING_KEYS`
  is the closed set `id, from, name, sprite, value, heal, use, keep, slot,
  mods, light`;
- the refusals, one plain sentence with a JSON pointer each (the
  `invalid/` corpus, one case per rule);
- what expansion writes: `world.json`'s `/items/<id>`, and the id appended
  at the END of the carrier's expanded `drops`;
- the lock, and format 1's stale rule over every pointer a thing owns;
- the byte-for-byte promise for a format-1 and a format-3 pack, and the
  exit ramp.

Where the ADR allowed more than one reading, this file froze one. The
reasons, so a later slice can see them:

1. **A thing's `name` is required.** `cli._player_items` drops an item entry
   with no name, so a thing without one would expand into an `items` entry
   the player would never meet. A refusal is the honest answer; a default
   name would be invented content.
2. **`id` and `from` are the Blueprint's own**; the other nine keys are
   exactly the item fields `_player_items` reads. The written entry is
   `name, sprite, value, heal, use, keep, light, slot, mods`: `sprite` is
   always there, because the bag draws a marker for every item, and nothing
   else is invented - a record that gives three keys gets three keys.
3. **`from` appends at the end, and a carrier with no `drops` of its own
   gets a one-element list.** The carrier's list is the hand's ordering,
   and a thing is a new arrival rather than a re-ordering of what the
   author already wrote.
4. **A thing's own id counts as a declared item** for the `drops` and
   `needs` checks. Without it the appended id would trip the existing
   "unknown item in drops" refusal on the very source that declares it.
5. **A `from` may only name an instance of a region this Blueprint owns.**
   A Blueprint writes the regions it owns and nothing else, so appending a
   drop into a region it does not own would write into a file no lock of
   its names.
6. **A thing may not take over an item the pack already declares.** The
   hand-written entry is the ordinary shape and no lock covers it, so the
   two would fight over one value with no stale rule to settle it.
7. **A format-1 and a format-3 pack normalize to the same bytes.** Only
   `blueprint.json` (which carries the version) and `blueprint.lock.json`
   (which records the format) may differ between them; `contract.json`,
   `world.json` and `map.md` are the same files either way.
8. **The exit ramp deletes the source, never the output.** A written
   `items` entry and an appended drop are the ordinary hand-written shape,
   so a pack that loses its Blueprint keeps working - which is the claim
   the ramp test proves, and the reason the whole shape has to be that.

Left undecided on purpose, and listed in the report rather than guessed
here: whether two things may share one carrier (the frozen reading is that
they may, because each is appended in source order), and whether a
carrier's `drops` may be inherited from a family rather than written on the
instance (the frozen reading follows the expanded record, so either counts).
"""

import json
from pathlib import Path

import pytest

from blueprint_helpers import mk, vefr

V1 = Path(__file__).parent / "fixtures" / "blueprint" / "v1"
V2 = Path(__file__).parent / "fixtures" / "blueprint" / "v2"
V3 = Path(__file__).parent / "fixtures" / "blueprint" / "v3"
VALID = sorted(p for p in (V2 / "valid").iterdir() if p.is_dir())
INVALID = sorted(p for p in (V2 / "invalid").iterdir() if p.is_dir())


# ----------------------------------------------------------------- the source
#
# `make_blueprint_pack` gives the pack two extra regions by copying the
# sample town: `act-1/cave-2` and `act-1/cave-3`. One family, one region,
# four instances, is enough for everything a `from` can do, and the id
# `shell` is the one item the pack declares by hand, so a source may drop
# it and a thing may not take it over.
FAMILIES = {"beetle": {"defaults": {"name": "a beetle", "sprite": "beetle",
                                    "hp": 3, "atk": 1, "xp": 2}}}
# `b1` drops nothing, so it is the carrier that gets a one-element list;
# `b2` drops the hand `shell`, so it is the carrier whose list must keep
# its own order.
CAVE_2 = [{"id": "b1", "family": "beetle", "at": [3, 4]},
          {"id": "b2", "family": "beetle", "at": [6, 4],
           "properties": {"drops": ["shell"]}},
          {"id": "m1", "family": "beetle", "at": [4, 2]},
          {"id": "odd1", "family": "beetle", "at": [5, 5],
           "properties": {"hp": 9}}]
# The same two carriers, and a torch the sample world already declares, so
# the hand list has two ids in it and a third can only arrive at the end.
CAVE_2_TWO_DROPS = [{"id": "b1", "family": "beetle", "at": [3, 4]},
                    {"id": "b2", "family": "beetle", "at": [6, 4],
                     "properties": {"drops": ["shell", "torch"]}}]
# And a carrier that already lists the very id a thing declares, which is
# the one case where "dropped" and "already dropped" are the same thing.
CAVE_2_ALREADY = [{"id": "b2", "family": "beetle", "at": [6, 4],
                   "properties": {"drops": ["shell", "pebble"]}}]
PEBBLE = {"id": "pebble", "from": "b1", "name": "a smooth pebble", "value": 4}


def _source(things=(), enemies=None, version=2):
    """A source in `version`, owning one region and carrying `things`.

    An empty `things` is left out of the file rather than written as an
    empty list, so the same builder can write a format-1 and a format-3
    source this slice must not disturb.
    """
    source = {
        "blueprint": version,
        "families": json.loads(json.dumps(FAMILIES)),
        "regions": {"act-1/cave-2": {"enemies": json.loads(json.dumps(
            CAVE_2 if enemies is None else enemies))}},
    }
    if things:
        source["things"] = [dict(thing) for thing in things]
    return source


# ------------------------------------------------------------------- the pack
def _pack(tmp_path, blueprint=None):
    """The built pack, with `cave-3` holding hand-written enemies.

    No source in this file owns `cave-3`, so its two hand-written records
    are the ones a `from` cannot reach: a carrier in a region this
    Blueprint does not own has to be refused for that reason and not for
    naming nothing at all, and the two cases are different rules.
    """
    pack = mk.build(tmp_path, blueprint=blueprint)
    path = pack / "acts" / "act-1" / "cave-3" / "contract.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    contract["enemies"] = json.loads(json.dumps(mk.STD_LEGACY["act-1/cave-3"]))
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return pack


def _normalized(tmp_path, source):
    """The same pack, with the source expanded into it."""
    pack = _pack(tmp_path, blueprint=source)
    rc, out = vefr("normalize", "--pack", pack, "--out", pack)
    assert rc == 0, out
    return pack


def _items(pack):
    return json.loads((pack / "world.json").read_text(
        encoding="utf-8"))["items"]


def _enemies(pack, region="cave-2"):
    return json.loads((pack / "acts" / "act-1" / region
                       / "contract.json").read_text(encoding="utf-8"))["enemies"]


def _record(pack, iid, region="cave-2"):
    """The one expanded enemy record with that id."""
    for record in _enemies(pack, region):
        if record["id"] == iid:
            return record
    raise AssertionError(f"no enemy {iid!r} in region {region!r}")


def _lock(pack):
    return json.loads((pack / "blueprint.lock.json").read_text(
        encoding="utf-8"))


def _source_file(pack):
    return json.loads((pack / "blueprint.json").read_text(encoding="utf-8"))


def _write_source(pack, source):
    (pack / "blueprint.json").write_text(json.dumps(source), encoding="utf-8")


def test_the_fixture_pack_is_valid_before_any_thing_is_written(tmp_path):
    """The guard on the pack above: if the two extra regions were broken,
    every other failure in this file would be a lie."""
    rc, out = vefr("check", "--pack", _pack(tmp_path))
    assert rc == 0, out


# ------------------------------------------------------------------- corpus
@pytest.mark.parametrize("case", VALID, ids=lambda p: p.name)
def test_valid_case_normalizes_and_checks_clean(case, tmp_path):
    """Every valid case is a whole pack: expand it, then `vefr check` it."""
    pack = _pack(tmp_path, blueprint=json.loads(
        (case / "blueprint.json").read_text(encoding="utf-8")))
    rc, out = vefr("normalize", "--pack", pack, "--out", pack)
    assert rc == 0, out
    rc, out = vefr("check", "--pack", pack)
    assert rc == 0, out


@pytest.mark.parametrize("case", INVALID, ids=lambda p: p.name)
def test_invalid_case_fails_with_a_plain_sentence(case, tmp_path):
    """Line 1 of `expected-error.txt` is a needle of the one sentence the
    reader must produce; line 2 is the JSON pointer it must name. The
    needles are the claim, not the prose, the way the other two corpora
    read ("unknown key", "duplicate", "missing", "no instance")."""
    from vefr import blueprint

    lines = (case / "expected-error.txt").read_text().splitlines()
    needle, pointer = lines[0].lower(), (lines[1] if len(lines) > 1 else "")
    pack = _pack(tmp_path)
    with pytest.raises(blueprint.BlueprintError) as err:
        blueprint.expand(blueprint.read(case / "blueprint.json"), pack_dir=pack)
    assert needle in str(err.value).lower(), str(err.value)
    assert "\n" not in str(err.value)
    if pointer:
        assert err.value.pointer == pointer


# ------------------------------------------------------------- the registry
def test_the_registry_reads_format_two():
    from vefr import blueprint

    minimal = json.loads(
        (V2 / "valid" / "minimal-things" / "blueprint.json").read_text(
            encoding="utf-8"))
    assert 2 in blueprint.READERS
    assert callable(blueprint.READERS[2])
    assert blueprint.READERS[2](minimal) == minimal


def test_the_closed_key_sets_gain_things():
    from vefr import blueprint

    assert blueprint.THING_KEYS == {
        "id", "from", "name", "sprite", "value", "heal", "use", "keep",
        "slot", "mods", "light"}
    assert blueprint.TOP_KEYS == {"blueprint", "families", "regions", "things"}


def test_format_one_and_three_still_read_what_they_read():
    """Two formats beside the new one, and neither of them moves: each
    reader still returns its own minimal file unchanged, and each still
    refuses the top-level key that is not its own."""
    from vefr import blueprint

    one = json.loads((V1 / "valid" / "minimal" / "blueprint.json").read_text(
        encoding="utf-8"))
    three = json.loads((V3 / "valid" / "minimal-places" / "blueprint.json")
                       .read_text(encoding="utf-8"))
    assert blueprint.READERS[1](one) == one
    assert blueprint.READERS[3](three) == three
    # `things` is format 2's own top key, so a format-1 file that brings
    # one is a file asking for a format it is not.
    with pytest.raises(blueprint.BlueprintError) as err:
        blueprint.READERS[1]({**one, "things": [dict(PEBBLE)]})
    assert err.value.pointer == "/things"
    # And `places` is format 3's, so format 2 closes its regions on
    # `enemies` alone, exactly as format 1 does.
    with pytest.raises(blueprint.BlueprintError) as err:
        blueprint.READERS[2]({"blueprint": 2, "regions": {
            "act-1/cave-2": {"enemies": [], "places": []}}})
    assert err.value.pointer == "/regions/act-1~1cave-2/places"


# ------------------------------------------ expansion equals a hand-written pack
def _hand_written_pack(dest):
    """The same pack with the two values a thing writes written by hand.

    `legacy=True` hands the two caves the records a format-1 Blueprint
    expands to, so the item entry and the appended drop are the only
    difference between this pack and the expanded one - which is the
    claim: a thing writes the ordinary shape, not a shape of its own.
    """
    pack = mk.build(dest, legacy=True)
    path = pack / "world.json"
    world = json.loads(path.read_text(encoding="utf-8"))
    world["items"]["pebble"] = {"name": "a smooth pebble", "sprite": "pebble",
                                "value": 4}
    path.write_text(json.dumps(world, indent=2) + "\n", encoding="utf-8")
    path = pack / "acts" / "act-1" / "cave-2" / "contract.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    for record in contract["enemies"]:
        if record["id"] == "b1":
            record["drops"] = ["pebble"]
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return pack


def test_expansion_equals_a_hand_written_equivalent_pack(tmp_path):
    """Two packs, one expanded and one written out longhand, agreeing on
    the item and on every enemy record. The hand-written twin is checked
    first, so the test can never pass by comparing one bad expansion
    against another."""
    from vefr import blueprint

    source = json.loads(
        (V2 / "valid" / "expansion-equals-a-hand-written-pack" / "blueprint.json"
         ).read_text(encoding="utf-8"))
    hand = _hand_written_pack(tmp_path / "hand")
    rc, out = vefr("check", "--pack", hand)
    assert rc == 0, out
    assert _items(hand)["pebble"] == {
        "name": "a smooth pebble", "sprite": "pebble", "value": 4}
    expanded = _normalized(tmp_path / "expanded", source)
    assert _items(expanded)["pebble"] == {
        "name": "a smooth pebble", "sprite": "pebble", "value": 4}
    assert _items(expanded) == _items(hand)
    for region in ("cave-2", "cave-3"):
        assert _enemies(expanded, region) == _enemies(hand, region), region
    assert blueprint.check_errors(expanded) == []


# ------------------------------------------------------------ what is written
def test_from_appends_the_id_after_the_carriers_own_drops(tmp_path):
    """Two hand ids keep their order and the thing's id lands last: the
    hand wrote that list, and a thing is an arrival, not a re-ordering."""
    from vefr import blueprint

    thing = {"id": "pebble", "from": "b2", "name": "a smooth pebble"}
    pack = _normalized(tmp_path, _source([thing], enemies=CAVE_2_TWO_DROPS))
    assert _record(pack, "b2")["drops"] == ["shell", "torch", "pebble"]
    assert _record(pack, "b1").get("drops") is None
    assert blueprint.check_errors(pack) == []


def test_a_carrier_with_no_drops_of_its_own_gets_a_one_element_list(tmp_path):
    """The list is created when the instance has none, and nothing else in
    the region moves: a carrier nobody gave a drop to is not given one."""
    from vefr import blueprint

    pack = _normalized(tmp_path, _source([PEBBLE]))
    assert _record(pack, "b1")["drops"] == ["pebble"]
    assert _record(pack, "b2")["drops"] == ["shell"]
    assert _record(pack, "m1").get("drops") is None
    assert blueprint.check_errors(pack) == []


def test_a_thing_with_no_from_writes_the_item_and_no_drop(tmp_path):
    """No `from` is the pack declaring an item of its own, not a refusal:
    the thing still reaches the player, just not by way of a carrier."""
    from vefr import blueprint

    thing = {"id": "pebble", "name": "a smooth pebble"}
    pack = _normalized(tmp_path, _source([thing]))
    assert _items(pack)["pebble"] == {"name": "a smooth pebble",
                                      "sprite": "pebble"}
    assert all("pebble" not in (record.get("drops") or [])
               for record in _enemies(pack))
    assert _record(pack, "b2")["drops"] == ["shell"]
    assert blueprint.check_errors(pack) == []


# ------------------------------------------------------------- the refusals
def _refuse(tmp_path, thing, enemies=None):
    """The one sentence and pointer a thing draws out of a real pack."""
    from vefr import blueprint

    pack = _pack(tmp_path, blueprint=_source([thing], enemies=enemies))
    with pytest.raises(blueprint.BlueprintError) as err:
        blueprint.expand(blueprint.read(pack / "blueprint.json"),
                         pack_dir=pack)
    assert "\n" not in str(err.value), str(err.value)
    return err.value


def test_a_carrier_that_already_drops_the_id_is_refused(tmp_path):
    """The expanded `drops` already lists it, so the append would write the
    same id twice and the lock would then disagree with its own source."""
    err = _refuse(tmp_path, {"id": "pebble", "from": "b2",
                             "name": "a smooth pebble"}, CAVE_2_ALREADY)
    assert err.pointer == "/things/0/from"
    assert "already" in str(err).lower()


def test_a_from_in_a_region_this_blueprint_does_not_own_is_refused(tmp_path):
    """`d1` is a real instance, hand-written into a region no source here
    names. A Blueprint writes the regions it owns, so this is a different
    refusal from naming nothing at all, and the author has to know which."""
    err = _refuse(tmp_path, {"id": "pebble", "from": "d1",
                             "name": "a smooth pebble"})
    assert err.pointer == "/things/0/from"
    assert "blueprint owns" in str(err).lower()


def test_a_from_that_names_no_instance_at_all_is_refused(tmp_path):
    err = _refuse(tmp_path, {"id": "pebble", "from": "ghost",
                             "name": "a smooth pebble"})
    assert err.pointer == "/things/0/from"
    assert "no instance" in str(err).lower()


def test_a_hand_items_entry_with_the_same_id_is_refused(tmp_path):
    """`shell` is the item the built pack declares by hand. A thing may
    not take it over: the hand-written entry is the ordinary shape and no
    lock of ours names it, so the two would fight over one value."""
    err = _refuse(tmp_path, {"id": "shell", "name": "a spiral shell"})
    assert err.pointer == "/things/0/id"
    assert "shell" in str(err)


def test_an_unknown_thing_key_is_one_plain_sentence_naming_the_field(tmp_path):
    """The closed set is a promise a reader can check without a pack, so
    the refusal is the reader's, before any file is read."""
    err = _refuse(tmp_path, {"id": "pebble", "name": "a smooth pebble",
                             "mood": "curious"})
    assert str(err) == "unknown key 'mood' at /things/0"
    assert err.pointer == "/things/0/mood"


# ---------------------------------------------------------------- the item
def test_sprite_defaults_to_the_id_and_nothing_is_invented(tmp_path):
    """The bag draws a marker for every item, so `sprite` is always
    written; the record gave two item fields and gets two, in the order
    the item reader writes them."""
    thing = {"id": "pebble", "name": "a smooth pebble"}
    pack = _normalized(tmp_path, _source([thing]))
    item = _items(pack)["pebble"]
    assert item == {"name": "a smooth pebble", "sprite": "pebble"}
    assert list(item) == ["name", "sprite"]


def test_an_explicit_sprite_is_kept_as_written(tmp_path):
    thing = {"id": "chalk", "name": "a stub of chalk", "sprite": "chalk-mark",
             "value": 2}
    pack = _normalized(tmp_path, _source([thing]))
    item = _items(pack)["chalk"]
    assert item == {"name": "a stub of chalk", "sprite": "chalk-mark",
                    "value": 2}
    assert list(item) == ["name", "sprite", "value"]


def test_a_thing_writes_its_own_fields_in_the_frozen_order(tmp_path):
    """Every optional field the item reader knows, in the order it reads
    them, and the two a worn thing may not carry beside a `slot` kept on
    two separate things rather than one that breaks both rules."""
    draught = {"id": "draught", "name": "a bitter draught", "use": "drink",
               "heal": 3, "value": 5, "keep": True}
    lantern = {"id": "lantern", "name": "a paper lantern",
               "light": {"radius": 2, "turns": 6}}
    bracer = {"id": "bracer", "name": "a leather bracer", "slot": "hand",
              "mods": {"atk": 1}}
    pack = _normalized(tmp_path, _source([draught, lantern, bracer]))
    items = _items(pack)
    assert items["draught"] == {"name": "a bitter draught", "sprite": "draught",
                                "value": 5, "heal": 3, "use": "drink",
                                "keep": True}
    assert list(items["draught"]) == ["name", "sprite", "value", "heal", "use",
                                     "keep"]
    assert items["lantern"] == {"name": "a paper lantern", "sprite": "lantern",
                                "light": {"radius": 2, "turns": 6}}
    assert list(items["lantern"]) == ["name", "sprite", "light"]
    assert items["bracer"] == {"name": "a leather bracer", "sprite": "bracer",
                               "slot": "hand", "mods": {"atk": 1}}
    assert list(items["bracer"]) == ["name", "sprite", "slot", "mods"]


# ----------------------------------------------------------------- the lock
def test_the_lock_names_the_format_the_source_and_the_written_item(tmp_path):
    from vefr import blueprint

    pack = _normalized(tmp_path, _source([PEBBLE]))
    lock = _lock(pack)
    assert lock["blueprint"] == 2
    assert lock["source_sha256"] == blueprint.canonical_hash(_source_file(pack))
    text = json.dumps(lock)
    assert "world.json" in text
    assert "/items/pebble" in text
    # one record per thing, naming the record it came from and its id
    assert "/things/0" in text and "pebble" in text
    # and the region provenance is format 1's, unchanged
    assert "acts/act-1/cave-2/contract.json" in text


# ------------------------------------------------------------- the stale rule
def _edit_thing_name_in_the_source(pack):
    source = _source_file(pack)
    source["things"][0]["name"] = "a river pebble"
    _write_source(pack, source)


def _edit_item_name(pack):
    path = pack / "world.json"
    world = json.loads(path.read_text(encoding="utf-8"))
    world["items"]["pebble"]["name"] = "a river pebble"
    path.write_text(json.dumps(world, indent=2) + "\n", encoding="utf-8")


def _edit_carrier_drop(pack):
    path = pack / "acts" / "act-1" / "cave-2" / "contract.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    contract["enemies"][0]["drops"] = ["shell"]
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")


def test_changing_a_thing_in_the_source_is_stale(tmp_path):
    """The source hash differs, so the pack is stale by format 1's own
    rule - and the value that no longer matches is the item the thing
    owns, which is what the next `vefr normalize` would rewrite."""
    pack = _normalized(tmp_path, _source([PEBBLE]))
    _edit_thing_name_in_the_source(pack)
    rc, out = vefr("check", "--pack", pack)
    assert rc != 0
    assert "stale" in out.lower()
    assert "blueprint.lock.json" in out
    assert "world.json" in out and "/items/pebble" in out


def test_hand_editing_a_written_item_is_stale(tmp_path):
    pack = _normalized(tmp_path, _source([PEBBLE]))
    _edit_item_name(pack)
    rc, out = vefr("check", "--pack", pack)
    assert rc != 0
    assert "stale" in out.lower()
    assert "world.json" in out and "/items/pebble" in out


def test_hand_editing_a_carriers_drops_is_stale(tmp_path):
    """The appended drop is part of the enemy record expansion already
    writes, so the carrier's own record is the owned pointer and the
    stale sentence names it."""
    pack = _normalized(tmp_path, _source([PEBBLE]))
    _edit_carrier_drop(pack)
    rc, out = vefr("check", "--pack", pack)
    assert rc != 0
    assert "stale" in out.lower()
    assert "acts/act-1/cave-2/contract.json" in out and "/enemies/0" in out


PUT_BACK = [
    ("source-name", _edit_thing_name_in_the_source,
     lambda pack: _items(pack)["pebble"]["name"] == "a river pebble"),
    ("item-name", _edit_item_name,
     lambda pack: _items(pack)["pebble"]["name"] == "a smooth pebble"),
    ("carrier-drop", _edit_carrier_drop,
     lambda pack: _record(pack, "b1")["drops"] == ["pebble"]),
]


@pytest.mark.parametrize("label,edit,wanted", PUT_BACK,
                         ids=[row[0] for row in PUT_BACK])
def test_normalize_puts_every_owned_value_back(label, edit, wanted, tmp_path):
    from vefr import blueprint

    pack = _normalized(tmp_path, _source([PEBBLE]))
    edit(pack)
    assert blueprint.check_errors(pack), (
        f"a hand edit to the {label} must read as stale")
    rc, out = vefr("normalize", "--pack", pack, "--out", pack)
    assert rc == 0, out
    assert wanted(pack), label
    assert blueprint.check_errors(pack) == []
    rc, out = vefr("check", "--pack", pack)
    assert rc == 0, out


# ------------------------------------------------------- byte for byte
# The one pack built twice from the equivalent format-1 and format-3
# sources. Only `blueprint.json` (the version) and `blueprint.lock.json`
# (which records the format) may differ; every file the engine generates
# is the same file either way, and that is the promise this slice has to
# keep while it adds a third format beside the two.
SAME_BYTES = ("world.json", "acts/act-1/world.json",
              "acts/act-1/cave-2/contract.json", "acts/act-1/cave-3/contract.json",
              "acts/act-1/town/map.md", "acts/act-1/cave-2/map.md",
              "acts/act-1/cave-3/map.md")


def test_a_format_one_and_a_format_three_pack_normalize_to_the_same_bytes(
        tmp_path):
    one = _normalized(tmp_path / "one", _source(version=1))
    three = _normalized(tmp_path / "three", _source(version=3))
    for rel in SAME_BYTES:
        assert (one / rel).read_bytes() == (three / rel).read_bytes(), rel
    # The two files that record the format are the two that may differ,
    # and the lock is where the format is recorded.
    assert _lock(one)["blueprint"] == 1
    assert _lock(three)["blueprint"] == 3
    assert ((one / "blueprint.lock.json").read_bytes()
            != (three / "blueprint.lock.json").read_bytes())


# -------------------------------------------------------------- exit ramp
def test_deleting_the_blueprint_leaves_a_working_pack(tmp_path):
    """The item and the appended drop are ordinary hand-written values in
    ordinary files, so the pack keeps working without its source."""
    pack = _normalized(tmp_path, _source([PEBBLE]))
    (pack / "blueprint.json").unlink()
    (pack / "blueprint.lock.json").unlink()
    assert _items(pack)["pebble"] == {"name": "a smooth pebble",
                                      "sprite": "pebble", "value": 4}
    assert _record(pack, "b1")["drops"] == ["pebble"]
    rc, out = vefr("check", "--pack", pack)
    assert rc == 0, out


def test_deleting_the_things_list_leaves_a_working_pack(tmp_path):
    """The softer ramp: the source stays, the things go, and the pack is
    still a pack. The item is nobody's now, so it is left exactly as it
    stands; the appended drop is part of the enemy record the source
    still owns, so it goes back to what the source says."""
    from vefr import blueprint

    pack = _normalized(tmp_path, _source([PEBBLE]))
    source = _source_file(pack)
    source.pop("things")
    _write_source(pack, source)
    rc, out = vefr("normalize", "--pack", pack, "--out", pack)
    assert rc == 0, out
    assert _items(pack)["pebble"] == {"name": "a smooth pebble",
                                      "sprite": "pebble", "value": 4}
    assert _record(pack, "b1").get("drops") is None
    assert blueprint.check_errors(pack) == []
    rc, out = vefr("check", "--pack", pack)
    assert rc == 0, out
