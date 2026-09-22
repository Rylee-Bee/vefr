"""Story tests - the demonstration pack (Emberfield) as the
tracked known-good fixture. The pack ships with the engine, so
these run on every checkout: the bones are provable with zero
flesh, and the flesh that IS tracked must surface intact."""


import copy


from vefr import maplab
from vefr.paths import pack_dir
from vefr.world import creed_from, current_act, load_world

WORLD = 'sample-world'


def _w():
    return load_world(WORLD)


def _legacy_town():
    """The flat-shape town block is preserved under the act's
    _town_legacy key (synthesized from the region's contract.json
    + map.md in the acts shape). This is the data the validator
    and the web renderer read."""
    return current_act(_w()).get("_town_legacy", {})


def test_maplab_validates_the_pack():
    errors = maplab.validate(_w(), pack_dir=pack_dir(WORLD))
    assert errors == []


def test_creed_reads_the_legacy_field_name():
    """The pre-rename `gold_rule` field is read forever: packs written
    before the rename keep their line, and `creed` wins when both exist
    (maplab writes the value back as `creed` on the next save)."""
    assert creed_from({"creed": "new line"}) == "new line"
    assert creed_from({"gold_rule": "old line"}) == "old line"
    assert creed_from({"creed": "new line", "gold_rule": "old line"}) == "new line"
    assert creed_from({}) == ""


def test_maplab_flags_a_broken_map():
    w = copy.deepcopy(_w())
    town = current_act(w).get("_town_legacy", {})
    m = town["map"]
    m[0] = m[0].replace(m[0][0], 'Q')  # unknown char
    solid = next(
        (x, y)
        for y, row in enumerate(m)
        for x, ch in enumerate(row)
        if town["legend"].get(ch, {}).get("solid")
    )
    town["hero_start"] = list(solid)  # a solid tile
    errors = maplab.validate(w)
    assert any('missing from legend' in e for e in errors)
    assert any('not walkable' in e for e in errors)


def test_pack_loads():
    w = _w()
    assert w["title"] == "Emberfield"
    assert list(w["phases"].keys()) == ["dusk", "dawn"]
    assert list(w["bonds"].keys()) == ["given", "found", "cold"]


def test_pack_files_exist():
    for rel in (
        "logbok.md",
        "ledger.md",
        "world.json",
        "voices/keeper.md",
        "voices/keeper.fragments.md",
        "acts/act-1/world.json",
        "acts/act-1/town/map.md",
        "acts/act-1/town/contract.json",
    ):
        assert pack_dir(WORLD).joinpath(rel).exists()


def test_town_payload_is_grid():
    m = _legacy_town()["map"]
    assert len(m) == 10
    assert all(len(row) == 12 for row in m)


def test_watch_levels_cover_every_phase():
    radii = _legacy_town()["watch"]["r_by_phase"]
    assert set(radii.keys()) == set(_w()["phases"].keys())
    assert all(isinstance(v, int) and v > 0 for v in radii.values())


def test_every_speaker_has_seeds_for_every_phase():
    w = _w()
    speakers = current_act(w)["speakers"]
    assert speakers, "sample-world ships one speaker"
    for key, spec in speakers.items():
        assert set(spec["seeds"].keys()) == set(w["phases"].keys()), key


def test_water_levels_cover_every_phase():
    town = _legacy_town()
    levels = town["water_by_phase"]
    assert set(levels.keys()) == set(_w()["phases"].keys())
    for x, y in town.get("flood_tiles", []):
        assert town["map"][y][x] in ("p", "."), (x, y)


def test_the_places_are_in_the_world():
    town = _legacy_town()
    assert "7,3" in town["pois"], "the stone"
    assert "7,5" in town["pois"], "the threshold"
    assert "D" in town["sanctuary_tiles"]
    joined = "".join(town["map"])
    for ch in ("S", "D"):
        assert ch in joined
    assert town["legend"]["D"].get("solid", False) is False


def test_hero_can_reach_every_place():
    town = _legacy_town()
    m = town["map"]

    def walkable(x, y):
        if y < 0 or y >= len(m) or x < 0 or x >= len(m[0]):
            return False
        return not town["legend"].get(m[y][x], {}).get("solid", False)

    start = tuple(town["hero_start"])
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in seen and walkable(*n):
                seen.add(n)
                stack.append(n)
    for poi in town["pois"]:
        x, y = (int(v) for v in poi.split(","))
        assert (x, y) in seen, f"unreachable place: {town['pois'][poi]}"


def test_the_offline_bank_ships_with_the_pack():
    w = _w()
    bank = w["fragments"].get("keeper") or []
    assert len(bank) >= 2, "the composer needs at least two lines to splice"
