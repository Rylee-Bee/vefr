
import pytest

from vefr import generator
from vefr.generator import build_payload, generate_rumor


GOOD = '{"speaker":"Old Katla","whisper":"They say the mill grinds what the miller forgets.","is_true":false}'


def test_payload_carries_vram_discipline_and_schema():
    p = build_payload("whispers", "a drowned bell")
    assert p["model"]
    assert p["keep_alive"] == generator.KEEP_ALIVE
    assert p["format"]["required"] == ["speaker", "whisper", "is_true"]
    assert "a drowned bell" in p["prompt"]


def test_generate_parses_card(monkeypatch):
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: GOOD)
    card = generate_rumor("whispers")
    assert card.speaker == "Old Katla"
    assert card.is_true is False


def test_generate_retries_on_bad_json(monkeypatch):
    calls = []

    def flaky(*a, **k):
        calls.append(1)
        return GOOD if len(calls) > 1 else "not json at all"

    monkeypatch.setattr(generator, "_completion", flaky)
    card = generate_rumor("whispers")
    assert "mill" in card.whisper
    assert len(calls) == 2


def test_generate_raises_after_two_failures(monkeypatch):
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: "still bad")
    with pytest.raises(RuntimeError):
        generate_rumor("whispers")


def test_openai_compatible_body_bounds_max_tokens(monkeypatch):
    # llama.cpp defaults to unlimited generation; the body must carry a cap
    # (the function default) unless the payload overrides it (lore drafts).
    from vefr import storyteller

    sent = []

    class _Resp:
        text = '{"choices": [{"message": {"content": "ok"}}]}'

        def raise_for_status(self):
            pass

    def fake_post(url, json, timeout):
        sent.append(json)
        return _Resp()

    st = storyteller.Storyteller(
        id="t", name="t", version="0", model_provider=storyteller.Provider.OPENAI_COMPATIBLE,
        model="m", capabilities=storyteller.Capabilities(text=True),
    )
    monkeypatch.setattr(storyteller, "resolve_active", lambda: st)
    monkeypatch.setattr(generator, "LLAMACPP_URL", "http://stub")
    monkeypatch.setattr(generator.httpx, "post", fake_post)

    assert generator._completion({"model": "m", "system": "s", "prompt": "p"}) == "ok"
    assert generator._completion({"model": "m", "prompt": "p"}, max_tokens=64) == "ok"
    assert generator._completion({"model": "m", "prompt": "p", "max_tokens": 4096}) == "ok"
    assert [b["max_tokens"] for b in sent] == [1024, 64, 4096]
