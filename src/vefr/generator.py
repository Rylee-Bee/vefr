import json
import os

import httpx
from pydantic import BaseModel, ValidationError

# Back-compat module attributes. Engine callers and tests import these
# names directly (see chat.py, npc.py, forge.py, stefna.py, lore.py,
# pool.py, trace.py). The actual values are now resolved per-call by
# the storyteller provider (src/vefr/storyteller.py) - which keeps the
# engine model-neutral while preserving the existing import surface.
#
# Single source of truth for which inference backend the engine talks to.
# Precedence:
#   VEFR_LLAMACPP_URL   llama.cpp's OpenAI-compatible /v1/chat/completions
#                       endpoint (preferred transport when present;
#                       usually the simplest path for a local small
#                       model on the same machine or nearby host).
#   OLLAMA_URL          ollama's /api/generate endpoint (legacy fallback).
#                       Empty string "" disables a backend; unset means use
#                       the default.
LLAMACPP_URL = (
    os.environ.get("VEFR_LLAMACPP_URL", "http://127.0.0.1:8081")
    .rstrip("/")
    .removesuffix("/v1")  # engine appends /v1/chat/completions itself
)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.environ.get("VEFR_MODEL", "gpt-oss-20b")
KEEP_ALIVE = os.environ.get("VEFR_KEEP_ALIVE", "1m")


def _active_model() -> str:
    """Return the model name the storyteller provider picked.

    Imported lazily so that unit tests that monkeypatch
    `generator.MODEL` keep working - the engine path is unchanged when
    no Storyteller Pack is installed.
    """
    from .storyteller import active_model_name

    return active_model_name()


class GeneratorUnavailable(RuntimeError):
    """Transport-level failure (endpoint down, timeout, bad wiring).
    Fail closed: never generate from a guess."""


class GeneratorFailed(RuntimeError):
    """The endpoint answered but the output broke the contract (empty,
    unreadable). Fail closed: the rumor is discarded."""


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
        "model": _active_model(),
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
    The active storyteller's [model].provider picks the adapter:

    - Provider.OPENAI_COMPATIBLE -> llama.cpp server / LM Studio / vLLM /
      LocalAI / TGI / OpenRouter / anything speaking /v1/chat/completions.
      Translates the ollama-shaped dict (system/prompt/format/think) into
      the OpenAI chat-completions shape (messages, response_format,
      chat_template_kwargs).

    - Provider.OLLAMA -> ollama's /api/generate endpoint. The payload
      shape stays ollama-native (system, prompt, format, keep_alive,
      options).

    gpt-oss reasoning: chat_template_kwargs.reasoning_effort=low is the
    fastest this model family supports - it has no true off (low/medium/
    high only, confirmed by llama.cpp maintainers; forcing lower breaks
    output). llama.cpp's jinja template honors it server-side; for
    non-gpt-oss models the kwarg is ignored. The transport seam itself
    stays provider-shaped, not model-family-shaped: a future small CPU
    model or hosted endpoint still comes through this same boundary.
    """
    from .storyteller import Provider, resolve_active

    provider = resolve_active().model_provider
    if provider == Provider.OPENAI_COMPATIBLE:
        if not LLAMACPP_URL:
            # No OpenAI-compatible backend configured. Caller will see
            # this as a connection error; we don't try to silently
            # fall back to ollama because the pack explicitly asked
            # for a different wire protocol.
            raise RuntimeError(
                "active storyteller targets an OpenAI-compatible backend "
                "(llama.cpp / LM Studio / vLLM / etc.) but VEFR_LLAMACPP_URL "
                "is unset"
            )
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
        try:
            r = httpx.post(
                f"{LLAMACPP_URL}/v1/chat/completions", json=body, timeout=180
            )
            r.raise_for_status()
            return json.loads(r.text)["choices"][0]["message"]["content"]
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
            raise GeneratorUnavailable(
                f"openai-compatible endpoint {LLAMACPP_URL} failed: {e}"
            ) from e
        except (KeyError, ValueError) as e:
            raise GeneratorFailed(
                f"openai-compatible endpoint {LLAMACPP_URL} returned unreadable output: {e}"
            ) from e
    # Provider.OLLAMA
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=180)
        r.raise_for_status()
        return json.loads(r.text)["response"]
    except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
        raise GeneratorUnavailable(
            f"ollama endpoint {OLLAMA_URL} failed: {e}"
        ) from e
    except (KeyError, ValueError) as e:
        raise GeneratorFailed(
            f"ollama endpoint {OLLAMA_URL} returned unreadable output: {e}"
        ) from e


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


def _completion_plain(
    system: str, user: str, temperature: float = 0.85, max_tokens: int = 512
) -> str:
    """Tier-1 storytelling call: text in, text out, no schema.

    This is the boundary the new Storyteller Pack tier ladder hangs on.
    A Tier 1 storyteller never sees `format=...` or `response_format` -
    it just gets system + user and returns prose. Tier 2/3 callers use
    the JSON path above; the engine never assumes a model can do JSON.

    Kept in generator.py (not storyteller.py) so the wire layer stays
    one module. The storyteller decides model name, chat_template_kwargs,
    and (eventually) endpoint routing; this function stays thin.
    """
    payload = {
        "model": _active_model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": temperature},
        "max_tokens": max_tokens,
    }
    return _completion(payload)


def storytell(packet, system: str = "", temperature: float | None = None):
    """Tier-1 entry point: hand a ScenePacket to the active storyteller.

    The active storyteller's `system` template (loaded from the pack's
    [templates].system file when present, otherwise the inline value)
    is used as the system role; callers may pass a pack-specific system
    override (e.g. a speaker voice file). The packet is rendered
    through the storyteller's scene template (default: as-is).

    Tier 1 storytellers receive plain text only. Tier 2/3 should use the
    JSON-shaped calls above. This function never asks for JSON.
    """
    from .storyteller import resolve_active, render_scene_packet

    st = resolve_active()
    if system:
        sys_msg = system
    else:
        inline = getattr(st, "system_template", "")
        sys_msg = st.load_template("system") or inline
    user_msg = render_scene_packet(packet)
    temp = temperature if temperature is not None else float(st.sampling.get("temperature", 0.85))
    return _completion_plain(sys_msg, user_msg, temperature=temp)