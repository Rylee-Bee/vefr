"""vefr#349: a Section's `tiles` is the ground its own floors are drawn with.

The shape typed `tiles` and `vefr check` validated it, and the play-time
descent never read it: every floor's legend came from one table baked beside
the Sections and every floor's pictures from `window.VEFR_TILES`, the pack's
global set - the town's grass. So every Section in a descent drew the same
ground, and for a pack whose whole pull is "what the next floor looks like"
that is the one gap that stops the dungeon from being somewhere.

Each test here is one acceptance bullet, written to fail on the head it
reviews:

1. a two-Section pack weaves so the two floors' legends differ and
   `VEFR_REGION_TILES` is populated for each;
2. a pack with no `tiles` draws exactly what it draws today;
3. a Section naming a sprite nothing has is a validation error that names the
   Section and the sprite;
4. the bake resolves each Section's pictures on its own, so the two Sections
   stop sharing one set before the player ever runs.

The first two boot the player in jsdom and are marked `needs_node`; the
last two are pure Python and run everywhere.

Both jsdom walks go down floors nothing lives on (`_descent_with_tiles`),
which is the walk the generator drew: what is under test here is the ground
a floor is drawn with, not the hero's way past a fight. The floors
themselves are unchanged - `families` is the mob stream, not the layout one.

The legend parity between Python and JavaScript is not here: the floor plan
already carries it, so `tests/test_descent_parity.py`'s field-for-field
comparison covers it, and says what the legend has to be.
"""

import copy
import json
import shutil
from pathlib import Path

import pytest

import play_kit
from vefr import delve, maplab

from test_descent_deltas import _descend
from test_descent_floors import DESCENT

# Only the tests that BOOT THE PLAYER need node. Marking the whole file would
# skip the two that do not - `vefr check`'s refusal of a tileset nothing has,
# and the bake's own resolution of each Section's pictures - on a machine
# without it, which is exactly where they are cheapest to run. So the guard
# sits on the two that call `play_kit.play`, not on the module.
needs_node = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not installed")

ROOT = Path(__file__).resolve().parents[1]

# Two Sections, two grounds. Every name here is a tileset the engine already
# ships (web/art/tiles/), so the test is about which floor is drawn with what
# and never about art this change did not add.
TILES = {
    "cellar": {"#": "dungeon-wall", ".": "wood-floor"},
    "hollow": {"#": "stone-wall", ".": "dungeon-rubble"},
}

# What the two floors' legends have to differ on, and the glyphs a glyph table
# has to have covered before the pictures mean anything.
GROUND = "."


def _descent_with_tiles(quiet: bool = False) -> dict:
    """The fixture descent, with each Section naming its own ground.

    `quiet` takes the monsters off the floors, and it is there for the two
    tests that WALK. A walk is a fixed list of directions pressed one after
    another, and a monster that steps onto the tile the hero was about to
    enter turns that press into a bump instead: the hero strikes and does
    not move (`move()` in the player's town input), so every direction
    after it lands a tile out of place and the stair is never reached. The
    floors are the generator's own either way - `families` is the mob
    stream and not the layout one, so the rows, the rooms and the stairs
    come out byte-identical with it emptied - which is the same quiet
    descent `test_descent_bot.py` walks.
    """
    descent = copy.deepcopy(DESCENT)
    for section in descent["sections"]:
        section["tiles"] = dict(TILES[section["id"]])
        if quiet:
            section["families"] = []
    return descent


def _played(tmp_path, descent, depth):
    """Weave the fixture pack with this descent and walk down to `depth`.

    The real player, in jsdom: `ensureRegion` is what grows
    `window.VEFR_REGIONS` and `window.VEFR_REGION_TILES`, so there is nothing
    to prove here that a call into the module would not prove by proxy.
    The walk is planned from the very descent that is packed, so the floors
    it steps on are the floors the player draws.

    Returns the woven file and the play, so a test can read both halves of
    one run off one file.
    """
    pack = play_kit.pack(tmp_path, "descent",
                        patch={"world.json": {"descent": descent}})
    html = play_kit.weave(pack, tmp_path)
    return html, play_kit.play(html, {
        "steps": _descend(depth, descent=descent),
        "read": ["VEFR_REGIONS.cellar-0-1", "VEFR_REGIONS.hollow-0-1",
                 "VEFR_REGION_TILES"],
    })


@needs_node
def test_two_sections_in_one_descent_draw_different_ground(tmp_path):
    """Acceptance 1: the two floors are drawn from their own Sections.

    Read off the running player, not off a helper: `VEFR_REGIONS[name].legend`
    is what the floor is painted from, and `VEFR_REGION_TILES[name]` is what
    the pictures come out of.

    Four descents, because that is where the second Section begins: the
    fixture's `cellar` holds three floors and `hollow` two, so depths 1-3
    are the cellar's and depth 4 is `hollow-0-1` (`delve.locate`). The
    floors are walked empty - see `_descent_with_tiles` - because what is
    under test here is the ground, not the walk past a fight.
    """
    descent = _descent_with_tiles(quiet=True)
    _html, play = _played(tmp_path, descent, 4)
    assert play["errors"] == [], play["errors"]
    reads = play["reads"]

    cellar, hollow = reads["VEFR_REGIONS.cellar-0-1"], reads["VEFR_REGIONS.hollow-0-1"]
    assert cellar and hollow, "the walk never reached both Sections"
    assert cellar["legend"] != hollow["legend"], \
        "two Sections named different ground and drew one of them"
    assert cellar["legend"][GROUND]["tile"] == TILES["cellar"][GROUND]
    assert hollow["legend"][GROUND]["tile"] == TILES["hollow"][GROUND]
    # A glyph the Section did not name is still the engine's, so the two
    # floors agree on the walls they were not asked about.
    assert cellar["legend"]["u"] == delve.LEGEND["u"], cellar["legend"]["u"]

    tiles = reads["VEFR_REGION_TILES"]
    for name in ("cellar-0-1", "hollow-0-1"):
        assert isinstance(tiles.get(name), dict) and tiles[name], \
            f"{name} has no pictures: it fell back to the pack's global set"
        assert tiles[name][GROUND].startswith("data:image/webp;base64,"), name
    assert tiles["cellar-0-1"][GROUND] != tiles["hollow-0-1"][GROUND], \
        "two Sections' ground is one picture"


@needs_node
def test_a_section_naming_no_tiles_draws_exactly_what_it_drew_today(tmp_path):
    """Acceptance 3: the no-breaking-change half.

    The fixture descent unchanged: no Section names `tiles`, so the weave bakes
    no per-Section pictures at all, the floor falls back to the pack's global
    tile set exactly as it did, and the legend is the shared one.

    What "no per-Section pictures" is measured against is the table the
    weave itself baked, and NOT an empty table: `window.VEFR_REGION_TILES`
    is keyed by REGION and has always held one entry per baked region, so
    the town's own tiles are in it - in this pack's weave and in every
    weave before this slice. What this slice could have added is a DESCENT
    FLOOR's entry, and what is asserted is that the running player's table
    is byte-for-byte the one the weave baked.
    """
    descent = copy.deepcopy(DESCENT)
    html, play = _played(tmp_path, descent, 1)
    assert play["errors"] == [], play["errors"]

    baked_tiles = _baked_region_tiles(html.read_text(encoding="utf-8"))
    # The pack has one baked region, so the table holds one key, and it
    # names the town rather than any descent floor. That entry is the
    # town's own tiles, written by `_player_region_tiles` - a function
    # this slice does not touch.
    assert set(baked_tiles) == {"town"}, sorted(baked_tiles)
    assert play["reads"]["VEFR_REGION_TILES"] == baked_tiles, \
        "a pack that named no tiles grew a per-Section picture table"
    assert play["reads"]["VEFR_REGIONS.cellar-0-1"]["legend"] == delve.LEGEND

    baked = _baked_descent(html.read_text(encoding="utf-8"))
    assert baked["section_tiles"] == {}, baked["section_tiles"]


def test_a_section_naming_a_sprite_nothing_has_is_a_validation_error(tmp_path):
    """Acceptance 4: named, with the Section and the sprite in the sentence.

    A tileset nothing has is a floor that quietly falls back to its own
    colour, which is the failure this whole slice is about - said the other
    way round, by the door a pack author actually stands at.
    """
    pack = tmp_path / "pack"
    (pack / "sections").mkdir(parents=True)
    (pack / "sections" / "cellar.json").write_text(json.dumps({
        "id": "cellar", "floors": 1, "size": {"w": [32, 32], "h": [24, 24]},
        "rooms": [6, 6], "tiles": {".": "ember-flagstone"},
        "families": [{"family": "rat", "weight": 1}],
    }), encoding="utf-8")

    errors = maplab.section_errors(pack)
    assert len(errors) == 1, errors
    said = errors[0]
    assert "cellar" in said and "ember-flagstone" in said and "/tiles/." in said, said

    # The same pack naming a tileset the engine ships validates clean, so the
    # sentence is about the sprite and not about naming `tiles` at all.
    _with_tiles(pack, {".": "dungeon-floor"})
    assert maplab.section_errors(pack) == []

    # And one the pack itself carries answers just as the engine set does.
    _with_tiles(pack, {".": "cellar-floor"})
    (pack / "tiles").mkdir()
    shutil.copy(ROOT / "web" / "art" / "tiles" / "dungeon-floor.webp",
                pack / "tiles" / "cellar-floor.webp")
    assert maplab.section_errors(pack) == []


def _with_tiles(pack: Path, tiles: dict) -> None:
    path = pack / "sections" / "cellar.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["tiles"] = tiles
    path.write_text(json.dumps(record), encoding="utf-8")


def _baked_descent(html: str) -> dict:
    """The descent block as `weave_html` wrote it into the player."""
    line = next(row for row in html.splitlines()
                if row.startswith("window.VEFR_DESCENT_DEF = "))
    return json.loads(line.split(" = ", 1)[1].rstrip().rstrip(";"))


def _baked_region_tiles(html: str) -> dict:
    """The pictures table as `weave_html` wrote it into the player."""
    line = next(row for row in html.splitlines()
                if row.startswith("window.VEFR_REGION_TILES = "))
    return json.loads(line.split(" = ", 1)[1].rstrip().rstrip(";"))


def test_the_weave_resolves_each_sections_pictures_its_own_way(tmp_path):
    """The bake is where the two Sections stop sharing one set of pictures.

    Read off the woven file rather than the helper that wrote it, because the
    helper resolving correctly and the weave carrying it are two claims.
    """
    pack = play_kit.pack(tmp_path, "descent",
                        patch={"world.json": {"descent": _descent_with_tiles()}})
    # `play_kit.weave` writes the file and returns its PATH; `_baked_descent`
    # reads the woven TEXT, so the file is read here. (It took the Path
    # straight through before, and every run died on `.splitlines`.)
    baked = _baked_descent(play_kit.weave(pack, tmp_path).read_text(encoding="utf-8"))
    table = baked["section_tiles"]
    assert set(table) == set(TILES), table
    for section_id, named in TILES.items():
        for glyph, tileset in named.items():
            assert table[section_id][glyph].startswith("data:image/webp;base64,"), \
                f"{section_id}/{glyph} baked no picture"
    assert table["cellar"][GROUND] != table["hollow"][GROUND]
    # The shared legend is still baked beside the Sections: a plan that carries
    # no legend of its own (nothing in play does) still has one to draw with.
    assert baked["legend"] == delve.LEGEND