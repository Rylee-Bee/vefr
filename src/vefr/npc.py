"""Whisper NPCs - the engine stepping into the world.

A speaker stands at a place and speaks in the current phase's tone.
Seeds hold the shape; the engine keeps the voice alive between
visits. If the model is unreachable, a seed line speaks instead -
the world never breaks because the whisper went quiet.
"""

import httpx
from pydantic import BaseModel, ValidationError

from . import generator
from .paths import pack_file
from .world import current_act, load_world, phase_tone

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

    No key means the pack's first speaker - the engine must never
    hardcode a name from anyone's story (a "the ferryman" default used to
    live here, which broke any pack that had never heard of her).
    """
    speakers = current_act(load_world())["speakers"]
    if key is None:
        return next(iter(speakers.values()))
    if key not in speakers:
        raise RuntimeError(f"unknown speaker '{key}' in world pack")
    return speakers[key]


def build_payload(phase: str, key: str | None = None) -> dict:
    spec = _speaker(key)
    voice = pack_file(spec["voice_file"]).read_text(encoding="utf-8")
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
