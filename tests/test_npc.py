"""Story tests - the ferryman. Skipped unless the resolved world
IS private-canon."""

import json
from pathlib import Path

import httpx
import pytest

from norn import npc
from norn.npc import build_payload, generate_line
from norn.paths import world_name

_pack = Path(__file__).resolve().parents[1] / 'worlds' / 'private-canon'
if world_name() != 'private-canon' or not (_pack / 'world.json').exists():
    pytest.skip('private-canon pack not resolved', allow_module_level=True)


class FakeResponse:
    def __init__(self, body: str):
        self._body = body
        self.status_code = 200

    def raise_for_status(self):
        pass

    @property
    def text(self):
        return json.dumps({"response": self._body})


GOOD = json.dumps(
    {"speaker": "the ferryman", "line": "Drink while the bucket's down."}
)


def test_payload_names_the_speaker_and_carries_the_voice():
    p = build_payload("feared", "the ferryman")
    assert p["format"]["required"] == ["speaker", "line"]
    assert "the ferryman" in p["prompt"]
    assert "parish ledger" in p["system"]


def test_line_parses(monkeypatch):
    monkeypatch.setattr(npc.httpx, "post", lambda *a, **k: FakeResponse(GOOD))
    line = generate_line("whispers")
    assert line.speaker == "the ferryman"
    assert line.source == "engine"


def test_fallback_uses_seed_when_the_whisper_is_quiet(monkeypatch):
    def down(*a, **k):
        raise httpx.ConnectError("ollama unreachable")

    monkeypatch.setattr(npc.httpx, "post", down)
    line = generate_line("awed")
    assert "the wanderer" in line.line
    assert line.source == "seed"


def test_unknown_speaker_raises():
    with pytest.raises(RuntimeError):
        build_payload("whispers", "nobody")
