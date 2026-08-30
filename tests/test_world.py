from old-name.paths import pack_dir
from old-name.world import load_world


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
    ):
        assert pack_dir().joinpath(rel).exists()


def test_town_payload_is_grid():
    m = load_world()["town"]["map"]
    assert len(m) == 20
    assert all(len(row) == len(m[0]) for row in m)


def test_watch_narrows_the_safe_world_each_phase():
    radii = load_world()["town"]["watch"]["r_by_phase"]
    assert radii["whispers"] < radii["doubts"] < radii["feared"] < radii["awed"]


def test_maren_seeds_cover_phases():
    w = load_world()
    seeds = w["speakers"]["the ferryman"]["seeds"]
    assert set(seeds.keys()) == set(w["phases"].keys())
