#!/usr/bin/env python3
"""E0a floor-generator bench (Python side) - measurement only.

Benchmarks the v2 generator (`vefr.delve.generate_floor_v2`) at the four
sizes the endless-dungeon plan is choosing between, over the `bench-*`
seed set, and reports:

  - generation time (p50 / p95 / max, milliseconds);
  - the stair-distance fallback rate (how often the up- and down-stair
    land at least `MIN_STAIR_DISTANCE` = 10 Manhattan tiles apart);
  - reachability (every walkable tile reachable from the up-stair, so
    every room is reachable);
  - walkable tiles per floor (deterministic, size context);
  - turns for the shortest u -> d path (a proxy for the plan's
    "turns from stair to stair").

Everything deterministic (counts, tile totals, path lengths) repeats
exactly across runs; only the timings vary.

The generator is called **directly**, not through a validating CLI:
`norns delve` and the pack validators are bypassed on purpose, because
the size limits quoted in `design/random-floors.md` ("width and height
20 to 64, rooms 3 to 16, floors 1 to 8") are a *proposed* validator -
nothing in `src/vefr/` enforces them on this commit, and 96x64 and
128x96 exceed them anyway. `generate_floor_v2`'s own contract is all
that is relied on (width/height >= 5, rooms >= 1).

Browser measurements (JS generation, monster turns, frame times, fog
bytes, autoexplore) live in `tests/browser/bench_floor_play.py`, which
runs only under VEFR_BENCH=1.

Usage:
    uv run python scripts/bench_floors.py
    uv run python scripts/bench_floors.py --seeds 5 --size 48x32x16
    uv run python scripts/bench_floors.py --seeds 200 --json bench/runs/endless-e0-py.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import deque
from pathlib import Path

# Make `vefr` importable from a bare `python scripts/bench_floors.py`
# as well as `uv run python ...`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from vefr import delve  # noqa: E402

# (width, height, rooms) - the four sizes E0 is choosing between
# (docs/plans/endless-dungeon/PLAN.md §3). The twin of this list lives
# in tests/browser/bench_floor_play.py; change both together.
SIZES: list[tuple[int, int, int]] = [(48, 32, 16), (64, 48, 18),
                                     (96, 64, 24), (128, 96, 32)]

# Seeds are bench-0 .. bench-<n-1>.
SEED_PREFIX = "bench-"


def pct(values: list[float], p: float) -> float:
    """Nearest-rank percentile: sorted[floor(p * (n - 1))].

    Used everywhere in this bench so Python and the browser report the
    same statistic for the same samples.
    """
    if not values:
        raise ValueError("pct() of an empty sample")
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(p * (len(ordered) - 1)))]


def _stairs(rows: list[str]) -> tuple[tuple[int, int], tuple[int, int]]:
    """The (up, down) tiles of a generated floor."""
    up = down = None
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "u":
                up = (x, y)
            elif ch == "d":
                down = (x, y)
    if up is None or down is None:
        raise ValueError("a generated floor carried no stairs")
    return up, down


def walkable_keys(rows: list[str]) -> list[str]:
    """Every non-wall tile as "x,y" keys, row-major (the fog key shape)."""
    return [f"{x},{y}"
            for y, row in enumerate(rows)
            for x, ch in enumerate(row) if ch != "#"]


def reachable_from(rows: list[str], start: tuple[int, int]) -> set[tuple[int, int]]:
    """Flood fill over non-wall tiles: everything `start` can walk to."""
    height, width = len(rows), len(rows[0])
    seen = {start}
    queue: deque[tuple[int, int]] = deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (0 <= nx < width and 0 <= ny < height
                    and rows[ny][nx] != "#" and (nx, ny) not in seen):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def shortest_path(rows: list[str], start: tuple[int, int],
                  goal: tuple[int, int]) -> int | None:
    """Steps from `start` to `goal` over walkable tiles; None if cut off."""
    if start == goal:
        return 0
    height, width = len(rows), len(rows[0])
    dist = {start: 0}
    queue: deque[tuple[int, int]] = deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if rows[ny][nx] == "#" or (nx, ny) in dist:
                continue
            dist[(nx, ny)] = dist[(x, y)] + 1
            if (nx, ny) == goal:
                return dist[(nx, ny)]
            queue.append((nx, ny))
    return None


def bench_size(size: tuple[int, int, int], seeds: list[str]) -> dict:
    """One size's Python numbers: timings plus the deterministic counts."""
    width, height, rooms = size
    gen_ms: list[float] = []
    stair_ok = 0
    connected = 0
    walkable: list[float] = []
    stair_path: list[float] = []
    for seed in seeds:
        t0 = time.perf_counter()
        rows = delve.generate_floor_v2(seed, width, height, rooms)
        gen_ms.append((time.perf_counter() - t0) * 1000.0)

        up, down = _stairs(rows)
        dist = abs(up[0] - down[0]) + abs(up[1] - down[1])
        if dist >= delve.MIN_STAIR_DISTANCE:
            stair_ok += 1

        tiles = walkable_keys(rows)
        walkable.append(float(len(tiles)))
        seen = reachable_from(rows, up)
        if len(seen) == len(tiles):
            connected += 1

        path = shortest_path(rows, up, down)
        if path is not None:
            stair_path.append(float(path))

    key = f"{width}x{height}x{rooms}"
    return key, {
        "seeds": len(seeds),
        "gen_ms": {"p50": round(pct(gen_ms, 0.50), 4),
                   "p95": round(pct(gen_ms, 0.95), 4),
                   "max": round(max(gen_ms), 4)},
        "stair_distance": {
            "min_10_or_more": stair_ok,
            "fallback_below_10": len(seeds) - stair_ok,
        },
        "reachability": {
            "all_walkable_reachable": connected,
            "disconnected": len(seeds) - connected,
        },
        "walkable_tiles": {"min": int(min(walkable)),
                           "p50": int(pct(walkable, 0.50)),
                           "max": int(max(walkable))},
        "stair_to_stair_turns": ({"p50": int(pct(stair_path, 0.50)),
                                  "p95": int(pct(stair_path, 0.95)),
                                  "max": int(max(stair_path))}
                                 if stair_path else None),
    }


def run(sizes: list[tuple[int, int, int]], seeds: list[str]) -> dict:
    """The whole Python bench: one entry per size, keyed 'WxHxR'."""
    results = {}
    for size in sizes:
        key, entry = bench_size(size, seeds)
        results[key] = entry
    return {
        "bench": "vefr-floor-bench",
        "version": 1,
        "generator": "vefr.delve.generate_floor_v2 (called directly, no validator)",
        "seeds": seeds,
        "sizes": [list(s) for s in sizes],
        "python": sys.version.split()[0],
        "results": results,
    }


def print_table(report: dict) -> None:
    """The human half: one line per size, counts and timings together."""
    header = (f"{'size':<11} {'gen p50':>8} {'gen p95':>8} "
              f"{'stair>=10':>10} {'connected':>10} {'walk p50':>9} {'u->d p50':>9}")
    print(header)
    print("-" * len(header))
    for key, entry in report["results"].items():
        gen = entry["gen_ms"]
        stair = entry["stair_distance"]
        reach = entry["reachability"]
        walk = entry["walkable_tiles"]
        path = entry["stair_to_stair_turns"] or {}
        print(f"{key:<11} {gen['p50']:>7.3f}m {gen['p95']:>7.3f}m "
              f"{stair['min_10_or_more']:>6}/{entry['seeds']:<3} "
              f"{reach['all_walkable_reachable']:>6}/{entry['seeds']:<3} "
              f"{walk['p50']:>9} {path.get('p50', '-'):>9}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, default=200,
                    help="how many seeds (bench-0 .. bench-N-1); default 200")
    ap.add_argument("--size", action="append", metavar="WxHxR",
                    help="a size to bench (repeatable); default: all four")
    ap.add_argument("--json", metavar="PATH", help="write the full report as JSON")
    ap.add_argument("--quiet", action="store_true", help="skip the stdout table")
    args = ap.parse_args(argv)

    if args.seeds < 1:
        ap.error("--seeds must be at least 1")
    sizes = SIZES
    if args.size:
        try:
            sizes = [tuple(int(v) for v in s.lower().split("x")) for s in args.size]  # type: ignore[misc]
        except ValueError:
            ap.error("--size must look like 48x32x16")
        if any(len(s) != 3 for s in sizes):
            ap.error("--size must look like 48x32x16")

    seeds = [f"{SEED_PREFIX}{i}" for i in range(args.seeds)]
    report = run(list(sizes), seeds)
    report["command"] = " ".join(["uv run python scripts/bench_floors.py"] + (argv or sys.argv[1:]))

    if not args.quiet:
        print_table(report)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if not args.quiet:
            print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
