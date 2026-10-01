"""A grid tile in a real browser: the woven player paints the cells of ONE picture.

The pack brings `grass.grid3x3.png`: a picture of nine different flat colours, one per cell. After the
player draws the town, every one of the nine colours must be on the canvas (the cells really come from
the one picture), and the single-picture grass the engine would otherwise draw must not be what shows.
"""

import argparse
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.request
import zlib
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

# Nine colours far apart from each other and from the engine's grass, in row-major cell order.
CELLS = [(250, 0, 0), (0, 250, 0), (0, 0, 250),
         (250, 250, 0), (250, 0, 250), (0, 250, 250),
         (250, 125, 0), (125, 0, 250), (250, 250, 250)]
CELL_PX = 8


def _png(cells, cols, rows, px):
    """A tiny RGB PNG, cols x rows cells of px x px each, with the standard library only."""
    w, h = cols * px, rows * px
    raw = b""
    for y in range(h):
        raw += b"\x00" + b"".join(bytes(cells[(y // px) * cols + x // px]) for x in range(w))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def woven(tmp_path_factory):
    home = tmp_path_factory.mktemp("grid-tiles-home")
    pack = home / "pack"
    shutil.copytree(SAMPLE, pack)
    tiles = pack / "acts" / "act-1" / "town" / "tiles"
    tiles.mkdir()
    (tiles / "grass.grid3x3.png").write_bytes(_png(CELLS, 3, 3, CELL_PX))
    rc = cli.cmd_build_web(argparse.Namespace(
        pack=str(pack), out=str(home / "grid.html"), pool=0, with_bundle=False, from_live=None))
    assert rc == 0
    port = _free_port()
    log = open(home / "server.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(home)],
        stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/grid.html"
    for _ in range(120):
        try:
            urllib.request.urlopen(url, timeout=2)
            break
        except Exception:  # noqa: BLE001 - not up yet
            time.sleep(0.25)
    else:
        proc.terminate()
        pytest.fail(f"the woven file never came up; see {home / 'server.log'}")
    yield url
    proc.terminate()
    proc.wait(timeout=10)


def test_all_nine_cells_of_the_one_picture_reach_the_canvas(page, woven):
    page.goto(woven)
    page.get_by_role("button", name="Begin").click()
    page.wait_for_function("window.VEFR_COMBAT && window.VEFR_COMBAT.region")
    page.wait_for_timeout(600)  # the picture decodes, then the map redraws
    found = page.evaluate(
        """(cells) => {
          const c = document.querySelector('#play canvas') || document.querySelector('canvas');
          const g = c.getContext('2d');
          const d = g.getImageData(0, 0, c.width, c.height).data;
          const seen = cells.map(() => 0);
          for (let i = 0; i < d.length; i += 4 * 3) {
            for (let k = 0; k < cells.length; k++) {
              const [r, gg, b] = cells[k];
              if (Math.abs(d[i] - r) < 6 && Math.abs(d[i + 1] - gg) < 6 && Math.abs(d[i + 2] - b) < 6) seen[k]++;
            }
          }
          return seen;
        }""",
        [list(c) for c in CELLS])
    missing = [CELLS[k] for k, n in enumerate(found) if n == 0]
    assert not missing, f"cells never drawn: {missing}; counts {found}"
