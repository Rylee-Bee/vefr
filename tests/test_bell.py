import json

import pytest

from old-name import bell
from old-name.bell import Letter, build_payload, generate_letter


class FakeResponse:
    def __init__(self, body: str):
        self._body = body
        self.status_code = 200

    def raise_for_status(self):
        pass

    @property
    def text(self):
        return json.dumps({"response": self._body})


GOOD = json.dumps({"letter": "Keep the door shut at night. The rest is yours. -m"})


def test_payload_asks_for_the_goodbye():
    p = build_payload()
    assert p["format"]["required"] == ["letter"]
    assert "goodbye" in p["prompt"]
    assert p["options"]["temperature"] == 0.8


def test_letter_parses(monkeypatch):
    monkeypatch.setattr(bell.httpx, "post", lambda *a, **k: FakeResponse(GOOD))
    letter = generate_letter()
    assert "door" in letter.letter


def test_letter_retries(monkeypatch):
    calls = []

    def flaky(*a, **k):
        calls.append(1)
        return FakeResponse(GOOD if len(calls) > 1 else "{oops")

    monkeypatch.setattr(bell.httpx, "post", flaky)
    assert "door" in generate_letter().letter
    assert len(calls) == 2
