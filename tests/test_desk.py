"""The Desk ruleset: verification, printing, and the world-knowledge
loop that feeds back into every later prompt.

Server-side mechanics only - the felt half lives in the playtest
notes and the desk harness (tests/fixtures/desk_harness.mjs).
"""

import pytest
from fastapi.testclient import TestClient

from vefr import journal, saga, npc
from vefr.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    return TestClient(app)


def _hear(sid, whisper, is_true):
    journal.log("rumor", sid=sid, phase="dusk", speaker="someone",
                whisper=whisper, is_true=is_true)


def test_verify_true_against_a_true_rumor(client):
    _hear("s1", "the miller's wheel is cracked", True)
    r = client.post("/api/desk/verify?session=s1",
                    json={"whisper": "the miller's wheel is cracked",
                          "verdict": "true"})
    body = r.json()
    assert r.status_code == 200
    assert body["verified"] is True
    assert body["correct"] is True
    assert body["fact"].startswith("confirmed:")


def test_verify_false_against_a_true_rumor_is_wrong_not_punished(client):
    _hear("s1", "the miller's wheel is cracked", True)
    r = client.post("/api/desk/verify?session=s1",
                    json={"whisper": "the miller's wheel is cracked",
                          "verdict": "false"})
    body = r.json()
    assert body["verified"] is True
    assert body["correct"] is False
    # a wrong verdict is a journal entry, not a failure state
    kinds = [e["kind"] for e in journal.entries("s1")]
    assert "desk_verdict" in kinds


def test_verify_unknown_whisper_is_honest(client):
    r = client.post("/api/desk/verify?session=s1",
                    json={"whisper": "never heard it", "verdict": "true"})
    body = r.json()
    assert body["verified"] is False
    assert "never heard" in body["reason"]


def test_verify_bad_verdict_is_a_400(client):
    _hear("s1", "x", True)
    r = client.post("/api/desk/verify?session=s1",
                    json={"whisper": "x", "verdict": "maybe"})
    assert r.status_code == 400


def test_print_and_facts_replay(client):
    _hear("s1", "the pool players sing at night", True)
    _hear("s1", "the mayor owns the ferry", False)
    client.post("/api/desk/verify?session=s1",
                json={"whisper": "the pool players sing at night",
                      "verdict": "true"})
    client.post("/api/desk/verify?session=s1",
                json={"whisper": "the mayor owns the ferry",
                      "verdict": "false"})
    client.post("/api/desk/print?session=s1",
                json={"headline": "SONG HEARD AT THE FLOODED POOL"})
    facts = client.get("/api/desk/facts?session=s1").json()["facts"]
    kinds = [f["kind"] for f in facts]
    assert kinds == ["confirmed", "debunked", "printed"]
    assert facts[2]["text"] == "SONG HEARD AT THE FLOODED POOL"


def test_print_empty_headline_is_a_400(client):
    r = client.post("/api/desk/print?session=s1", json={"headline": "  "})
    assert r.status_code == 400


def test_knowledge_feeds_the_whisper_prompt(client):
    _hear("s1", "the pool players sing at night", True)
    client.post("/api/desk/verify?session=s1",
                json={"whisper": "the pool players sing at night",
                      "verdict": "true"})
    prompt = saga.system_prompt("dusk", sid="s1")
    assert "WHAT THE WORLD KNOWS NOW" in prompt
    assert "confirmed: the pool players sing at night" in prompt
    # without a session the prompt stays silent - no filler
    assert "WHAT THE WORLD KNOWS NOW" not in saga.system_prompt("dusk")


def test_knowledge_feeds_the_npc_prompt():
    journal.log("rumor", sid="s2", phase="dusk", speaker="x",
                whisper="the ferry rope was cut", is_true=False)
    from vefr import desk
    desk.verify("s2", "the ferry rope was cut", "false")
    payload = npc.build_payload("dusk", None, sid="s2")
    assert "debunked: the ferry rope was cut" in payload["system"]
