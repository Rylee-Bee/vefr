import json


from vefr import stefna, generator
from vefr.stefna import build_payload, generate_letter


GOOD = json.dumps({"letter": "Keep the door shut at night. The rest is yours. -m"})


def test_payload_asks_for_the_goodbye():
    p = build_payload()
    assert p["format"]["required"] == ["letter"]
    assert "goodbye" in p["prompt"]
    assert p["options"]["temperature"] == 0.8


def test_stefna_voice_defaults_to_mother_for_older_packs(monkeypatch):
    # A pack written before stefna_voice existed has no such key -
    # the mechanic must still work without forcing a rename on disk.
    monkeypatch.setattr(stefna, "load_world", lambda: {"voices": {"mother": {}}})
    assert stefna.stefna_voice_key() == "mother"


def test_stefna_voice_honors_the_pack_pointer(monkeypatch):
    monkeypatch.setattr(
        stefna, "load_world",
        lambda: {"stefna_voice": "keeper", "voices": {"keeper": {}}},
    )
    assert stefna.stefna_voice_key() == "keeper"


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
