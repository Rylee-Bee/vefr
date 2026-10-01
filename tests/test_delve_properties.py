"""Property-based tests for the deterministic dungeon-floor generator.

These assert the invariants `generate_floor` promises in its docstring
hold for arbitrary seeds and small dimensions, not just the examples in
`test_delve.py`. The generator is build-time, not hot-path, so we keep
example counts modest and the deadline off.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
import pytest

from vefr import delve


# The alphabet `generate_floor` emits. Every row must be a string over
# exactly these four characters.
_LEGEND_CHARS = frozenset("#.ud")

# Walkable tiles: anything the hero can step on.
_WALKABLE = frozenset(".ud")

# Small dimensions keep each example fast while still exercising rooms,
# corridors, and stair placement. `rooms` starts at 1 so the generator
# actually places at least one chamber.
_SEEDS = st.text(min_size=1, max_size=24)
_WIDTHS = st.integers(min_value=8, max_value=24)
_HEIGHTS = st.integers(min_value=8, max_value=24)
_ROOMS = st.integers(min_value=1, max_value=8)


def _stairs(rows: list[str]) -> tuple[tuple[int, int] | None,
                                      tuple[int, int] | None]:
    """The (up, down) stair tiles a floor carries; either may be None."""
    up = down = None
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "u":
                up = (x, y)
            elif ch == "d":
                down = (x, y)
    return up, down


def _flood(rows: list[str], start: tuple[int, int]) -> set[tuple[int, int]]:
    """Every non-wall tile reachable from `start` by cardinal moves."""
    seen = {start}
    stack = [start]
    height, width = len(rows), len(rows[0])
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (0 <= nx < width and 0 <= ny < height
                    and rows[ny][nx] != "#" and (nx, ny) not in seen):
                seen.add((nx, ny))
                stack.append((nx, ny))
    return seen


# ------------------------------------------------------------- the properties


@given(seed=_SEEDS, width=_WIDTHS, height=_HEIGHTS, rooms=_ROOMS)
@settings(max_examples=50, deadline=None)
def test_determinism(seed, width, height, rooms):
    """The same (seed, width, height, rooms) always draws the same rows."""
    a = delve.generate_floor(seed, width=width, height=height, rooms=rooms)
    b = delve.generate_floor(seed, width=width, height=height, rooms=rooms)
    assert a == b


@given(seed=_SEEDS, width=_WIDTHS, height=_HEIGHTS, rooms=_ROOMS)
@settings(max_examples=50, deadline=None)
def test_border_is_wall(seed, width, height, rooms):
    """Row 0, the last row, column 0 and the last column are all `#`."""
    rows = delve.generate_floor(seed, width=width, height=height, rooms=rooms)
    assert rows[0] == "#" * width
    assert rows[-1] == "#" * width
    assert all(r[0] == "#" and r[-1] == "#" for r in rows)


@given(seed=_SEEDS, width=_WIDTHS, height=_HEIGHTS, rooms=_ROOMS)
@settings(max_examples=50, deadline=None)
def test_shape_and_alphabet(seed, width, height, rooms):
    """`height` rows of `width`; every character is one of `#`, `.`, `u`, `d`."""
    rows = delve.generate_floor(seed, width=width, height=height, rooms=rooms)
    assert len(rows) == height
    assert all(len(r) == width for r in rows)
    assert set("".join(rows)) <= _LEGEND_CHARS


@given(seed=_SEEDS, width=_WIDTHS, height=_HEIGHTS, rooms=_ROOMS)
@settings(max_examples=50, deadline=None)
def test_reachability(seed, width, height, rooms):
    """Every walkable tile is reachable from the up-stair by flood fill."""
    rows = delve.generate_floor(seed, width=width, height=height, rooms=rooms)
    up, _ = _stairs(rows)
    assert up is not None, "a generated floor must have an up-stair"
    seen = _flood(rows, up)
    walkable = {(x, y) for y, r in enumerate(rows)
                for x, c in enumerate(r) if c in _WALKABLE}
    assert seen == walkable


@given(seed=_SEEDS, width=_WIDTHS, height=_HEIGHTS, rooms=_ROOMS)
@settings(max_examples=50, deadline=None)
def test_stairs(seed, width, height, rooms):
    """Exactly one `u` and one `d`; distinct and reachable from each other."""
    rows = delve.generate_floor(seed, width=width, height=height, rooms=rooms)
    u_count = sum(r.count("u") for r in rows)
    d_count = sum(r.count("d") for r in rows)
    assert u_count == 1
    assert d_count == 1
    up, down = _stairs(rows)
    assert up is not None and down is not None
    assert up != down
    assert down in _flood(rows, up)


# ------------------------------------------------------- rejects tiny floors


@pytest.mark.parametrize(
    "width, height, rooms",
    [
        (4, 20, 8),    # width too small
        (30, 4, 8),    # height too small
        (3, 3, 8),     # both too small
        (30, 20, 0),   # no rooms
        (30, 20, -1),  # negative rooms
    ],
)
def test_rejects_tiny_floors(width, height, rooms):
    with pytest.raises(ValueError):
        delve.generate_floor("tiny", width=width, height=height, rooms=rooms)
