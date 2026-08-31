import json

import pytest

from norn import generator
from norn.generator import RumorCard, build_payload, generate_rumor


class FakeResponse:
    def __init__(self, body: str, status: int = 200):
        self._body = body
        self.status_code = status

    def raise_for_status(self):
        assert self.status_code == 200

    @property
    def text(self):
        return json.dumps({"response": self._body})


GOOD = '{"speaker":"Old Katla","whisper":"They say the mill grinds what the miller forgets.","is_true":false}'


def test_payload_carries_vram_discipline_and_schema():
    p = build_payload("whispers", "a drowned bell")
    assert p["model"]
    assert p["keep_alive"] == generator.KEEP_ALIVE
    assert p["format"]["required"] == ["speaker", "whisper", "is_true"]
    assert "a drowned bell" in p["prompt"]


def test_generate_parses_card(monkeypatch):
    monkeypatch.setattr(
        generator.httpx, "post", lambda *a, **k: FakeResponse(GOOD)
    )
    card = generate_rumor("whispers")
    assert card.speaker == "Old Katla"
    assert card.is_true is False


def test_generate_retries_on_bad_json(monkeypatch):
    calls = []

    def flaky(*a, **k):
        calls.append(1)
        return FakeResponse(GOOD if len(calls) > 1 else "not json at all")

    monkeypatch.setattr(generator.httpx, "post", flaky)
    card = generate_rumor("whispers")
    assert "mill" in card.whisper
    assert len(calls) == 2


def test_generate_raises_after_two_failures(monkeypatch):
    monkeypatch.setattr(
        generator.httpx, "post", lambda *a, **k: FakeResponse("still bad")
    )
    with pytest.raises(RuntimeError):
        generate_rumor("whispers")
