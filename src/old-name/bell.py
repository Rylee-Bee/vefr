import json

import httpx
from pydantic import BaseModel, ValidationError

from .generator import KEEP_ALIVE, MODEL, OLLAMA_URL

SCHEMA = {
    "type": "object",
    "properties": {"letter": {"type": "string"}},
    "required": ["letter"],
}


class Letter(BaseModel):
    letter: str


def build_payload() -> dict:
    return {
        "model": MODEL,
        "system": _system(),
        "prompt": (
            "The bell has been struck. Write the goodbye: the mother's "
            "letter, found with the tongueless bell, kept shut by the "
            "ledger-clasp. Reply with only the JSON object."
        ),
        "format": SCHEMA,
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": 0.8},
    }


def _system() -> str:
    from .style import mother_voice

    return mother_voice()


def generate_letter() -> Letter:
    payload = build_payload()
    last_err: Exception | None = None
    for _ in range(2):
        r = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=180)
        r.raise_for_status()
        raw = json.loads(r.text)["response"]
        try:
            return Letter.model_validate_json(raw)
        except ValidationError as e:
            last_err = e
    raise RuntimeError(f"letter failed schema twice: {last_err}")
