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
   Section and the sprite.

The legend parity between Python and JavaScript is not here: the floor plan
already carries it, so `tests/test_descent_parity.py`'s field-for-field
comparison covers it, and says what the legend has to be.
"""

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import play_kit
from vefr import delve, maplab

from test_descent_deltas import _descend
from test_descent_floors import DESCENT

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
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


def _descent_with_tiles() -> dict:
    """The fixture descent, with each Section naming its own ground."""
    descent = copy.deepcopy(DESCENT)
    for section in descent["sections"]:
        section["tiles"] = dict(TILES[section["id"]])
    return descent


def _played(tmp_path, descent, depth):
    """Weave the fixture pack with this descent and walk down to `depth`.

    The real player, in jsdom: `ensureRegion` is what grows
    `window.VEFR_REGIONS` and `window.VEFR_REGION_TILES`, so there is nothing
    to prove here that a call into the module would not prove by proxy.
    """
    pack = play_kit.pack(tmp_path, "descent",
                        patch={"world.json": {"descent": descent}})
    html = play_kit.weave(pack, tmp_path)
    return play_kit.play(html, {
        "steps": _descend(depth),
        "read": ["VEFR_REGIONS.cellar-0-1", "VEFR_REGIONS.hollow-0-1",
                 "VEFR_REGION_TILES"],
    })


def test_two_sections_in_one_descent_draw_different_ground(tmp_path):
    """Acceptance 1: the two floors are drawn from their own Sections.

    Read off the running player, not off a helper: `VEFR_REGIONS[name].legend`
    is what the floor is painted from, and `VEFR_REGION_TILES[name]` is what
    the pictures come out of.
    """
    descent = _descent_with_tiles()
    play = _played(tmp_path, descent, 4)
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


def test_a_section_naming_no_tiles_draws_exactly_what_it_drew_today(tmp_path):
    """Acceptance 3: the no-breaking-change half.

    The fixture descent unchanged: no Section names `tiles`, so the weave bakes
    no per-Section pictures at all, the floor falls back to the pack's global
    tile set exactly as it did, and the legend is the shared one.
    """
    descent = copy.deepcopy(DESCENT)
    play = _played(tmp_path, descent, 1)
    assert play["errors"] == [], play["errors"]
    assert play["reads"]["VEFR_REGION_TILES"] in (None, {}), \
        "a pack that named no tiles grew a per-Section picture table"
    assert play["reads"]["VEFR_REGIONS.cellar-0-1"]["legend"] == delve.LEGEND

    html = play_kit.weave(play_kit.pack(tmp_path / "plain", "descent",
                                        patch={"world.json": {"descent": descent}}),
                          tmp_path / "plain")
    baked = _baked_descent(html)
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


def test_the_weave_resolves_each_sections_pictures_its_own_way(tmp_path):
    """The bake is where the two Sections stop sharing one set of pictures.

    Read off the woven file rather than the helper that wrote it, because the
    helper resolving correctly and the weave carrying it are two claims.
    """
    pack = play_kit.pack(tmp_path, "descent",
                        patch={"world.json": {"descent": _descent_with_tiles()}})
    baked = _baked_descent(play_kit.weave(pack, tmp_path))
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