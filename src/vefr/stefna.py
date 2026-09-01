import httpx
from pydantic import BaseModel, ValidationError

from . import generator
from .saga import sealed_voice
from .world import PackError, load_world

SCHEMA = {
    "type": "object",
    "properties": {"letter": {"type": "string"}},
    "required": ["letter"],
}


class Letter(BaseModel):
    letter: str


def stefna_voice_key() -> str:
    """Which speaker's voice fills the Stefna role for this pack.

    A pack points at whichever voice should write the sealed letter
    via a top-level `stefna_voice` field. No default lives in the
    engine - the pack declares its own bell voice; a pack without
    the field falls back to its first declared voice, and a pack
    with no voices at all has nothing for the bell to say.
    """
    w = load_world()
    declared = w.get("stefna_voice")
    voices = w.get("voices") or {}
    pack_name = w.get("name") or w.get("title") or "pack"
    if declared:
        if declared not in voices:
            raise PackError(f"pack '{pack_name}' declares stefna_voice '{declared}' but no such voice exists")
        return declared
    if not voices:
        raise PackError(f"pack '{pack_name}' declares no voices for the bell")
    return next(iter(voices))


def build_payload() -> dict:
    key = stefna_voice_key()
    w = load_world()
    pack_name = w.get("name") or w.get("title") or "pack"
    voice = (w.get("voices") or {}).get(key)
    if not isinstance(voice, dict) or "strike" not in voice:
        raise PackError(f"pack '{pack_name}' voice '{key}' has no strike prompt")
    return {
        "model": generator.MODEL,
        "system": _system(),
        "prompt": voice["strike"],
        "format": SCHEMA,
        "stream": False,
        "think": False,
        "keep_alive": generator.KEEP_ALIVE,
        "options": {"temperature": 0.8},
    }


def _system() -> str:
    return sealed_voice(stefna_voice_key())


def generate_letter() -> Letter:
    payload = build_payload()
    last_err: Exception | None = None
    for _ in range(2):
        try:
            raw = generator._completion(payload)
            return Letter.model_validate_json(raw)
        except (httpx.HTTPError, ValidationError, KeyError, ValueError) as e:
            last_err = e
    raise RuntimeError(f"letter failed schema twice: {last_err}")
