"""Teach while building: Fróði names the idea an author just used."""
import re

import pytest
from fastapi.testclient import TestClient

from vefr import teach
from vefr.room import load_glossary

G = load_glossary()
TEACH = teach.teachable(G)


@pytest.fixture(autouse=True)
def fresh_store(tmp_path, monkeypatch):
    monkeypatch.setattr(teach, "_store", lambda: tmp_path / "learning.json")


def test_there_are_43_ideas_each_complete():
    assert len(TEACH) >= 43
    for key, e in TEACH.items():
        assert e["plain"] and e["when"] and e["why"] and e["example"], key
        assert e["teach"] in {"core", "story", "world", "feel", "characters", "systems", "maps", "type"}, key
        for c in e["cues"]:
            re.compile(c)


@pytest.mark.parametrize("key", sorted(TEACH))
def test_each_example_wakes_its_own_idea(key):
    """If an idea's own example sentence can't wake it, its cues are wrong."""
    assert key in teach.candidates(TEACH[key]["example"], G)


def test_plain_chat_wakes_nothing():
    for msg in ["hello!", "what should I do next?", "thanks, that's lovely"]:
        assert teach.candidates(msg, G) == []


def _model(term, context):
    calls = []

    def fake(message, cands, glossary):
        calls.append(cands)
        return (term if term in cands or term == "none" else "none"), context
    fake.calls = calls
    return fake


def test_no_cue_means_no_model_call():
    m = _model("gating", "x")
    out = teach.recognize("hello there", G, model=m)
    assert out["teach"] is None and m.calls == []


def test_no_model_means_no_note():
    out = teach.recognize("You can't open it until you find the key.", G, model=lambda *a: None)
    assert out["teach"] is None and "never guesses" in out["why_not"]


def test_the_hidden_door_then_the_ability_then_familiar():
    door = "I want a hidden door here, but you can't find it until you have the weird lantern."
    card = teach.recognize(door, G, model=_model("gating", "the hidden door that needed the lantern"))["teach"]
    assert card["term"] == "gating" and card["stage"] == "first"
    assert card["context"] == "the hidden door that needed the lantern" and "first_context" not in card

    ability = "Don't let the player use this ability until they've spoken to Mira."
    card = teach.recognize(ability, G, model=_model("gating", "the ability that needs Mira"))["teach"]
    assert card["stage"] == "again" and card["first_context"] == "the hidden door that needed the lantern"

    teach.recognize(ability, G, model=_model("gating", "the ability that needs Mira"))
    out = teach.recognize(ability, G, model=_model("gating", "the ability that needs Mira"))
    assert out["teach"] is None and "familiar" in out["why_not"]


def test_got_it_twice_makes_an_idea_familiar():
    teach.record_got_it("pacing")
    assert teach.stage(teach.load()["concepts"]["pacing"]) == "again"
    teach.record_got_it("pacing")
    assert teach.stage(teach.load()["concepts"]["pacing"]) == "familiar"


def test_context_must_be_the_authors_own_words():
    msg = "Behind the bookshelf there's a hidden room."
    card = teach.recognize(msg, G, model=_model("secret area", "a dragon's treasure vault in the mountains"))["teach"]
    assert card["term"] == "secret area" and card["context"] == ""


def test_routes(monkeypatch):
    from vefr.main import app
    monkeypatch.setattr(teach, "ask_model", _model("sanctuary", "the tavern where nothing can hurt you"))
    c = TestClient(app)
    r = c.post("/api/teach/recognize", json={"message": "The tavern should be a safe place where nothing can hurt you."})
    card = r.json()["teach"]
    assert card["term"] == "sanctuary" and card["local"] == "safe squares" and card["why"]
    assert c.post("/api/teach/got-it", json={"term": "sanctuary"}).json()["got_it"] == 1
    assert c.post("/api/teach/got-it", json={"term": "commit"}).status_code == 404
    state = c.get("/api/teach").json()["concepts"]
    assert state["sanctuary"]["stage"] == "again" and state["gating"]["stage"] == "new"
