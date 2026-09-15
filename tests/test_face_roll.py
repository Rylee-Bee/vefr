"""Face roll is a proposal, never a write.

"Invite a new face" drafts name/role/seed through the same
schema-constrained model path as the interview, but where the face
stands is always deterministic engine code (reachable from the hero's
start, not on anyone's spot, not on flood ground). The route never
touches the pack - the web room keeps the card as a vault item only
when the storyteller says so.
"""

import json

from fastapi.testclient import TestClient

from vefr import chat as chat_mod
from vefr.main import app

# A tiny flat pack with enough room for a new face to stand. The
# hero starts at (0,0) on open ground; row 1 is a wall; the top row
# has three more reachable tiles, so a stranger can be placed at
# (3,0) - the only tile spread-3 from the crowd.
ROOMY_PACK = {
    "name": "roomy-pack",
    "title": "Roomy Pack",
    "phases": {"dusk": "the dusk phase", "dawn": "the dawn phase"},
    "surface": "plain",
    "speakers": {},
    "voices": {},
    "town": {
        "tile": 32,
        "bg": "#131311",
        "hero_start": [0, 0],
        "sanctuary_tiles": ["."],
        "map": ["....", "####", "...."],
        "legend": {
            ".": {"base": ["#212a20"]},
            "#": {"base": ["#2a2e33"], "solid": True},
        },
        "pois": {},
        "water_by_phase": {"dusk": "low", "dawn": "low"},
        "flood_tiles": [],
        "watch": {
            "tower": [0, 0],
            "r_by_phase": {"dusk": 1, "dawn": 2},
            "overlay": "rgba(0,0,0,0.3)",
        },
        "hero_color": "#e8e5df",
    },
}


def _write_roomy(home):
    p = home / "worlds" / "roomy-pack"
    p.mkdir(parents=True, exist_ok=True)
    (p / "world.json").write_text(json.dumps(ROOMY_PACK, ensure_ascii=False), encoding="utf-8")


def test_face_roll_returns_a_drafted_face_without_writing(fixture_vefr_home, monkeypatch):
    _write_roomy(fixture_vefr_home)
    world_json = fixture_vefr_home / "worlds" / "roomy-pack" / "world.json"
    before = world_json.read_text(encoding="utf-8")

    monkeypatch.setattr(
        chat_mod,
        "propose_face",
        lambda story, mood, w: {
            "name": "Moss",
            "role": "the gate-tender",
            "seed": "The gate is heavy this dusk.",
        },
    )

    client = TestClient(app)
    r = client.post("/api/builder/face/roll", json={"name": "roomy-pack", "mood": "quiet"})

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["face"]["name"] == "Moss"
    assert body["face"]["role"] == "the gate-tender"
    assert body["face"]["seed"] == "The gate is heavy this dusk."
    # Placement is engine-chosen: the only spread-3 tile from the hero.
    assert body["face"]["at"] == [3, 0]
    assert world_json.read_text(encoding="utf-8") == before


def test_face_roll_is_honest_without_a_model(fixture_vefr_home):
    _write_roomy(fixture_vefr_home)
    client = TestClient(app)
    r = client.post("/api/builder/face/roll", json={"name": "roomy-pack"})

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["reason"]
