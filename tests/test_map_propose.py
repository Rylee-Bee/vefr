"""The map-propose route is a sketch, never a write.

The storyteller's "sketch new land" is a proposal only: the model may
redraw the town grid - gated by the same geometry checks as the norns
chat interview - but the route never mutates pack files. The web room
paints over the result and keeps it as a keepsake.
"""

from fastapi.testclient import TestClient

from vefr import chat as chat_mod
from vefr.main import app


def test_map_propose_returns_validated_grid_without_writing(fixture_vefr_home, monkeypatch):
    rows = ["###.###", "#.....#", "#.p...#", "#######"]
    monkeypatch.setattr(chat_mod, "propose_map", lambda story, mood, w, dest: rows)

    pack_json = fixture_vefr_home / "worlds" / "four-phase-pack" / "world.json"
    before = pack_json.read_text(encoding="utf-8")

    client = TestClient(app)
    r = client.post(
        "/api/builder/map/propose",
        json={"name": "four-phase-pack", "story": "a quiet hollow with one path"},
    )

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["grid"] == rows
    assert body["dimensions"] == [len(rows), len(rows[0])]
    assert set(body["legend"]) == {".", "#"}
    assert pack_json.read_text(encoding="utf-8") == before


def test_map_propose_is_honest_without_a_model(fixture_vefr_home):
    client = TestClient(app)
    r = client.post(
        "/api/builder/map/propose",
        json={"name": "four-phase-pack", "story": "a cave under the hill"},
    )

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["reason"]
