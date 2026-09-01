"""Tests for Contextual AI Enhance structured generation.

Covers:
  - Map / POI enhancement (title, description, details)
  - Voice prompt enhancement (rules, seed_line, strike_prompt)
  - Item curse / flavor enhancement (name, kind, lore, enchant, curse)
  - FastAPI endpoints for all three under /api/builder/enhance/*
"""

import json
import pytest
from fastapi.testclient import TestClient

from pathlib import Path

from vefr import enhance, generator, main, world as world_mod


@pytest.fixture
def sample_pack():
    return Path(__file__).resolve().parents[1] / "worlds" / "sample-world"


@pytest.fixture
def client():
    return TestClient(main.app)


def test_enhance_map_schema_and_generator(sample_pack, monkeypatch):
    monkeypatch.setenv("VEFR_WORLD", "sample-world")
    world_mod.load_world.cache_clear()

    mock_resp = {
        "title": "The Old Scriptorium",
        "description": "Candles flicker against damp stone walls. The smell of ink and old reed paper lingers.",
        "details": ["A carved wooden lectern", "An iron key hanging by a braided thread"],
    }
    monkeypatch.setattr(generator, "_completion", lambda *args, **kwargs: json.dumps(mock_resp))

    req = enhance.MapEnhanceRequest(
        region="town",
        poi_name="scriptorium",
        context="A quiet study where town ledgers are kept.",
        phase="whispers",
    )
    res = enhance.enhance_map(req)
    assert res.region == "town"
    assert res.poi_name == "scriptorium"
    assert res.title == "The Old Scriptorium"
    assert "ink" in res.description
    assert len(res.details) == 2


def test_enhance_voice_schema_and_generator(sample_pack, monkeypatch):
    monkeypatch.setenv("VEFR_WORLD", "sample-world")
    world_mod.load_world.cache_clear()

    mock_resp = {
        "name": "Astrid the Weaver",
        "rules": "Speaks softly with measured pauses. Never mentions the sea directly.",
        "seed_line": "The thread does not break unless you pull it crooked.",
        "strike_prompt": "Astrid writes a short letter about mending what was torn.",
    }
    monkeypatch.setattr(generator, "_completion", lambda *args, **kwargs: json.dumps(mock_resp))

    req = enhance.VoiceEnhanceRequest(
        speaker_name="Astrid",
        role="weaver",
        personality="patient, observant",
        phase="doubts",
    )
    res = enhance.enhance_voice(req)
    assert res.name == "Astrid the Weaver"
    assert "thread" in res.seed_line
    assert "mending" in res.strike_prompt


def test_enhance_item_schema_and_generator(sample_pack, monkeypatch):
    monkeypatch.setenv("VEFR_WORLD", "sample-world")
    world_mod.load_world.cache_clear()

    mock_resp = {
        "name": "Ring of Muted Echoes",
        "kind": "ring",
        "lore": "Forged in the hearth when the north wind blew cold.",
        "enchant": "Softens the sound of footsteps on frozen grass.",
        "curse": "The bearer cannot hear their own reflection in water.",
    }
    monkeypatch.setattr(generator, "_completion", lambda *args, **kwargs: json.dumps(mock_resp))

    req = enhance.ItemEnhanceRequest(
        base_name="iron ring",
        kind="ring",
        bond="attuned",
        intent="subtle audio dampening relic",
    )
    res = enhance.enhance_item(req)
    assert res.name == "Ring of Muted Echoes"
    assert res.kind == "ring"
    assert "footsteps" in res.enchant
    assert "reflection" in res.curse


def test_fastapi_enhance_routes(sample_pack, monkeypatch, client):
    monkeypatch.setenv("VEFR_WORLD", "sample-world")
    world_mod.load_world.cache_clear()

    mock_map = {
        "title": "Town Gate",
        "description": "Heavy timber bound with rusted iron bands.",
        "details": ["Deep ruts from wagon wheels", "A sentinel's bell hanging above"],
    }
    mock_voice = {
        "name": "the old soldier",
        "rules": "Speaks plain and direct.",
        "seed_line": "The wind carries no lies today.",
        "strike_prompt": "the soldier warns of oncoming weather.",
    }
    mock_item = {
        "name": "Weaver's Token",
        "kind": "token",
        "lore": "A smooth river pebble wrapped in twine.",
        "enchant": "Always feels warm to the touch.",
        "curse": "Draws curious birds to your shoulder at dawn.",
    }

    # Test /api/builder/enhance/map
    monkeypatch.setattr(generator, "_completion", lambda *args, **kwargs: json.dumps(mock_map))
    r = client.post("/api/builder/enhance/map", json={"region": "town", "poi_name": "gate"})
    assert r.status_code == 200
    assert r.json()["title"] == "Town Gate"

    # Test /api/builder/enhance/voice
    monkeypatch.setattr(generator, "_completion", lambda *args, **kwargs: json.dumps(mock_voice))
    r = client.post("/api/builder/enhance/voice", json={"speaker_name": "the soldier", "role": "sentinel"})
    assert r.status_code == 200
    assert r.json()["name"] == "the old soldier"

    # Test /api/builder/enhance/item
    monkeypatch.setattr(generator, "_completion", lambda *args, **kwargs: json.dumps(mock_item))
    r = client.post("/api/builder/enhance/item", json={"base_name": "token", "kind": "token", "bond": "assigned"})
    assert r.status_code == 200
    assert r.json()["name"] == "Weaver's Token"
