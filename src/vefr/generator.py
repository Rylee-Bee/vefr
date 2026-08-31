import json
import os

import httpx
from pydantic import BaseModel, ValidationError

# Single source of truth for which inference backend the engine talks to.
# Precedence:
#   VEFR_LLAMACPP_URL   llama.cpp's OpenAI-compatible /v1/chat/completions
#                       endpoint (preferred, currently ~13x faster on
#                       Bazzite's 6900XT than ollama with broken ROCm).
#   OLLAMA_URL          ollama's /api/generate endpoint (legacy fallback).
#                       Empty string "" disables a backend; unset means use
#                       the default.
LLAMACPP_URL = os.environ.get("VEFR_LLAMACPP_URL", "http://127.0.0.1:8081").rstrip("/")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.environ.get("VEFR_MODEL", "gpt-oss-20b")
KEEP_ALIVE = os.environ.get("VEFR_KEEP_ALIVE", "1m")


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
    """Build an ollama-style payload (stable build spec, kept for tests).

    The actual HTTP request is shaped by _completion() into whatever the
    active backend speaks. Tests assert on this dict; the wire format is
    _completion's problem.
    """
    theme_line = f" The rumor touches: {theme}." if theme else ""
    return {
        "model": MODEL,
        "system": _system(phase),
        "prompt": f"Whisper one tavern rumor.{theme_line} Reply with only the JSON object.",
        "format": SCHEMA,
        "stream": False,
        "think": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": 0.95},
    }


def _system(phase: str) -> str:
    from .saga import system_prompt

    return system_prompt(phase)


def _completion(payload: dict, max_tokens: int = 1024) -> str:
    """Send `payload` to the active backend and return the assistant text.

    Single source of truth for backend choice and wire-format translation.
    Translates the ollama-shaped dict (system/prompt/format/think) into
    the llama.cpp /v1/chat/completions shape (messages, response_format,
    chat_template_kwargs) when VEFR_LLAMACPP_URL is set. Returns the
    assistant content string; callers validate against their pydantic
    models.

    gpt-oss reasoning: chat_template_kwargs.reasoning_effort=low is the
    fastest this model family supports - it has no true off (low/medium/
    high only, confirmed by llama.cpp maintainers; forcing lower breaks
    output). llama.cpp's jinja template honors it server-side; for
    non-gpt-oss models the kwarg is ignored.
    """
    if LLAMACPP_URL:
        # Three payload shapes are supported:
        #   - legacy ollama shape: {system, prompt, format, ...}
        #   - messages shape (with optional response_format): messages is the source of truth
        #   - explicit response_format from the caller (e.g. lore previews)
        if payload.get("messages"):
            messages = payload["messages"]
        else:
            messages = [
                {"role": "system", "content": payload.get("system", "")},
                {"role": "user", "content": payload.get("prompt", "")},
            ]
        # response_format priority:
        #   1. caller-provided response_format (already JSON-schema shaped)
        #   2. legacy `format` field (converted to JSON-schema)
        #   3. plain text fallback
        if "response_format" in payload:
            response_format = payload["response_format"]
        else:
            schema = payload.get("format")
            response_format = (
                {"type": "json_schema",
                 "json_schema": {"schema": schema, "strict": True}}
                if schema else {"type": "text"}
            )
        body = {
            "model": payload["model"],
            "messages": messages,
            "response_format": response_format,
            "stream": False,
            "chat_template_kwargs": {"reasoning_effort": "low"},
        }
        # Allow callers to override defaults via the payload (useful
        # for lore drafts that need much more headroom than 1024).
        for k in ("max_tokens", "temperature"):
            if k in payload:
                body[k] = payload[k]
        r = httpx.post(
            f"{LLAMACPP_URL}/v1/chat/completions", json=body, timeout=180
        )
        r.raise_for_status()
        return json.loads(r.text)["choices"][0]["message"]["content"]
    r = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=180)
    r.raise_for_status()
    return json.loads(r.text)["response"]


def generate_rumor(phase: str = "whispers", theme: str | None = None) -> RumorCard:
    payload = build_payload(phase, theme)
    last_err: Exception | None = None
    for _ in range(2):
        raw = _completion(payload)
        try:
            return RumorCard.model_validate_json(raw)
        except ValidationError as e:
            last_err = e
    raise RuntimeError(f"model output failed schema twice: {last_err}")