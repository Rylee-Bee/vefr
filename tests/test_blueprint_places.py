"""Blueprint format 3: places (ADR 0010, slice B2), and the placement
sentences B2 has to resolve to write a glyph into a `map.md`
(ADR 0010's B3 bullet, the six words, frozen here at the size B2 needs).

This mission's numbering: `places` is format **3**. Format 2 is reserved
for `things` (slice B1) and does not exist yet, so a `"blueprint": 3`
file is valid on its own and never waits for format 2. A format-1 pack
is unchanged, byte for byte: the tree hash at the bottom of this file was
recorded from today's `main` before any of this was written.

What is frozen here, in the order the plan's B2 bullet lists it:

- `REGION_KEYS` gains `places`; `PLACE_KEYS` is the closed set
  `id, kind, at, glyph, tile, base, label, text, to, to_at, needs,
  locked_text`, and the registry reads format 3;
- the reader's refusals, one plain sentence with a JSON pointer each
  (the `invalid/` corpus, one case per rule);
- what expansion writes: `/legend/<glyph>`, `/pois/<x,y>`,
  `/poi_text/<x,y>`, one act `transitions` entry per door and stair
  appended after the hand-written ones, and the resolved cell's
  character in the region's `map.md`;
- the lock, the stale rule (format 1's, plus the owned `map.md` cell),
  and the byte-for-byte promise for a format-1 pack;
- the exit ramp, and the Cottage trial.

Where the ADR allowed more than one reading, this file froze one. The
reasons, so a later slice can see them:

1. **`label` and `text` are sign-only**: allowed on a `sign`, refused on
   a `door` or a `stair`, and skipped when a sign does not give them (so
   a sign with no `label` writes its glyph and no poi). The ADR says
   only that they "are sign-only", and a closed key set is about which
   keys a record may use, so the narrow reading is the one a reader can
   check.
2. **Every generated legend entry carries `"solid": false`**, for every
   kind. `_map_tile_walkable` reads a bool `solid` as `solid is False`
   and falls back to `BLOCKED_FALLBACK` when the key is absent, so a
   door or stair glyph like `T` would be solid and `_door_tile_problem`
   would refuse the door. The woven player reads the same key the same
   way (`web/player/parts/480`), and a sign is a tile the hero stands on
   to read it, so all three kinds carry it.
3. **`base` is the legend's own shape**, a list of colour strings copied
   whole, because the default (the region's own `"."` base) is copied
   whole too and one form then needs no conversion.
4. **An anchor is `start`, a place `id`, or the LABEL of a poi.** A poi
   label is the id everywhere else in the engine (`_rule_known_ids`:
   "POI labels are their own ids"), so `far:far-corner` means the tile
   the poi labelled "far-corner" names.
5. **Ties are not frozen, and neither is `near:`'s own tile.** No pack
   carries a `seed` field today, so the ADR's `sha256(pack seed, record
   id)` cannot be written down. What is frozen is the two properties it
   exists to give: the same Blueprint expands to the same `map.md` every
   run, and adding a record cannot move another record's tile. Both are
   tested on a word with more than one answer on the fixture map, which
   is the only honest way to test a tie-break.
6. **The glyph goes into `map.md`**, per the plan's answer to its own
   question 1 and ADR 0010's status note. The exit-ramp test is what
   proves it: delete the source and the glyph is still on the map.

Left undecided on purpose, and listed in the report rather than guessed
here: `room:N` (only its malformed form is refused), the tie-break and
the seed, whether `to_at` may be a sentence, what happens when two
places resolve to one tile, and whether a place may stand on a solid
tile.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

from blueprint_helpers import ROOT, mk, normalized_pack, tree_hash, vefr

V3 = Path(__file__).parent / "fixtures" / "blueprint" / "v3"
VALID = sorted(p for p in (V3 / "valid").iterdir() if p.is_dir())
INVALID = sorted(p for p in (V3 / "invalid").iterdir() if p.is_dir())

# The Cottage trial (ADR 0010: every slice must show the Cottage trial
# passing the same threshold Blueprint did). It has no `blueprint.json`
# today, so this freezes "a pack with no Blueprint is completely
# unchanged".
import os
# A real game pack to trial against, named by the environment so no
# machine path lives in this public repo. Unset means the trial skips.
COTTAGE = Path(os.environ.get("VEFR_TRIAL_PACK", "/nonexistent-trial-pack"))


# ------------------------------------------------------------------ the map
#
# The places tests need a map whose answers are unique, so `far:`,
# `dead-end` and `off:` each have exactly one right tile and a test can
# name it. The sample town ties on all of them (its farthest tile is
# (10,1) or (10,7); its nearest tile is three ways), so this file brings
# its own region.
HALL_MAP = [
    "#########",
    "#.......#",
    "#.#####.#",
    "#.......#",
    "#.......#",
    "#.......#",
    "###.#####",
]
# The answers, counted over the walkable tiles of HALL_MAP:
#   hero_start (1,1); the only dead end is (3,6); the only tile off the
#   shortest route from (1,1) to (7,5) is (3,6); the farthest walkable
#   tile from (1,1) is (7,5); the farthest from (5,5) is (3,1). The
#   nearest tile to (1,1) ties, which is what the determinism tests use.
HALL_CONTRACT = {
    "tile": 32,
    "bg": "#131311",
    "hero_start": [1, 1],
    "sanctuary_tiles": ["."],
    "water_by_phase": {"dusk": "low", "dawn": "low"},
    "flood_tiles": [],
    "legend": {
        ".": {"base": ["#212a20", "#242d22"]},
        "#": {"base": ["#2a2e33"], "solid": True},
        # A hand legend entry a place's glyph may NOT take over: its base
        # is not the region's "." base.
        "p": {"base": ["#332e26"]},
        # A hand legend entry that is exactly what expansion writes for a
        # glyph with the default base, so a place may use this glyph.
        "S": {"base": ["#212a20", "#242d22"], "solid": False},
    },
    "hero_color": "#e8e5df",
    # The anchor of the `off:` tests. One word, because a sentence is
    # split on spaces and a poi label may hold one ("the stone").
    "pois": {"7,5": "far-corner"},
    "enemies": [],
}
DOT_BASE = ["#212a20", "#242d22"]
# The one hand-written door, out of the town. It stays at `transition 0`.
HAND_TRANSITION = {"from": "town", "to": "far-hall", "at": [7, 4],
                   "to_at": [3, 4]}

# The flagship source: one region carrying enemies AND places, with a
# door, a stair and a sign, and a key beetle that drops the door's key
# (`vefr check` follows locks, so the key must be obtainable before the
# door it opens).
PLACES_BLUEPRINT = {
    "blueprint": 3,
    "families": {"beetle": {"defaults": {"name": "a beetle",
                                         "sprite": "beetle",
                                         "hp": 3, "atk": 1}}},
    "regions": {"act-1/hall": {
        "enemies": [{"id": "k1", "family": "beetle", "at": [3, 1],
                     "properties": {"drops": ["shell"]}}],
        "places": [
            {"id": "d1", "kind": "door", "at": "far:start", "glyph": "+",
             "tile": "door", "to": "far-hall", "to_at": "3,4",
             "needs": "shell",
             "locked_text": "The door will not open yet."},
            {"id": "st1", "kind": "stair", "at": "7,3", "glyph": "u",
             "to": "far-hall", "to_at": "1,1"},
            {"id": "s1", "kind": "sign", "at": "dead-end", "glyph": "?",
             "label": "the stub",
             "text": "Nothing grows at the end of this hall."},
        ]}},
}


def _source(places, **kw):
    """A format-3 source that owns `places` in one region."""
    out = {"blueprint": 3}
    out.update(kw)
    out["regions"] = {"act-1/hall": {"places": places}}
    return out


COORDINATE = _source([{"id": "d1", "kind": "door", "at": "5,4", "glyph": "+",
                       "to": "far-hall", "to_at": "3,4"}])
# A glyph in `BLOCKED_FALLBACK` ('T'), so the legend entry has to say
# `"solid": false` for the stair tile to be walkable at all.
BLOCKED_GLYPH = _source([{"id": "st1", "kind": "stair", "at": "7,3",
                          "glyph": "T", "to": "far-hall", "to_at": "1,1"}])
OFF_ROUTE = _source([{"id": "d1", "kind": "door", "at": "off:start>far-corner",
                      "glyph": "+", "to": "far-hall", "to_at": "3,4"}])
# `near:start` has more than one answer on HALL_MAP, so these two freeze
# determinism, not a tile.
NEAR = _source([{"id": "s1", "kind": "sign", "at": "near:start", "glyph": "?",
                 "label": "the first", "text": "One way."}])
NEAR_PLUS_ONE = _source([
    {"id": "s1", "kind": "sign", "at": "near:start", "glyph": "?",
     "label": "the first", "text": "One way."},
    {"id": "s2", "kind": "sign", "at": "near:far-corner", "glyph": "*",
     "label": "the second", "text": "Another way."}])
# The dead end is (3,6) and the farthest tile from the far corner (7,5)
# is (1,1), so no tile satisfies both words.
IMPOSSIBLE = _source([{"id": "d1", "kind": "door",
                       "at": "dead-end far:far-corner", "glyph": "+",
                       "to": "far-hall", "to_at": "3,4"}])
PLACE_ID_ANCHOR = _source([
    {"id": "gate", "kind": "door", "at": "5,5", "glyph": "+",
     "to": "far-hall", "to_at": "3,4"},
    {"id": "lamp", "kind": "sign", "at": "far:gate", "glyph": "*",
     "label": "the lamp", "text": "The lamp is cold."}])


# ------------------------------------------------------------------ the pack
def _pack(tmp_path, blueprint=None):
    """A pack with two purpose-made regions and one hand-written door.

    `hall` is the act's FIRST region, so `vefr check` runs the whole
    geometry on it (legend, hero_start, pois, unreachable doors) - which
    is what proves a written glyph keeps the pack valid. `far-hall` is
    where the places' doors lead. The act's own `regions` list has to
    declare both, or `vefr check` would not know they are regions at all.
    """
    pack = mk.build(tmp_path, blueprint=blueprint)
    for name in ("hall", "far-hall"):
        region = pack / "acts" / "act-1" / name
        region.mkdir(parents=True, exist_ok=True)
        (region / "map.md").write_text("\n".join(HALL_MAP) + "\n",
                                       encoding="utf-8")
        (region / "contract.json").write_text(
            json.dumps(HALL_CONTRACT, indent=2) + "\n", encoding="utf-8")
    # The library books name tiles of the first region, so they follow it.
    for book in sorted((pack / "library").glob("*.md")):
        book.write_text(
            re.sub(r"^at: .*$", "at: [1, 1]",
                   book.read_text(encoding="utf-8"), flags=re.M),
            encoding="utf-8")
    act_path = pack / "acts" / "act-1" / "world.json"
    act = json.loads(act_path.read_text(encoding="utf-8"))
    act["regions"] = ["hall", "town", "far-hall", "cave-2", "cave-3"]
    act["transitions"] = [dict(HAND_TRANSITION)]
    act_path.write_text(json.dumps(act, indent=2) + "\n", encoding="utf-8")
    return pack


def _normalized(tmp_path, blueprint):
    """The same pack, with the Blueprint expanded into it."""
    pack = _pack(tmp_path, blueprint=blueprint)
    rc, out = vefr("normalize", "--pack", pack, "--out", pack)
    assert rc == 0, out
    return pack


def _contract(pack, region="hall"):
    return json.loads((pack / "acts" / "act-1" / region
                       / "contract.json").read_text(encoding="utf-8"))


def _rows(pack, region="hall"):
    text = (pack / "acts" / "act-1" / region / "map.md").read_text(
        encoding="utf-8")
    return [line for line in text.splitlines() if line.strip()]


def _cell(pack, x, y, region="hall"):
    """The character the region wrote at (x, y)."""
    return _rows(pack, region)[y][x]


def _cell_of(pack, glyph, region="hall"):
    """Where a glyph landed, for a sentence this file does not pin."""
    for y, row in enumerate(_rows(pack, region)):
        if glyph in row:
            return row.index(glyph), y
    raise AssertionError(f"no {glyph!r} on the map of {region}")


def _act(pack):
    return json.loads((pack / "acts" / "act-1" / "world.json"
                       ).read_text(encoding="utf-8"))


def _lock(pack):
    return json.loads((pack / "blueprint.lock.json").read_text(
        encoding="utf-8"))


def _write(pack, rel, data):
    (pack / rel).write_text(json.dumps(data), encoding="utf-8")


def test_the_fixture_pack_is_valid_before_any_place_is_written(tmp_path):
    """The guard on the pack above: if the two purpose-made regions were
    broken, every other failure in this file would be a lie."""
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
    needles are the claim, not the prose, the way the format-1 corpus
    reads ("missing", "duplicate", "unknown key")."""
    from vefr import blueprint

    lines = (case / "expected-error.txt").read_text().splitlines()
    needle, pointer = lines[0].lower(), (lines[1] if len(lines) > 1 else "")
    pack = _pack(tmp_path)
    with pytest.raises(blueprint.BlueprintError) as err:
        blueprint.expand(blueprint.read(case / "blueprint.json"),
                         pack_dir=pack)
    assert needle in str(err.value).lower(), str(err.value)
    if pointer:
        assert err.value.pointer == pointer


def test_a_refused_blueprint_prints_one_sentence_and_no_traceback(tmp_path):
    """The front door prints the sentence, not a Python stack."""
    pack = _pack(tmp_path, blueprint=IMPOSSIBLE)
    rc, out = vefr("normalize", "--pack", pack, "--out", pack)
    assert rc == 1
    assert "Traceback" not in out
    assert len([line for line in out.splitlines() if line.strip()]) == 1, out


# ------------------------------------------------------------ the registry
def test_the_registry_reads_format_three():
    from vefr import blueprint

    minimal = json.loads(
        (V3 / "valid" / "minimal-places" / "blueprint.json").read_text(
            encoding="utf-8"))
    assert 3 in blueprint.READERS
    assert callable(blueprint.READERS[3])
    assert blueprint.READERS[3](minimal) == minimal


def test_format_two_is_not_a_reader_yet(tmp_path):
    """Format 2 is reserved for `things` (slice B1). A file that asks for
    it must be refused, not read as a format it is not."""
    from vefr import blueprint

    assert 2 not in blueprint.READERS
    pack = _pack(tmp_path, blueprint=json.loads(
        (V3 / "invalid" / "version-two" / "blueprint.json").read_text(
            encoding="utf-8")))
    with pytest.raises(blueprint.BlueprintError) as err:
        blueprint.expand(blueprint.read(pack / "blueprint.json"),
                         pack_dir=pack)
    assert err.value.pointer == "/blueprint"


def test_the_closed_key_sets_gain_places():
    from vefr import blueprint

    assert blueprint.PLACE_KEYS == {
        "id", "kind", "at", "glyph", "tile", "base", "label", "text",
        "to", "to_at", "needs", "locked_text"}
    assert blueprint.REGION_KEYS == {"enemies", "places"}


def test_a_format_three_source_is_valid_on_its_own(tmp_path):
    """No families, no enemies, no format 2: a places-only file is a whole
    pack on its own."""
    from vefr import blueprint

    pack = _normalized(tmp_path, json.loads(
        (V3 / "valid" / "minimal-places" / "blueprint.json").read_text(
            encoding="utf-8")))
    assert blueprint.check_errors(pack) == []


# ------------------------------------------------------- what is written
def test_a_door_writes_the_legend_the_transition_and_the_map_cell(tmp_path):
    from vefr import blueprint

    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    assert _contract(pack)["legend"]["+"] == {
        "base": DOT_BASE, "solid": False, "tile": "door"}
    assert _cell(pack, 7, 5) == "+"
    assert _act(pack)["transitions"][1] == {
        "from": "hall", "at": [7, 5], "to": "far-hall", "to_at": [3, 4],
        "requires": {"item": "shell"},
        "locked_text": "The door will not open yet."}
    assert blueprint.check_errors(pack) == []
    rc, out = vefr("check", "--pack", pack)
    assert rc == 0, out


def test_a_stair_glyph_that_is_solid_by_default_carries_solid_false(tmp_path):
    """'T' is in `BLOCKED_FALLBACK`, so without `"solid": false` in the
    legend the stair tile would not be walkable and the door check would
    refuse the whole pack."""
    pack = _normalized(tmp_path, BLOCKED_GLYPH)
    assert _contract(pack)["legend"]["T"] == {"base": DOT_BASE,
                                              "solid": False}
    assert _cell(pack, 7, 3) == "T"
    assert _act(pack)["transitions"][1] == {"from": "hall", "at": [7, 3],
                                            "to": "far-hall",
                                            "to_at": [1, 1]}
    rc, out = vefr("check", "--pack", pack)
    assert rc == 0, out


def test_a_sign_writes_a_poi_and_its_text_and_no_transition(tmp_path):
    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    contract = _contract(pack)
    # The hand poi keeps its tile and the sign adds its own: the two poi
    # keys are exactly the hand one and the sign's.
    assert contract["pois"] == {"7,5": "far-corner", "3,6": "the stub"}
    assert contract["poi_text"] == {
        "3,6": "Nothing grows at the end of this hall."}
    assert _cell(pack, 3, 6) == "?"
    # One hand door, one door, one stair: the sign wrote none.
    assert [t["from"] for t in _act(pack)["transitions"]] == [
        "town", "hall", "hall"]


def test_a_sign_with_no_label_writes_a_glyph_and_no_poi(tmp_path):
    pack = _normalized(tmp_path, json.loads(
        (V3 / "valid" / "minimal-places" / "blueprint.json").read_text(
            encoding="utf-8")))
    assert _cell(pack, 3, 6) == "?"
    assert _contract(pack)["pois"] == {"7,5": "far-corner"}
    assert _contract(pack).get("poi_text", {}) == {}
    assert [t["from"] for t in _act(pack)["transitions"]] == ["town"]


def test_generated_values_are_appended_after_the_hand_written_ones(tmp_path):
    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    assert list(_contract(pack)["legend"]) == [".", "#", "p", "S", "+", "u",
                                               "?"]
    assert list(_contract(pack)["pois"]) == ["7,5", "3,6"]
    assert _act(pack)["transitions"][0] == HAND_TRANSITION


def test_a_glyph_already_in_the_legend_with_the_same_value_is_left_alone(
        tmp_path):
    """'S' is in the hand legend as exactly what expansion writes for a
    glyph with the default base, so the place may use it and the entry
    is not rewritten."""
    from vefr import blueprint

    pack = _normalized(tmp_path, _source([
        {"id": "s1", "kind": "sign", "at": "3,6", "glyph": "S",
         "label": "the mark", "text": "The mark is worn."}]))
    assert _contract(pack)["legend"]["S"] == {"base": DOT_BASE,
                                              "solid": False}
    assert _cell(pack, 3, 6) == "S"
    assert blueprint.check_errors(pack) == []


def test_the_lock_records_the_source_hash_the_format_and_the_map_cells(
        tmp_path):
    from vefr import blueprint

    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    lock = _lock(pack)
    source = json.loads((pack / "blueprint.json").read_text(encoding="utf-8"))
    assert lock["source_sha256"] == blueprint.canonical_hash(source)
    assert lock["blueprint"] == 3
    # The lock names every file it owns. How a map cell is written down is
    # not frozen, so the cell is looked for in either spelling.
    text = json.dumps(lock)
    assert "acts/act-1/hall/contract.json" in text
    assert "acts/act-1/hall/map.md" in text
    assert "acts/act-1/world.json" in text
    assert "3,6" in text or "[3, 6]" in text or "[3,6]" in text


# ---------------------------------------------------- placement sentences
def test_a_plain_coordinate_is_taken_as_it_is_written(tmp_path):
    pack = _normalized(tmp_path, COORDINATE)
    assert _cell(pack, 5, 4) == "+"
    assert _act(pack)["transitions"][1]["at"] == [5, 4]


def test_far_picks_the_one_farthest_walkable_tile(tmp_path):
    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    assert _cell(pack, 7, 5) == "+"
    assert _act(pack)["transitions"][1]["at"] == [7, 5]


def test_dead_end_picks_the_one_tile_with_one_walkable_neighbour(tmp_path):
    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    assert _cell(pack, 3, 6) == "?"


def test_off_picks_the_one_tile_that_is_on_no_route_between_two_anchors(
        tmp_path):
    pack = _normalized(tmp_path, OFF_ROUTE)
    assert _cell(pack, 3, 6) == "+"
    assert _act(pack)["transitions"][1]["at"] == [3, 6]


def test_a_place_id_is_an_anchor(tmp_path):
    """`far:gate` reads the door's own tile, (5,5), and picks (3,1)."""
    pack = _normalized(tmp_path, PLACE_ID_ANCHOR)
    assert _cell(pack, 3, 1) == "*"
    assert _contract(pack)["pois"]["3,1"] == "the lamp"


def test_a_sentence_with_no_answer_is_refused(tmp_path):
    from vefr import blueprint

    pack = _pack(tmp_path, blueprint=IMPOSSIBLE)
    with pytest.raises(blueprint.BlueprintError) as err:
        blueprint.expand(IMPOSSIBLE, pack_dir=pack)
    assert err.value.pointer == "/regions/act-1~1hall/places/0/at"
    assert "\n" not in str(err.value)


def test_a_hand_transition_with_the_same_from_and_at_is_refused(tmp_path):
    from vefr import blueprint

    source = _source([{"id": "d1", "kind": "door", "at": "3,6", "glyph": "+",
                       "to": "far-hall", "to_at": "3,4"}])
    pack = _pack(tmp_path, blueprint=source)
    # A hand door already standing where this place would write its own.
    act = _act(pack)
    act["transitions"].append({"from": "hall", "to": "far-hall",
                               "at": [3, 6], "to_at": [3, 4]})
    (pack / "acts" / "act-1" / "world.json").write_text(
        json.dumps(act, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(blueprint.BlueprintError) as err:
        blueprint.expand(blueprint.read(pack / "blueprint.json"),
                         pack_dir=pack)
    assert err.value.pointer == "/regions/act-1~1hall/places/0/at"


def test_the_same_blueprint_expands_to_the_same_map_every_run(tmp_path):
    """`near:start` has more than one answer on this map, so only the
    tie-break can pick one. The test says it is the same one every run,
    not which one it is."""
    first = _normalized(tmp_path / "one", NEAR)
    second = _normalized(tmp_path / "two", NEAR)
    assert ((first / "acts/act-1/hall/map.md").read_bytes()
            == (second / "acts/act-1/hall/map.md").read_bytes())


def test_adding_a_record_cannot_move_another_records_tile(tmp_path):
    """The reason the tie-break is per record: a second sign may not move
    the first one."""
    one = _normalized(tmp_path / "one", NEAR)
    two = _normalized(tmp_path / "two", NEAR_PLUS_ONE)
    assert _cell_of(one, "?") == _cell_of(two, "?")
    assert _cell_of(two, "*") != _cell_of(two, "?")


# ------------------------------------------------------------- the stale rule
def _edit_legend(pack):
    data = _contract(pack)
    data["legend"]["+"]["base"] = ["#000000"]
    _write(pack, "acts/act-1/hall/contract.json", data)


def _edit_poi(pack):
    data = _contract(pack)
    data["pois"]["3,6"] = "something else"
    _write(pack, "acts/act-1/hall/contract.json", data)


def _edit_transition(pack):
    act = _act(pack)
    act["transitions"][1]["to_at"] = [1, 1]
    _write(pack, "acts/act-1/world.json", act)


def _edit_map_cell(pack):
    path = pack / "acts" / "act-1" / "hall" / "map.md"
    rows = _rows(pack)
    rows[6] = rows[6][:3] + "." + rows[6][4:]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


OWNED = [
    ("legend", "acts/act-1/hall/contract.json", "/legend/+", _edit_legend),
    ("poi", "acts/act-1/hall/contract.json", "/pois/3,6", _edit_poi),
    ("transition", "acts/act-1/world.json", "/transitions/1",
     _edit_transition),
    ("map-cell", "acts/act-1/hall/map.md", "3,6", _edit_map_cell),
]


@pytest.mark.parametrize("label,rel,pointer,mutate", OWNED,
                         ids=[row[0] for row in OWNED])
def test_hand_editing_an_owned_value_is_stale(label, rel, pointer, mutate,
                                             tmp_path):
    from vefr import blueprint

    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    mutate(pack)
    errors = blueprint.check_errors(pack)
    assert errors, f"a hand edit to the generated {label} must read as stale"
    joined = " ".join(errors)
    assert "stale" in joined.lower()
    assert rel in joined and pointer in joined


def test_normalize_puts_a_hand_edited_map_cell_back(tmp_path):
    from vefr import blueprint

    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    _edit_map_cell(pack)
    assert blueprint.check_errors(pack)
    rc, out = vefr("normalize", "--pack", pack, "--out", pack)
    assert rc == 0, out
    assert _cell(pack, 3, 6) == "?"
    assert blueprint.check_errors(pack) == []


def test_editing_a_place_without_normalizing_is_stale(tmp_path):
    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    source = json.loads((pack / "blueprint.json").read_text(encoding="utf-8"))
    source["regions"]["act-1/hall"]["places"][2]["text"] = "Nothing here."
    (pack / "blueprint.json").write_text(json.dumps(source), encoding="utf-8")
    rc, out = vefr("check", "--pack", pack)
    assert rc != 0 and "stale" in out.lower()


def test_changing_a_glyph_then_normalizing_rewrites_the_map_cell(tmp_path):
    from vefr import blueprint

    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    source = json.loads((pack / "blueprint.json").read_text(encoding="utf-8"))
    source["regions"]["act-1/hall"]["places"][2]["glyph"] = "!"
    (pack / "blueprint.json").write_text(json.dumps(source), encoding="utf-8")
    rc, out = vefr("normalize", "--pack", pack, "--out", pack)
    assert rc == 0, out
    assert _cell(pack, 3, 6) == "!"
    # The old glyph's legend entry is a pointer this Blueprint no longer
    # owns, so normalize leaves it alone (the plan's mixed-ownership trap).
    assert "?" in _contract(pack)["legend"]
    assert blueprint.check_errors(pack) == []
    rc, out = vefr("check", "--pack", pack)
    assert rc == 0, out


def test_hand_editing_a_generated_enemies_record_is_stale(tmp_path):
    """Format 1's rule, in a region that also carries places."""
    from vefr import blueprint

    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    data = _contract(pack)
    data["enemies"][0]["hp"] = 99
    _write(pack, "acts/act-1/hall/contract.json", data)
    errors = blueprint.check_errors(pack)
    assert errors and "stale" in " ".join(errors).lower()
    joined = " ".join(errors)
    assert "acts/act-1/hall/contract.json" in joined and "/enemies/0" in joined


# ------------------------------------------------------ byte for byte
# Recorded from today's `main`, before format 3 existed, by running
# `normalized_pack(tmp_path)` and hashing the result. It was recorded in a
# clean checkout, and it means "every tracked file of a format-1 pack is
# byte-identical" - see `pack_tree_hash` below for the one thing it must
# not depend on.
FORMAT_ONE_TREE = ("6fabffea60df7060546ab1d9279b1550f90f46a712e53f7ddf06a3"
                   "04584ed0c0")
FORMAT_ONE_FILES = {
    "blueprint.json":
        "13adf2990ba9badb476a4435aae8e055f49750f82ac8f17c17d83c8d90337107",
    "blueprint.lock.json":
        "5ff655c372f081696fd38efd96b8b000a4cd08ff08961dec23ffe85cb2bf1498",
    "world.json":
        "f376f63d796c3290faf8333502b58f97f83e42d65399819d3a3d69831220771f",
    # Untouched by a format-1 normalize, and still untouched after B2.
    "acts/act-1/world.json":
        "d8d7f608fbacade091455c22ac29e27ad7576de62194336ab62309091d52cb06",
    "acts/act-1/cave-2/contract.json":
        "f27d4145b5ff0c0eb28ff2020eff955d7fafbf7b67cf0220c92f854a2c3b0159",
    "acts/act-1/cave-2/map.md":
        "ff5c7c844562c1f356752d777bd70d9602f1bfb6bca1de0758b2ae400f305b19",
}
# The format-1 conformance corpus, byte for byte: this slice may not
# quietly reword a baseline.
FORMAT_ONE_FIXTURES = ("29c6b6a6155bfb19015d7522bcdadfed3712bb23f14b1b6d5e"
                       "47f1c824a75b0d")


# The two per-pack artifacts the engine derives and the repo refuses to
# track (`.gitignore`: "derived per-pack artifacts (norns handbok,
# world-tree view) ... regenerated by the engine; never commit"). No
# test may read them, and no pack carries them on disk in a clean clone.
DERIVED_PACK_ARTIFACTS = ("world-tree.md", "handbok.md")


def pack_tree_hash(pack: Path) -> str:
    """`tree_hash` over a generated pack, minus the files the repo ignores.

    THE TRAP THIS EXISTS FOR: `normalized_pack()` copies
    `worlds/sample-world` into a temp dir, and a developer's working copy
    of that directory usually holds a `world-tree.md` the engine
    regenerated at some point. That file is gitignored, so it is present
    in a dev checkout and absent from a clean clone and from CI - the
    very same test then hashed two different packs and only the dirty
    one failed, on evidence that said nothing about the code. The
    recorded `FORMAT_ONE_TREE` is right; the checkout was the variable.

    So: hash every file a pack is *made of*, and skip only the artifacts
    the repo itself declares derived. The pack is built in a temp
    directory, not in a repo, so `git check-ignore` has nothing to ask;
    the two names are written out instead, narrow enough to read.
    """
    h = hashlib.sha256()
    files = (p for p in Path(pack).rglob("*")
             if p.is_file() and p.name not in DERIVED_PACK_ARTIFACTS)
    for f in sorted(files):
        h.update(str(f.relative_to(pack)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def test_a_format_one_pack_normalizes_to_the_same_bytes(tmp_path):
    pack = normalized_pack(tmp_path)
    assert pack_tree_hash(pack) == FORMAT_ONE_TREE
    for rel, digest in FORMAT_ONE_FILES.items():
        assert hashlib.sha256((pack / rel).read_bytes()).hexdigest() == (
            digest), rel


def test_the_format_one_fixtures_are_unchanged_byte_for_byte():
    assert tree_hash(ROOT / "tests" / "fixtures" / "blueprint" / "v1") == (
        FORMAT_ONE_FIXTURES)


def test_a_pack_with_no_blueprint_is_unchanged(tmp_path):
    """The local twin of the Cottage trial: a pack that never opted in."""
    pack = mk.build(tmp_path)
    before = tree_hash(pack)
    assert vefr("check", "--pack", pack)[0] == 0
    rc, out = vefr("normalize", "--pack", pack)
    assert rc == 0 and "no blueprint" in out.lower()
    assert tree_hash(pack) == before


# -------------------------------------------------------------- exit ramp
def test_deleting_the_blueprint_leaves_a_working_pack(tmp_path):
    """The glyph is a generated cell of `map.md`, not a weave-time
    overlay, so the pack keeps working without the source."""
    pack = _normalized(tmp_path, PLACES_BLUEPRINT)
    (pack / "blueprint.json").unlink()
    (pack / "blueprint.lock.json").unlink()
    assert _cell(pack, 7, 5) == "+"
    assert _cell(pack, 3, 6) == "?"
    rc, out = vefr("check", "--pack", pack)
    assert rc == 0, out


# --------------------------------------------------------- the Cottage trial
def test_the_cottage_trial_still_checks_clean():
    if not COTTAGE.is_dir():
        pytest.skip(f"{COTTAGE} is not set or not on this machine (set VEFR_TRIAL_PACK)")
    rc, out = vefr("check", "--pack", COTTAGE)
    assert rc == 0, out
