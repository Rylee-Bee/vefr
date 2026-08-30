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
        "voices/hearth.md",
    ):
        assert pack_dir().joinpath(rel).exists()


def test_town_payload_is_grid():
    m = load_world()["town"]["map"]
    assert len(m) == 20
    assert all(len(row) == len(m[0]) for row in m)


def test_watch_narrows_the_safe_world_each_phase():
    radii = load_world()["town"]["watch"]["r_by_phase"]
    assert radii["whispers"] < radii["doubts"] < radii["feared"] < radii["awed"]


def test_every_speaker_has_seeds_for_every_phase():
    w = load_world()
    for key, spec in w["speakers"].items():
        assert set(spec["seeds"].keys()) == set(w["phases"].keys()), key


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
