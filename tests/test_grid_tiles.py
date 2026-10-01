"""A grid tile: one picture drawn as a block of cells, chosen by position.

`wood-floor.grid3x3.webp` is ONE picture. The weaver inlines it once with its cell counts and the player
draws cell (x mod cols, y mod rows), so a floor painted as one scene repeats only every few tiles. These
tests cover naming (valid and invalid), discovery, the baked shape, the validator and the real player
function (run in node).
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from vefr import cli, maplab
from vefr.world import TILE_GRID_MAX, _discover_tiles, tile_grid

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "worlds" / "sample-world"
PACKAGED = ROOT / "web" / "packaged.html"
HARNESS = Path(__file__).resolve().parent / "fixtures" / "grid_harness.mjs"


def _webp(marker: bytes) -> bytes:
    return b"RIFF\x00\x00\x00\x00WEBPVP8 " + marker


def _copy_sample(tmp_path: Path) -> Path:
    pack = tmp_path / "sample-world"
    shutil.copytree(SAMPLE, pack)
    return pack


def _baked(html: str, name: str):
    prefix = f"window.{name} = "
    line = next(ln for ln in html.splitlines() if ln.startswith(prefix))
    return json.loads(line[len(prefix):].rstrip(";"))


def _validate(pack: Path) -> list[str]:
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


# ---- naming ----

@pytest.mark.parametrize("stem,expect", [
    ("wood.grid3x3", ("wood", 3, 3)),
    ("stone-wall.grid2x4", ("stone-wall", 2, 4)),
    ("a.b.grid8x8", ("a.b", 8, 8)),
    ("wood.grid1x2", ("wood", 1, 2)),
])
def test_valid_grid_names(stem, expect):
    assert tile_grid(stem) == expect


@pytest.mark.parametrize("stem", [
    "wood", "wood.2", "wood.grid1x1", "wood.grid0x3", "wood.grid9x3", "wood.grid3x9",
    "wood.grid3", "wood.gridaxb", "grid3x3", "wood.grid3x3x3",
])
def test_everything_else_is_not_a_grid(stem):
    assert tile_grid(stem) is None
    assert TILE_GRID_MAX == 8


# ---- discovery ----

def test_a_grid_picture_is_listed_first_and_wins(tmp_path):
    t = tmp_path / "tiles"
    t.mkdir()
    for n in ("wood.webp", "wood.2.webp", "wood.grid3x3.webp", "wall.webp"):
        (t / n).write_bytes(_webp(n.encode()))
    found = _discover_tiles(t)
    assert found["wood"][0] == "wood.grid3x3.webp"
    assert found["wall"] == ["wall.webp"]
    assert "wood.grid3x3" not in found


# ---- the baked shape ----

def test_weave_bakes_a_grid_as_one_object_with_its_cell_counts(tmp_path):
    pack = _copy_sample(tmp_path)
    region = pack / "acts" / "act-1" / "town"
    (region / "tiles").mkdir()
    pic = _webp(b"grid-picture")
    (region / "tiles" / "grass.grid3x3.webp").write_bytes(pic)
    html = cli.weave_html(pack)
    expect = {"src": "data:image/webp;base64," + base64.b64encode(pic).decode(), "cols": 3, "rows": 3}
    assert _baked(html, "VEFR_TILES")["."] == expect
    assert _baked(html, "VEFR_REGION_TILES")["town"]["."] == expect


def test_the_grid_wins_over_variants_of_the_same_name(tmp_path):
    pack = _copy_sample(tmp_path)
    region = pack / "acts" / "act-1" / "town"
    (region / "tiles").mkdir()
    (region / "tiles" / "grass.webp").write_bytes(_webp(b"one"))
    (region / "tiles" / "grass.2.webp").write_bytes(_webp(b"two"))
    (region / "tiles" / "grass.grid2x2.png").write_bytes(b"\x89PNG-grid")
    baked = _baked(cli.weave_html(pack), "VEFR_TILES")["."]
    assert isinstance(baked, dict) and (baked["cols"], baked["rows"]) == (2, 2)
    assert baked["src"].startswith("data:image/png;base64,")


def test_a_pack_with_no_grid_bakes_exactly_as_before(tmp_path):
    """Strings and lists stay strings and lists: only a grid name makes an object."""
    pack = _copy_sample(tmp_path)
    region = pack / "acts" / "act-1" / "town"
    (region / "tiles").mkdir()
    (region / "tiles" / "grass.webp").write_bytes(_webp(b"one"))
    baked = _baked(cli.weave_html(pack), "VEFR_TILES")["."]
    assert isinstance(baked, str)


# ---- the validator ----

def _tiles_with(tmp_path, *names):
    pack = _copy_sample(tmp_path)
    tiles = pack / "acts" / "act-1" / "town" / "tiles"
    tiles.mkdir()
    for n in names:
        (tiles / n).write_bytes(_webp(n.encode()))
    return pack


def test_a_good_grid_validates(tmp_path):
    assert not [e for e in _validate(_tiles_with(tmp_path, "grass.grid3x3.webp")) if "grid" in e]


@pytest.mark.parametrize("name", ["grass.grid1x1.webp", "grass.grid9x3.webp", "grass.grid0x2.webp"])
def test_a_bad_grid_name_is_reported_by_file(tmp_path, name):
    errors = _validate(_tiles_with(tmp_path, name))
    assert any(name in e and "not a valid grid" in e for e in errors), errors


def test_a_grid_beside_variants_is_reported(tmp_path):
    errors = _validate(_tiles_with(tmp_path, "grass.grid3x3.webp", "grass.2.webp"))
    assert any("grass" in e and "grid picture AND other pictures" in e for e in errors), errors


# ---- the real player function ----

@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_pick_cell_is_positional_periodic_and_safe_for_negatives():
    out = json.loads(subprocess.run(["node", str(HARNESS), str(PACKAGED)],
                                    capture_output=True, text=True, check=True, timeout=30).stdout)
    for y in range(7):
        for x in range(7):
            assert out["grid"][y][x] == [x % 3, y % 3]
    assert out["negatives"] == [[2, 2], [0, 2], [2, 2]]
    assert out["wide"] == [[0, 0], [1, 1], [2, 1]]


def test_the_player_draws_a_grid_cell_from_the_one_picture():
    """The loader and draw wiring ships in the page (asserted from source, like the variant wiring)."""
    src = PACKAGED.read_text(encoding="utf-8")
    assert "tileGrids[ch] = { img: gim, cols: cols, rows: rows };" in src
    assert "ctx.drawImage(grid.img, cell[0] * cw, cell[1] * chh, cw, chh, x * T, y * T, T, T);" in src
