"""Build a skinned fixture pack (sample world + a tiny synthetic skin).

Neutral engine-test canon only: solid-colour PNGs written with the standard library, so no image
library is needed. `build(dest)` returns the pack dir; its world.json declares
`"skin": "skins/test-skin"` and the skin folder sits inside the pack.
"""

import json
import shutil
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"


def png(w: int, h: int, rgb=(200, 170, 120)) -> bytes:
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


SKIN = {
    "name": "test-skin",
    "credit": "Rylee and Claude (a synthetic test skin)",
    "parts": {
        "panel": {"file": "panel.png", "slice": 16},
        "button": {"file": "button.png", "slice": 12, "hover": "button-hover.png",
                   "pressed": "button-pressed.png", "disabled": "button-disabled.png"},
        "bar": {"frame": "bar-frame.png", "fill": "bar-fill.png"},
        "cursor": {"file": "cursor.png", "hotspot": [2, 2]},
    },
    "ink": {"on_panel": "#2B2118", "on_panel_dim": "#5A4A38"},
}
FILES = {"panel.png": (64, 64), "button.png": (48, 32), "button-hover.png": (48, 32),
         "button-pressed.png": (48, 32), "button-disabled.png": (48, 32),
         "bar-frame.png": (96, 16), "bar-fill.png": (96, 16), "cursor.png": (32, 32)}


def build(dest: Path, skin=None, files=None, name="skin-test") -> Path:
    pack = dest / "worlds" / name
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    world["name"] = name
    world["skin"] = "skins/test-skin"
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")
    sk = pack / "skins" / "test-skin"
    sk.mkdir(parents=True)
    (sk / "skin.json").write_text(json.dumps(skin if skin is not None else SKIN), encoding="utf-8")
    for fname, (w, h) in (files if files is not None else FILES).items():
        (sk / fname).write_bytes(png(w, h))
    return pack


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
