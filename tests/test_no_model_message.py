"""When no model answers, a person gets a sentence, not a URL.

The contract, in one place:

- `GeneratorUnavailable` / `GeneratorFailed` carry a plain-English
  sentence in `str(exc)`: what was tried (pack + model, in words), that
  the game still plays, and what to do next.
- The raw endpoint URL, exception class and text stay on `.detail` (and
  in the ERROR log), so debuggers keep what they need.
- `storyteller_test._looks_like_missing_model` keeps working off that
  preserved detail - a 404 is still a skip, a refused connection is
  still an error.

All HTTP is monkeypatched. No network, no skips.
"""

from __future__ import annotations

import httpx
import pytest

from vefr import generator, storyteller, storyteller_test
from vefr.generator import GeneratorUnavailable

NEXT_STEPS = ("ratatoskr spark install", "VEFR_LLAMACPP_URL")


def _clean_env(monkeypatch):
    """No BYOM pin: the active pack is whatever ships with the engine."""
    monkeypatch.delenv("VEFR_STORYTELLER", raising=False)


def test_the_message_names_the_pack_and_model_in_words(monkeypatch):
    """The sentence says who was asked, that play continues, and how to fix it."""
    _clean_env(monkeypatch)
    pack = storyteller.resolve_active()
    # Resolve in the test rather than hardcoding a second copy - but a
    # resolved pack must actually name something.
    assert pack.id and pack.model

    def fake_post(url, json=None, timeout=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(GeneratorUnavailable) as excinfo:
        generator._completion(generator.build_payload("whispers", None))

    msg = str(excinfo.value)
    assert pack.id in msg
    assert pack.model in msg
    assert "still plays" in msg
    for step in NEXT_STEPS:
        assert step in msg


def test_the_message_leaks_no_url_or_status(monkeypatch):
    """Regression guard for the whole task: the sentence stays human.

    The raw transport facts live on `.detail`, not in the message.
    """
    _clean_env(monkeypatch)

    def fake_post(url, json=None, timeout=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(GeneratorUnavailable) as excinfo:
        generator._completion(generator.build_payload("whispers", None))

    msg = str(excinfo.value)
    for leak in ("http://", "127.0.0.1", "500", "404"):
        assert leak not in msg
    # ...while the detail keeps the endpoint URL for whoever debugs.
    assert "http://" in excinfo.value.detail
    assert generator.LLAMACPP_URL in excinfo.value.detail


def test_a_missing_model_still_reads_as_skipped(monkeypatch):
    """The trap: a 404 from the endpoint must still classify as SKIPPED.

    `_looks_like_missing_model` substring-matches the raw detail. The
    friendly sentence drops it from `str(exc)`, so this only passes if
    the detail is genuinely preserved on the exception.
    """
    _clean_env(monkeypatch)
    request = httpx.Request("POST", f"{generator.LLAMACPP_URL}/v1/chat/completions")

    def fake_post_404(url, json=None, timeout=None):
        raise httpx.HTTPStatusError(
            "Client error '404 Not Found' for url "
            f"'{generator.LLAMACPP_URL}/v1/chat/completions'",
            request=request,
            response=httpx.Response(404, request=request),
        )

    monkeypatch.setattr(httpx, "post", fake_post_404)

    with pytest.raises(GeneratorUnavailable) as excinfo:
        generator._completion(generator.build_payload("whispers", None))

    # The status is NOT in the sentence...
    assert "404" not in str(excinfo.value)
    # ...so the heuristic must be reading the preserved raw detail.
    assert "404" in excinfo.value.detail
    assert storyteller_test._looks_like_missing_model(excinfo.value) is True

    # A refused connection is a real error, never a skip.
    def fake_post_refused(url, json=None, timeout=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", fake_post_refused)
    with pytest.raises(GeneratorUnavailable) as refused:
        generator._completion(generator.build_payload("whispers", None))
    assert storyteller_test._looks_like_missing_model(refused.value) is False


def test_a_byom_pin_still_builds_a_message(monkeypatch):
    """A pin with no pack behind it still yields a sane sentence.

    Building an error message must never raise - there is no pack to
    name, so the model name stands alone.
    """
    pinned = "totally-unpinned-model-9b"
    monkeypatch.setenv("VEFR_STORYTELLER", pinned)
    assert storyteller.resolve_active().model == pinned

    def fake_post(url, json=None, timeout=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(GeneratorUnavailable) as excinfo:
        generator._completion(generator.build_payload("whispers", None))

    msg = str(excinfo.value)
    assert pinned in msg
    assert "still plays" in msg
