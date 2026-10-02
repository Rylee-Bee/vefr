"""Random floors, R1: `generate_floor_v2` (design/random-floors.md).

Same shape as today's floors (rooms, corridors, a solid border, `u` and `d` far apart,
everything connected) but drawn ONLY from `delve.prng`, so a JavaScript twin can draw the
same rows. The old `generate_floor` must stay byte-identical (its output is pinned below by
hashes taken before this work), so every floor `norns delve` already baked is unchanged.
"""

import hashlib
from collections import deque

import pytest

from vefr import delve

SIZES = [(30, 20, 8), (48, 32, 10), (20, 20, 3), (64, 64, 16), (40, 28, 9)]
SEEDS = [f"seed-{i}" for i in range(24)]


def _bfs(rows):
    h, w = len(rows), len(rows[0])
    start = next((x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == "u")
    seen, q = {start}, deque([start])
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and rows[ny][nx] != "#" and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


@pytest.mark.parametrize("w,h,rooms", SIZES)
def test_every_floor_is_well_formed_and_connected(w, h, rooms):
    for seed in SEEDS:
        rows = delve.generate_floor_v2(seed, w, h, rooms)
        assert len(rows) == h and all(len(r) == w for r in rows), (seed, w, h)
        assert set("".join(rows)) <= set("#.ud"), seed
        assert rows[0] == "#" * w and rows[-1] == "#" * w, seed
        assert all(r[0] == "#" and r[-1] == "#" for r in rows), seed
        flat = "".join(rows)
        assert flat.count("u") == 1 and flat.count("d") == 1, seed
        walkable = {(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c != "#"}
        assert _bfs(rows) == walkable, f"{seed}: a floor tile cannot be reached"


@pytest.mark.parametrize("w,h,rooms", [(48, 32, 10), (64, 64, 16), (40, 28, 9)])
def test_the_stairs_are_far_apart_on_big_floors(w, h, rooms):
    for seed in SEEDS:
        rows = delve.generate_floor_v2(seed, w, h, rooms)
        pos = {c: (x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c in "ud"}
        dist = abs(pos["u"][0] - pos["d"][0]) + abs(pos["u"][1] - pos["d"][1])
        assert dist >= delve.MIN_STAIR_DISTANCE, (seed, dist)


def test_deterministic_and_varied():
    a = delve.generate_floor_v2("same", 48, 32, 10)
    assert a == delve.generate_floor_v2("same", 48, 32, 10)
    many = {tuple(delve.generate_floor_v2(s, 48, 32, 10)) for s in SEEDS}
    assert len(many) >= 22        # 24 seeds, at most a couple of accidental repeats


def test_bad_sizes_are_refused_like_the_old_generator():
    with pytest.raises(ValueError):
        delve.generate_floor_v2("x", 4, 20, 5)
    with pytest.raises(ValueError):
        delve.generate_floor_v2("x", 20, 20, 0)


def test_the_old_generator_is_untouched():
    pinned = {("cottage-deeper-zone", 48, 32, 10): "62083653e82bb6c5",
              ("a", 30, 20, 8): "8d1de71c6b66714e",
              ("zz9", 20, 20, 3): "1a3c9ee36c71044b"}
    for (seed, w, h, rooms), digest in pinned.items():
        rows = delve.generate_floor(seed, w, h, rooms)
        assert hashlib.sha256("\n".join(rows).encode()).hexdigest()[:16] == digest
