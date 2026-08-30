"""Whisper NPCs - the engine stepping into the world.

A speaker stands at a place and speaks in the current phase's tone.
Seeds hold the shape; the engine keeps the voice alive between
visits. If the model is unreachable, a seed line speaks instead -
the world never breaks because the whisper went quiet.
"""

import json
import os

import httpx
from pydantic import BaseModel, ValidationError

from .generator import KEEP_ALIVE, MODEL, OLLAMA_URL
from .paths import pack_file
from .world import load_world, phase_tone

SCHEMA = {
    "type": "object",
    "properties": {
        "speaker": {"type": "string"},
        "line": {"type": "string"},
    },
    "required": ["speaker", "line"],
}


class NpcLine(BaseModel):
    speaker: str
    line: str
    source: str = "engine"


def _speaker(key: str) -> dict:
    speakers = load_world()["speakers"]
    if key not in speakers:
        raise RuntimeError(f"unknown speaker '{key}' in world pack")
    return speakers[key]


def build_payload(phase: str, key: str) -> dict:
    spec = _speaker(key)
    voice = pack_file(spec["voice_file"]).read_text(encoding="utf-8")
    return {
        "model": MODEL,
        "system": (
            voice
            + f"\n\nCURRENT PHASE: {phase_tone(phase)}\n"
        ),
        "prompt": (
            f"{spec['name']} speaks one line at {spec['near']}, in the "
            "current phase's tone. Reply with only the JSON object."
        ),
        "format": SCHEMA,
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": 0.85},
    }


def generate_line(phase: str = "whispers", key: str = "the ferryman") -> NpcLine:
    spec = _speaker(key)
    payload = build_payload(phase, key)
    for _ in range(2):
        try:
            r = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=180)
            r.raise_for_status()
            raw = json.loads(r.text)["response"]
            line = NpcLine.model_validate_json(raw)
            line.speaker = spec["name"]
            return line
        except (httpx.HTTPError, ValidationError, KeyError, ValueError):
            continue
    return NpcLine(
        speaker=spec["name"],
        line=spec["seeds"].get(phase, next(iter(spec["seeds"].values()))),
        source="seed",
    )
