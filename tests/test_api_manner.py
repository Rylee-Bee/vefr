"""API manner: the routes say no in a way a caller can act on.

Three behaviors the live play-loop verification surfaced (2026-09-01):

  - POST /api/vault takes a typed ItemCard body, so a shape error is
    a 422 naming the missing field - not a bare-dict 500 that leaves
    the caller guessing which key it forgot.
  - POST /api/npc with a speaker the pack has never heard of is a
    404 in plain English, not a raw RuntimeError 500.
  - POST /api/npc with no key on a voice-less pack (sample-world's
    permanent state) is also a 404 - `next(iter({}))` used to die
    as StopIteration/500.

The UI cannot reach the last two on sample-world (town.js never
calls /api/npc without a nearby speaker), but the API is public:
hand-rolled calls deserve the honest answer too.
"""

import json

import pytest
from fastapi.testclient import TestClient

from vefr import journal as journal_mod
from vefr import main, npc as npc_mod


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def hermetic(tmp_path, monkeypatch):
    """Point the journal and vault at tmp files so the tests never
    touch the real runtime state."""
    monkeypatch.setattr(journal_mod, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr("vefr.forge.VAULT", tmp_path / "vault.json")
    # forge.py reads the module-level VAULT via derive() at call time,
    # so patching the attribute is enough.


def test_vault_bad_shape_is_422_naming_the_field(client):
    """A keep with a missing required field is a 422 that says which
    field - not a 500 that says nothing."""
    r = client.post("/api/vault", json={"name": "Half a Card"})
    assert r.status_code == 422
    blob = json.dumps(r.json())
    assert "kind" in blob and "bond" in blob


def test_vault_valid_card_still_keeps(client):
    card = {
        "name": "Manner Coin",
        "kind": "trinket",
        "bond": "assigned",
        "lore": "warm from being held.",
    }
    r = client.post("/api/vault", json=card)
    assert r.status_code == 200
    assert r.json()["kept"] is True
    listed = client.get("/api/vault").json()
    assert any(i["name"] == "Manner Coin" for i in listed["items"])


def _fake_speakers(monkeypatch, speakers):
    monkeypatch.setattr(npc_mod, "load_world", lambda: {})
    monkeypatch.setattr(npc_mod, "current_act", lambda w: {"speakers": speakers})


def test_npc_unknown_speaker_is_404(client, monkeypatch):
    _fake_speakers(monkeypatch, {"keeper": {"name": "The Keeper", "near": "the stone", "voice_file": "keeper.md", "seeds": {"dusk": "sit."}}})
    r = client.post("/api/npc", json={"speaker": "nobody", "phase": "dusk"})
    assert r.status_code == 404
    assert "unknown speaker" in r.json()["detail"]
    assert "nobody" in r.json()["detail"]


def test_npc_voiceless_pack_is_404_not_500(client, monkeypatch):
    """sample-world ships voices: 0 by design. The UI never asks for
    a line there, but a hand-rolled call gets an honest 404 instead
    of a StopIteration 500."""
    _fake_speakers(monkeypatch, {})
    r = client.post("/api/npc", json={})
    assert r.status_code == 404
    assert "no speakers" in r.json()["detail"]
