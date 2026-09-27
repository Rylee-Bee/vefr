"""VEFR as a Worlds room: the five room/0 endpoints and the library extra.

Shapes are checked against Play-Nice's schemas when a sibling checkout is
present (the estate layout); the behaviour checks run everywhere.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vefr.main import app

H = {"Authorization": "Bearer test-token"}
SCHEMAS = Path(__file__).resolve().parents[2] / "play-nice-contracts" / "schema"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("VEFR_ROOM_TOKEN", "test-token")
    return TestClient(app)


def _validate(doc, schema_file, ref=None):
    jsonschema = pytest.importorskip("jsonschema")
    if not (SCHEMAS / schema_file).is_file():
        pytest.skip("play-nice-contracts not checked out beside vefr")
    schema = json.loads((SCHEMAS / schema_file).read_text())
    if ref:
        schema = {"$schema": schema.get("$schema"), "$defs": schema["$defs"], "$ref": f"#/$defs/{ref}"}
    jsonschema.Draft202012Validator(schema).validate(doc)


def test_room_is_off_without_a_token(monkeypatch):
    monkeypatch.delenv("VEFR_ROOM_TOKEN", raising=False)
    r = TestClient(app).get("/room", headers=H)
    assert r.status_code == 503 and "test-token" not in r.text


def test_room_needs_the_right_bearer_token(client):
    assert client.get("/room").status_code == 401
    assert client.get("/room/library", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_descriptor_offers_the_library(client):
    d = client.get("/room", headers=H).json()
    assert d["contract"] == "room/0" and d["id"] == "vefr"
    assert d["status"] in {"healthy", "degraded", "unhealthy", "unknown"}
    assert set(d["offers"]) == {"art", "library", "views"}


def test_cards_needs_and_actions(client):
    cards = client.get("/room/cards", headers=H).json()
    assert cards and cards[0]["link"] == "/#library" and cards[0]["lane"] == "work"
    assert client.get("/room/needs-you", headers=H).json() == []
    assert client.get("/room/actions", headers=H).json() == []


def test_every_action_call_gets_a_labelled_refusal(client):
    r = client.post("/room/actions/anything", headers=H)
    assert r.status_code == 400 and r.json()["ok"] is False
    r = client.post("/room/actions/anything", headers={**H, "Idempotency-Key": "k1"})
    assert r.status_code == 404 and r.json()["summary"] == "There's no action with that name."


def test_library_is_frodi_with_both_shelves_and_every_book(client):
    doc = client.get("/room/library", headers=H).json()
    assert doc["contract"] == "library/0" and doc["keeper"]["id"] == "frodi"
    assert [s["id"] for s in doc["shelves"]] == ["how-games-are-made", "how-vefr-works"]
    assert len(doc["books"]) == len(list((Path(__file__).resolve().parents[1] / "web/library").glob("[0-9]*.md")))
    for b in doc["books"]:
        assert b["short"] and b["pages"][0]["kind"] == "plain", b["id"]
        assert b["source"].startswith("vefr: "), b["id"]
        path = Path(__file__).resolve().parents[1] / b["source"].removeprefix("vefr: ")
        assert path.exists(), f"{b['id']}: source {path} is missing"


def test_words_page_is_built_from_the_glossary(client):
    doc = client.get("/room/library", headers=H).json()
    maps = next(b for b in doc["books"] if b["id"] == "14-how-maps-work")
    words = [p for p in maps["pages"] if p["kind"] == "words"]
    assert len(words) == 1 and "- *tile*: One square of a map." in words[0]["text"]


def test_art_is_an_allow_list(client):
    r = client.get("/room/art/frodi.webp", headers=H)
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    assert client.get("/room/art/icon-192.webp", headers=H).status_code == 404


def test_shapes_match_the_play_nice_schemas(client):
    _validate(client.get("/room/library", headers=H).json(), "library.schema.json")
    _validate(client.get("/room", headers=H).json(), "room.schema.json", "room")
    _validate(client.get("/room/cards", headers=H).json(), "room.schema.json", "cards_response")
    _validate(client.get("/room/needs-you", headers=H).json(), "room.schema.json", "needs_you_response")
    _validate(client.get("/room/actions", headers=H).json(), "room.schema.json", "actions_response")
    _validate(client.post("/room/actions/x", headers={**H, "Idempotency-Key": "k"}).json(),
              "room.schema.json", "action_receipt")


def test_library_carries_the_glossary_for_tap_to_learn(client):
    doc = client.get("/room/library", headers=H).json()
    assert doc["glossary"]["commit"] == {"plain": "Saving a change for good, with a note of what changed.", "local": "Keep"}
