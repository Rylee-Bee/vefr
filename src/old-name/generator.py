import json
import os

import httpx
from pydantic import BaseModel, ValidationError

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("MUNR_MODEL", "qwen3.8-27b:ctx32k")
KEEP_ALIVE = os.environ.get("MUNR_KEEP_ALIVE", "1m")


class RumorCard(BaseModel):
    speaker: str
    whisper: str
    is_true: bool
    hook: str | None = None


SCHEMA = {
    "type": "object",
    "properties": {
        "speaker": {"type": "string"},
        "whisper": {"type": "string"},
        "is_true": {"type": "boolean"},
        "hook": {"type": "string"},
    },
    "required": ["speaker", "whisper", "is_true"],
}


def build_payload(phase: str, theme: str | None) -> dict:
    theme_line = f" The rumor touches: {theme}." if theme else ""
    return {
        "model": MODEL,
        "system": _system(phase),
        "prompt": f"Whisper one tavern rumor.{theme_line} Reply with only the JSON object.",
        "format": SCHEMA,
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": 0.95},
    }


def _system(phase: str) -> str:
    from .saga import system_prompt

    return system_prompt(phase)


def generate_rumor(phase: str = "whispers", theme: str | None = None) -> RumorCard:
    payload = build_payload(phase, theme)
    last_err: Exception | None = None
    for _ in range(2):
        r = httpx.post(
            f"{OLLAMA_URL}/api/generate", json=payload, timeout=180
        )
        r.raise_for_status()
        raw = json.loads(r.text)["response"]
        try:
            return RumorCard.model_validate_json(raw)
        except ValidationError as e:
            last_err = e
    raise RuntimeError(f"model output failed schema twice: {last_err}")
