"""A pack brings its own tiles, with variants.

Phase C: a region's `tiles/` directory may override the engine's ground
pictures for a legend symbol, and a tile may carry numbered variants the
player tries in order. A pack with no tiles/ must bake exactly what it
did before, so the engine set still answers every symbol.
"""

from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import pytest

from vefr import cli
from vefr.maplab import load_pack
from vefr.world import _discover_tiles, load_world

SAMPLE = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"
WEB = Path(__file__).resolve().parents[1] / "web"

# A real 1x1 PNG. The webp below carries a RIFF/WEBP signature; the
# player only inlines the bytes, so the tests compare which bytes land
# where, not that a decoder accepts the picture.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def _webp(marker: bytes) -> bytes:
    return b"RIFF\x00\x00\x00\x00WEBPVP8 " + marker


def _copy_sample(tmp_path: Path) -> Path:
    pack = tmp_path / "sample-world"
    shutil.copytree(SAMPLE, pack)
    return pack


def _baked(html: str, name: str):
    """The JSON on the woven file's single `window.<name> = ...;` line."""
    prefix = f"window.{name} = "
    line = next(ln for ln in html.splitlines() if ln.startswith(prefix))
    return json.loads(line[len(prefix):].rstrip(";"))


def _write_flat_pack(pack: Path) -> Path:
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "world.json").write_text(json.dumps({
        "title": "Flat Pack",
        "phases": {"dusk": "quiet", "dawn": "warm"},
        "voices": {},
        "bonds": {},
        "town": {"map": ["###", "#.#", "###"], "legend": {".": {}}},
    }), encoding="utf-8")
    return pack


def _pack_region(tmp_path: Path) -> tuple[Path, Path]:
    """A minimal acts pack root and one region directory (no tiles/)."""
    pack = tmp_path / "pack"
    region = pack / "acts" / "act-1" / "town"
    region.mkdir(parents=True)
    return pack, region


# ---------------------------------------------------------------- loader

def test_discover_tiles_orders_variants(tmp_path):
    """Variant 1 is the unnumbered file; numbered variants follow in
    numeric (not lexicographic) order, and a name may be numbered only."""
    tiles = tmp_path / "tiles"
    tiles.mkdir()
    (tiles / "stone-wall.webp").write_bytes(_webp(b"1"))
    (tiles / "stone-wall.2.webp").write_bytes(_webp(b"2"))
    (tiles / "stone-wall.10.webp").write_bytes(_webp(b"10"))
    (tiles / "path.2.webp").write_bytes(_webp(b"p2"))
    (tiles / "path.3.webp").write_bytes(_webp(b"p3"))
    (tiles / "notes.txt").write_bytes(b"ignore me")
    (tiles / ".hidden.webp").write_bytes(_webp(b"hidden"))

    assert _discover_tiles(tiles) == {
        "stone-wall": ["stone-wall.webp", "stone-wall.2.webp",
                       "stone-wall.10.webp"],
        "path": ["path.2.webp", "path.3.webp"],
    }


def test_discover_tiles_doubled_suffix_is_deterministic(tmp_path):
    """A name with both a .webp and a .png picture picks the filename
    that sorts first (.png), so the same pack always bakes the same one."""
    tiles = tmp_path / "tiles"
    tiles.mkdir()
    (tiles / "grass.webp").write_bytes(_webp(b"webp"))
    (tiles / "grass.png").write_bytes(PNG_1X1)

    assert _discover_tiles(tiles) == {"grass": ["grass.png"]}


def test_discover_tiles_missing_dir_is_empty(tmp_path):
    assert _discover_tiles(tmp_path / "nope") == {}


def test_region_without_tiles_gets_an_empty_dict():
    """Every region dict carries a tiles key, empty when there is none."""
    load_world.cache_clear()
    for act in load_world(SAMPLE)["acts"]:
        for region in act["regions"].values():
            assert region["tiles"] == {}


def test_a_region_with_tiles_orders_them_by_name(tmp_path):
    pack = _copy_sample(tmp_path)
    region = pack / "acts" / "act-1" / "town"
    (region / "tiles").mkdir()
    (region / "tiles" / "grass.webp").write_bytes(_webp(b"1"))
    (region / "tiles" / "grass.2.webp").write_bytes(_webp(b"2"))

    load_world.cache_clear()
    town = load_world(pack)["acts"][0]["regions"]["town"]
    assert town["tiles"] == {"grass": ["grass.webp", "grass.2.webp"]}


def test_flat_shape_gains_a_tiles_key(tmp_path):
    """The legacy flat shape's implicit town also carries tiles."""
    pack = _write_flat_pack(tmp_path / "flat")

    load_world.cache_clear()
    world = load_world(pack)
    assert world["_shape"] == "flat"
    assert world["acts"][0]["regions"]["town"]["tiles"] == {}

    (pack / "tiles").mkdir()
    (pack / "tiles" / "grass.webp").write_bytes(_webp(b"flat"))

    load_world.cache_clear()
    town = load_world(pack)["acts"][0]["regions"]["town"]
    assert town["tiles"] == {"grass": ["grass.webp"]}


# ---------------------------------------------------------------- weave

def test_weave_bakes_a_packs_own_tiles_and_variants(tmp_path):
    """A pack's tiles/ rides into VEFR_TILES and VEFR_REGION_TILES;
    several pictures for one symbol bake as an ordered list."""
    pack = _copy_sample(tmp_path)
    region = pack / "acts" / "act-1" / "town"
    (region / "tiles").mkdir()
    one = _webp(b"pack-v1")
    two = _webp(b"pack-v2")
    (region / "tiles" / "grass.webp").write_bytes(one)
    (region / "tiles" / "grass.2.webp").write_bytes(two)

    html = cli.weave_html(pack)
    expect = [
        "data:image/webp;base64," + base64.b64encode(one).decode(),
        "data:image/webp;base64," + base64.b64encode(two).decode(),
    ]
    # '.' is the first open ground symbol, so it maps to grass.
    assert _baked(html, "VEFR_TILES")["."] == expect
    assert _baked(html, "VEFR_REGION_TILES")["town"]["."] == expect


def test_weave_bakes_a_single_png_pack_tile_as_a_string(tmp_path):
    pack = _copy_sample(tmp_path)
    region = pack / "acts" / "act-1" / "town"
    (region / "tiles").mkdir()
    (region / "tiles" / "grass.png").write_bytes(PNG_1X1)

    html = cli.weave_html(pack)
    expect = "data:image/png;base64," + base64.b64encode(PNG_1X1).decode()
    assert _baked(html, "VEFR_TILES")["."] == expect


def test_a_pack_with_no_tiles_bakes_the_engine_tiles_unchanged():
    """The hard rule: no tiles/ means the engine set, byte for byte."""
    load_world.cache_clear()
    html = cli.weave_html(SAMPLE)
    tiles = _baked(html, "VEFR_TILES")
    region_tiles = _baked(html, "VEFR_REGION_TILES")

    # Every value is the single-picture string shape.
    assert tiles and all(isinstance(v, str) for v in tiles.values())
    for by_symbol in region_tiles.values():
        assert all(isinstance(v, str) for v in by_symbol.values())

    # The old call shape (no pack, no region) resolves the engine set.
    world = {
        **json.loads((SAMPLE / "world.json").read_text(encoding="utf-8")),
        **load_pack(SAMPLE),
    }
    assert tiles == cli._player_tiles(world, WEB)
    assert region_tiles == cli._player_region_tiles(world, WEB)


def test_flat_shape_bakes_its_own_tiles(tmp_path):
    """A flat pack's tiles live at the pack root and surface in both
    VEFR_TILES and VEFR_REGION_TILES (the town region)."""
    pack = _write_flat_pack(tmp_path / "flat")
    (pack / "tiles").mkdir()
    mine = _webp(b"flat")
    (pack / "tiles" / "grass.webp").write_bytes(mine)

    html = cli.weave_html(pack)
    expect = "data:image/webp;base64," + base64.b64encode(mine).decode()
    assert _baked(html, "VEFR_TILES")["."] == expect
    assert _baked(html, "VEFR_REGION_TILES")["town"]["."] == expect


def test_flat_shape_without_tiles_bakes_as_before(tmp_path):
    """A flat pack with no tiles/ keeps its empty per-region contract
    tiles, byte for byte the shape it had before tiles existed."""
    pack = _write_flat_pack(tmp_path / "flat")
    assert _baked(cli.weave_html(pack), "VEFR_REGION_TILES") == {"town": {}}


def test_a_pack_tile_overrides_the_engine_tile(tmp_path):
    pack, region = _pack_region(tmp_path)
    (region / "tiles").mkdir()
    mine = _webp(b"mine")
    (region / "tiles" / "grass.webp").write_bytes(mine)

    out = cli._tiles_for_legend({".": {}}, [], WEB, region, pack)
    engine = cli._tiles_for_legend({".": {}}, [], WEB)
    assert out["."] == "data:image/webp;base64," + base64.b64encode(mine).decode()
    assert out["."] != engine["."]


def test_a_region_dir_alone_resolves_pack_tiles(tmp_path):
    """The 4th parameter is enough: a caller with only the region dir
    still gets its tiles, guarded against that directory."""
    pack, region = _pack_region(tmp_path)
    (region / "tiles").mkdir()
    mine = _webp(b"region-only")
    (region / "tiles" / "grass.webp").write_bytes(mine)

    out = cli._tiles_for_legend({".": {}}, [], WEB, region)
    assert out["."] == "data:image/webp;base64," + base64.b64encode(mine).decode()


def test_engine_tile_still_answers_when_the_pack_has_none(tmp_path):
    pack, region = _pack_region(tmp_path)  # no tiles/ directory

    out = cli._tiles_for_legend({".": {}}, [], WEB, region, pack)
    assert out == cli._tiles_for_legend({".": {}}, [], WEB)
    assert isinstance(out["."], str)


def test_act_id_may_differ_from_its_directory_name(tmp_path):
    """Pack tiles are found for an act whose world.json `id` is not its
    directory name, matching the loader's own convention."""
    pack = tmp_path / "renamed"
    act = pack / "acts" / "chapter-one"
    region = act / "town"
    region.mkdir(parents=True)
    (pack / "world.json").write_text(json.dumps({
        "title": "Renamed", "phases": {"dusk": "q", "dawn": "w"},
        "voices": {}, "bonds": {},
    }), encoding="utf-8")
    (act / "world.json").write_text(json.dumps({
        "id": "act-1", "title": "Renamed", "regions": ["town"],
        "speakers": {},
    }), encoding="utf-8")
    (region / "map.md").write_text("###\n#.#\n###\n", encoding="utf-8")
    (region / "contract.json").write_text(json.dumps({
        "legend": {".": {}}, "sanctuary_tiles": [], "hero_start": [1, 1],
    }), encoding="utf-8")
    (region / "tiles").mkdir()
    mine = _webp(b"renamed")
    (region / "tiles" / "grass.webp").write_bytes(mine)

    region_tiles = _baked(cli.weave_html(pack), "VEFR_REGION_TILES")
    assert region_tiles["town"]["."] == (
        "data:image/webp;base64," + base64.b64encode(mine).decode())


def test_tiles_never_read_outside_the_pack(tmp_path):
    """A picture that resolves outside the pack is skipped, not read.

    A symlink inside tiles/ is the only way a discovered name can point
    outside the pack; the real-path guard drops it. A traversal name the
    tiles dir does not hold is skipped the same way.
    """
    secret = tmp_path / "secret.webp"
    secret.write_bytes(_webp(b"secret-bytes"))
    b64 = base64.b64encode(secret.read_bytes()).decode()

    pack, region = _pack_region(tmp_path)
    (region / "tiles").mkdir()
    try:
        (region / "tiles" / "grass.webp").symlink_to(secret)
    except OSError:
        pytest.skip("this filesystem does not allow symlinks")

    out = cli._tiles_for_legend({".": {}}, [], WEB, region, pack)
    assert b64 not in json.dumps(out)

    # A name that could climb out of the pack is never read either.
    escaped = cli._tiles_for_legend(
        {".": {"tile": "../../../etc/passwd"}}, [], WEB, region, pack)
    assert "passwd" not in json.dumps(escaped)


# ----------------------------------------------------------- end to end

def _engine_tile(name: str) -> str:
    """The engine's own picture for a tile name, as the player bakes it."""
    f = WEB / "art" / "tiles" / f"{name}.webp"
    return "data:image/webp;base64," + base64.b64encode(f.read_bytes()).decode()


def test_woven_pack_with_tiles_carries_its_own_picture_end_to_end(tmp_path):
    """End to end: a pack that brings tiles bakes its bytes into the file.

    Weaves a copy of the sample pack carrying one grass picture, then
    reads both tile globals back out of the finished single file. '.' is
    the sample town's first open ground symbol, so it resolves to the
    pack's grass - in the legacy global and the region global - and not
    to the engine's grass.
    """
    pack = _copy_sample(tmp_path)
    region = pack / "acts" / "act-1" / "town"
    (region / "tiles").mkdir()
    mine = _webp(b"end-to-end-pack-picture")
    (region / "tiles" / "grass.webp").write_bytes(mine)

    html = cli.weave_html(pack)
    expect = "data:image/webp;base64," + base64.b64encode(mine).decode()
    assert _baked(html, "VEFR_TILES")["."] == expect
    assert _baked(html, "VEFR_REGION_TILES")["town"]["."] == expect
    assert expect != _engine_tile("grass")


def test_woven_pack_without_tiles_bakes_the_engine_pictures_unchanged():
    """End to end: no tiles/ bakes the engine set, string for string.

    Every value in both globals is a single data-URI string equal to the
    engine picture for its symbol, so the untouched pack bakes exactly
    what it baked before tiles existed.
    """
    html = cli.weave_html(SAMPLE)
    tiles = _baked(html, "VEFR_TILES")
    region_tiles = _baked(html, "VEFR_REGION_TILES")

    assert tiles
    assert all(isinstance(v, str) for v in tiles.values())
    for by_symbol in region_tiles.values():
        assert by_symbol
        assert all(isinstance(v, str) for v in by_symbol.values())

    # The sample town's legend, resolved by hand to the engine's own art.
    assert tiles == {
        ".": _engine_tile("grass"),
        "p": _engine_tile("path"),
        "#": _engine_tile("stone-wall"),
        "S": _engine_tile("grass"),
        "D": _engine_tile("rug"),
    }
    assert region_tiles["town"] == tiles

    # And the pack-aware bake equals the pack-free engine resolution.
    world = {
        **json.loads((SAMPLE / "world.json").read_text(encoding="utf-8")),
        **load_pack(SAMPLE),
    }
    assert tiles == cli._player_tiles(world, WEB)
    assert region_tiles == cli._player_region_tiles(world, WEB)
