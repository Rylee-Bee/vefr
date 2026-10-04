"""Walk sheets, phase B of design/pack-art-proposal.md (Cottage release 1, plan W1). FROZEN CONTRACT.

A pack may put a sprite sheet next to a sprite:
  sprites/<key>.png            the single picture (still the fallback)
  sprites/<key>-sheet.png      the frames, numbered left to right, top to bottom
  sprites/<key>.sheet.json     {"image": "<key>-sheet.png", "frame": [w, h], "fps": 8,
                                "directions": {"down": {"idle": [0], "walk": [1,2,3,4]}, "left": ..., "right": ..., "up": ...}}
  - `*.sheet.json` files are never sprites themselves. A missing `left`/`right` is the other side mirrored; a
    missing `up` falls back to `down`; `down` is required.
  - validator: image must exist beside it; frame two ints 8..512; fps int 1..30; every index an int inside the
    sheet's grid (image size / frame size); idle exactly one index; walk 2..16 indexes. Plain sentences naming the
    sheet file.
  - weave: window.VEFR_SPRITE_SHEETS = {<key>: {image: data URI, frame, fps, directions}} — `{}` for a pack with no sheets.
  - player: window.VEFR_HERO_FRAME = {dir, state: "idle"|"walk", frame: <sheet index>, mirrored: bool} exists only when the
    hero has a sheet. Facing the hero's last move (down at the start); standing shows `idle`; a step shows a `walk`
    frame of that direction; it returns to `idle` after the step settles. A missing side is drawn mirrored
    (`mirrored: true`). No sheet: Phase A hop as today, no VEFR_HERO_FRAME.
Neutral fixtures only.
"""

import json
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from vefr import cli, maplab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_lock_pack as mk  # noqa: E402

HARNESS = ROOT / "tests" / "fixtures" / "walk_harness.mjs"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def png(w, h, rgb=(180, 60, 60)):
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


SHEET = {"image": "hero-sheet.png", "frame": [32, 32], "fps": 8,
         "directions": {"down": {"idle": [0], "walk": [1, 2, 3, 4]},
                        "right": {"idle": [10], "walk": [11, 12, 13, 14]},
                        "up": {"idle": [15], "walk": [16, 17, 18, 19]}}}   # left is the mirror of right


def build(tmp_path, sheet=SHEET, image_size=(160, 128), with_image=True):
    pack = mk.build(tmp_path)
    sp = pack / "sprites"
    (sp / "hero.png").write_bytes(png(1, 1))
    wj = pack / "world.json"
    cfg = json.loads(wj.read_text(encoding="utf-8"))
    cfg["player"]["sprites"]["hero"] = "sprites/hero.png"
    wj.write_text(json.dumps(cfg), encoding="utf-8")
    if sheet is not None:
        (sp / "hero.sheet.json").write_text(json.dumps(sheet), encoding="utf-8")
        if with_image:
            (sp / "hero-sheet.png").write_bytes(png(*image_size))
    return pack


def extra_errors(tmp_path, **kw):
    bpack = build(tmp_path / "b", sheet=None)
    base = maplab.validate(maplab.load_pack(bpack), pack_dir=bpack)
    pack = build(tmp_path / "x", **kw)
    return [e for e in maplab.validate(maplab.load_pack(pack), pack_dir=pack) if e not in base]


# --- validator -------------------------------------------------------------------------------

def test_a_good_sheet_validates(tmp_path):
    assert extra_errors(tmp_path) == []


def test_no_sheet_is_unchanged(tmp_path):
    assert extra_errors(tmp_path, sheet=None) == []


def mod(**over):
    s = json.loads(json.dumps(SHEET))
    for k, v in over.items():
        s[k] = v
    return s


@pytest.mark.parametrize("sheet,needle", [
    (mod(frame=[32]), "hero.sheet.json"),
    (mod(frame=[2, 2]), "hero.sheet.json"),
    (mod(fps=0), "hero.sheet.json"),
    (mod(directions={"left": SHEET["directions"]["right"]}), "down"),                 # down required
    (mod(directions={"down": {"idle": [0, 1], "walk": [1, 2]}}), "idle"),
    (mod(directions={"down": {"idle": [0], "walk": [1]}}), "walk"),
    (mod(directions={"down": {"idle": [0], "walk": [1, 2, 99]}}), "99"),              # outside the grid
    (mod(image="missing.png"), "missing.png"),
])
def test_bad_sheets_are_named(tmp_path, sheet, needle):
    errs = extra_errors(tmp_path, sheet=sheet)
    assert any(needle in e for e in errs), errs


# --- loader and weave -----------------------------------------------------------------------

def test_a_sheet_json_is_not_a_sprite_and_the_sheet_is_baked(tmp_path):
    pack = build(tmp_path)
    html = cli.weave_html(pack)
    assert '"hero.sheet"' not in html and '"hero-sheet"' not in html   # not baked as sprite keys
    assert "window.VEFR_SPRITE_SHEETS" in html
    assert "data:image/png;base64," in html.split("window.VEFR_SPRITE_SHEETS", 1)[1][:2000]


def test_a_pack_with_no_sheets_bakes_an_empty_map(tmp_path):
    html = cli.weave_html(build(tmp_path, sheet=None))
    assert "window.VEFR_SPRITE_SHEETS = {}" in html


# --- player ------------------------------------------------------------------------------------

def play(tmp_path, steps, **kw):
    pack = build(tmp_path, **kw)
    html = tmp_path / "walk.html"
    html.write_text(cli.weave_html(pack), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(html), json.dumps({"steps": steps})],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_standing_then_a_step_then_standing(tmp_path):
    r = play(tmp_path, ["right"])
    assert r["errors"] == []
    assert r["sheets"] == ["hero"]
    assert r["start"] == {"dir": "down", "state": "idle", "frame": 0, "mirrored": False}
    d = r["during"][0]
    assert d["dir"] == "right" and d["state"] == "walk" and d["frame"] in (11, 12, 13, 14) and d["mirrored"] is False
    assert r["settled"] == {"dir": "right", "state": "idle", "frame": 10, "mirrored": False}


def test_a_missing_side_is_the_other_mirrored(tmp_path):
    r = play(tmp_path, ["left"])
    d = r["during"][0]
    assert d["dir"] == "left" and d["state"] == "walk" and d["frame"] in (11, 12, 13, 14) and d["mirrored"] is True
    assert r["settled"]["frame"] == 10 and r["settled"]["mirrored"] is True


def test_up_uses_its_own_frames(tmp_path):
    r = play(tmp_path, ["up"])
    d = r["during"][0]
    assert d["dir"] == "up" and d["frame"] in (16, 17, 18, 19)


def test_a_pack_without_a_sheet_has_no_frame_snapshot(tmp_path):
    r = play(tmp_path, ["right"], sheet=None)
    assert r["sheets"] == [] and r["start"] is None and r["settled"] is None
    assert r["errors"] == []
