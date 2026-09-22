"""vefr-interface - the Interface Translator, VEFR's smallest brain.

The entire job, on purpose:

    "What is the person trying to do?"

expressed as a STRICT, validated action intent in the engine's own
canonical action vocabulary. It is NOT the Storyteller, NOT a planner,
NOT a lore generator, NOT a world-state authority, and NOT a general
chatbot. The model proposes one intent; VEFR validates it
deterministically; VEFR (not this module) decides what happens.

Architecture follows the Step 1 Lorekeeper precedent:

    structured durable truth  +  replaceable derived acceleration

Here the *canonical action contract is authoritative* and the small
model is *replaceable machinery*: removing this module must not change
any world semantics. The module never mutates world state; its only
side effects are a private runtime log under data/ and the stdout of
the vefr-interface CLI.

The canonical action vocabulary is the engine's own (combat.py's
verb set {attack, console, hurl, strike, observe} plus the two other
player mechanics: speak -> POST /api/npc, move -> POST /api/journal/move).
No second action language was invented; the intent envelope below is the
smallest translator-specific container for that vocabulary.

Config (plain process env, repo convention; loopback ONLY):

    VEFR_INTERFACE_URL       llama.cpp /v1/chat/completions endpoint
                             (default http://127.0.0.1:8087)
    VEFR_INTERFACE_MODEL     alias/model sent to the endpoint
                             (default qwen3.5-9b-mtp)
    VEFR_INTERFACE_TIMEOUT   seconds for one completion (default 60)
    VEFR_INTERFACE_TEMPLATE  override the templates/interface/intent.json

Selected model: qwen3.5-9b-mtp won the bench/interface benchmark. The
tiny candidates (Qwen2.5-1.5B Q4, Qwen3.5-0.8B Q4) reach 100% schema
validity but fail the boundary - they route unsupported, injected, and
fabricated instructions as actions (48-55% safe, ~12 unsafe false
positives each). The 9B shard holds 100% / 100% / zero across the same
29 deterministic cases.

Port note: 8087 is the translator's unambiguous default - 8081 is the
engine's llama.cpp default, 8082 is Spark's default AND the live
llama-embed (bge-m3) service, 8083-8086 are the bundled fleet (8085 is
the bundled Vision/SmolVLM2 tenant - the translator moved off it when
vision shipped,2026-09-22), 11436/11437 are the 9B servers. The
translator never shares a default port with another conceptual service.

Only 127.0.0.1 is ever used - the host's pasta IPv6 loopback is broken,
never resolve localhost to ::1.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .paths import app_home

# Canonical engine action vocabulary (combat.record_combat_action's set
# + speak + move). Do NOT extend this without an engine mechanic for the
# new verb - a verb with no mechanic is a lie in the contact surface.
ACTIONS = ("attack", "console", "hurl", "strike", "observe", "speak", "move")

# Required arguments per verb, per CURRENT engine mechanics.
#   attack/console/hurl/strike: who or what you act on.
#   speak: who you speak to (/api/npc posts a line for a speaker).
#   move: which way you go (/api/journal/move carries the place).
#   observe: no required argument - "look around" is always valid.
REQUIRED_BY_ACTION = {
    "attack": ("target",),
    "console": ("target",),
    "hurl": ("target",),
    "strike": ("target",),
    "speak": ("target",),
    "move": ("direction",),
    "observe": (),
}

# Grammar-compatible strict schema. Every field is REQUIRED so the
# llmama.cpp strict grammar forces the model to emit real content for
# every slot (with optional slots the tiny models shortcut them to
# ""). `action` is always a real verb (no null union - plain enums
# work far more reliably); a clarification intent is expressed as
# needs_clarification=true + clarification text, and the deterministic
# cleanup then nulls every routed field so the canonical envelope is
# reached before validation. Empty fields are normalized to None.
_ENVELOPE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": list(ACTIONS)},
        "target": {"type": "string"},
        "topic": {"type": "string"},
        "direction": {"type": "string"},
        "confidence": {"type": "number"},
        "needs_clarification": {"type": "boolean"},
        "clarification": {"type": "string"},
    },
    "required": [
        "action", "target", "topic", "direction",
        "confidence", "needs_clarification", "clarification",
    ],
    "additionalProperties": False,
}


class Intent(BaseModel):
    """The strictly-validated intent envelope. No field beyond the
    justified set; no narrative; no world state."""

    model_config = ConfigDict(extra="forbid")

    action: str | None = None
    target: str | None = None
    topic: str | None = None
    direction: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    needs_clarification: bool = False
    clarification: str | None = None

    @field_validator("action")
    @classmethod
    def _known_action(cls, v: str | None) -> str | None:
        if v is not None and v not in ACTIONS:
            raise ValueError(f"unknown action {v!r} - not in the engine vocabulary")
        return v

    @model_validator(mode="after")
    def _coherent(self) -> "Intent":
        if self.needs_clarification:
            if self.action is not None:
                raise ValueError("needs_clarification must carry action=null")
            if not (self.clarification and self.clarification.strip()):
                raise ValueError("needs_clarification must carry a clarification")
        else:
            if self.action is None:
                raise ValueError("a routed intent must carry an action")
            if self.clarification is not None:
                raise ValueError("a routed intent carries no clarification")
        missing = [
            req for req in REQUIRED_BY_ACTION.get(self.action, ())
            if not (getattr(self, req) and getattr(self, req).strip())
        ]
        if missing:
            raise ValueError(
                f"action {self.action!r} requires: {', '.join(missing)}"
            )
        return self


class InterfaceUnavailable(RuntimeError):
    """The endpoint is down (unreachable / HTTP error / timeout).
    Fail closed: never guess an action."""


class InterfaceMalformed(RuntimeError):
    """The endpoint answered but the payload missed the contract
    (bad JSON, wrong keys, unknown verb, incoherent intent). Fail
    closed: the proposal is discarded."""


# --- configuration ------------------------------------------------------

def interface_url() -> str:
    return os.environ.get("VEFR_INTERFACE_URL", "http://127.0.0.1:8087").rstrip("/")


def interface_model() -> str:
    return os.environ.get("VEFR_INTERFACE_MODEL", "qwen3.5-9b-mtp")


def interface_timeout() -> float:
    return float(os.environ.get("VEFR_INTERFACE_TIMEOUT", "60"))


def interface_log_path() -> Path:
    return app_home() / "data" / "interface.jsonl"


# --- template-as-data (the fleet's template convention) -----------------

def template_path() -> Path:
    """templates/interface/intent.json at the repo root, or the env
    override (VEFR_INTERFACE_TEMPLATE) for tests/deploys."""
    env = os.environ.get("VEFR_INTERFACE_TEMPLATE")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "templates" / "interface" / "intent.json"


def load_template(path: Path | None = None) -> dict:
    """Load the intent template as data. Missing or malformed template
    fails loudly - the translator must never run with half a contract."""
    p = path or template_path()
    if not p.exists():
        raise InterfaceUnavailable(f"template missing: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise InterfaceUnavailable(f"template unreadable ({p}): {e}") from e
    if not isinstance(data, dict) or not data.get("schema_version"):
        raise InterfaceUnavailable(f"template {p} has no schema_version")
    return data


def _template_examples(tpl: dict) -> list[dict]:
    raw = tpl.get("examples") or []
    if not isinstance(raw, list) or not (1 <= len(raw) <= 12):
        raise InterfaceUnavailable(
            f"template requires 1-12 examples, found {raw!r}"
        )
    return raw


def build_system(tpl: dict) -> str:
    """Compose the system prompt from the data file. No Python-spelled
    prompt: everything behavioral lives in templates/interface/."""
    lines = [tpl.get("role", "").strip()]
    vocab = "\n".join(
        f"- {a['name']}: {a.get('when', '')}"
        for a in tpl.get("actions", [])
    )
    if vocab:
        lines.append("CANONICAL ACTIONS (the ONLY verbs you may emit):\n" + vocab)
    reqs = "\n".join(
        f"- {name}: {req}"
        for name, req in tpl.get("required", {}).items()
    )
    if reqs:
        lines.append("REQUIRED ARGUMENTS per action:\n" + reqs)
    boundary = tpl.get("boundary")
    if boundary:
        if isinstance(boundary, list):
            boundary = "\n".join(str(b) for b in boundary)
        lines.append(str(boundary).strip())
    if tpl.get("schema_ref"):
        lines.append(
            f"Output schema: reply with ONLY a JSON object matching "
            f"{tpl['schema_ref']}. No prose before or after."
        )
    return "\n\n".join(x for x in lines if x)


def build_fewshot(tpl: dict) -> list[dict]:
    """The template's 5 exemplars as alternating user/assistant turns.
    Generic examples only - never private story canon."""
    turns: list[dict] = []
    for ex in _template_examples(tpl):
        turns.append({"role": "user", "content": ex["input"]})
        turns.append({"role": "assistant", "content": json.dumps(
            ex["intent"], ensure_ascii=False)})
    return turns


def build_messages(tpl: dict, instruction: str) -> list[dict]:
    """The full chat payload: system (role+vocabulary+boundary) then the
    template's few-shot pairs then the live instruction. Small by design
    - the translator's world is the vocabulary, not the lore corpus."""
    return [{"role": "system", "content": build_system(tpl)}] + \
        build_fewshot(tpl) + [{"role": "user", "content": instruction}]


# --- the client (fail-closed) -------------------------------------------

def _completion(messages: list[dict], *, url: str | None = None,
                timeout: float | None = None,
                temperature: float = 0.0,
                max_tokens: int = 200) -> str:
    """One strict json_schema call to the interface endpoint. Raises
    InterfaceUnavailable on transport failure - never a guessed answer."""
    tpl = load_template()
    base = (url or interface_url()).rstrip("/")
    gen = tpl.get("generation", {})
    body = {
        "model": interface_model(),
        "messages": messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "vefr_intent",
                "schema": _ENVELOPE_SCHEMA,
                "strict": True,
            },
        },
        "stream": False,
        "temperature": gen.get("temperature", temperature),
        "max_tokens": gen.get("max_tokens", max_tokens),
        # Thinking models (Qwen3.x) must never reason here: the budget is
        # tiny and their reasoning would consume it all. Qwen2.x ignores
        # this key, so it is safe to send on every schema call.
        "chat_template_kwargs": {"enable_thinking": False},
    }
    try:
        r = httpx.post(f"{base}/v1/chat/completions", json=body,
                       timeout=timeout if timeout is not None else interface_timeout())
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, httpx.TimeoutException, KeyError, ValueError) as e:
        raise InterfaceUnavailable(f"interface endpoint {base} failed: {e}") from e
    if not isinstance(raw, str) or not raw.strip():
        raise InterfaceMalformed("interface returned empty content")
    return raw


def _cleanup_clarification(raw: dict) -> dict:
    """Deterministic pass over the model's strict-schema object. Optional
    string fields may arrive as "" (llama.cpp strict grammar fills the
    whitespace slots the schema left open) - normalize to None so the
    canonical envelope stays honest: absent means absent. When the model
    says it cannot map an intent, every routed field must be null -
    never force an action."""
    for key in ("target", "topic", "direction", "clarification"):
        if isinstance(raw.get(key), str):
            raw[key] = raw[key].strip() or None
    if raw.get("needs_clarification"):
        raw["action"] = None
        raw["target"] = None
        raw["topic"] = None
        raw["direction"] = None
    else:
        # A routed action's clarification slot must stay empty: any text
        # the model left there is commentary, not a state change. The
        # needs_clarification flag is the ONLY clarification authority.
        raw["clarification"] = None
    return raw


def translate(instruction: str, *, url: str | None = None) -> tuple[Intent, dict]:
    """Natural language -> strictly validated Intent. Returns
    (intent, meta).

    Raises InterfaceUnavailable / InterfaceMalformed. The returned
    intent holds NO world facts and MUTATES NOTHING - it is an intent,
    nothing else.
    """
    tpl = load_template()
    messages = build_messages(tpl, instruction)
    t0 = time.monotonic()
    raw = _completion(messages, url=url)
    latency_ms = round((time.monotonic() - t0) * 1000, 1)
    meta = {
        "role": "interface",
        "model": interface_model(),
        "template_revision": tpl.get("schema_version"),
        "latency_ms": latency_ms,
    }
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        meta["validation"] = "malformed"
        meta["raw"] = raw[:200]
        _log_entry(instruction, meta, intent=None)
        raise InterfaceMalformed(f"interface output is not JSON: {e}") from e
    try:
        intent = Intent.model_validate(_cleanup_clarification(parsed))
        meta["validation"] = "ok" if not intent.needs_clarification else "clarification"
        _log_entry(instruction, meta, intent=intent)
        return intent, meta
    except (ValidationError, ValueError) as e:
        meta["validation"] = "malformed"
        meta["raw"] = raw[:200]
        _log_entry(instruction, meta, intent=None)
        raise InterfaceMalformed(f"intent failed validation: {e}") from e


# --- logging (evidence first, training later) ----------------------------

def _sanitize(text: str, limit: int = 300) -> str:
    """Inputs are evidence, not secrets - but bound the size and collapse
    whitespace so a runaway paste never becomes a runaway log line."""
    return " ".join(text.split())[:limit]


def _log_entry(instruction: str, meta: dict, *, intent: Intent | None) -> None:
    """One private runtime log line. Never logs VEFR_INTERFACE_* values
    or raw credentials; intent and raw stay bounded. Runtime state under
    data/ is gitignored - this never reaches a tracked artifact."""
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "role": "interface",
        "model": meta.get("model"),
        "template_revision": meta.get("template_revision"),
        "input": _sanitize(instruction),
        "output": intent.model_dump() if intent else None,
        "validation": meta.get("validation"),
        "latency_ms": meta.get("latency_ms"),
    }
    path = interface_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# --- CLI ----------------------------------------------------------------

def _cmd_interface(args: argparse.Namespace) -> int:
    try:
        intent, meta = translate(
            args.instruction,
            url=args.url or None,
        )
    except InterfaceUnavailable as e:
        print(f"[vefr-interface] endpoint unavailable: {e}", file=sys.stderr)
        return 2
    except InterfaceMalformed as e:
        print(f"[vefr-interface] output failed closed: {e}", file=sys.stderr)
        return 2
    if args.json:
        payload = {"intent": intent.model_dump(), "meta": meta}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if intent.needs_clarification:
        print("clarification required:")
        print(f"    {intent.clarification}")
        return 0
    line = f"{intent.action}"
    if intent.target and intent.action not in {"move"}:
        line += f" → {intent.target}"
        if intent.topic:
            line += f"  topic: {intent.topic}"
    elif intent.direction:
        line += f" → {intent.direction}"
    print(line)
    print(meta["latency_ms"], "ms")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vefr-interface",
        description="Interface translator: intent in, strict action intent out.",
    )
    parser.add_argument("instruction", help="what the person appears to be trying to do")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--model", dest="model", default=None,
                        help="override VEFR_INTERFACE_MODEL for this call")
    parser.add_argument("--endpoint", "--url", dest="url", default=None,
                        help="override VEFR_INTERFACE_URL for this call")
    args = parser.parse_args(argv)
    if args.model:
        os.environ["VEFR_INTERFACE_MODEL"] = args.model
    return _cmd_interface(args)


if __name__ == "__main__":
    raise SystemExit(main())