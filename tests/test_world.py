"""Story tests - Private Canon canon. Skipped unless the resolved
world IS private-canon: the bones must be provable with zero flesh."""

from pathlib import Path

import pytest

from norn import maplab
from norn.paths import pack_dir, world_name
from norn.world import load_world

_pack = Path(__file__).resolve().parents[1] / 'worlds' / 'private-canon'
if world_name() != 'private-canon' or not (_pack / 'world.json').exists():
    pytest.skip('private-canon pack not resolved', allow_module_level=True)


def test_maplab_validates_the_pack():
    errors = maplab.validate(load_world(), pack_dir=pack_dir())
    assert errors == []


def test_maplab_flags_a_broken_map():
    import copy

    w = copy.deepcopy(load_world())
    w['town']['map'][0] = w['town']['map'][0].replace('=', 'Q')  # unknown char
    w['town']['willow_start'] = [23, 3]  # the tower - solid
    errors = maplab.validate(w)
    assert any('missing from legend' in e for e in errors)
    assert any('not walkable' in e for e in errors)


def test_pack_loads():
    w = load_world()
    assert w["title"] == "Private Canon"
    assert list(w["phases"].keys()) == ["whispers", "doubts", "feared", "awed"]
    assert list(w["bonds"].keys()) == ["assigned", "attuned", "cold"]


def test_pack_files_exist():
    for rel in (
        "bible.md",
        "ledger.md",
        "map.md",
        "world.json",
        "voices/mother.md",
        "voices/the ferryman.md",
        "voices/hearth.md",
        "voices/katla.md",
        "voices/sigga.md",
        "voices/the roll-keeper.md",
    ):
        assert pack_dir().joinpath(rel).exists()


def test_town_payload_is_grid():
    m = load_world()["town"]["map"]
    assert len(m) == 28
    assert all(len(row) == 40 for row in m)


def test_watch_narrows_the_safe_world_each_phase():
    radii = load_world()["town"]["watch"]["r_by_phase"]
    assert radii["whispers"] < radii["doubts"] < radii["feared"] < radii["awed"]


def test_every_speaker_has_seeds_for_every_phase():
    w = load_world()
    for key, spec in w["speakers"].items():
        assert set(spec["seeds"].keys()) == set(w["phases"].keys()), key


def test_water_rises_when_the_world_grows_wary():
    town = load_world()["town"]
    m = town["map"]
    levels = town["water_by_phase"]
    assert levels["feared"] == "high"
    for low in ("whispers", "doubts", "awed"):
        assert levels[low] == "low"
    for x, y in town["flood_tiles"]:
        assert m[y][x] == "p", (x, y)


def test_the_hearth_is_in_the_world():
    town = load_world()["town"]
    assert "23,17" in town["pois"]
    assert "D" in town["sanctuary_tiles"]
    joined = "".join(town["map"])
    for ch in ("O", "o", "D"):
        assert ch in joined
    assert town["legend"]["O"].get("solid") is True
    assert town["legend"]["D"].get("solid", False) is False


def test_willow_can_leave_the_bookshop():
    town = load_world()["town"]
    m = town["map"]

    def walkable(x, y):
        if y < 0 or y >= len(m) or x < 0 or x >= len(m[0]):
            return False
        return not town["legend"].get(m[y][x], {}).get("solid", False)

    start = tuple(town["willow_start"])
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in seen and walkable(*n):
                seen.add(n)
                stack.append(n)
    assert (14, 6) in seen, "the well"
    assert (15, 7) in seen, "the whisper-stone"
    assert (23, 17) in seen, "the hearth door"
    assert (12, 13) in seen, "the bookshop back door"
    assert (13, 15) in seen, "the bookshop front door"
    assert (31, 5) in seen, "the moot hall door"
    assert (36, 6) in seen, "the tavern door"
    assert (32, 14) in seen, "the store door"
