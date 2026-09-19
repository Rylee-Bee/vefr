"""Map check is the engine's own gate on a storyteller's sketch.

The drawing table never trusts its own ink: the draft grid is
swapped into a copy of the unified pack and run through the same
maplab.validate checks as `norns validate`. Deterministic, read-only,
no model calls.
"""

from fastapi.testclient import TestClient

from vefr.main import app


def test_map_check_accepts_the_packs_own_ground(fixture_vefr_home):
    client = TestClient(app)
    r = client.post(
        "/api/builder/map/check",
        json={"name": "four-phase-pack", "grid": ["###", "#.#", "###"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["errors"] == []


def test_map_check_rejects_a_walled_hero(fixture_vefr_home):
    client = TestClient(app)
    r = client.post(
        "/api/builder/map/check",
        json={"name": "four-phase-pack", "grid": ["###", "###", "###"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert any("not walkable" in e for e in body["errors"])


def test_map_check_needs_a_rectangular_grid(fixture_vefr_home):
    client = TestClient(app)
    r = client.post(
        "/api/builder/map/check",
        json={"name": "four-phase-pack", "grid": ["###", "##"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["errors"]
