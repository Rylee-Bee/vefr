"""maplab checks a pack's own tiles, with variants.

Phase C: a region may bring a `tiles/` directory of ground pictures.
`maplab.validate` must catch a legend entry that names a picture the
region does not have, a hole in the numbered variants, and a file the
loader cannot read - while a region with no tiles/ stays exactly as it
was (the silent engine fallback).
"""

from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

from vefr import maplab
from vefr.world import load_world

SAMPLE = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"

# A real 1x1 PNG, written by the test - no picture ships in the repo.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def _webp(marker: bytes) -> bytes:
    """A tiny file with a RIFF/WEBP signature; the validator only reads
    the name and the suffix, not the pixels."""
    return b"RIFF\x00\x00\x00\x00WEBPVP8 " + marker


def _copy_sample(tmp_path: Path) -> Path:
    pack = tmp_path / "sample-world"
    shutil.copytree(SAMPLE, pack)
    return pack


def _region(pack: Path) -> Path:
    return pack / "acts" / "act-1" / "town"


def _add_legend_tile(region: Path, symbol: str, tile_name: str) -> None:
    """Wire an explicit `"tile"` onto a symbol in the region contract."""
    contract = region / "contract.json"
    data = json.loads(contract.read_text(encoding="utf-8"))
    data["legend"][symbol] = {"tile": tile_name}
    contract.write_text(json.dumps(data), encoding="utf-8")


def _validate(pack: Path) -> list[str]:
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def test_unknown_tile_in_a_region_with_tiles_names_region_symbol_and_tile(tmp_path):
    pack = _copy_sample(tmp_path)
    region = _region(pack)
    (region / "tiles").mkdir()
    (region / "tiles" / "grass.webp").write_bytes(_webp(b"1"))
    _add_legend_tile(region, "~", "mossy-wall")

    errors = _validate(pack)
    assert any("town" in e and "~" in e and "mossy-wall" in e
               for e in errors), errors


def test_unknown_tile_without_a_tiles_dir_is_still_not_an_error(tmp_path):
    """The compatibility rule: no tiles/ keeps the silent fallback."""
    pack = _copy_sample(tmp_path)
    _add_legend_tile(_region(pack), "~", "mossy-wall")

    assert _validate(pack) == []


def test_variant_gap_names_the_missing_number(tmp_path):
    pack = _copy_sample(tmp_path)
    region = _region(pack)
    (region / "tiles").mkdir()
    (region / "tiles" / "stone-wall.3.webp").write_bytes(_webp(b"3"))

    errors = _validate(pack)
    assert any("town" in e and "stone-wall" in e and "2" in e
               for e in errors), errors


def test_unnumbered_with_number_two_is_not_a_gap(tmp_path):
    """Variant 1 is the unnumbered file and is optional."""
    pack = _copy_sample(tmp_path)
    region = _region(pack)
    (region / "tiles").mkdir()
    (region / "tiles" / "stone-wall.webp").write_bytes(_webp(b"1"))
    (region / "tiles" / "stone-wall.2.webp").write_bytes(_webp(b"2"))

    assert _validate(pack) == []


def test_numbered_only_two_and_three_is_not_a_gap(tmp_path):
    """A name with only numbered files is legal, and 2 + 3 is whole."""
    pack = _copy_sample(tmp_path)
    region = _region(pack)
    (region / "tiles").mkdir()
    (region / "tiles" / "floor.2.webp").write_bytes(_webp(b"2"))
    (region / "tiles" / "floor.3.webp").write_bytes(_webp(b"3"))

    assert _validate(pack) == []


def test_numbered_only_starting_at_two_is_not_a_gap(tmp_path):
    """floor.2 with no unnumbered file: variant 1 is optional, so the
    absence of the unnumbered picture is not a gap."""
    pack = _copy_sample(tmp_path)
    region = _region(pack)
    (region / "tiles").mkdir()
    (region / "tiles" / "floor.2.webp").write_bytes(_webp(b"2"))

    assert _validate(pack) == []


def test_numbered_only_two_and_four_names_the_missing_three(tmp_path):
    """A hole in the numbered sequence is a gap; 2 + 4 misses 3."""
    pack = _copy_sample(tmp_path)
    region = _region(pack)
    (region / "tiles").mkdir()
    (region / "tiles" / "floor.2.webp").write_bytes(_webp(b"2"))
    (region / "tiles" / "floor.4.webp").write_bytes(_webp(b"4"))

    errors = _validate(pack)
    assert ("region 'town': tile 'floor' has a variant gap - "
            "variant 3 is missing") in errors, errors


def test_numbered_only_starting_at_three_names_the_missing_two(tmp_path):
    """floor.3 alone: the sequence starts at 2, so 2 is the hole."""
    pack = _copy_sample(tmp_path)
    region = _region(pack)
    (region / "tiles").mkdir()
    (region / "tiles" / "floor.3.webp").write_bytes(_webp(b"3"))

    errors = _validate(pack)
    assert ("region 'town': tile 'floor' has a variant gap - "
            "variant 2 is missing") in errors, errors


def test_an_uppercase_webp_is_a_legal_tile(tmp_path):
    pack = _copy_sample(tmp_path)
    region = _region(pack)
    (region / "tiles").mkdir()
    (region / "tiles" / "Stone-Wall.WEBP").write_bytes(_webp(b"1"))
    (region / "tiles" / "Grass.PNG").write_bytes(PNG_1X1)
    _add_legend_tile(region, "~", "Stone-Wall")

    assert _validate(pack) == []


def test_unsupported_files_error_but_dotfiles_are_ignored(tmp_path):
    pack = _copy_sample(tmp_path)
    region = _region(pack)
    (region / "tiles").mkdir()
    (region / "tiles" / "grass.webp").write_bytes(_webp(b"1"))
    (region / "tiles" / "moss.gif").write_bytes(b"not a tile")
    (region / "tiles" / "notes.txt").write_bytes(b"not a tile either")
    (region / "tiles" / ".hidden.txt").write_bytes(b"hush")

    errors = _validate(pack)
    assert any("town" in e and "moss.gif" in e for e in errors), errors
    assert any("notes.txt" in e for e in errors), errors
    assert not any(".hidden" in e for e in errors), errors


def test_a_flat_pack_with_pack_level_tiles_is_checked(tmp_path):
    """A flat pack's tiles/ lives at the pack root and is checked the
    same way a region's tiles/ is."""
    pack = tmp_path / "flat"
    pack.mkdir()
    (pack / "world.json").write_text(json.dumps({
        "title": "Flat",
        "phases": {"dusk": "quiet", "dawn": "warm"},
        "voices": {},
        "bonds": {},
        "town": {
            "map": ["###", "#.#", "###"],
            "legend": {"#": {"solid": True}, ".": {}, "~": {"tile": "mossy-wall"}},
            "hero_start": [1, 1],
            "sanctuary_tiles": ["."],
            "water_by_phase": {"dusk": "low", "dawn": "low"},
            "flood_tiles": [],
        },
    }), encoding="utf-8")
    (pack / "tiles").mkdir()
    (pack / "tiles" / "grass.webp").write_bytes(_webp(b"1"))

    errors = maplab.validate(maplab.load_pack(pack), pack_dir=pack)
    assert any("town" in e and "~" in e and "mossy-wall" in e
               for e in errors), errors


def test_act_id_may_differ_from_its_directory_name(tmp_path):
    """An act whose world.json id is not its directory name still has
    its region's tiles/ checked (cli._act_dir_for's rule)."""
    pack = tmp_path / "renamed"
    act = pack / "acts" / "chapter-one"
    region = act / "town"
    region.mkdir(parents=True)
    (pack / "world.json").write_text(json.dumps({
        "title": "Renamed", "phases": {"dusk": "q", "dawn": "w"},
        "voices": {}, "bonds": {},
    }), encoding="utf-8")
    (act / "world.json").write_text(json.dumps({
        "id": "act-1", "title": "Renamed", "regions": ["town"], "speakers": {},
    }), encoding="utf-8")
    (region / "map.md").write_text("###\n#.#\n###\n", encoding="utf-8")
    (region / "contract.json").write_text(json.dumps({
        "hero_start": [1, 1],
        "sanctuary_tiles": ["."],
        "water_by_phase": {"dusk": "low", "dawn": "low"},
        "flood_tiles": [],
        "legend": {"#": {"solid": True}, ".": {}, "~": {"tile": "mossy-wall"}},
    }), encoding="utf-8")
    (region / "tiles").mkdir()
    (region / "tiles" / "grass.webp").write_bytes(_webp(b"1"))

    load_world.cache_clear()
    errors = maplab.validate(load_world(pack), pack_dir=pack)
    assert any("town" in e and "mossy-wall" in e for e in errors), errors


def test_shipped_sample_world_still_validates_green():
    assert _validate(SAMPLE) == []


def test_norns_validate_reaches_the_tile_check(tmp_path, capsys):
    """`norns validate` funnels through maplab.cmd_validate, which calls
    validate(load_pack(pack), pack_dir=pack); the tile error surfaces."""
    pack = _copy_sample(tmp_path)
    region = _region(pack)
    (region / "tiles").mkdir()
    (region / "tiles" / "grass.webp").write_bytes(_webp(b"1"))
    _add_legend_tile(region, "~", "mossy-wall")

    rc = maplab.main(["validate", "--pack", str(pack)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "mossy-wall" in out


def test_a_tile_name_that_climbs_out_never_resolves_and_is_reported(tmp_path):
    """A legend tile like '../../../etc/passwd' (or one with a NUL byte) must be reported as an
    unknown tile, never resolved against the filesystem (CodeQL py/path-injection hardening)."""
    pack = _copy_sample(tmp_path)
    region = _region(pack)
    (region / "tiles").mkdir()
    (region / "tiles" / "grass.webp").write_bytes(_webp(b"1"))
    _add_legend_tile(region, "~", "../../../../etc/passwd")
    _add_legend_tile(region, "^", "bad\x00name")

    errors = _validate(pack)
    assert any("~" in e and "passwd" in e for e in errors), errors
    assert any("^" in e for e in errors), errors
