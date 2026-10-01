"""Characters can have their own size: `player.sprite_scale` in world.json.

A pack may say `{"hearth-cat": 0.5}` to draw that character at half height (feet on the tile). Anything not listed, and any
bad entry, stays at the standard size (1.0, which is 1.5 tiles tall). The bake keeps only sane numbers, the validator reports
the rest in plain sentences, and the player draws residents, monsters and the hero through one pure function.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from vefr import cli, maplab

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "worlds" / "sample-world"
PACKAGED = ROOT / "web" / "packaged.html"
HARNESS = Path(__file__).resolve().parent / "fixtures" / "sprite_scale_harness.mjs"


def _pack(tmp_path: Path, scales=None, sprites=None) -> Path:
    pack = tmp_path / "pack"
    shutil.copytree(SAMPLE, pack)
    data = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    player = data.setdefault("player", {})
    player["sprites"] = sprites if sprites is not None else {"hero": "sprites/hero.png", "keeper": "sprites/keeper.png"}
    if scales is not None:
        player["sprite_scale"] = scales
    (pack / "world.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (pack / "sprites").mkdir(exist_ok=True)
    png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")
    for name in ("hero", "keeper"):
        (pack / "sprites" / f"{name}.png").write_bytes(png)
    return pack


def _baked(html: str, name: str):
    prefix = f"window.{name} = "
    line = next(ln for ln in html.splitlines() if ln.startswith(prefix))
    return json.loads(line[len(prefix):].rstrip(";"))


# ---- the bake ----

def test_a_pack_with_scales_bakes_them(tmp_path):
    html = cli.weave_html(_pack(tmp_path, {"keeper": 0.5, "hero": 1.2}))
    assert _baked(html, "VEFR_SPRITE_SCALE") == {"keeper": 0.5, "hero": 1.2}


def test_a_pack_with_no_scales_bakes_an_empty_object(tmp_path):
    assert _baked(cli.weave_html(_pack(tmp_path)), "VEFR_SPRITE_SCALE") == {}


def test_only_sane_numbers_are_baked(tmp_path):
    bad = {"a": 0.1, "b": 3, "c": "0.5", "d": True, "e": None, "f": -1, "keeper": 0.9}
    assert _baked(cli.weave_html(_pack(tmp_path, bad)), "VEFR_SPRITE_SCALE") == {"keeper": 0.9}


def test_the_sample_world_still_weaves_and_has_no_scales():
    assert _baked(cli.weave_html(SAMPLE), "VEFR_SPRITE_SCALE") == {}


# ---- the validator ----

def _errors(pack: Path) -> list[str]:
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def test_a_good_scale_validates(tmp_path):
    assert not [e for e in _errors(_pack(tmp_path, {"keeper": 0.5})) if "sprite_scale" in e]


def test_no_scale_block_validates(tmp_path):
    assert not [e for e in _errors(_pack(tmp_path)) if "sprite_scale" in e]


@pytest.mark.parametrize("value", [0.1, 2.5, "big", True, None])
def test_an_out_of_range_or_wrong_type_value_is_reported(tmp_path, value):
    errors = [e for e in _errors(_pack(tmp_path, {"keeper": value})) if "sprite_scale" in e]
    assert errors and "'keeper'" in errors[0] and "0.2 to 2" in errors[0]


def test_a_name_with_no_picture_is_reported(tmp_path):
    errors = [e for e in _errors(_pack(tmp_path, {"ghost": 0.5})) if "sprite_scale" in e]
    assert errors == ["player.sprite_scale names 'ghost', which has no picture in player.sprites"]


def test_a_non_object_is_reported(tmp_path):
    errors = [e for e in _errors(_pack(tmp_path, [0.5])) if "sprite_scale" in e]
    assert errors and "must be an object" in errors[0]


# ---- the player ----

@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_real_spritescale_function_trusts_only_sane_numbers():
    out = json.loads(subprocess.run(["node", str(HARNESS), str(PACKAGED)], capture_output=True, text=True,
                                    check=True, timeout=30).stdout)
    assert out["cat"] == 0.5 and out["big"] == 1.5
    for k in ("tiny", "huge", "nan", "inf", "str", "nul", "neg", "absent", "noScales", "nullScales"):
        assert out[k] == 1, k


def test_residents_monsters_and_the_hero_are_drawn_through_the_function():
    src = PACKAGED.read_text(encoding="utf-8")
    assert "var h = T * 1.5 * spriteScale(window.VEFR_SPRITE_SCALE, key);" in src       # drawSprite: residents and monsters
    assert "var baseH = T * 1.5 * spriteScale(window.VEFR_SPRITE_SCALE, 'hero');" in src  # the hero's own path
