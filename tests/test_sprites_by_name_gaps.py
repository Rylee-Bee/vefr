"""Sprites by name: the gaps the plan builder found in the first contract (docs/plans/tighten-shapes/PLAN.md, B0). FROZEN.

  - `player.sprite_scale` may name any sprite that exists by name, not only keys listed in `player.sprites` (Cottage
    has 18 such keys; today the validator refuses a key that is not listed).
  - The hero's walk sheet (`sprites/hero.sheet.json` + `hero-sheet.png`) keeps baking when `hero` is found by name:
    VEFR_SPRITE_SHEETS has `hero`, and VEFR_SPRITES has `hero` (the player always references `hero`).
  - A pack that lists everything explicitly bakes exactly the files it lists, byte for byte.
"""

import base64
import json
import re
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_interact_pack as mk  # noqa: E402

from vefr import cli, maplab  # noqa: E402


def png(w, h, rgb=(180, 60, 60)):
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def baked(html, name):
    m = re.search(r"window\.%s = (\{.*?\});\n" % name, html, re.S)
    return json.loads(m.group(1)) if m else {}


def build(tmp_path, *, drop=True, scale=None):
    pack = mk.build(tmp_path)
    p = pack / "world.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    if drop:
        cfg["player"].pop("sprites", None)
    if scale is not None:
        cfg["player"]["sprite_scale"] = scale
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return pack


def test_a_scale_may_name_a_sprite_found_by_name(tmp_path):
    pack = build(tmp_path, scale={"rat": 0.5})
    errs = maplab.validate(maplab.load_pack(pack), pack_dir=pack)
    assert not [e for e in errs if "sprite_scale" in e or "scale" in e.lower()], errs


def test_a_scale_naming_nothing_at_all_is_still_refused(tmp_path):
    pack = build(tmp_path, scale={"no-such-picture": 0.5})
    errs = maplab.validate(maplab.load_pack(pack), pack_dir=pack)
    assert any("no-such-picture" in e for e in errs), errs


def test_the_hero_keeps_its_walk_sheet_when_found_by_name(tmp_path):
    pack = build(tmp_path)
    sp = pack / "sprites"
    (sp / "hero.png").write_bytes(png(1, 1))
    (sp / "hero-sheet.png").write_bytes(png(160, 128))
    (sp / "hero.sheet.json").write_text(json.dumps({
        "image": "hero-sheet.png", "frame": [32, 32], "fps": 8,
        "directions": {"down": {"idle": [0], "walk": [1, 2, 3, 4]}}}), encoding="utf-8")
    html = cli.weave_html(pack)
    assert "hero" in baked(html, "VEFR_SPRITES")
    assert list(baked(html, "VEFR_SPRITE_SHEETS")) == ["hero"]


def test_an_explicit_pack_bakes_exactly_its_files(tmp_path):
    pack = build(tmp_path, drop=False)
    html = cli.weave_html(pack)
    got = baked(html, "VEFR_SPRITES")
    cfg = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    for key, rel in cfg["player"]["sprites"].items():
        want = "data:image/png;base64," + base64.b64encode((pack / rel).read_bytes()).decode()
        assert got[key] == want, key
    assert set(got) == set(cfg["player"]["sprites"])
