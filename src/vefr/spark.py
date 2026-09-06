"""Spark - the resident intelligence.

Spark is VEFR's small, always-available local brain. The benchmark
(2026-09-06, bazzite, CPU-only llama.cpp b10818) settled the shape:

  spark-quality  Phi-4-mini-instruct Q4_K_M   100/100 VEFR suite,
                 ~1.9 GiB resident, ~21 tok/s, ~635 ms TTFT
  spark-tiny     Qwen3.5-0.8B Q8_0            80.3/100 VEFR suite,
                 ~1.05 GiB resident, ~58 tok/s, ~231 ms TTFT
                 (Q4 is forbidden for sub-1B: state edits corrupt)

The GGUF is the engine, not the product. VEFR owns the intelligence:
this module builds Spark's context in layers from authoritative data
(the spark contract, the loaded world pack, the speaker's voice file,
the runtime state, the task's schema) so a fresh install teaches Spark
the world because the pack says so - never because someone hand-wrote
a prompt file.

The division of labor the benchmark proved:

  - structured output, bounded state edits, continuity, and
    escalation judgment are Spark-safe (LOCAL)
  - architecture, debugging, research, and cross-file reasoning are
    K2 territory (ESCALATE) - an escalated call goes through
    generator._completion, the same K2-backed seam the engine already
    uses, so K2's configuration is never touched

Fail-closed everywhere: a dead, slow, or unreachable Spark raises
SparkUnavailable (callers degrade gracefully or escalate) and a
response that misses the task's schema is discarded after two tries
(SparkMalformed). The model proposes; VEFR validates; VEFR applies.
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path

import httpx
from pydantic import BaseModel, ValidationError


class SparkUnavailable(RuntimeError):
    """Spark is down, timed out, or unreachable. Callers degrade
    gracefully or escalate; a dead Spark never corrupts state."""


class SparkMalformed(RuntimeError):
    """Spark answered, but missed the task's schema twice. Fail
    closed: the proposal is discarded, never applied."""

# --- configuration -----------------------------------------------------

# Spark's own endpoint. Unset -> the engine's LLAMACPP_URL, which on
# bazzite is K2: a config that points Spark at the heavyweight is a
# configuration error, not a feature, so keep the default honest.
SPARK_URL = os.environ.get("VEFR_SPARK_URL", "http://127.0.0.1:8082").rstrip("/")
SPARK_PROFILE = os.environ.get("VEFR_SPARK_PROFILE", "quality")
SPARK_TIMEOUT = float(os.environ.get("VEFR_SPARK_TIMEOUT", "180"))
SPARK_MODELS = Path(os.environ.get("VEFR_SPARK_MODELS", "~/spark/models")).expanduser()

# Pinned artifacts: exact repo, file, size, sha256 - no floating tags.
# Hashes computed from the benchmark copies on bazzite (2026-09-06);
# verify_model() re-checks size and hash on every acquire.
PROFILES: dict[str, dict] = {
    "quality": {
        "repo": "unsloth/Phi-4-mini-instruct-GGUF",
        "file": "Phi-4-mini-instruct-Q4_K_M.gguf",
        "size_bytes": 2_490_000_000,
        "sha256": "88c00229914083cd112853aab84ed51b87bdf6b9ce42f532d8c85c7c63b1730a",
        "license": "MIT",
        "alias": "phi-4-mini-instruct-q4",
        # Phi's chat template has no thinking mode: nothing to disable.
        # The benchmark ran the stock template with reasoning_effort=low
        # (the engine-wide gpt-oss accommodation; phi ignores it).
        "chat_template_kwargs": {"reasoning_effort": "low"},
        "notes": "default resident; 100/100 VEFR suite",
    },
    "tiny": {
        "repo": "unsloth/Qwen3.5-0.8B-GGUF",
        "file": "Qwen3.5-0.8B-Q8_0.gguf",
        "size_bytes": 810_000_000,
        "sha256": "0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c",
        "license": "Apache-2.0",
        "alias": "qwen3.5-0.8b-q8",
        # Thinking-mode invariant: Qwen3.5 ships thinking ON by default
        # and burns the entire output budget in reasoning_content before
        # any visible answer (2026-09-06 find: a healthy model scored
        # 0.0 on every test until this kwarg was set). Never rely on
        # defaults; when swapping profiles, re-test.
        "chat_template_kwargs": {"enable_thinking": False},
        "notes": "low-memory profile; Q8 minimum - Q4 corrupts state edits",
    },
}


def profile(name: str | None = None) -> dict:
    """Resolve a Spark profile by name (default: the configured one)."""
    key = (name or SPARK_PROFILE or "quality").lower()
    if key not in PROFILES:
        raise KeyError(f"unknown Spark profile {key!r}; known: {', '.join(PROFILES)}")
    return {"key": key, **PROFILES[key]}


def spark_url() -> str:
    """Spark's endpoint, resolved from configuration."""
    return SPARK_URL


# --- model acquisition (ratatoskr spark) -------------------------------

def models_root() -> Path:
    """The canonical Spark model directory on this machine."""
    return Path(os.environ.get("VEFR_SPARK_MODELS", str(SPARK_MODELS))).expanduser()


def model_path(prof: dict, root: Path | None = None) -> Path:
    """The canonical on-disk location for a profile's GGUF."""
    return (root or models_root()) / prof["file"]


def verify_model(prof: dict, path: Path | None = None) -> tuple[bool, str]:
    """Size + sha256 gate. A partial download fails loudly here."""
    p = path or model_path(prof)
    if not p.exists():
        return False, f"missing: {p}"
    size = p.stat().st_size
    if abs(size - prof["size_bytes"]) > 64 * 1024 * 1024:
        return False, (f"size {size} is not near the pinned {prof['size_bytes']} "
                       f"- partial or corrupt download")
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != prof["sha256"]:
        return False, f"sha256 mismatch: {p.name} is not the pinned artifact"
    return True, f"verified: {p.name} matches the pinned sha256"


# --- context builder (the layers) --------------------------------------

_CORE_PATH = Path(__file__).resolve().parent / "spark-contract.md"


def core_contract() -> str:
    """Layer 1 - the versioned Spark contract, shipped with the engine."""
    return _CORE_PATH.read_text(encoding="utf-8")


def world_context() -> str:
    """Layer 3 - generated from the loaded pack. Never a hand-written copy."""
    from .world import load_world
    w = load_world()
    lines = [f"World: {w['title']}."]
    if w.get("gold_rule"):
        lines.append(f"The world's rule: {w['gold_rule']}")
    if w.get("description"):
        lines.append(f"About: {w['description']}")
    phases = "; ".join(f"{k}: {v}" for k, v in w.get("phases", {}).items())
    if phases:
        lines.append(f"Phases: {phases}")
    bonds = ", ".join(w.get("bonds", {}))
    if bonds:
        lines.append(f"Bonds (how items connect to the player): {bonds}.")
    canon = _logbok()
    if canon:
        lines.append(f"Canon (fixed - never contradict):\n{canon}")
    return "\n".join(lines)


def _logbok() -> str:
    """The pack's canon, capped: relevant context beats more context."""
    from .saga import logbok
    text = logbok()
    if len(text) > 1600:
        return text[:1600].rsplit("\n", 1)[0]
    return text


def character_context(speaker: str) -> str:
    """Layer 4 - the speaker's own rules, from their voice file in the pack."""
    from .world import load_world, resolve_voice_file
    w = load_world()
    spec = w["voices"].get(speaker)
    if not spec:
        return f"Speaker '{speaker}' has no voice file - do not invent one."
    rules = resolve_voice_file(spec["file"]).read_text(encoding="utf-8")
    return (f"Voice rules for {spec.get('name', speaker)} (absolute):\n"
            f"{rules.strip()}")


def runtime_context(state: dict | None) -> str:
    """Layer 5 - the minimum current state, generated fresh per request."""
    if not state:
        return "Current state: none supplied."
    keep = {}
    for k, v in state.items():
        keep[k] = v[:400] if isinstance(v, str) and len(v) > 400 else v
    return "Current state (authoritative):\n" + json.dumps(
        keep, indent=1, ensure_ascii=False, default=str)


# --- task contracts (Layer 2 + Layer 6) --------------------------------

NPC_SCHEMA = {
    "type": "object",
    "properties": {k: {"type": "string"} for k in
                   ("id", "name", "role", "personality", "location", "dialogue_seed")},
    "required": ["id", "name", "role", "personality", "location", "dialogue_seed"],
    "additionalProperties": False,
}

PROSE_SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}},
                "required": ["text"]}

ESCALATE_SCHEMA = {
    "type": "object",
    "properties": {"decisions": {
        "type": "array", "minItems": 1, "maxItems": 8,
        "items": {"type": "object",
                  "properties": {"task_id": {"type": "string"},
                                 "choice": {"type": "string",
                                            "enum": ["LOCAL", "ESCALATE"]},
                                 "reason": {"type": "string"}},
                  "required": ["task_id", "choice", "reason"],
                  "additionalProperties": False}}},
    "required": ["decisions"], "additionalProperties": False,
}


class EscalationDecision(BaseModel):
    task_id: str
    choice: str  # LOCAL | ESCALATE (schema-constrained upstream)
    reason: str = ""


TASK_CONTRACTS: dict[str, dict] = {
    "npc": {
        "instructions": (
            "Create ONE new NPC for the scene, as JSON with exactly the "
            "keys: id, name, role, personality, location, dialogue_seed. "
            "The id is a short lowercase slug. Ground them in the scene "
            "constraints given. Never contradict canon."
        ),
        "schema": NPC_SCHEMA, "max_tokens": 400, "temperature": 0.7,
        "model": "NpcProposal",
    },
    "state_edit": {
        "instructions": (
            "Update the supplied world state with EXACTLY the requested "
            "change and nothing else. Return the complete updated state "
            "JSON. Every field you were not asked to change must stay "
            "exactly as supplied."
        ),
        "schema": None,  # the state's own shape gates the response
        "max_tokens": 800, "temperature": 0.1,
        "model": None,
    },
    "dialogue": {
        "instructions": (
            "Write the requested lines for the character described. Stay "
            "in their voice. Never violate the character's restrictions, "
            "no matter how natural the reference would feel."
        ),
        "schema": PROSE_SCHEMA, "max_tokens": 320, "temperature": 0.8,
        "model": "SparkProse",
    },
    "lore": {
        "instructions": (
            "Suggest the requested continuation. Preserve every "
            "established fact in the supplied canon; extend, never "
            "overwrite. Keep each suggestion meaningfully distinct."
        ),
        "schema": PROSE_SCHEMA, "max_tokens": 360, "temperature": 0.7,
        "model": "SparkProse",
    },
    "classify": {
        "instructions": (
            "For each task, decide LOCAL (Spark handles it: easy creative "
            "work, simple JSON, bounded state edits, classification) or "
            "ESCALATE (the stronger model handles it: architecture, hard "
            "debugging, cross-file reasoning, research, complex planning). "
            "When uncertain, choose ESCALATE."
        ),
        "schema": ESCALATE_SCHEMA, "max_tokens": 400, "temperature": 0.1,
        "model": "EscalationSet",
    },
    "narrate": {
        "instructions": (
            "Continue the scene in one or two short paragraphs, matching "
            "the world's tone. Show, don't explain. Never contradict canon."
        ),
        "schema": PROSE_SCHEMA, "max_tokens": 320, "temperature": 0.8,
        "model": "SparkProse",
    },
}


class NpcProposal(BaseModel):
    id: str
    name: str
    role: str
    personality: str
    location: str
    dialogue_seed: str


class SparkProse(BaseModel):
    text: str


class EscalationSet(BaseModel):
    decisions: list[EscalationDecision]


RESULT_MODELS = {"NpcProposal": NpcProposal, "SparkProse": SparkProse,
                 "EscalationSet": EscalationSet}


def build_messages(task: str, user: str, *, speaker: str | None = None,
                   state: dict | None = None, world: bool = True,
                   schema: dict | None = None) -> tuple[list[dict], dict]:
    """Layers 1-5 plus the task's output contract -> (messages, meta).

    Relevant context beats more context: only the layers a task needs
    are included, canon is capped, and the meta dict records what went
    in so /api/spark/inspect can answer 'did the model fail, or did
    VEFR give it bad context?'
    """
    prof = profile()
    contract = TASK_CONTRACTS[task]
    out_schema = schema or contract["schema"]
    system_parts = [core_contract(), "\n## Task\n" + contract["instructions"]]
    if out_schema is not None:
        system_parts.append("Reply with only the JSON object the schema names.")
    if world:
        system_parts.append("\n## World\n" + world_context())
    if speaker:
        system_parts.append("\n" + character_context(speaker))
    if state is not None:
        system_parts.append("\n" + runtime_context(state))
    messages = [{"role": "system", "content": "\n".join(system_parts)},
                {"role": "user", "content": user}]
    approx_words = sum(len(re.findall(r"\S+", m["content"])) for m in messages)
    meta = {"task": task, "profile": prof["key"], "model": prof["alias"],
            "sections": [p.splitlines()[0].lstrip("# ") for p in system_parts],
            "approx_prompt_words": approx_words,
            "chat_template_kwargs": prof["chat_template_kwargs"],
            "schema": "json_schema" if out_schema is not None else "text"}
    return messages, meta


def inspect_context(task: str, user: str, **kw) -> dict:
    """The safe debug view: what WOULD be sent, section by section."""
    messages, meta = build_messages(task, user, **kw)
    return {**meta, "messages": messages}


# --- the Spark client (fail-closed) -------------------------------------

def health(timeout: float = 4.0, url: str | None = None) -> dict:
    """Spark's liveness, with a tiny end-to-end latency probe. Raises
    SparkUnavailable - the route layer turns that into a graded,
    non-fatal payload."""
    base = (url or spark_url()).rstrip("/")
    t0 = time.time()
    r = httpx.get(f"{base}/health", timeout=timeout)
    r.raise_for_status()
    payload = r.json()
    return {"url": base, "status": payload.get("status", "?"),
            "probe_ms": round((time.time() - t0) * 1000)}


def _spark_completion(messages: list[dict], schema: dict | None,
                      max_tokens: int, temperature: float,
                      url: str | None = None) -> str:
    """One Spark call. Profile-owned chat_template_kwargs (the
    thinking-mode invariant lives here, server-shaped), json_schema
    response_format when the task carries a schema. Two retries on
    transport errors; then SparkUnavailable - never a guessed answer."""
    prof = profile()
    body = {
        "model": prof["alias"],
        "messages": messages,
        "response_format": (
            {"type": "json_schema",
             "json_schema": {"name": "spark_out", "schema": schema, "strict": True}}
            if schema else {"type": "text"}
        ),
        "stream": False,
        "chat_template_kwargs": prof["chat_template_kwargs"],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    base = (url or spark_url()).rstrip("/")
    last: Exception | None = None
    for _ in range(2):
        try:
            r = httpx.post(f"{base}/v1/chat/completions", json=body,
                           timeout=SPARK_TIMEOUT)
            r.raise_for_status()
            return json.loads(r.text)["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            last = e
    raise SparkUnavailable(f"spark unreachable at {base}: {last}")


def spark_call(task: str, user: str, *, speaker: str | None = None,
               state: dict | None = None, world: bool = True,
               schema: dict | None = None, model_cls=None,
               tries: int = 2, url: str | None = None) -> tuple[BaseModel | dict, dict]:
    """Run a task through Spark: context in, validated result out.

    Returns (result, meta). result is a pydantic model when the task
    names one, else the parsed JSON. Raises SparkUnavailable when
    Spark cannot be reached, SparkMalformed when the response misses
    the schema after `tries` - callers degrade or escalate, never
    apply an unvalidated proposal.
    """
    contract = TASK_CONTRACTS[task]
    use_schema = schema if schema is not None else contract["schema"]
    messages, meta = build_messages(task, user, speaker=speaker, state=state,
                                    world=world, schema=use_schema)
    last_err: Exception | None = None
    for _ in range(tries):
        raw = _spark_completion(messages, use_schema, contract["max_tokens"],
                                contract["temperature"], url=url)
        try:
            if contract["model"]:
                result = RESULT_MODELS[contract["model"]].model_validate_json(raw)
            else:
                result = json.loads(raw)
            meta["validation"] = "ok"
            meta["response"] = raw
            return result, meta
        except (ValidationError, json.JSONDecodeError, ValueError) as e:
            last_err = e
    meta["validation"] = f"failed: {last_err}"
    meta["response"] = raw
    raise SparkMalformed(f"spark output failed the {task} schema twice: {last_err}")


# --- escalation ---------------------------------------------------------

ESCALATION_PROBES = [
    # The phrasing mirrors the benchmark's scored probes - those are the
    # measured ground truth for this model (T9 = 2/2 at 100/100).
    {"task_id": "haiku", "desc": "Write a haiku about the Hollow Lamp lighting the tower."},
    {"task_id": "merge", "desc": "Return JSON merging {\"item\":\"voucher\",\"kept\":true} into the inventory."},
    {"task_id": "migrate", "desc": "Design a save-state migration system for three on-disk schema versions, with rollback."},
    {"task_id": "debug", "desc": "Debug why the journal occasionally writes two entries for one action, across three async writers."},
    {"task_id": "bond", "desc": "Should the Hollow Lamp be 'found' or 'given'? The pack is ambiguous - use your judgment."},
]
ESCALATION_EXPECT = {"haiku": "LOCAL", "merge": "LOCAL",
                     "migrate": "ESCALATE", "debug": "ESCALATE"}
ESCALATION_FLEX = {"bond"}  # a defensible judgment call either way


def classify_escalation(tasks: list[dict], *, url: str | None = None) -> list[EscalationDecision]:
    """Ask Spark which of these tasks belong to K2.

    The benchmark proved this is a capability tiny models can do
    reliably (Phi: 5/5; Qwen 0.8B Q8: 5/5): the little brain knows
    when not to try. Deterministic probes are included so the
    integrated check has a fixed reference shape.
    """
    listing = "\n".join(f"task_id={t['task_id']}: {t['desc']}" for t in tasks)
    user = (f"For each task below, decide whether Spark should handle it "
            f"locally (LOCAL) or hand it to the stronger resident model "
            f"(ESCALATE).\n{listing}\n\nOne decision object per task, in order.")
    # World context included: the probes name world objects (the Hollow
    # Lamp) and the benchmark measured classification WITH that context.
    result, meta = spark_call("classify", user, world=True, url=url)
    return result.decisions


def escalation_verdict(decisions: list[EscalationDecision]) -> tuple[bool, str]:
    """Score a classify run against the known ground truth.

    Returns (ok, detail). The four fixed probes must match; the bond
    question is a defensible judgment call either way.
    """
    got = {d.task_id: d.choice for d in decisions}
    misses = [k for k, v in ESCALATION_EXPECT.items() if got.get(k) != v]
    ok = not misses
    return ok, ("all escalation probes correct" if ok
                else f"misses: {misses} (got {got})")


def state_edit_check(original: dict, updated: dict,
                     allowed: set[str]) -> tuple[bool, str]:
    """VEFR's side of the state-edit contract: the proposal is valid
    only when every difference from `original` is inside `allowed`
    (top-level keys the request was allowed to touch). One extra
    mutation anywhere - an invented field, a renamed key, a shifted
    value - fails closed. This is the 'VEFR validates' half of
    'the model proposes; VEFR validates; VEFR applies'."""
    if not isinstance(updated, dict):
        return False, "response is not a JSON object"
    added = set(updated) - set(original)
    removed = set(original) - set(updated)
    if added or removed:
        return False, f"key drift: +{sorted(added)} -{sorted(removed)}"
    changed = []
    for k in original:
        if json.dumps(original[k], sort_keys=True, default=str) != \
                json.dumps(updated[k], sort_keys=True, default=str):
            changed.append(k)
    outside = [k for k in changed if k not in allowed]
    if outside:
        return False, f"unrequested changes: {outside}"
    if not changed:
        return False, "nothing changed - the edit did not apply"
    return True, f"changed exactly: {sorted(set(changed) & set(allowed))}"


def needs_escalation(desc: str) -> bool:
    """The deterministic pre-filter: keywords the benchmark showed no
    tiny model should touch. The model's own judgment still runs for
    everything that passes this gate - two gates, cheap one first."""
    low = desc.lower()
    hard_markers = ("architecture", "migrat", "schema version", "rollback",
                    "debug", "race", "async", "cross-file", "refactor",
                    "research", "optimize the engine", "repository")
    return any(m in low for m in hard_markers)
