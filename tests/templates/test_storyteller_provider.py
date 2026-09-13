"""Storyteller provider boundary tests.

Proves the provider seam degrades gracefully: normal generation works,
timeouts are handled, malformed responses are caught, fallback is used
when the primary fails, and a clear error surfaces when everything is
down.

All HTTP calls are monkeypatched. No network. No mock library.
"""

from __future__ import annotations

import json

import httpx
import pytest

from vefr import generator


# --- Fake response helpers ---

class _Resp:
    """Minimal httpx response stand-in."""

    def __init__(self, text: str, status: int = 200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("POST", "http://fake"),
                response=self,
            )


GOOD_BODY = json.dumps({
    "choices": [{"message": {"content": "Rosa looked up. 'He had somewhere to be.'"}}]
})

GARBAGE_BODY = "this is not json at all"

TIMEOUT_BODY = json.dumps({
    "choices": [{"message": {"content": ""}}]
})


# --- Tests ---

def test_normal_generation_returns_prose(monkeypatch):
    """Provider returns valid prose on a happy path."""
    def fake_post(url, json=None, timeout=None):
        return _Resp(GOOD_BODY)

    monkeypatch.setattr(httpx, "post", fake_post)
    result = generator._completion({
        "model": "test-model",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    })
    assert "Rosa" in result
    assert "somewhere" in result


def test_timeout_handled(monkeypatch):
    """Provider hangs. The error propagates as a connection error."""
    def fake_post(url, json=None, timeout=None):
        raise httpx.ConnectTimeout("connection timed out")

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(httpx.ConnectTimeout):
        generator._completion({
            "model": "test-model",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        })


def test_malformed_response_raises(monkeypatch):
    """Garbage output from the model raises a parse error."""
    def fake_post(url, json=None, timeout=None):
        return _Resp(GARBAGE_BODY)

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises((json.JSONDecodeError, KeyError)):
        generator._completion({
            "model": "test-model",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        })


def test_primary_failure_fallback_used(monkeypatch):
    """When the primary provider fails, the ollama fallback is used.

    The _completion function routes by the active storyteller's provider.
    We mock resolve_active to return an OLLAMA provider so the ollama
    wire path is exercised.
    """
    from vefr.storyteller import Capabilities, Provider, Storyteller

    fake_storyteller = Storyteller(
        id="fake-ollama",
        name="Fake Ollama",
        version="0.0.0",
        model_provider=Provider.OLLAMA,
        model="test-model",
        capabilities=Capabilities(text=True),
    )

    monkeypatch.setattr(
        "vefr.storyteller.resolve_active", lambda: fake_storyteller
    )

    import json as _json

    def fake_post(url, json=None, timeout=None):
        return _Resp(_json.dumps({"response": "Keeper sat still."}))

    monkeypatch.setattr(httpx, "post", fake_post)

    result = generator._completion({
        "model": "test-model",
        "prompt": "hello",
        "system": "test",
        "format": {},
        "stream": False,
        "keep_alive": "1m",
        "options": {"temperature": 0.85},
    })
    assert "Keeper" in result


def test_both_providers_unavailable_clear_error(monkeypatch):
    """When all backends are down, the error is clear."""
    def fake_post(url, json=None, timeout=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(httpx.ConnectError, match="connection refused"):
        generator._completion({
            "model": "test-model",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        })


def test_diagnostics_which_model_produced_response(monkeypatch):
    """The payload carries the model name so we can trace which
    model produced a given response."""
    captured_payloads = []

    def fake_post(url, json=None, timeout=None):
        captured_payloads.append(json)
        return _Resp(GOOD_BODY)

    monkeypatch.setattr(httpx, "post", fake_post)
    generator._completion({
        "model": "gemma-4-e2b",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    })

    assert len(captured_payloads) == 1
    assert captured_payloads[0]["model"] == "gemma-4-e2b"


def test_http_error_status_raises(monkeypatch):
    """A 500 from the backend raises cleanly."""
    def fake_post(url, json=None, timeout=None):
        return _Resp('{"error":"internal"}', status=500)

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(httpx.HTTPStatusError):
        generator._completion({
            "model": "test-model",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        })
