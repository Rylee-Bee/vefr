from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import json
import os
import re
import threading
from datetime import date, datetime, timezone
from pathlib import Path

from . import (
    combat,
    desk,
    enhance,
    forge,
    inspect as inspect_mod,
    journal,
    lore,
    sessions,
    starred,
    trace,
)
from .stefna import generate_letter
from .export import export_story
from .forge import ItemCard, forge_item, keep_item, list_vault
from .generator import generate_rumor
from .npc import generate_line
from .paths import app_home
from .world import load_world, current_act

PURPOSE = "a rumor engine for playable worlds"


def _app_title() -> str:
    try:
        return load_world()["title"]
    except Exception:
        return "vefr"


app = FastAPI(title=_app_title(), version="2.0.0", description=PURPOSE.capitalize())
WEB = app_home() / "web"


class _WebStatics(StaticFiles):
    """Serve web/ assets with revalidate-on-every-use.

    The plain StaticFiles mount ships ETags but no Cache-Control, so
    browsers heuristic-cache the UI and serve stale HTML/CSS/JS while
    we iterate. "no-cache" keeps 304 revalidation (fast) but never a
    stale 200.
    """

    def file_response(self, *args, **kwargs):
        resp = super().file_response(*args, **kwargs)
        resp.headers["Cache-Control"] = "no-cache"
        return resp


if WEB.is_dir():
    app.mount("/static", _WebStatics(directory=str(WEB)), name="static")
# The reading row's "What does that mean?" link points at the
# glossary under docs/guides/. Serve the guides read-only so the
# link lands on the file instead of a 404 (dev checkouts + container
# installs that ship docs/ alongside web/).
DOCS = app_home() / "docs" / "guides"
if DOCS.is_dir():
    app.mount("/docs/guides", StaticFiles(directory=str(DOCS)), name="guides")


class RumorRequest(BaseModel):
    phase: str = "whispers"
    theme: str | None = None


class NpcRequest(BaseModel):
    phase: str = "whispers"
    speaker: str | None = None  # None -> the pack's first speaker


@app.get("/api/health")
def health():
    return {"ok": True, "service": "vefr", "purpose": PURPOSE}


@app.post("/api/rumor")
def rumor(req: RumorRequest, session: str = ""):
    with trace.span("/api/rumor", phase=req.phase, session=session or "default") as sp:
        card = generate_rumor(req.phase, req.theme, sid=session or None)
        sp.set(speaker=card.speaker)
    journal.log(
        "rumor",
        sid=session,
        phase=req.phase,
        speaker=card.speaker,
        whisper=card.whisper,
        is_true=card.is_true,
    )
    return card


@app.post("/api/forge")
def forge_roll():
    with trace.span("/api/forge"):
        return forge_item()


@app.post("/api/vault")
def vault_keep(item: ItemCard, session: str = ""):
    """A typed body, not a bare dict: a shape error is a 422 naming
    the missing field. The route used to model_validate a bare dict
    and answered a caller's typo with a bare 500."""
    result = keep_item(item, sid=session)
    # Only a kept item is journalled - a forge roll nobody took is a
    # thing that never happened.
    journal.log("item_forged", sid=session, name=item.name, bond=item.bond, lore=item.lore)
    return result


@app.get("/api/vault")
def vault_list(session: str = ""):
    items = list_vault(sid=session)
    return {"items": items, "starred": starred.list_starred()}


@app.post("/api/vault/star/{index}")
def vault_star(index: int, session: str = ""):
    """Star a kept vault item - same shape as the journal star route."""
    from fastapi import HTTPException

    items = list_vault()
    if index < 0 or index >= len(items):
        raise HTTPException(status_code=404, detail=f"no vault item at index {index}")
    return starred.star(
        {
            "kind": "item_forged",
            "name": items[index].get("name", ""),
            "lore": items[index].get("lore", ""),
            "speaker": "",
        }
    )


@app.post("/api/vault/remove/{index}")
def vault_remove(index: int, session: str = ""):
    """Drop a kept item from the vault; undoable for 60s."""
    from fastapi import HTTPException

    removed = forge.remove(index, sid=session)
    if removed is None:
        raise HTTPException(status_code=404, detail=f"no vault item at index {index}")
    return {"removed": True, "item": removed, "undo_window_s": forge.UNDO_WINDOW_S}


@app.post("/api/vault/undo")
def vault_undo(session: str = ""):
    """Restore the most recently removed vault item."""
    from fastapi import HTTPException

    restored = forge.undo(sid=session)
    if restored is None:
        raise HTTPException(
            status_code=400,
            detail="nothing to undo - either nothing was removed, "
            f"or the {forge.UNDO_WINDOW_S}s window has elapsed",
        )
    return {"restored": True, "item": restored}


@app.post("/api/stefna")
def stefna(session: str = ""):
    with trace.span("/api/stefna", session=session or "default"):
        letter = generate_letter()
    journal.log("stefna_letter", sid=session, letter=letter.letter)
    return letter


@app.post("/api/npc")
def npc(req: NpcRequest, session: str = ""):
    """An unknown speaker (or a voice-less pack) is a 404 in plain
    English - the engine's own words, not a RuntimeError 500."""
    from fastapi import HTTPException

    try:
        with trace.span("/api/npc", phase=req.phase, session=session or "default") as sp:
            spoken = generate_line(req.phase, req.speaker, sid=session or None)
            sp.set(speaker=spoken.speaker)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    journal.log("npc_line", sid=session, phase=req.phase, speaker=spoken.speaker, line=spoken.line)
    return spoken


class CombatAction(BaseModel):
    kind: str
    phase: str | None = None
    target: str | None = None


@app.post("/api/combat/action")
def combat_action(req: CombatAction, session: str = ""):
    """Record a combat action (attack, console, hurl, ...).

    The action is just a journal entry. The HUD has whatever
    costume it wants (HP bar, encounter prompt, verb buttons);
    the engine doesn't change any game state. The surface is
    a costume, the costume is the point.
    """
    with trace.span(
        "/api/combat/action",
        kind=req.kind,
        phase=req.phase or "default",
        session=session or "default",
    ):
        try:
            entry = combat.record_combat_action(
                kind=req.kind,
                phase=req.phase,
                target=req.target,
                session=session,
                allowed=combat.verbs_for_pack(load_world()),
            )
        except ValueError as e:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail=str(e))
    return entry


class DeskVerify(BaseModel):
    whisper: str
    verdict: str


class DeskPrint(BaseModel):
    headline: str


@app.post("/api/desk/verify")
def desk_verify(req: DeskVerify, session: str = ""):
    """Judge a whisper this session heard. The engine compares the
    verdict against the truth it actually sent - the Desk is where
    is_true finally gets consumed."""
    from fastapi import HTTPException

    try:
        return desk.verify(session or None, req.whisper, req.verdict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/desk/print")
def desk_print(req: DeskPrint, session: str = ""):
    """Print a headline. What the paper says, the world hears:
    later prompts carry the printed list."""
    from fastapi import HTTPException

    try:
        entry = desk.print_headline(session or None, req.headline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return entry


@app.get("/api/desk/facts")
def desk_facts(session: str = ""):
    """The session's derived world knowledge: confirmed, debunked,
    printed. Replay of the journal - always honest, never stale."""
    return {"facts": desk.facts(session or None)}


@app.get("/api/world")
def world():
    """The town payload - everything the renderer needs, from the pack.

    Returns the always-array shape: the world's metadata at the top
    level, plus `act` (the current act) and `regions` (named regions
    of the current act). The renderer is a single-region experience
    in this PR; `regions.town` is the same data the legacy
    `town` block used to expose, so the web layer can read either
    path during the migration.
    """
    w = load_world()
    act = current_act(w)
    region = act["regions"].get("town", {})
    # Town metadata can come from three places, in priority order:
    #   1. The region's contract.json (acts shape, convention-driven)
    #   2. The act's _town_legacy (acts shape, transitional)
    #   3. The legacy flat-shape town block (in _town_legacy too)
    # The contract wins so a future PR can move the canary's
    # data to town/contract.json without the API route changing.
    legacy = act.get("_town_legacy", {}) or region.get("contract", {})
    # The map lives in one of two places: the region's map_text
    # (acts shape, served by the loader from town/map.md) or the
    # legacy block's `map` key (flat shape, served from the
    # pack-level world.json). Union them so the web layer doesn't
    # care which shape the pack is in.
    raw_map = region.get("map_text", "") or "\n".join(legacy.get("map", []))
    town_map = [ln for ln in raw_map.splitlines() if ln.strip()]
    speakers = [
        {
            "key": key,
            "name": spec["name"],
            "at": spec["at"],
            "near": spec["near"],
            "seeds": spec.get("seeds", {}),
        }
        for key, spec in act["speakers"].items()
    ]
    return {
        "title": w["title"],
        "creed": w.get("creed", ""),
        "phases": list(w["phases"].keys()),
        "surface": w["surface"],
        "hp": combat.hp_for_pack(w) if w["surface"] == "combat" else None,
        "act": {
            "id": act["id"],
            "title": act["title"],
            "verbs": list(act.get("verbs") or []),
            "floor": act.get("floor", "costume"),
            "tone": act.get("tone", ""),
            "ruleset": act.get("ruleset", "ambient"),
        },
        "regions": {"town": {"map_text": town_map}},
        "tile": legacy.get("tile", 32),
        "bg": legacy.get("bg", "#131311"),
        "map": town_map,
        "legend": legacy.get("legend", {}),
        "pois": legacy.get("pois", {}),
        "hero_start": legacy.get("hero_start", [1, 1]),
        "hero_color": legacy.get("hero_color", "#e8e5df"),
        "watch": legacy.get("watch", {}),
        "sanctuary_tiles": legacy.get("sanctuary_tiles", []),
        "water_by_phase": legacy.get("water_by_phase", {}),
        "flood_tiles": legacy.get("flood_tiles", []),
        "speakers": speakers,
        "speaker_color": legacy.get("speaker_color", "#8b939c"),
        "speaker_head": legacy.get("speaker_head", "#d8d5cf"),
    }


@app.get("/api/journal")
def journal_list(session: str = ""):
    entries = journal.list_entries(sid=session)
    return {
        "entries": entries,
        "starred": starred.list_starred(),
    }


@app.post("/api/journal/star/{index}")
def journal_star(index: int, session: str = ""):
    """Append the entry at `index` to starred-whispers.md in the pack.

    The file lands on disk in the same place as logbok.md - next
    `ratatoskr ferry fetch --pull` ships it to the deploy host. Idempotent:
    starring the same entry twice appends a second line.
    """
    entries = journal.list_entries(sid=session)
    if index < 0 or index >= len(entries):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"no journal entry at index {index}")
    return starred.star(entries[index])


@app.post("/api/journal/remove/{index}")
def journal_remove(index: int, session: str = ""):
    """Remove one journal entry. Refuses the last entry of its kind.

    The removed entry is stashed server-side for one minute; call
    /api/journal/undo within that window to bring it back.
    """
    from fastapi import HTTPException

    try:
        removed = journal.remove(index, sid=session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if removed is None:
        raise HTTPException(status_code=404, detail=f"no journal entry at index {index}")
    return {"removed": True, "entry": removed, "undo_window_s": journal.UNDO_WINDOW_S}


@app.post("/api/journal/undo")
def journal_undo(session: str = ""):
    """Restore the most recently removed entry, if still in the undo window."""
    from fastapi import HTTPException

    restored = journal.undo(sid=session)
    if restored is None:
        raise HTTPException(
            status_code=400,
            detail="nothing to undo - either nothing was removed, "
            f"or the {journal.UNDO_WINDOW_S}s window has elapsed",
        )
    return {"restored": True, "entry": restored}


@app.post("/api/journal/clear")
def journal_clear(session: str = ""):
    journal.clear(sid=session)
    return {"cleared": True}


class RewindRequest(BaseModel):
    at: int  # keep entries[:at] - same semantics as the fork's cut


class ForkRequest(BaseModel):
    at: int  # keep entries[:at]


class MoveRequest(BaseModel):
    """One arrival the town renderer witnessed.

    `poi` is where the hero stands (a place name from the pack, or
    the world title when between places); `x`/`y` are tile
    coordinates; `phase` is the world's phase at the moment of
    arrival. The client only posts on change of place, never per
    tile - a walk logs visits, not footsteps.
    """

    poi: str
    x: int
    y: int
    phase: str | None = None


@app.post("/api/journal/move")
def journal_move(req: MoveRequest, session: str = ""):
    """Journal one arrival - where the hero actually stood.

    The town renderer posts this when the place under the hero
    changes, so the export's "The Fen Walked" section can witness
    the journey the way it witnesses whispers and lines. Pure
    bookkeeping: no model call, no validation against the map -
    the client is the only thing that knows where the hero is.
    """
    entry = journal.log(
        "move",
        sid=session,
        poi=req.poi,
        x=req.x,
        y=req.y,
        phase=req.phase,
    )
    return {"logged": True, "entry": entry}


@app.post("/api/journal/rewind")
def journal_rewind(req: RewindRequest, session: str = ""):
    """Cut the journal back to entries[:at]; the tail is undoable 60s.

    The vault is left untouched: possessions were forged before the
    cut, and the UI confirms before calling.
    """
    from fastapi import HTTPException

    result = journal.rewind(req.at, sid=session)
    if result is None:
        raise HTTPException(status_code=404, detail=f"nothing to rewind at {req.at}")
    result["undo_window_s"] = journal.UNDO_WINDOW_S
    return result


@app.post("/api/journal/rewind/undo")
def journal_rewind_undo(session: str = ""):
    """Bring back the tail of the most recent rewind, within the window."""
    from fastapi import HTTPException

    restored = journal.rewind_undo(sid=session)
    if restored is None:
        raise HTTPException(
            status_code=400,
            detail="nothing to undo - either nothing was rewound, "
            f"or the {journal.UNDO_WINDOW_S}s window has elapsed",
        )
    return restored


@app.post("/api/journal/fork")
def journal_fork(req: ForkRequest, session: str = ""):
    """Copy journal[:at] + the vault into a new session; parent pointer kept.

    The current session is never modified - forking branches, never
    cuts. The new session's journal opens with one `fork` entry
    describing where it came from, and sessions/<sid>.meta.json
    records the parent for tooling.
    """
    entries = journal.list_entries(sid=session)
    at = max(0, min(req.at, len(entries)))
    new_sid = sessions.new_id()
    journal.set_entries(entries[:at], sid=new_sid)
    forge.set_vault(forge.list_vault(sid=session), sid=new_sid)
    parent = sessions.clean(session)
    sessions.write_meta(
        new_sid,
        {"parent": parent, "fork_at": at, "at": sessions.now_iso()},
    )
    label = "the default playthrough" if sessions.is_default(session) else f"session {parent}"
    journal.log(
        "fork",
        sid=new_sid,
        parent=parent,
        fork_at=at,
        note=f"forked from {label} with {at} entries kept",
    )
    return {
        "session": new_sid,
        "parent": parent,
        "fork_at": at,
        "kept": at,
        "url": f"/?session={new_sid}",
    }


# --------------------------------------------------------------- builder

# The builder surface in the web UI: stateless turn-based chat with
# the local model, plus thin wrappers around vefr's import/validate/
# verify commands. The web UI holds the conversation history; the
# server is just "given the history so far, write the next line".
# Same `chat.draft()` machinery as the CLI interview, but driven by
# fetch() from the page instead of input() in a terminal.

BUILDER_SYSTEM = (
    "You are a warm, curious world-building collaborator helping "
    "an author shape their own story. Plain prose, never purple, "
    "never a lecture. Reply with one short paragraph (2-5 sentences) "
    "or one short list. If the author is stuck, ask a focused question. "
    "Stay grounded in the pack they're editing - if they reference "
    "a character or place by name, treat that as part of their canon. "
    "Never invent facts about the story; when you don't know, ask. "
    "You propose edits and directions; you do not commit canon or mutate the pack."
)


class BuilderChatTurn(BaseModel):
    message: str
    history: list[dict] = []  # [{role, content}] pairs
    world: str | None = None  # pack to focus on (None = current)


@app.post("/api/builder/chat")
def builder_chat(turn: BuilderChatTurn):
    """One turn of the builder-mode chat. Stateless, proposal-only."""
    from .chat import draft

    # Replay the history briefly so the model has context. We keep it
    # short - the page holds the long view.
    context_lines = []
    for h in turn.history[-6:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            who = "Author" if h["role"] == "user" else "Builder"
            context_lines.append(f"{who}: {h['content']}")
    context = "\n".join(context_lines)
    prompt = turn.message
    if context:
        prompt = f"(recent conversation)\n{context}\n\nAuthor: {turn.message}"
    text = draft(prompt, system=BUILDER_SYSTEM)

    return {"reply": text}


@app.get("/api/spark/health")
def spark_health_route():
    """Spark's liveness as VEFR sees it: up, down, or timed out.

    A graded payload, never an exception - a dead Spark is a state of
    the world the UI can show, not a 500. The probe also records the
    round-trip so 'slow but alive' is distinguishable from 'gone'.
    """
    from . import spark as spark_mod

    try:
        probe = spark_mod.health()
        return {
            "ok": True,
            "spark": "available",
            **probe,
            "profile": spark_mod.profile()["key"],
            "model": spark_mod.profile()["alias"],
        }
    except Exception as exc:  # noqa: BLE001 - down is data, not a crash
        return {
            "ok": False,
            "spark": "unavailable",
            "url": spark_mod.spark_url(),
            "error": f"{exc.__class__.__name__}: {exc}",
            "profile": spark_mod.profile()["key"],
        }


class SparkTaskRequest(BaseModel):
    task: str  # a TASK_CONTRACTS key: npc, state_edit, dialogue, lore, narrate
    user: str  # the task's own payload, in the task's language
    speaker: str | None = None
    state: dict | None = None
    world: bool = True


@app.post("/api/spark/task")
def spark_task(req: SparkTaskRequest):
    """The production Spark path: context in, validated result out.

    Fail-closed by design - SparkUnreachable and schema failures come
    back as graded payloads naming the escalation path, never as an
    applied guess. The model proposes; this route validates; VEFR
    applies. `escalated=true` names a response VEFR routed to K2
    instead (the generator seam), so a Spark outage degrades to the
    pre-Spark behavior rather than an error.
    """
    from . import spark as spark_mod

    if req.task not in spark_mod.TASK_CONTRACTS:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail=f"unknown spark task {req.task!r}; known: {sorted(spark_mod.TASK_CONTRACTS)}",
        )
    try:
        result, meta = spark_mod.spark_call(
            req.task, req.user, speaker=req.speaker, state=req.state
        )
        meta.pop("response", None)  # the debug view lives in inspect
        return {"ok": True, "spark": "ok", "result": result, "meta": meta, "escalated": False}
    except spark_mod.SparkUnavailable as exc:
        return {
            "ok": False,
            "spark": "unavailable",
            "error": f"{exc.__class__.__name__}: {exc}",
            "escalated": False,
            "hint": "escalate to K2 or degrade",
        }
    except spark_mod.SparkMalformed as exc:
        # Spark answered twice with garbage. That is data about Spark,
        # not a license to apply an unvalidated proposal: fail closed,
        # offer the K2 path.
        return {"ok": False, "spark": "malformed", "error": f"{exc}", "escalated": False}


@app.get("/api/spark/inspect")
def spark_inspect(task: str, user: str, speaker: str | None = None, call: bool = False):
    """Development view of the Context Builder (read-only by default).

    Shows the profile, model, context sections, approximate prompt
    size, and the exact messages Spark would receive - the answer to
    'did the model fail, or did VEFR give it bad context?'. With
    call=true it also runs the task and returns the response plus the
    validation result. Never mutates anything.
    """
    from . import spark as spark_mod
    from fastapi import HTTPException

    if task not in spark_mod.TASK_CONTRACTS:
        raise HTTPException(
            status_code=422,
            detail=f"unknown spark task {task!r}; known: {sorted(spark_mod.TASK_CONTRACTS)}",
        )
    view = spark_mod.inspect_context(task, user, speaker=speaker)
    if not call:
        return {"ok": True, **view}
    try:
        result, meta = spark_mod.spark_call(task, user, speaker=speaker)
        return {"ok": True, **view, "validation": "ok", "response": meta.get("response", "")}
    except spark_mod.SparkUnavailable as exc:
        return {"ok": False, **view, "validation": f"unavailable: {exc}"}
    except spark_mod.SparkMalformed as exc:
        return {"ok": False, **view, "validation": f"malformed: {exc}"}


@app.post("/api/spark/escalate")
def spark_escalate():
    """Run the escalation self-check: the benchmark's fixed probes
    through the live Spark, scored against known ground truth. The
    integrated answer to 'does the resident model still know what is
    not its job?' - and, transitively, whether the K2 path it names is
    still the escalation target."""
    from . import spark as spark_mod

    try:
        decisions = spark_mod.classify_escalation(spark_mod.ESCALATION_PROBES)
        ok, detail = spark_mod.escalation_verdict(decisions)
        return {
            "ok": ok,
            "escalation": detail,
            "decisions": [d.model_dump() for d in decisions],
            "escalation_target": "K2 via VEFR_LLAMACPP_URL",
        }
    except spark_mod.SparkUnavailable as exc:
        return {"ok": False, "error": f"{exc}", "decisions": []}


@app.get("/api/runes")
def runes_registry():
    """The full 24-rune Elder Futhark registry for the gallery view.

    Each rune includes its stave (the carved shape), aettir,
    short meaning, long meaning, and the engine phase it anchors.
    The web UI uses this to render the rune gallery - the player
    can see all 24 staves + meanings at a glance.
    """
    from .runes import RUNES, PHASE_ANCHOR

    return {
        "runes": [
            {
                "name": r.name,
                "stave": r.stave,
                "aettir": r.aettir,
                "short": r.short,
                "long": r.long,
                "engine_phase": r.engine_phase,
            }
            for r in RUNES
        ],
        "anchors": {
            phase: {"name": r.name, "stave": r.stave, "short": r.short}
            for phase, r in PHASE_ANCHOR.items()
        },
    }


@app.get("/api/runes/cast")
def runes_cast(phase: str | None = None):
    """Today's cast - three runes for the current moment.

    Seeded from (world_name, current ISO minute). Same cast within
    a session-minute; new cast every minute. The model sees this
    same cast in its system prompt; the player sees it in the UI.
    Pass ?phase=X to get the cast for a specific phase.
    """
    from datetime import datetime, timezone
    from .runes import cast_for, render_for_prompt, seed_for

    pack_phases = list(load_world().get("phases", {}).keys())
    if not phase:
        phase = pack_phases[0] if pack_phases else "whispers"
    iso_minute = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    seed = seed_for("api.runes.cast", phase, iso_minute)
    cast_result = cast_for(seed, phase=phase)
    return {
        "phase": phase,
        "seed": seed,
        "iso_minute": iso_minute,
        "positions": [
            {"position": pos, "name": r.name, "stave": r.stave, "short": r.short, "long": r.long}
            for pos, r in cast_result
        ],
        "prompt_block": render_for_prompt(cast_result),
    }


@app.post("/api/builder/lore")
def builder_lore(req: lore.LorePreviewRequest):
    """Preview a lore pack's mood-board for a topic + seeds.

    Reads the pack's textures.md / names.md / questions.md,
    threads them through one LLM call, returns the wandering-poets
    shape: {textures, names[], questions[]}. No canonical fields -
    lore is mood, not canon.
    """
    from fastapi import HTTPException
    from .lore import preview_lore

    try:
        result = preview_lore(req)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return result.model_dump()


@app.post("/api/builder/lore/list")
def builder_lore_list():
    """Every lore pack with a manifest of files."""
    from .lore import list_lore

    return [_e.model_dump() for _e in list_lore()]


@app.get("/api/builder/worlds")
def builder_worlds():
    """Every pack under worlds/ that has a world.json.

    Surfaces the engine-shipped packs (sample-world + lore packs)
    alongside any pack the author has imported via `ferry fetch`.
    The page uses this to populate the world picker in the Builder
    tab.
    """
    from .world import discover_packs

    out = []
    for entry in discover_packs():
        p = Path(entry["path"])
        try:
            w = json.loads((p / "world.json").read_text(encoding="utf-8"))
            # Acts-shape packs put speakers inside the per-act
            # contract; flat packs put them at the top level.
            speakers: list[str] = []
            if (p / "acts").is_dir():
                for ad in sorted((p / "acts").iterdir()):
                    if not ad.is_dir() or ad.name.startswith("."):
                        continue
                    act_w = json.loads((ad / "world.json").read_text(encoding="utf-8"))
                    speakers.extend(act_w.get("speakers", {}).keys())
            else:
                speakers = list(w.get("speakers", {}).keys())
            out.append(
                {
                    "name": entry["name"],
                    "title": w.get("title", entry["name"]),
                    "phases": list(w.get("phases", {}).keys()),
                    "speakers": speakers,
                    "source": entry["source"],
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return {"worlds": out}


@app.post("/api/builder/import")
def builder_import(payload: dict):
    """Thin wrapper around `ratatoskr ferry fetch --pull`.

    Payload: {repo: 'owner/name', name: 'your-pack-name'}
    """
    from .cli import GITEA_BASE, cmd_import
    import argparse

    args = argparse.Namespace(
        repo=payload.get("repo", ""),
        name=payload.get("name"),
        base=payload.get("base", GITEA_BASE),
        target=payload.get("target", "local"),
        pull=payload.get("pull", True),
        dry_run=False,
    )
    rc = cmd_import(args)
    return {"rc": rc}


@app.post("/api/builder/validate")
def builder_validate(payload: dict):
    """Run maplab.validate on the named pack."""
    from .maplab import load_pack, validate
    from .paths import pack_dir

    name = payload.get("name") or None
    try:
        pack = pack_dir(name)
        w = load_pack(pack)
        errors = validate(w, pack_dir=pack)
    except Exception as e:  # noqa: BLE001
        return {"errors": [f"validate failed: {e}"], "ok": False}
    return {"errors": errors, "ok": len(errors) == 0, "pack": str(pack)}


@app.post("/api/builder/verify")
def builder_verify(payload: dict):
    """Verify the live deployment's served world against the live URL."""
    from .maplab import verify_live

    url = payload.get("url", "http://127.0.0.1:8820")
    ok, errors = verify_live(url)
    return {"ok": bool(ok), "errors": errors, "url": url}


# --------------------------------------------------------------- weave file

# The served builder's "Make shareable file" pair. `ratatoskr weave`
# is terminal-only; a phone user with no terminal needs the same
# packaging from the page. The build is the CLI's own build_web core,
# so the bytes match `ratatoskr weave` exactly. Output is server-owned
# (VEFR_WEAVE_DIR or app_home()/dist) - a request never names a path -
# and one weave runs at a time.

_WEAVE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.html$")
_WORLD_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_WEAVE_LOCK = threading.Lock()


def _weave_output_dir() -> Path:
    """Where the served builder drops woven files. Server-owned only.

    VEFR_WEAVE_DIR is operator config (deploys/tests); otherwise the
    repo/container's dist/, the same tree `ratatoskr weave` writes to.
    """
    env = os.environ.get("VEFR_WEAVE_DIR")
    return Path(env) if env else app_home() / "dist"


class BuilderWeaveRequest(BaseModel):
    world: str | None = None  # pack to weave (None = current), like the other builder routes


@app.post("/api/builder/weave")
def builder_weave(req: BuilderWeaveRequest | None = None):
    """Weave the current world into one shareable HTML file.

    Resolves the pack exactly as the other /api/builder routes do
    (pack_dir over the named pack or the current world), builds it
    with the CLI's own packaging core into a server-owned directory,
    and returns {name, size_bytes, built_at, download_url}. A second
    weave while one is running gets 409 instead of racing the output.
    """
    from .cli import build_web
    from .paths import pack_dir

    world = req.world if req else None
    if world is not None and not _WORLD_NAME_RE.match(world):
        # A bare pack name only: this route bundles whatever it resolves
        # into a downloadable file, so "../elsewhere" must never reach pack_dir.
        raise HTTPException(status_code=400, detail="world must be a bare pack name")
    pack = pack_dir(world)
    if not (pack / "world.json").exists():
        raise HTTPException(status_code=404, detail=f"pack not found: {pack.name}")
    if not _WEAVE_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="a weave is already running")
    try:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", pack.name).strip("-") or "world"
        out_path = build_web(
            pack,
            _weave_output_dir(),
            out_name=f"{safe}-{date.today().isoformat()}.html",
        )
    finally:
        _WEAVE_LOCK.release()
    stat = out_path.stat()
    return {
        "name": out_path.name,
        "size_bytes": stat.st_size,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "download_url": f"/api/builder/weave/file/{out_path.name}",
    }


@app.get("/api/builder/weave/file/{name}")
def builder_weave_file(name: str):
    """Download a woven file as an attachment.

    `name` must match a strict filename pattern and resolve inside the
    server-owned output dir; anything else is refused before the disk
    is touched (path traversal never reaches FileResponse).
    """
    if not _WEAVE_NAME_RE.match(name):
        raise HTTPException(status_code=404, detail="no such woven file")
    out_dir = _weave_output_dir().resolve()
    target = (out_dir / name).resolve()
    if target.parent != out_dir or not target.is_file():
        raise HTTPException(status_code=404, detail="no such woven file")
    return FileResponse(target, media_type="text/html", filename=name)


@app.get("/api/starred")
def starred_list():
    """Which entries are starred - mirror of the journal/starred pair.

    Surfaced separately so the UI can mark already-starred entries
    on page load without parsing the starred file itself.
    """
    return {"starred": starred.list_starred()}


@app.get("/api/trace")
def trace_list(limit: int = 100):
    """The engine's own trace - what actually ran, newest last.

    Dev-UI instrumentation only: never in the journal, never in the
    export, never in the packaged game.
    """
    return {"events": trace.recent(limit)}


@app.get("/api/weave")
def weave_list(limit: int = 200):
    """The engine's weave log - what the loader did, newest first.

    The weave log is fire-and-forget; the ring is in-memory, the
    file is on disk. The builder's Weave tab polls this route.
    """
    return inspect_mod.recent_weave(limit)


@app.get("/api/builder/resolved")
def builder_resolved():
    """The merged world the engine sees, after convention resolution.

    A mirror of load_world()'s return value with engine-only
    bookkeeping stripped. The builder renders this in the
    "what does the engine see?" view so the author can compare
    it against their on-disk files.
    """
    return inspect_mod.resolved_world()


@app.get("/api/builder/aspects")
def builder_aspects(phase: str | None = None):
    """Active world aspects for the Dev Overlay & Aspect Inspector.

    Returns loaded pack aspects, active act metadata, active regions,
    speaker seed matrices, current rune cast, and recent trace events.
    """
    return inspect_mod.pack_aspects(phase=phase)


@app.post("/api/builder/enhance/map")
def builder_enhance_map(req: enhance.MapEnhanceRequest):
    """Contextual AI Enhance for POI and map descriptions.

    Enriches sensory descriptions and interactive details for a
    point of interest or room using loaded pack canon and active tone.
    """
    with trace.span("/api/builder/enhance/map", region=req.region, poi=req.poi_name):
        return enhance.enhance_map(req)


@app.post("/api/builder/map/propose")
def builder_map_propose(payload: dict):
    """The storyteller's pen - the model proposes a validated town redraw.

    Same machinery as the `norns chat` interview (chat.propose_map):
    run-length rows at the current map's exact dimensions, legend
    characters only, gated by maplab.validate's geometry and
    reachability checks before anything is returned. This route never
    writes to the pack - the web room treats the result as a sketch
    the author can paint over and keep as a keepsake.
    """
    from . import chat
    from .maplab import load_pack
    from .paths import pack_dir

    name = payload.get("name") or None
    story = (payload.get("story") or "").strip()
    mood = (payload.get("mood") or "").strip() or "quiet"
    try:
        pack = pack_dir(name)
        w = load_pack(pack)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"couldn\u2019t open the pack: {e}"}
    town = w.get("town") or {}
    if not town.get("map") or not town.get("legend"):
        return {"ok": False, "reason": "this world has no map to sketch yet"}
    try:
        rows = chat.propose_map(story or w.get("title", ""), mood, w, pack)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"the surveyor couldn\u2019t reach a pen: {e}"}
    if not rows:
        return {
            "ok": False,
            "reason": "the surveyor drew nothing usable \u2014 describe it differently, or paint it yourself",
        }
    return {
        "ok": True,
        "grid": rows,
        "legend": town.get("legend", {}),
        "dimensions": [len(rows), len(rows[0])],
    }


@app.post("/api/builder/map/check")
def builder_map_check(payload: dict):
    """The engine checks a storyteller's sketch before it's kept.

    Purely deterministic: the draft grid is swapped into a copy of
    the unified pack and run through the same maplab.validate gate
    as `norns validate` - shape, legend coverage, hero placement,
    reachability of every door, poi and speaker. Never writes.
    """
    from .maplab import load_pack, validate
    from .paths import pack_dir

    name = payload.get("name") or None
    grid = payload.get("grid") or []
    if not isinstance(grid, list) or not grid or not all(isinstance(r, str) for r in grid):
        return {"ok": False, "errors": ["the sketch needs a rectangular grid of text rows"]}
    try:
        pack = pack_dir(name)
        w = load_pack(pack)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "errors": [f"couldn\u2019t open the pack: {e}"]}
    town = w.get("town") or {}
    if not town.get("map") or not town.get("legend"):
        return {"ok": False, "errors": ["this world has no map to check yet"]}
    # The sketch replaces only the ground; everything else is the
    # pack's own proven content.
    w["town"]["map"] = grid
    errors = validate(w)
    return {"ok": not errors, "errors": errors}


@app.post("/api/builder/face/roll")
def builder_face_roll(payload: dict):
    """Invite a new face: model-drafted, engine-placed, never written.

    The model only suggests prose (name, role, seed line); where
    they stand comes from the interview's own deterministic rule
    (reachable from the hero's start, not on anyone's spot, not on
    flood ground). The web room keeps the card as a vault item
    (kind "face") only when the storyteller says so.
    """
    from . import chat
    from .maplab import load_pack
    from .paths import pack_dir

    name = payload.get("name") or None
    mood = (payload.get("mood") or "").strip() or "quiet"
    try:
        pack = pack_dir(name)
        w = load_pack(pack)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"couldn\u2019t open the pack: {e}"}
    town = w.get("town") or {}
    if not town.get("map") or not town.get("legend"):
        return {"ok": False, "reason": "this world has no map to place anyone on yet"}
    tile = chat._pick_tile(w)
    if tile is None:
        return {"ok": False, "reason": "there is nowhere left to stand in this world"}
    try:
        face = chat.propose_face(w.get("title", ""), mood, w)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"the keeper couldn\u2019t reach a pen: {e}"}
    if not face:
        return {
            "ok": False,
            "reason": "the keeper drew nothing usable \u2014 try again, or write the face yourself",
        }
    return {"ok": True, "face": {**face, "at": list(tile)}}


@app.post("/api/builder/enhance/voice")
def builder_enhance_voice(req: enhance.VoiceEnhanceRequest):
    """Contextual AI Enhance for NPC voices and speech rules.

    Drafts cadence rules, seed dialogue, and strike prompts for
    world characters in the requested tone.
    """
    with trace.span("/api/builder/enhance/voice", speaker=req.speaker_name):
        return enhance.enhance_voice(req)


@app.post("/api/builder/enhance/item")
def builder_enhance_item(req: enhance.ItemEnhanceRequest):
    """Contextual AI Enhance for item flavor, enchants, and curses.

    Crafts quiet enchantments and subtle, non-gory curses anchored
    in the world's forge texture.
    """
    with trace.span("/api/builder/enhance/item", kind=req.kind, bond=req.bond):
        return enhance.enhance_item(req)


@app.post("/api/handoff")
def handoff_create():
    """Write a markdown bundle to data/handoffs/. Returns the path
    so the builder can show a "saved to X" link.

    The bundle has sections the author fills in (what I tried,
    what I saw, what I've already done) plus auto-filled context
    (resolved world, recent weave events). It is the AI-buddy
    handoff format; see docs/guides/handoff.md.
    """
    inspect_mod._ensure_data_dir()
    from .paths import app_home

    out_dir = app_home() / "data" / "handoffs"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = inspect_mod.build_handoff(out_dir)
    return {"path": str(path), "filename": path.name}


@app.get("/api/wiki")
def wiki(session: str = ""):
    """The world's wiki, auto-generated from canon + play - read-only.

    Characters are the pack's voices joined to what they actually
    said this session (npc_line entries, newest last). Relics are
    the session's kept items, canon order. The counts give the
    session's shape at a glance. No model calls - the wiki is a
    lens on data that already exists.
    """
    w = load_world()
    speakers = current_act(w)["speakers"]
    entries = journal.list_entries(sid=session)
    by_speaker: dict[str, list[dict]] = {}
    for e in entries:
        if e.get("kind") == "npc_line":
            by_speaker.setdefault(e.get("speaker") or "a voice", []).append(
                {"at": e.get("at", ""), "phase": e.get("phase", ""), "line": e.get("line", "")}
            )
    characters = []
    for key, spec in speakers.items():
        spoken = by_speaker.get(spec["name"], [])
        characters.append(
            {
                "key": key,
                "name": spec["name"],
                "lines": len(spoken),
                "recent": spoken[-3:],
            }
        )
    # A journal speaker the canon doesn't name still belongs here -
    # generated whispers sometimes speak through strangers.
    known = {spec["name"] for spec in speakers.values()}
    for speaker, spoken in by_speaker.items():
        if speaker not in known:
            characters.append(
                {
                    "key": "",
                    "name": speaker,
                    "lines": len(spoken),
                    "recent": spoken[-3:],
                }
            )
    return {
        "characters": characters,
        "relics": forge.list_vault(sid=session),
        "rumors": sum(1 for e in entries if e.get("kind") == "rumor"),
        "letters": sum(1 for e in entries if e.get("kind") in ("stefna_letter", "bell_letter")),
    }


@app.get("/api/export", response_class=PlainTextResponse)
def export(session: str = ""):
    """The whole playthrough as markdown - one section per dev UI
    tab, in the order the player met them. See export.py for the
    shape. Raw text, easy to download.
    """
    return PlainTextResponse(export_story(sid=session), media_type="text/markdown")


@app.get("/api/export/tabs", response_class=PlainTextResponse)
def export_tabs_list():
    """List of available per-tab exports, for the web UI to render
    as 'Export this tab' buttons."""
    return PlainTextResponse(
        "\n".join(["town", "rumors", "vault", "stefna", "voices", "journal"]),
        media_type="text/plain",
    )


@app.get("/api/export/tabs/{name}", response_class=PlainTextResponse)
def export_tab(name: str, session: str = ""):
    """One tab's worth of the world as markdown.

    The web UI's "Export this tab" button posts here; the result
    is a complete document (canon + that tab) ready to download.
    """
    from fastapi import HTTPException
    from .export import export_tab as render_tab, _TAB_NAMES

    if name not in _TAB_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"unknown tab {name!r}; expected one of {list(_TAB_NAMES)}",
        )
    return PlainTextResponse(render_tab(name, sid=session), media_type="text/markdown")


@app.get("/")
def index():
    # Primary UI: the workshop shell (app.html). The historical Board
    # shell lives on as /static/index.html (and as the canonical
    # board markup the shipped-JS tests lock in).
    idx = WEB / "app.html"
    if idx.is_file():
        return FileResponse(idx, headers={"Cache-Control": "no-cache"})
    return PlainTextResponse("vefr engine running (web UI unbundled)", status_code=200)
