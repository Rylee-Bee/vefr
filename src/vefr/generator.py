import json
import logging
import os

import httpx
from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)

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
    Fail closed: never generate from a guess.

    The message is the plain sentence a person at the keyboard reads
    (see `_no_model_message`); the raw endpoint URL, exception class
    and text stay on `.detail` and in the log for whoever debugs.
    """

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message)
        # Back-compat: callers that construct this with a single
        # argument (tests, future adapters) keep that text as the raw
        # detail, so nothing that reads `.detail` sees an empty string.
        self.detail = message if detail is None else detail


class GeneratorFailed(RuntimeError):
    """The endpoint answered but the output broke the contract (empty,
    unreadable). Fail closed: the rumor is discarded.

    Same split as GeneratorUnavailable: friendly message in `str()`,
    raw detail on `.detail` and in the log.
    """

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message)
        self.detail = message if detail is None else detail


def _asked_for() -> tuple[str | None, str]:
    """(pack id, model name) for the active storyteller - never raises.

    Building an error message must not itself fail: a broken or BYOM
    pin falls back to the model name alone, then to the engine's
    default model constant.
    """
    pack_id: str | None = None
    model = ""
    try:
        from .storyteller import resolve_active

        st = resolve_active()
        model = str(getattr(st, "model", "") or "")
        pinned = str(getattr(st, "id", "") or "")
        # "byom:<name>" is the placeholder resolve_active() builds when
        # the env var names a model with no pack behind it - there is
        # no pack to name, so say the model alone.
        if pinned and not pinned.startswith("byom:"):
            pack_id = pinned
    except Exception:  # noqa: BLE001 - error text must never raise
        pass
    if not model:
        model = MODEL
    return pack_id, model


def _tried(*, start_of_sentence: bool = False) -> str:
    """What was asked, in words, as the subject of an error sentence.

    `start_of_sentence` only uppercases the first letter - never
    `str.capitalize()`, which would lowercase the rest and mangle a
    model name like gemma-4-E2B-it.
    """
    pack_id, model = _asked_for()
    tried = (
        f"the storyteller pack {pack_id}, asking for the model {model}"
        if pack_id
        else f"the model {model}"
    )
    return tried[0].upper() + tried[1:] if start_of_sentence else tried


def _no_model_message() -> str:
    """The plain sentence for "no model answered" (see Task: friendly).

    Names what was tried in words, says the game still plays, and
    gives the next step. No URL, no status code, no traceback.
    """
    tried = _tried()
    return (
        f"No model answered for {tried}. The game still plays without a model; "
        "run `ratatoskr spark install` to fetch the pinned small model, or start "
        "your own OpenAI-compatible server and set VEFR_LLAMACPP_URL to it."
    )


def _unreadable_message() -> str:
    """The sibling sentence for GeneratorFailed: the endpoint is fine.

    Different cause, different next step - the model answered, but the
    words could not be read.
    """
    tried = _tried(start_of_sentence=True)
    return (
        f"{tried} answered, but the words could not be read. "
        "The game still plays without a model; try again, or check the model "
        "and its settings."
    )


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


def build_payload(phase: str, theme: str | None, sid: str | None = None) -> dict:
    """Build an ollama-style payload (stable build spec, kept for tests).

    The actual HTTP request is shaped by _completion() into whatever the
    active backend speaks. Tests assert on this dict; the wire format is
    _completion's problem.
    """
    theme_line = f" The rumor touches: {theme}." if theme else ""
    return {
        "model": _active_model(),
        "system": _system(phase, sid),
        "prompt": f"Whisper one tavern rumor.{theme_line} Reply with only the JSON object.",
        "format": SCHEMA,
        "stream": False,
        "think": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": 0.95},
    }


def _system(phase: str, sid: str | None = None) -> str:
    from .saga import system_prompt

    return system_prompt(phase, sid=sid)


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
            # llama.cpp's default n_predict is unlimited: a model that
            # rambles inside the JSON grammar would run to the context
            # limit and hit the 180 s client timeout instead of failing
            # fast into generate_rumor's retry.
            "max_tokens": max_tokens,
        }
        # Allow callers to override defaults via the payload (useful
        # for lore drafts that need much more headroom than 1024).
        for k in ("max_tokens", "temperature"):
            if k in payload:
                body[k] = payload[k]
        # Optional GBNF fallback. Some OpenAI-compatible backends ignore
        # response_format; a caller may ask for a grammar instead
        # (`grammar: True`), derived from the same schema when convertible.
        # The default path is unchanged: no grammar, response_format as-is.
        if payload.get("grammar"):
            schema = None
            if (isinstance(response_format, dict)
                    and response_format.get("type") == "json_schema"):
                schema = response_format.get("json_schema", {}).get("schema")
            elif "format" in payload:
                schema = payload["format"]
            if schema is not None:
                from .schema_grammar import SchemaGrammarError, grammar_from_schema

                try:
                    body["grammar"] = grammar_from_schema(schema)
                    body.pop("response_format", None)
                except SchemaGrammarError:
                    pass  # not convertible: keep response_format, no grammar
        try:
            r = httpx.post(
                f"{LLAMACPP_URL}/v1/chat/completions", json=body, timeout=180
            )
            r.raise_for_status()
            return json.loads(r.text)["choices"][0]["message"]["content"]
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
            detail = (
                f"openai-compatible endpoint {LLAMACPP_URL} failed: "
                f"{type(e).__name__}: {e}"
            )
            log.error("generator unavailable: %s", detail)
            raise GeneratorUnavailable(_no_model_message(), detail) from e
        except (KeyError, ValueError) as e:
            detail = (
                f"openai-compatible endpoint {LLAMACPP_URL} returned unreadable "
                f"output: {type(e).__name__}: {e}"
            )
            log.error("generator failed: %s", detail)
            raise GeneratorFailed(_unreadable_message(), detail) from e
    # Provider.OLLAMA
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=180)
        r.raise_for_status()
        return json.loads(r.text)["response"]
    except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
        detail = f"ollama endpoint {OLLAMA_URL} failed: {type(e).__name__}: {e}"
        log.error("generator unavailable: %s", detail)
        raise GeneratorUnavailable(_no_model_message(), detail) from e
    except (KeyError, ValueError) as e:
        detail = (
            f"ollama endpoint {OLLAMA_URL} returned unreadable output: "
            f"{type(e).__name__}: {e}"
        )
        log.error("generator failed: %s", detail)
        raise GeneratorFailed(_unreadable_message(), detail) from e


def generate_rumor(
    phase: str = "whispers", theme: str | None = None,
    sid: str | None = None,
) -> RumorCard:
    payload = build_payload(phase, theme, sid)
    last_err: Exception | None = None
    for attempt in range(2):
        # Second attempt: ask for a GBNF grammar derived from the same
        # schema, for backends that ignored response_format the first time.
        if attempt == 1:
            payload = {**payload, "grammar": True}
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