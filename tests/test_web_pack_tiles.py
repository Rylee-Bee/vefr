"""The woven player's tile variants, executed for real.

Phase C lets a pack bring several pictures for one legend symbol. A
symbol maps to either one data-URI string (one picture, the old shape)
or a list of data-URI strings in variant order. The player picks one
deterministically from the tile's own map coordinates, so the same cell
always shows the same picture; a symbol with a single picture keeps
drawing index 0, exactly as it did before variants existed.

This closes the gap the same way tests/test_web_packaged.py does: it
extracts the REAL window.pickVariant helper from web/packaged.html
between its marker comments and runs it in a node vm sandbox that needs
no npm packages, then checks it against a Python mirror cell by cell.
The loader/draw wiring is asserted from the shipped source text.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGED = ROOT / "web" / "packaged.html"
HARNESS = Path(__file__).resolve().parent / "fixtures" / "tiles_harness.mjs"
COUNTS = (1, 2, 3, 5)

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)


def _js_grids() -> dict[str, list[list[int]]]:
    """The 16x16 pick grids the shipped helper produces, keyed by count."""
    result = subprocess.run(
        ["node", str(HARNESS), str(PACKAGED)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"tiles harness failed:\n{result.stdout}\n{result.stderr}")
    return json.loads(result.stdout)


def _mirror(x: int, y: int, n: int) -> int:
    """The Python statement of the shipped unsigned-32-bit hash."""
    h = ((x * 73856093) & 0xFFFFFFFF) ^ ((y * 19349663) & 0xFFFFFFFF)
    return (h & 0xFFFFFFFF) % n


def test_load_tiles_accepts_a_string_or_a_list():
    """The loader normalizes both shapes to a list of Images, and the
    draw loop resolves one image through pickVariant at the cell."""
    src = PACKAGED.read_text(encoding="utf-8")
    # The loader wraps a lone string and keeps a list as-is.
    assert "if (typeof srcs === 'string') srcs = [srcs];" in src
    assert "if (!Array.isArray(srcs)) return;" in src
    # The draw loop picks from the tile's own coordinates.
    assert "imgs[pickVariant(x, y, imgs.length)]" in src
    # The old single-image shape is gone from the draw loop: nothing
    # assigns the bare symbol image to `tile` anymore.
    assert "var tile = tileImgs[ch];" not in src


def test_pick_variant_is_deterministic_and_in_range():
    grids = _js_grids()
    assert set(grids) == {str(n) for n in COUNTS}
    for n in COUNTS:
        grid = grids[str(n)]
        assert len(grid) == 16
        for row in grid:
            assert len(row) == 16
            for v in row:
                assert isinstance(v, int)
                assert 0 <= v < n


def test_a_single_picture_always_picks_index_zero():
    """One picture must behave exactly as today: index 0 everywhere."""
    grid = _js_grids()["1"]
    assert all(v == 0 for row in grid for v in row)


def test_js_and_python_pick_variant_agree_on_every_cell():
    """The shipped helper and the Python mirror are the same function.

    Checked on all 256 cells of a 16x16 grid for counts 2, 3 and 5. Any
    disagreement names the exact cell instead of papering over it.
    """
    grids = _js_grids()
    mismatches = []
    for n in (2, 3, 5):
        for y in range(16):
            for x in range(16):
                js = grids[str(n)][y][x]
                py = _mirror(x, y, n)
                if js != py:
                    mismatches.append((n, x, y, js, py))
    assert not mismatches, (
        "JS and Python pickVariant disagree (count, x, y, js, py): "
        f"{mismatches[:8]}"
    )
