import httpx
from pydantic import BaseModel, ValidationError

from . import generator
from .saga import sealed_voice
from .world import load_world

SCHEMA = {
    "type": "object",
    "properties": {"letter": {"type": "string"}},
    "required": ["letter"],
}


class Letter(BaseModel):
    letter: str


def build_payload() -> dict:
    return {
        "model": generator.MODEL,
        "system": _system(),
        "prompt": load_world()["voices"]["mother"]["strike"],
        "format": SCHEMA,
        "stream": False,
        "think": False,
        "keep_alive": generator.KEEP_ALIVE,
        "options": {"temperature": 0.8},
    }


def _system() -> str:
    return sealed_voice("mother")


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
