"""Turning a kept face into a REAL speaker: POST /api/builder/character/place.

A face the storyteller drafted only lives in the vault until it is
placed. This is the route that writes it into the game: one entry in
the act's `speakers` plus a voice file under the region's voices/.

These pins cover the writer, the path safety, the placement rule, the
weave loop, and the compatibility promise that a pack nobody placed
anything into bakes byte-for-byte what it did before.

The route mirrors POST /api/builder/map/build: the pack name goes
through _safe_world_name(), an existing id is never clobbered without
`force` (409), the previous speakers file is backed up, the write goes
through maplab.write_pack, and maplab.validate gates the result in
plain sentences. It never calls a model.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vefr import cli
from vefr import main as main_mod
from vefr import maplab
from vefr import world as world_mod
from vefr.main import app

SAMPLE_WORLD = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"

# A flat pack for the placement edges: a room the hero can walk, plus
# one '.' sealed behind walls at (1,3) so "unreachable" is a real tile
# and not a hypothesis. hero_start is (1,1).
#
#   #######
#   #.....#
#   #####.#
#   #.#...#
#   #######
PLACEMENT_PACK = {
    "name": "placement-pack",
    "title": "Placement Pack",
    "phases": {"dusk": "the dusk phase", "dawn": "the dawn phase"},
    "surface": "plain",
    "speakers": {},
    "voices": {},
    "town": {
        "tile": 32,
        "bg": "#131311",
        "hero_start": [1, 1],
        "sanctuary_tiles": ["."],
        "map": ["#######", "#.....#", "#####.#", "#.#...#", "#######"],
        "legend": {
            ".": {"base": ["#212a20"]},
            "#": {"base": ["#2a2e33"], "solid": True},
        },
        "pois": {},
        "water_by_phase": {"dusk": "low", "dawn": "low"},
        "flood_tiles": [],
    },
}


# ------------------------------------------------------------- fixtures


@pytest.fixture
def acts_home(tmp_path, monkeypatch):
    """A temp home whose world is the acts-shape sample-world pack.

    The served builder's own worlds are acts shape, so the speaker and
    its voice file land in acts/act-1/town/ - the files this route
    owns.
    """
    home = tmp_path / "vefr-home"
    (home / "worlds").mkdir(parents=True)
    shutil.copytree(SAMPLE_WORLD, home / "worlds" / "sample-world")
    monkeypatch.setenv("VEFR_HOME", str(home))
    world_mod.load_world.cache_clear()
    yield home
    world_mod.load_world.cache_clear()


@pytest.fixture
def flat_home(fixture_vefr_home):
    """The shared four-phase fixture home + a flat pack built for
    placement edges (room, plus one unreachable tile)."""
    pack = fixture_vefr_home / "worlds" / "placement-pack"
    pack.mkdir(parents=True)
    (pack / "world.json").write_text(
        json.dumps(PLACEMENT_PACK, ensure_ascii=False), encoding="utf-8"
    )
    return fixture_vefr_home


# --------------------------------------------------------------- helpers


def _pack(home: Path, name: str = "sample-world") -> Path:
    return home / "worlds" / name


def _snapshot(pack: Path) -> dict[str, bytes]:
    """Every file under the pack, by relative path - a byte fingerprint."""
    return {
        str(p.relative_to(pack)): p.read_bytes()
        for p in sorted(pack.rglob("*"))
        if p.is_file()
    }


def _baked(html: str, name: str):
    prefix = f"window.{name} = "
    line = next(ln for ln in html.splitlines() if ln.startswith(prefix))
    return json.loads(line[len(prefix):].rstrip(";"))


def _place(**over) -> dict:
    body = {
        "name": "sample-world",
        "id": "stern",
        "display_name": "Stern",
        "role": "guard",
        "near": "the gate",
        "seeds": {"dusk": "Halt. ...oh, it's you.", "dawn": "Morning."},
        "voice": "You are Stern, a big burly guard who is secretly very soft...",
        "region": "town",
    }
    body.update(over)
    return body


def _speakers(pack: Path) -> dict:
    return json.loads(
        (pack / "acts" / "act-1" / "world.json").read_text(encoding="utf-8")
    )["speakers"]


# --------------------------------------------- 1. writer (preview + real)


def test_preview_writes_nothing(acts_home):
    pack = _pack(acts_home)
    before = _snapshot(pack)

    r = TestClient(app).post(
        "/api/builder/character/place", json=_place(preview=True)
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["written"] is False
    assert body["preview"]["speaker"]["name"] == "Stern"
    assert body["preview"]["speaker"]["seeds"]["dawn"] == "Morning."
    assert body["preview"]["voice_text"].startswith("You are Stern")
    assert body["preview"]["at"]
    assert _snapshot(pack) == before
    assert "stern" not in _speakers(pack)


def test_place_writes_one_speaker_and_its_voice(acts_home):
    pack = _pack(acts_home)
    before = _speakers(pack)

    r = TestClient(app).post(
        "/api/builder/character/place",
        json=_place(at=[4, 4]),
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["written"] is True
    assert body["files"] == [
        "acts/act-1/world.json",
        "acts/act-1/town/voices/stern.md",
    ]
    assert body["backup"].startswith("acts/act-1/world.json.bak-")

    after = _speakers(pack)
    assert set(after) == set(before) | {"stern"}
    assert after["stern"]["name"] == "Stern"
    assert after["stern"]["at"] == [4, 4]
    assert after["stern"]["near"] == "the gate"
    assert after["stern"]["voice_file"] == "voices/stern.md"
    assert set(after["stern"]["seeds"]) == {"dusk", "dawn"}

    voice = pack / "acts" / "act-1" / "town" / "voices" / "stern.md"
    assert voice.read_text(encoding="utf-8") == (
        "You are Stern, a big burly guard who is secretly very soft...\n"
    )
    # The pack still validates with the new speaker on disk.
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []


def test_a_second_place_of_the_same_id_is_409_unless_forced(acts_home):
    pack = _pack(acts_home)
    client = TestClient(app)

    assert client.post(
        "/api/builder/character/place", json=_place(at=[4, 4])
    ).status_code == 200
    settled = _snapshot(pack)

    r = client.post("/api/builder/character/place", json=_place(at=[4, 5]))
    assert r.status_code == 409, r.text
    assert "already exists" in r.json()["detail"]
    assert _snapshot(pack) == settled

    r = client.post(
        "/api/builder/character/place",
        json=_place(at=[4, 5], force=True),
    )
    assert r.status_code == 200, r.text
    after = _speakers(pack)
    assert set(after) == {"keeper", "stern"}
    assert after["stern"]["at"] == [4, 5]


def test_unknown_world_is_404(acts_home):
    r = TestClient(app).post(
        "/api/builder/character/place",
        json=_place(name="no-such-world"),
    )
    assert r.status_code == 404


# --------------------------------------------------------------- 2. safety


@pytest.mark.parametrize(
    "bad",
    ["..", "../stern", "stern/../keeper", "Stern", "a b", "", "a" * 33, "stern.md",
     "/etc/passwd", "stern\\keeper", ".stern"],
)
def test_bad_ids_are_422_and_the_disk_is_untouched(acts_home, bad):
    pack = _pack(acts_home)
    before = _snapshot(pack)

    r = TestClient(app).post(
        "/api/builder/character/place", json=_place(id=bad)
    )

    assert r.status_code == 422, (bad, r.status_code, r.text)
    assert _snapshot(pack) == before


def test_bad_region_is_422(acts_home):
    pack = _pack(acts_home)
    before = _snapshot(pack)
    r = TestClient(app).post(
        "/api/builder/character/place",
        json=_place(region="../outside"),
    )
    assert r.status_code == 422
    assert _snapshot(pack) == before


def test_unknown_region_is_422(acts_home):
    r = TestClient(app).post(
        "/api/builder/character/place", json=_place(region="cellar")
    )
    assert r.status_code == 422
    assert "no region named" in r.json()["detail"]


def test_voice_target_refuses_to_leave_the_pack(acts_home):
    """The CodeQL guard: a path built from pack data resolves inside the
    pack or not at all - same shape as the act-id/region regression."""
    import os

    pack = _pack(acts_home)
    w = maplab.load_pack(pack)
    base = os.path.realpath(pack)

    assert main_mod._voice_target(pack, w, "stern", "town")[0] is not None
    # Enough `..` to climb out of the pack is nothing; the region regex
    # refuses these before the helper is ever reached.
    for evil in ("../../../outside", "../../../../etc", "../" * 12):
        path, rel = main_mod._voice_target(pack, w, "stern", evil)
        assert path is None, (evil, rel, path)
    # A path the helper does return always resolves inside the pack.
    for region in ("..", "../..", "a/b"):
        path, _rel = main_mod._voice_target(pack, w, "stern", region)
        if path is not None:
            assert os.path.realpath(path).startswith(base + os.sep), region


def test_route_refuses_a_voice_path_that_leaves_the_pack(acts_home, monkeypatch):
    """Even if the guard were made to see a traversal, the route refuses
    it before touching the disk (the hard backstop in the route)."""
    pack = _pack(acts_home)
    before = _snapshot(pack)
    monkeypatch.setattr(
        main_mod,
        "_voice_target",
        lambda *a, **k: (None, "../../outside/voices/stern.md"),
    )

    r = TestClient(app).post(
        "/api/builder/character/place", json=_place(preview=False)
    )

    assert r.status_code == 422
    assert _snapshot(pack) == before


# ------------------------------------------------------------ 3. placement


def test_solid_tile_is_422(flat_home):
    r = TestClient(app).post(
        "/api/builder/character/place",
        json=_place(name="placement-pack", id="stern", at=[0, 0]),
    )
    assert r.status_code == 422
    assert "not walkable" in r.json()["detail"]


def test_unreachable_tile_is_422(flat_home):
    r = TestClient(app).post(
        "/api/builder/character/place",
        json=_place(name="placement-pack", id="stern", at=[1, 3]),
    )
    assert r.status_code == 422
    assert "not reachable" in r.json()["detail"]


def test_occupied_tile_is_422(flat_home):
    client = TestClient(app)
    assert client.post(
        "/api/builder/character/place",
        json=_place(name="placement-pack", id="first", at=[4, 1]),
    ).status_code == 200

    r = client.post(
        "/api/builder/character/place",
        json=_place(name="placement-pack", id="second", at=[4, 1]),
    )
    assert r.status_code == 422
    assert "already stands" in r.json()["detail"]


def test_without_at_the_tile_is_reachable_walkable_and_free(flat_home):
    pack = _pack(flat_home, "placement-pack")
    r = TestClient(app).post(
        "/api/builder/character/place",
        json=_place(name="placement-pack", id="stern"),
    )
    assert r.status_code == 200, r.text
    at = r.json()["preview"]["at"]

    w = maplab.load_pack(pack)
    assert maplab.walkable(w, at[0], at[1])
    assert tuple(at) in maplab.reach(w, tuple(w["town"]["hero_start"]))
    assert tuple(at) != tuple(w["town"]["hero_start"])
    assert at == [4, 1]  # the only widest-band tile, deterministic


# ------------------------------------------------------- 4. the weave loop


def test_a_placed_speaker_rides_into_the_weave(acts_home):
    pack = _pack(acts_home)
    r = TestClient(app).post(
        "/api/builder/character/place", json=_place()
    )
    assert r.status_code == 200, r.text
    at = r.json()["preview"]["at"]

    baked = _baked(cli.weave_html(pack), "VEFR_SPEAKERS")
    assert "stern" in baked["town"]
    assert baked["town"]["stern"]["at"] == at
    assert baked["town"]["stern"]["name"] == "Stern"
    assert baked["town"]["stern"]["voice_file"] == "voices/stern.md"

    w = maplab.load_pack(pack)
    assert maplab.walkable(w, at[0], at[1])


# ------------------------------------------------------- 5. compatibility


def test_sample_world_bakes_byte_for_byte_when_nothing_is_placed(acts_home):
    """A preview is not a write: the woven game is unchanged."""
    pack = _pack(acts_home)
    before = cli.weave_html(pack).encode("utf-8")

    r = TestClient(app).post(
        "/api/builder/character/place", json=_place(preview=True)
    )
    assert r.status_code == 200, r.text

    after = cli.weave_html(pack).encode("utf-8")
    assert after == before


# ----------------------------------------- 5. size limits (orchestrator, 2026-10-01)


@pytest.mark.parametrize("over,needle", [
    ({"voice": "x" * 4001}, "voice is too long"),
    ({"display_name": "n" * 65}, "display name is too long"),
    ({"near": "w" * 65}, "near is too long"),
    ({"seeds": {"dusk": "s" * 281}}, "seed line is too long"),
])
def test_oversized_text_is_a_422_and_the_disk_is_untouched(acts_home, over, needle):
    pack = _pack(acts_home)
    before = _snapshot(pack)
    r = TestClient(app).post("/api/builder/character/place", json=_place(**over))
    assert r.status_code == 422, r.text
    assert needle in r.json()["detail"]
    assert _snapshot(pack) == before


def test_text_at_exactly_the_limit_is_accepted(acts_home):
    r = TestClient(app).post(
        "/api/builder/character/place",
        json=_place(preview=True, voice="v" * 4000, display_name="n" * 64, near="w" * 64,
                    seeds={"dusk": "s" * 280, "dawn": "s" * 280}),
    )
    assert r.status_code == 200, r.text


# ----------------------------- 6. a pack with several rooms (found 2026-10-01 placing a cat in Cottage's cottage)


def _add_cellar(home: Path) -> Path:
    """sample-world plus a 14 x 5 `cellar` room joined to the town by doors both ways.

    The cellar's map is deliberately different from the town's: (3, 2) is solid in the cellar but open in the
    town, and (12, 1) is open in the cellar but off the town's map entirely.
    """
    pack = _pack(home)
    act = pack / "acts" / "act-1"
    shutil.copytree(act / "town", act / "cellar")
    (act / "cellar" / "map.md").write_text(
        "##############\\n#............#\\n#..##........#\\n#............#\\n##############\\n".replace("\\n", "\n"),
        encoding="utf-8",
    )
    contract = json.loads((act / "cellar" / "contract.json").read_text(encoding="utf-8"))
    contract["hero_start"] = [1, 1]
    for key in ("pois", "poi_text", "watch", "flood_tiles", "fog"):
        contract.pop(key, None)
    (act / "cellar" / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    data = json.loads((act / "world.json").read_text(encoding="utf-8"))
    data["regions"] = ["town", "cellar"]
    data["transitions"] = [
        {"from": "town", "at": [9, 8], "to": "cellar", "to_at": [1, 1]},
        {"from": "cellar", "at": [12, 3], "to": "town", "to_at": [8, 8]},
    ]
    (act / "world.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    world_mod.load_world.cache_clear()
    return pack


def test_the_two_room_fixture_is_itself_a_good_pack(acts_home):
    pack = _add_cellar(acts_home)
    from vefr import maplab
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []


def test_a_tile_is_judged_against_the_room_it_is_in(acts_home):
    pack = _add_cellar(acts_home)
    c = TestClient(app)
    # open in the cellar, but off the town's map: this used to be refused ("not walkable") against the town
    r = c.post("/api/builder/character/place", json=_place(id="mole", display_name="Mole", region="cellar", at=[12, 1]))
    assert r.status_code == 200, r.text
    assert _speakers(pack)["mole"]["region"] == "cellar"
    assert _speakers(pack)["mole"]["at"] == [12, 1]
    assert (pack / "acts" / "act-1" / "cellar" / "voices" / "mole.md").is_file()
    # solid in the cellar, though open in the town: this used to be accepted (and put someone inside a wall)
    r = c.post("/api/builder/character/place", json=_place(id="ghost", display_name="Ghost", region="cellar", at=[3, 2], preview=True))
    assert r.status_code == 422
    assert "not walkable" in r.json()["detail"]


def test_two_rooms_can_each_hold_someone_on_the_same_tile(acts_home):
    pack = _add_cellar(acts_home)
    c = TestClient(app)
    assert c.post("/api/builder/character/place", json=_place(id="one", display_name="One", region="cellar", at=[5, 1])).status_code == 200
    r = c.post("/api/builder/character/place", json=_place(id="two", display_name="Two", region="town", at=[5, 1]))
    assert r.status_code == 200, r.text                                # a person in another room does not occupy this tile
    again = c.post("/api/builder/character/place", json=_place(id="three", display_name="Three", region="cellar", at=[5, 1]))
    assert again.status_code == 422 and "someone already stands" in again.json()["detail"]
    assert set(_speakers(pack)) >= {"one", "two"}


def test_with_no_tile_given_the_engine_picks_one_inside_that_room(acts_home):
    pack = _add_cellar(acts_home)
    r = TestClient(app).post("/api/builder/character/place", json=_place(id="auto", display_name="Auto", region="cellar"))
    assert r.status_code == 200, r.text
    x, y = _speakers(pack)["auto"]["at"]
    rows = (pack / "acts" / "act-1" / "cellar" / "map.md").read_text(encoding="utf-8").splitlines()
    assert rows[y][x] == "."                                           # a floor tile of the CELLAR map
