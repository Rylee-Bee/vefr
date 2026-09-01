"""Whisper NPCs - the engine stepping into the world.

A speaker stands at a place and speaks in the current phase's tone.
Seeds hold the shape; the engine keeps the voice alive between
visits. If the model is unreachable, a seed line speaks instead -
the world never breaks because the whisper went quiet.
"""

import httpx
from pydantic import BaseModel, ValidationError

from . import generator
from .world import current_act, load_world, phase_tone, resolve_voice_file

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


def _speaker(key: str | None) -> dict:
    """Resolve a speaker key against the pack.

    No key means the pack's first speaker - the engine never
    hardcodes a speaker name; a hardcoded default used to live here
    and broke any pack that had never heard of it. A pack with no
    speakers at all (sample-world's permanent state) raises a plain
    RuntimeError instead of dying inside next(iter({})) - the route
    turns it into a 404 that names the real situation.
    """
    speakers = current_act(load_world())["speakers"]
    if not speakers:
        raise RuntimeError("this pack has no speakers")
    if key is None:
        return next(iter(speakers.values()))
    if key not in speakers:
        raise RuntimeError(f"unknown speaker '{key}' in world pack")
    return speakers[key]


def build_payload(phase: str, key: str | None = None) -> dict:
    spec = _speaker(key)
    voice = resolve_voice_file(spec["voice_file"]).read_text(encoding="utf-8")
    seed = spec["seeds"].get(phase, next(iter(spec["seeds"].values()), ""))
    return {
        "model": generator.MODEL,
        "system": (
            voice
            + f"\n\nCURRENT PHASE: {phase_tone(phase)}\n"
        ),
        "prompt": (
            f"{spec['name']} speaks one line at {spec['near']}, in the "
            "current phase's tone. The seed line for this phase - match "
            f"its plainness and shape, do not copy it word for word: "
            f"\"{seed}\" Reply with only the JSON object."
        ),
        "format": SCHEMA,
        "stream": False,
        "think": False,
        "keep_alive": generator.KEEP_ALIVE,
        "options": {"temperature": 0.85},
    }


def generate_line(phase: str = "whispers", key: str | None = None) -> NpcLine:
    spec = _speaker(key)
    payload = build_payload(phase, key)
    for _ in range(2):
        try:
            raw = generator._completion(payload)
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
