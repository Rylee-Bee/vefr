"""Story tests - the demonstration pack's speaker (The Keeper) as
the tracked known-good fixture. The pack ships with the engine:
NPC payload tests prove the engine surfaces a pack's speaker
voices intact on every checkout."""

import json

import httpx
import pytest

from vefr import generator
from vefr.npc import build_payload, generate_line

GOOD = json.dumps(
    {"speaker": "The Keeper", "line": "Sit. The stone does not ask your name."}
)


def test_payload_names_the_speaker_and_carries_the_voice():
    p = build_payload("dusk", "keeper")
    assert p["format"]["required"] == ["speaker", "line"]
    assert "The Keeper" in p["prompt"]
    # the voice system prompt is the pack's own file, not engine prose
    assert "short sentences" in p["system"]


def test_line_parses(monkeypatch):
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: GOOD)
    line = generate_line("dusk")
    assert line.speaker == "The Keeper"
    assert line.source == "engine"


def test_fallback_uses_seed_when_the_whisper_is_quiet(monkeypatch):
    def down(*a, **k):
        raise httpx.ConnectError("backend unreachable")

    monkeypatch.setattr(generator, "_completion", down)
    line = generate_line("dawn")
    assert "The stone kept the night" in line.line
    assert line.source == "seed"


def test_fallback_survives_the_fail_closed_translation(monkeypatch):
    """Pin at the PRODUCTION seam, not below it.

    _completion wraps httpx failures as GeneratorUnavailable /
    GeneratorFailed before generate_line ever sees them (the
    fail-closed boundary). The seed must still speak through that
    translation - a raw httpx error injected under _completion would
    have kept passing while live runs404'd with leaked internals.
    """
    # Patch only the transport call on generator's real httpx module:
    # _completion's except clauses must still resolve httpx.ConnectError
    # & friends, so a whole-module stub would break them.
    def down(*a, **k):
        raise httpx.ConnectError("backend unreachable")

    monkeypatch.setattr(generator.httpx, "post", down)
    line = generate_line("dawn")
    assert "The stone kept the night" in line.line
    assert line.source == "seed"


def test_unknown_speaker_raises():
    with pytest.raises(RuntimeError):
        build_payload("dusk", "nobody")
