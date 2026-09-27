"""Teach while building: after an author makes something, Fróði names the idea.

The Book Girl direction (estate docs/orchestration/BOOK-GIRL-2026-09-27.md):
intent → action → consequence → recognition → term. Recognition, never
correction. At most one idea per turn, and only after the builder replied.

How an idea is recognised, cheapest first:
  1. cues: each teachable glossary entry lists phrasings ("until", "only if")
     that wake the check. No cue, no model call - the usual answer is none.
  2. the model: given the author's words and the 1-4 woken ideas (each with
     its one-line `when`), pick one or "none", schema-locked, plus a short
     phrase naming what the author made, in their own words.
No model running means no note: Fróði never guesses.

Familiarity is per person, across worlds (data/learning.json): how often an
idea was offered, what it was first seen in, and "Got it" taps. Stage:
first (never offered) → again (offered 1-2 times) → familiar (3+ offers or
Got it twice: no note, the word is simply used).
"""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from .paths import data_dir

MAX_CANDIDATES = 4
_lock = threading.Lock()

SCHEMA_TEMPLATE = {
    "type": "object",
    "properties": {
        "designing": {"type": "boolean"},
        "term": {"type": "string"},
        "context": {"type": "string", "maxLength": 90},
    },
    "required": ["designing", "term", "context"],
}

SYSTEM = (
    "You spot design ideas in what a game author just described. First decide "
    "`designing`: true only if the author is describing something that happens in "
    "their game or story (a place, rule, character, event, screen). Requests to the "
    "assistant, questions, and talk about the studio or themselves are false. "
    "Then pick the one idea whose description clearly matches what they described, "
    "or \"none\". When designing is false, the term is none. Most messages use none.\n"
    "Examples of none: \"Can you make the text in this panel larger?\" / \"Please "
    "keep your replies short.\" / \"How many coins is that sword again?\" / \"The "
    "smith wants a new title, any ideas?\"\n"
    "For context, write a short phrase naming the thing the author made, in their "
    "own words, like \"the hidden door that needed the lantern\"."
)


def teachable(glossary: dict) -> dict:
    return {k: e for k, e in glossary.items() if e.get("teach")}


def _norm(text: str) -> str:
    return text.lower().replace("’", "'").replace("‘", "'")


def candidates(message: str, glossary: dict) -> list[str]:
    """Ideas whose cues appear in the author's words, most cues first."""
    text = _norm(message)
    hits = []
    for key, e in teachable(glossary).items():
        n = sum(1 for c in e.get("cues", []) if re.search(c, text))
        if n:
            hits.append((-n, key))
    return [k for _, k in sorted(hits)][:MAX_CANDIDATES]


# --- familiarity ------------------------------------------------------------

def _store() -> Path:
    return data_dir() / "learning.json"


def load() -> dict:
    try:
        data = json.loads(_store().read_text())
        return data if isinstance(data, dict) and isinstance(data.get("concepts"), dict) else {"concepts": {}}
    except (OSError, ValueError):
        return {"concepts": {}}


def _save(data: dict) -> None:
    path = _store()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    os.replace(tmp, path)


def stage(record: dict | None) -> str:
    if not record:
        return "first"
    if record.get("got_it", 0) >= 2 or record.get("offered", 0) >= 3:
        return "familiar"
    return "again"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def record_offer(term: str, context: str) -> dict:
    with _lock:
        data = load()
        rec = data["concepts"].setdefault(term, {"offered": 0, "got_it": 0})
        if not rec.get("first_context") and context:
            rec["first_context"] = context
            rec["first_at"] = _now()
        rec["offered"] = rec.get("offered", 0) + 1
        rec["last_at"] = _now()
        _save(data)
        return rec


def record_got_it(term: str) -> dict:
    worlds("POST", "/api/learning/got-it", {"concept": concept_id(term)})
    with _lock:
        data = load()
        rec = data["concepts"].setdefault(term, {"offered": 0, "got_it": 0})
        rec["got_it"] = rec.get("got_it", 0) + 1
        _save(data)
        return rec


# --- recognition -------------------------------------------------------------

def _grounded(context: str, message: str) -> str:
    """Keep the model's phrase only if it's made of the author's own words."""
    context = " ".join(str(context).split())[:90].strip(" .")
    # a short name for the thing, not the author's sentence read back to them
    if len(context.split()) > 10 or re.match(r"(?i)(i|we|you|let'?s|there|it|make|can)\b", context):
        return ""
    words = {w for w in re.findall(r"[a-z']{4,}", _norm(context))}
    theirs = {w for w in re.findall(r"[a-z']{4,}", _norm(message))}
    return context if words and len(words & theirs) >= max(1, len(words) // 2) else ""


def ask_model(message: str, cands: list[str], glossary: dict) -> tuple[str, str] | None:
    """(term, context), ("none", "") or None when no model answered."""
    from . import generator

    schema = json.loads(json.dumps(SCHEMA_TEMPLATE))
    schema["properties"]["term"]["enum"] = cands + ["none"]
    ideas = "\n".join(f"- {k}: {glossary[k]['when']}" for k in cands)
    payload = {
        "model": generator.MODEL,
        "system": SYSTEM,
        "prompt": f"The author wrote: \"{message}\"\n\nIdeas:\n{ideas}\n\nReply with only the JSON object.",
        "format": schema,
        "stream": False,
        "think": False,
        "keep_alive": generator.KEEP_ALIVE,
        "options": {"temperature": 0.0},
    }
    for _ in range(2):
        try:
            out = json.loads(generator._completion(payload))
            term = str(out.get("term", ""))
            if out.get("designing") is False:
                return "none", ""
            if term in cands or term == "none":
                return term, str(out.get("context", ""))
        except Exception:  # noqa: BLE001 - a quiet model means no note, never a crash
            continue
    return None


# --- Worlds' shared learning memory ------------------------------------------
# One memory across all of Rylee's projects (Book Girl): Worlds answers how to teach
# an idea now (first / again / familiar / off, with its mode applied) and keeps
# only a concept id and a few words. VEFR mirrors every answer locally, so a note
# never waits on Worlds: unreachable (or no key) means the local record decides.

MODE_TO_WORLDS = {"build": "build", "tips": "occasional", "off": "plain"}
MODE_FROM_WORLDS = {v: k for k, v in MODE_TO_WORLDS.items()}


def concept_id(term: str) -> str:
    """Worlds' concept ids: lowercase, apostrophes dropped, spaces to dashes."""
    return re.sub(r"[^a-z0-9-]+", "-", term.lower().replace("'", "").replace("\u2019", "")).strip("-")[:64]


def worlds(method: str, path: str, body: dict | None = None, timeout: float = 3.0) -> dict | None:
    """Call Worlds' /api/learning* with the learning-only key; None when unset or unreachable."""
    import urllib.request

    base, token = os.environ.get("VEFR_WORLDS_URL", ""), os.environ.get("VEFR_WORLDS_LEARNING_TOKEN", "")
    if not base or not token:
        return None
    req = urllib.request.Request(base.rstrip("/") + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read() or b"{}")
        return out.get("data") if isinstance(out, dict) and out.get("ok") else None
    except Exception:  # noqa: BLE001 - Worlds away is a normal state, never an error for the author
        return None


def recognize(message: str, glossary: dict, *, model=None) -> dict:
    """{"teach": card | None, "why_not": reason}. Records the offer when a card is made."""
    message = str(message or "").strip()[:2000]
    cands = candidates(message, glossary) if message else []
    if not cands:
        return {"teach": None, "why_not": "no idea's cue in these words"}
    picked = (model or ask_model)(message, cands, glossary)
    if picked is None:
        return {"teach": None, "why_not": "no model answered, and Fróði never guesses"}
    term, context = picked
    if term == "none":
        return {"teach": None, "why_not": "the model saw none of the woken ideas"}
    context = _grounded(context, message)
    home = worlds("POST", "/api/learning/encounter",
                  {"concept": concept_id(term), "project": "vefr", "context": context})
    if home and home.get("stage") in ("familiar", "off"):
        record_offer(term, context)                       # mirror, for when Worlds is away
        why = "the owner chose plain words" if home["stage"] == "off" else f"{term} is already familiar"
        return {"teach": None, "why_not": why + " (Worlds)"}
    before = load()["concepts"].get(term)
    st = home["stage"] if home and home.get("stage") in ("first", "again") else stage(before)
    if st == "familiar":
        return {"teach": None, "why_not": f"{term} is already familiar"}
    rec = record_offer(term, context)
    if home and home.get("first_context"):
        rec = {**rec, "first_context": home["first_context"]}
    e = glossary[term]
    card = {"term": term, "stage": st, "plain": e["plain"], "why": e.get("why", ""), "context": context}
    if e.get("vefr"):
        card["local"] = e["vefr"]
    if st == "again" and rec.get("first_context") and rec["first_context"] != context:
        card["first_context"] = rec["first_context"]
    return {"teach": card, "why_not": ""}
