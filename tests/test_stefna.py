import json

import pytest

from vefr import stefna, generator
from vefr.stefna import build_payload, generate_letter


GOOD = json.dumps({"letter": "Keep the door shut at night. The rest is yours."})


def test_payload_asks_for_a_letter():
    p = build_payload()
    assert p["format"]["required"] == ["letter"]
    assert "letter" in p["prompt"]
    assert p["options"]["temperature"] == 0.8


def test_stefna_voice_falls_back_to_the_packs_first_voice(monkeypatch):
    # A pack that never named its bell voice still works: the first
    # declared voice takes the role. The engine holds no default -
    # the pack declares itself.
    monkeypatch.setattr(
        stefna, "load_world",
        lambda: {"voices": {"keeper": {}, "other": {}}},
    )
    assert stefna.stefna_voice_key() == "keeper"


def test_stefna_voice_refuses_a_voiceless_pack(monkeypatch):
    monkeypatch.setattr(stefna, "load_world", lambda: {"voices": {}})
    with pytest.raises(KeyError):
        stefna.stefna_voice_key()


def test_letter_parses(monkeypatch):
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: GOOD)
    letter = generate_letter()
    assert "door" in letter.letter


def test_letter_retries(monkeypatch):
    calls = []

    def flaky(*a, **k):
        calls.append(1)
        return GOOD if len(calls) > 1 else "{oops"

    monkeypatch.setattr(generator, "_completion", flaky)
    assert "door" in generate_letter().letter
    assert len(calls) == 2
