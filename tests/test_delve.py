"""The deterministic dungeon-floor generator and `norns delve`.

Rules-only: every floor comes from a seed through `random.Random`, and
`norns delve` only reads and writes pack files - no model call anywhere.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vefr import cli, delve, maplab

# A small acts pack whose town holds one down-stair the author placed.
TOWN_MAP = [
    "#########",
    "#.......#",
    "#.......#",
    "#...d...#",
    "#.......#",
    "#.......#",
    "#########",
]
TOWN_CONTRACT = {
    "tile": 32,
    "bg": "#131311",
    "hero_start": [1, 1],
    "legend": {
        ".": {"base": ["#212a20"], "tile": "dungeon-floor"},
        "#": {"base": ["#2a2e33"], "solid": True, "tile": "dungeon-wall"},
        "d": {"base": ["#2b2f38"], "tile": "dungeon-stairs-down"},
    },
    "sanctuary_tiles": ["."],
    "water_by_phase": {"dusk": "low", "dawn": "low"},
    "flood_tiles": [],
    "pois": {},
}
EXTRA_CONTRACT = {
    "tile": 32,
    "bg": "#131311",
    "hero_start": [1, 1],
    "legend": {
        ".": {"base": ["#212a20"], "tile": "dungeon-floor"},
        "#": {"base": ["#2a2e33"], "solid": True, "tile": "dungeon-wall"},
    },
    "sanctuary_tiles": ["."],
    "water_by_phase": {"dusk": "low", "dawn": "low"},
    "flood_tiles": [],
    "pois": {},
}


def _make_pack(root: Path, *, extra_regions=()) -> Path:
    """A one-stair town plus any pre-existing floor regions."""
    pack = root / "worlds" / "delve-test"
    act = pack / "acts" / "act-1"
    (act / "town").mkdir(parents=True)
    (pack / "world.json").write_text(json.dumps({
        "title": "Delve Test",
        "phases": {"dusk": "quiet", "dawn": "warm"},
        "voices": {},
    }), encoding="utf-8")
    (act / "world.json").write_text(json.dumps({
        "id": "act-1",
        "title": "Delve Test",
        "regions": ["town", *extra_regions],
        "speakers": {},
        "transitions": [],
    }), encoding="utf-8")
    (act / "town" / "map.md").write_text(
        "\n".join(TOWN_MAP) + "\n", encoding="utf-8")
    (act / "town" / "contract.json").write_text(
        json.dumps(TOWN_CONTRACT), encoding="utf-8")
    for name in extra_regions:
        region = act / name
        region.mkdir(parents=True, exist_ok=True)
        (region / "map.md").write_text("###\n#.#\n###\n", encoding="utf-8")
        (region / "contract.json").write_text(
            json.dumps(EXTRA_CONTRACT), encoding="utf-8")
    return pack


def _args(pack: Path, **kw) -> argparse.Namespace:
    base = dict(
        pack=str(pack), seed="cavern", floors=1,
        from_region="town", from_at="4,3",
        width=30, height=20, rooms=8,
        first_name=None, force=False,
    )
    base.update(kw)
    return argparse.Namespace(**base)


def _stairs(rows: list[str]):
    """The (up, down) tiles a floor's rows carry; either may be None."""
    up = down = None
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "u":
                up = (x, y)
            elif ch == "d":
                down = (x, y)
    return up, down


def _flood(rows: list[str], start: tuple[int, int]) -> set:
    """Every non-wall tile reachable from `start` (4-neighbour)."""
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


def _rows(pack: Path, name: str) -> list[str]:
    return [ln for ln in (pack / "acts" / "act-1" / name / "map.md")
            .read_text(encoding="utf-8").splitlines() if ln.strip()]


# ------------------------------------------------------------- the generator

def test_same_inputs_draw_the_same_floor():
    assert delve.generate_floor("cavern") == delve.generate_floor("cavern")


def test_a_different_seed_draws_a_different_floor():
    assert delve.generate_floor("cavern") != delve.generate_floor("cellar")


def test_the_floor_is_rectangular_and_uses_only_the_legend():
    rows = delve.generate_floor("shape", width=30, height=20, rooms=8)
    assert len(rows) == 20
    assert {len(r) for r in rows} == {30}
    assert set("".join(rows)) <= set("#.ud")
    assert sum(r.count("u") for r in rows) == 1
    assert sum(r.count("d") for r in rows) == 1


def test_the_border_is_solid_wall():
    rows = delve.generate_floor("border")
    assert rows[0] == "#" * len(rows[0])
    assert rows[-1] == "#" * len(rows[-1])
    assert all(r[0] == "#" and r[-1] == "#" for r in rows)


def test_every_floor_tile_is_reachable_from_the_stairs():
    rows = delve.generate_floor("connected")
    up, down = _stairs(rows)
    assert up is not None and down is not None
    seen = _flood(rows, up)
    floor_tiles = {(x, y) for y, r in enumerate(rows)
                   for x, c in enumerate(r) if c != "#"}
    assert seen == floor_tiles
    assert down in seen


def test_the_down_stair_is_at_least_the_minimum_distance_away():
    for seed in ("a", "b", "c", "d", "e", "f"):
        rows = delve.generate_floor(seed, width=30, height=20, rooms=8)
        up, down = _stairs(rows)
        dist = abs(up[0] - down[0]) + abs(up[1] - down[1])
        assert dist >= delve.MIN_STAIR_DISTANCE, (seed, up, down, dist)


def test_contract_names_the_stairs_and_the_legend():
    rows = delve.generate_floor("contract")
    up, down = _stairs(rows)
    c = delve.contract(len(rows[0]), len(rows), up, down)
    assert c["hero_start"] == list(up)
    assert c["tile"] == 32
    assert set(c["legend"]) == set("#.ud")
    assert c["legend"]["#"]["solid"] is True
    assert f"{up[0]},{up[1]}" in c["pois"]
    assert f"{down[0]},{down[1]}" in c["pois"]
    assert set(c["poi_text"]) == set(c["pois"])


# ------------------------------------------------------------ norns delve

def test_delve_writes_regions_and_wires_the_stairs(tmp_path):
    """Two generated floors: the regions land, the doors join them, and
    the first region stays first."""
    pack = _make_pack(tmp_path)
    assert cli.cmd_delve(_args(pack, floors=2)) == 0

    act = json.loads(
        (pack / "acts" / "act-1" / "world.json").read_text(encoding="utf-8"))
    assert act["regions"] == ["town", "floor-2", "floor-3"]
    assert (pack / "acts" / "act-1" / "floor-2" / "map.md").exists()
    assert (pack / "acts" / "act-1" / "floor-2" / "contract.json").exists()
    assert (pack / "acts" / "act-1" / "floor-3" / "map.md").exists()

    up2, down2 = _stairs(_rows(pack, "floor-2"))
    up3, down3 = _stairs(_rows(pack, "floor-3"))
    assert down2 is not None
    assert down3 is None  # the bottom floor has no way down yet

    ts = act["transitions"]
    assert len(ts) == 4
    assert {"from": "town", "at": [4, 3],
            "to": "floor-2", "to_at": list(up2)} in ts
    assert {"from": "floor-2", "at": list(down2),
            "to": "floor-3", "to_at": list(up3)} in ts
    assert {"from": "floor-2", "at": list(up2),
            "to": "town", "to_at": [4, 3]} in ts
    assert {"from": "floor-3", "at": list(up3),
            "to": "floor-2", "to_at": list(down2)} in ts

    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []


def test_delve_refuses_a_second_run_without_force(tmp_path):
    pack = _make_pack(tmp_path)
    args = _args(pack, floors=1, first_name="floor-2")
    assert cli.cmd_delve(args) == 0
    assert cli.cmd_delve(args) != 0


def test_delve_force_rewrites_an_existing_floor(tmp_path):
    pack = _make_pack(tmp_path)
    assert cli.cmd_delve(_args(pack, floors=1, first_name="floor-2")) == 0
    before = _rows(pack, "floor-2")
    assert cli.cmd_delve(_args(pack, floors=1, first_name="floor-2",
                               force=True, seed="other")) == 0
    assert _rows(pack, "floor-2") != before
    act = json.loads(
        (pack / "acts" / "act-1" / "world.json").read_text(encoding="utf-8"))
    assert act["regions"] == ["town", "floor-2"]


def test_delve_continues_the_floor_numbering(tmp_path):
    pack = _make_pack(tmp_path, extra_regions=["floor-2"])
    assert cli.cmd_delve(_args(pack, floors=1)) == 0
    act = json.loads(
        (pack / "acts" / "act-1" / "world.json").read_text(encoding="utf-8"))
    assert act["regions"] == ["town", "floor-2", "floor-3"]


def test_delve_refuses_a_solid_start_tile(tmp_path):
    pack = _make_pack(tmp_path)
    assert cli.cmd_delve(_args(pack, from_at="0,0")) != 0
    assert not (pack / "acts" / "act-1" / "floor-2").exists()


def test_delve_refuses_an_unknown_from_region(tmp_path):
    pack = _make_pack(tmp_path)
    assert cli.cmd_delve(_args(pack, from_region="cellar")) != 0
    assert not (pack / "acts" / "act-1" / "floor-2").exists()
