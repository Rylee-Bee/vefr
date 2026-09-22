"""Storyteller fleet role - narrative prose from AUTHORITATIVE results.

The question this role answers:

    "How do we make what happened feel alive?"

It does NOT answer:
    - "What is the person trying to do?"      -> Interface Translator
    - "What actually happens?"                -> VEFR mechanics / world authority
    - "What relevant things do we already know?" -> Lorekeeper

Placement is strict: the Storyteller is invoked AFTER world resolution.
It receives what the player attempted, what VEFR decided actually
happened, bounded current scene state, and top-k retrieved lore - and
returns narrative prose and nothing else. It never sits before world
resolution, never mutates state, and holds ZERO arbitrary tools.

Authority precedence (deterministic + re-stated in the template):

    authoritative action result  >  template instruction  >  lore  >  prose

The Storyteller may embellish sensory detail, pacing, dialogue texture,
atmosphere, emotional framing, and connective prose INSIDE authoritative
facts. It may NOT invent outcomes, inventory, wounds, NPC knowledge,
locations, relationships, mechanics, hidden facts, canon, or consequences.

Output is prose. The client wraps it:

    {"text": "...", "model": "...", "template_revision": "...",
     "latency_ms": ...}

No chain-of-thought is enabled or captured.

Config (plain process env, repo convention; loopback ONLY):

    VEFR_NARRATE_URL       llama.cpp /v1/chat/completions endpoint
                           (default http://127.0.0.1:8088)
    VEFR_NARRATE_MODEL     alias/model sent to the endpoint
                           (default smollm3-3b-q4 - the fleet hypothesis;
                            replaced by the benchmark winner)
    VEFR_NARRATE_TIMEOUT   seconds for one completion (default 60)
    VEFR_NARRATE_TEMPLATE  override templates/storyteller/narrate.json

Port note: 8088 is the storyteller shard default - 8081 engine, 8082
embed/Spark, 8085 bundled vision, 8087 interface, 11436/11437 9B,
8086/8089/8090 bench shards.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .paths import app_home


class StorytellerUnavailable(RuntimeError):
    """Transport-level failure (endpoint down, timeout, bad wiring). Fail
    closed: never narrate from a guess."""


class StorytellerFailed(RuntimeError):
    """The endpoint answered but the payload missed the contract (empty
    content, unreadable output). Fail closed: the story is discarded."""


# --- configuration ------------------------------------------------------

def narrate_url() -> str:
    return os.environ.get("VEFR_NARRATE_URL", "http://127.0.0.1:8088").rstrip("/")


def narrate_model() -> str:
    return os.environ.get("VEFR_NARRATE_MODEL", "smollm3-3b-q4")


def narrate_timeout() -> float:
    return float(os.environ.get("VEFR_NARRATE_TIMEOUT", "60"))


def storyteller_log_path() -> Path:
    return app_home() / "data" / "storyteller.jsonl"


# --- presentation input envelope (facts, not authority) ------------------

def _clean_list(v: object) -> list[str]:
    if not v:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return [str(v)]


class LoreRef(BaseModel):
    """One retrieved lore fragment. Text/source are evidence handed to
    the Storyteller; score is retrieval ordering only. Lore is flavor and
    history - it can never override the current authoritative result."""

    text: str
    source: str = ""
    score: float = 0.0

    model_config = ConfigDict(extra="ignore")


class StoryInput(BaseModel):
    """The explicit Storyteller input envelope. PRESENTATION INPUT: it
    carries facts for this beat, never an authority store. `action_result`
    is REQUIRED - the Storyteller cannot be invoked before world
    resolution."""

    player_intent: str = Field(default="", description="what the player tried to do, in their words")
    action: str = Field(default="", description="the validated action (e.g. strike, move)")
    target: str = Field(default="", description="the validated target/direction, if any")
    action_result: dict | None = Field(
        default=None,
        description="REQUIRED - what VEFR decided actually happened",
    )
    scene_location: str = Field(default="", description="current bounded scene location")
    visible_entities: list[str] = Field(default_factory=list)
    relevant_lore: list[LoreRef] = Field(default_factory=list)
    voice_tone: str = Field(default="", description="tone guidance from the active world/story pack")
    voice_guidance: str = Field(default="")
    constraints: str = Field(default="", description="e.g. 'short', 'one or two paragraphs'")

    model_config = ConfigDict(extra="ignore")

    @property
    def has_result(self) -> bool:
        return bool(self.action_result)

    def envelope_text(self) -> str:
        """Render the envelope as the stable plain-text section format.

        The field NAMES and ORDER are part of the prompt contract - the
        exemplars use the exact same rendering, so a model only ever sees
        one shape. Action result is always presented as THE authority."""
        sections: list[str] = []
        sections.append("PLAYER INTENT\n\n" + (self.player_intent.strip() or "(none given)"))
        if self.action:
            intent_line = f"Validated intent: {self.action}"
            if self.target:
                intent_line += f", target: {self.target}"
            sections[-1] += "\n" + intent_line
        result = self.action_result or {}
        outcome = result.get("outcome") or result.get("detail") or json.dumps(result, ensure_ascii=False)
        if result.get("success") is False:
            label = "(failed)"
        elif result.get("success") is True:
            label = "(succeeded)"
        else:
            label = "(outcome)"
        sections.append(
            "AUTHORITATIVE RESULT\n\n" + label + " " + outcome
        )
        scene_line = []
        if self.scene_location:
            scene_line.append(f"Location: {self.scene_location}")
        if self.visible_entities:
            scene_line.append("Present: " + ", ".join(self.visible_entities))
        if scene_line:
            sections.append("CURRENT SCENE\n\n" + "\n".join(scene_line))
        lore = list(self.relevant_lore)[: int(os.environ.get("VEFR_NARRATE_MAX_LORE", "5"))]
        if lore:
            lines = []
            for ref in lore:
                lines.append(f"- {ref.text}")
            sections.append("RELEVANT LORE (facts you may use but never change)\n\n" + "\n".join(lines))
        if self.voice_tone or self.voice_guidance:
            voice = self.voice_tone or ""
            if self.voice_guidance:
                voice = (voice + " - " if voice else "") + self.voice_guidance
            sections.append("VOICE\n\n" + voice)
        write = "Narrate the moment. " + (self.constraints or self._default_write())
        sections.append("WRITE\n\n" + write.strip())
        return "\n\n".join(sections)

    def _default_write(self) -> str:
        return ("One or two short paragraphs. Plain sentences. "
                "Leave room for the player; never choose their next action.")


# --- template-as-data ----------------------------------------------------

def template_path() -> Path:
    env = os.environ.get("VEFR_NARRATE_TEMPLATE")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "templates" / "storyteller" / "narrate.json"


def load_template(path: Path | None = None) -> dict:
    """Load the storyteller template as data. Missing or malformed fails
    loudly - the role never runs with half a contract."""
    p = path or template_path()
    if not p.exists():
        raise StorytellerUnavailable(f"template missing: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise StorytellerUnavailable(f"template unreadable ({p}): {e}") from e
    if not isinstance(data, dict) or not data.get("schema_version"):
        raise StorytellerUnavailable(f"template {p} has no schema_version")
    return data


def _template_examples(tpl: dict) -> list[dict]:
    raw = tpl.get("examples") or []
    if not isinstance(raw, list) or not (1 <= len(raw) <= 12):
        raise StorytellerUnavailable(
            f"template requires 1-12 examples, found {raw!r}"
        )
    return raw


def build_system(tpl: dict, voice: str = "") -> str:
    """Compose the system prompt from the data file. Template is data,
    not code: everything behavioral lives in templates/storyteller/."""
    pieces: list[str] = []
    role = tpl.get("role", "").strip()
    if role:
        pieces.append(role)
    for section in ("authority", "creative_freedom", "forbidden_invention",
                    "world_result_precedence", "output_constraints"):
        body = tpl.get(section)
        if not body:
            continue
        if isinstance(body, list):
            body = "\n".join(str(b) for b in body)
        pieces.append(str(body).strip())
    if voice:
        pieces.append("VOICE\n\n" + voice)
    return "\n\n".join(p for p in pieces if p)


def build_fewshot(tpl: dict) -> list[dict]:
    """Template exemplars as alternating user/assistant turns. Absolute
    numbers: each envelope renders with envelope_text(), each story is
    prose, one or two paragraphs - the exact shape the live path uses."""
    turns: list[dict] = []
    for ex in _template_examples(tpl):
        env = StoryInput(
            player_intent=ex.get("player_intent", ""),
            action=ex.get("action", ""),
            target=ex.get("target", ""),
            action_result=ex.get("action_result"),
            scene_location=ex.get("scene_location", ""),
            visible_entities=ex.get("visible_entities", []),
            relevant_lore=[LoreRef(**r) for r in ex.get("relevant_lore", [])],
            voice_tone=ex.get("voice_tone", ""),
            voice_guidance=ex.get("voice_guidance", ""),
            constraints=ex.get("constraints", ""),
        )
        turns.append({"role": "user", "content": env.envelope_text()})
        turns.append({"role": "assistant", "content": ex["story"]})
    return turns


def build_messages(tpl: dict, env: StoryInput, voice: str = "") -> list[dict]:
    """Full chat payload: system (role + boundary + voice) then the
    template's exemplars then the live envelope. Small by design."""
    return [{"role": "system", "content": build_system(tpl, voice=voice)}] + \
        build_fewshot(tpl) + [{"role": "user", "content": env.envelope_text()}]


def prompt_size(env: StoryInput) -> int:
    """Approximate prompt size in tokens (chars/4) for one envelope, for
    progressive-context measurements in the benchmark."""
    tpl = load_template()
    msgs = build_messages(tpl, env)
    return sum(len(m["content"]) // 4 for m in msgs)


# --- the client (fail-closed, prose only, no tools) ----------------------

def _completion(messages: list[dict], *, url: str | None = None,
                timeout: float | None = None) -> str:
    """One plain chat completion. NO json_schema (the useful output is
    prose), NO tools, NO chain-of-thought. Thinking models (Qwen3.x) keep
    reasoning OFF - reasoning is captured nowhere. Qwen2.x ignores the key."""
    tpl = load_template()
    base = (url or narrate_url()).rstrip("/")
    gen = tpl.get("generation", {})
    body = {
        "model": narrate_model(),
        "messages": messages,
        "stream": False,
        "temperature": gen.get("temperature", 0.7),
        "top_p": gen.get("top_p", 0.9),
        "max_tokens": gen.get("max_tokens", 220),
        "chat_template_kwargs": {"enable_thinking": False},
    }
    try:
        r = httpx.post(f"{base}/v1/chat/completions", json=body,
                       timeout=timeout if timeout is not None else narrate_timeout())
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, httpx.TimeoutException, KeyError, ValueError) as e:
        raise StorytellerUnavailable(f"storyteller endpoint {base} failed: {e}") from e
    if not isinstance(raw, str) or not raw.strip():
        raise StorytellerFailed("storyteller returned empty content")
    return raw


class StoryOutput(BaseModel):
    """The client-side wrapper around the prose."""

    text: str
    model: str
    template_revision: str
    latency_ms: float


def narrate(env: StoryInput, *, url: str | None = None) -> tuple[StoryOutput, dict]:
    """Authoritative result + bounded context -> narrative prose.

    Fail-closed: raises StorytellerUnavailable (transport) or
    StorytellerFailed (empty/undecodable output). Never mutates state,
    never calls tools, never logs chain-of-thought.
    """
    if not env.has_result:
        raise StorytellerFailed("action_result is required - the Storyteller "
                                "cannot run before world resolution")
    tpl = load_template()
    voice = ""
    if env.voice_tone or env.voice_guidance:
        voice = env.voice_tone + (" - " + env.voice_guidance if env.voice_guidance else "")
    messages = build_messages(tpl, env, voice=voice)
    t0 = time.monotonic()
    raw = _completion(messages, url=url)
    latency_ms = round((time.monotonic() - t0) * 1000, 1)
    text = raw.strip()
    if not text:
        raise StorytellerFailed("storyteller returned empty content")
    meta = {
        "role": "storyteller",
        "model": narrate_model(),
        "template_revision": tpl.get("schema_version"),
        "latency_ms": latency_ms,
        "validation": "ok",
    }
    output = StoryOutput(
        text=text,
        model=narrate_model(),
        template_revision=tpl.get("schema_version"),
        latency_ms=latency_ms,
    )
    _log_entry(env, meta, text)
    return output, meta


# --- logging (private runtime, evidence first) ---------------------------

def _sanitize(text: str, limit: int = 300) -> str:
    return " ".join(text.split())[:limit]


def _log_entry(env: StoryInput, meta: dict, text: str) -> None:
    """One private runtime log line (data/storyteller.jsonl, gitignored).

    Logs the player intent (sanitized), a bounded scene identifier, the
    lore COUNT (never the lore text - retrieved evidence stays private),
    and the bounded story. Never logs VEFR_NARRATE_* values, credentials,
    raw payloads, or chain-of-thought.
    """
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "role": "storyteller",
        "model": meta.get("model"),
        "template_revision": meta.get("template_revision"),
        "input": _sanitize(env.player_intent),
        "action": env.action or None,
        "target": _sanitize(env.target, 80) or None,
        "scene_location": _sanitize(env.scene_location, 80) or None,
        "lore_count": len(env.relevant_lore),
        "output": _sanitize(text, 500),
        "validation": meta.get("validation"),
        "latency_ms": meta.get("latency_ms"),
    }
    path = storyteller_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# --- CLI (narrow testing entrypoint) -------------------------------------

def _cmd_story(args: argparse.Namespace) -> int:
    if args.fixture:
        try:
            data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"[vefr-story] fixture unreadable: {e}", file=sys.stderr)
            return 2
        env = StoryInput.model_validate(data)
    else:
        env = StoryInput(
            player_intent=args.text,
            action_result={"success": True, "outcome": args.text},
        )
    try:
        output, meta = narrate(env, url=args.url or None)
    except StorytellerUnavailable as e:
        print(f"[vefr-story] endpoint unavailable: {e}", file=sys.stderr)
        return 2
    except StorytellerFailed as e:
        print(f"[vefr-story] output failed closed: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(output.model_dump(), ensure_ascii=False, indent=2))
        return 0
    print(output.text)
    print(meta["latency_ms"], "ms")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vefr-story",
        description="Storyteller: authoritative result + bounded context -> prose.",
    )
    parser.add_argument("text", nargs="?", default="",
                        help="what the player attempted (free text)")
    parser.add_argument("--fixture", default=None,
                        help="JSON file with a full StoryInput envelope")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--model", dest="model", default=None,
                        help="override VEFR_NARRATE_MODEL for this call")
    parser.add_argument("--endpoint", "--url", dest="url", default=None,
                        help="override VEFR_NARRATE_URL for this call")
    args = parser.parse_args(argv)
    if args.model:
        os.environ["VEFR_NARRATE_MODEL"] = args.model
    if not args.text and not args.fixture:
        parser.error("pass a player intent or --fixture")
    return _cmd_story(args)


if __name__ == "__main__":
    raise SystemExit(main())