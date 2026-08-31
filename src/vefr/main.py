from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import json

from . import forge, journal, lore, starred
from .stefna import generate_letter
from .export import export_story
from .forge import forge_item, keep_item, list_vault
from .generator import generate_rumor
from .npc import generate_line
from .paths import app_home
from .world import load_world

PURPOSE = "it gives the hellos that never happened"

app = FastAPI(title=load_world()["title"], version="2.0.0", description=PURPOSE.capitalize())
WEB = app_home() / "web"
app.mount("/static", StaticFiles(directory=str(WEB)), name="static")


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
    card = generate_rumor(req.phase, req.theme)
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
def forge():
    return forge_item()


@app.post("/api/vault")
def vault_keep(item: dict, session: str = ""):
    from .forge import ItemCard

    card = ItemCard.model_validate(item)
    result = keep_item(card, sid=session)
    # Only a kept item is journalled - a forge roll nobody took is a
    # thing that never happened.
    journal.log(
        "item_forged", sid=session, name=card.name, bond=card.bond, lore=card.lore
    )
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
    letter = generate_letter()
    journal.log("stefna_letter", sid=session, letter=letter.letter)
    return letter


@app.post("/api/npc")
def npc(req: NpcRequest, session: str = ""):
    spoken = generate_line(req.phase, req.speaker)
    journal.log(
        "npc_line", sid=session, phase=req.phase, speaker=spoken.speaker, line=spoken.line
    )
    return spoken


@app.get("/api/world")
def world():
    """The town payload - everything the renderer needs, from the pack."""
    w = load_world()
    town = w["town"]
    return {
        "title": w["title"],
        "gold_rule": w.get("gold_rule", ""),
        "phases": list(w["phases"].keys()),
        "tile": town["tile"],
        "bg": town["bg"],
        "map": town["map"],
        "legend": town["legend"],
        "pois": town["pois"],
        "hero_start": town["hero_start"],
        "hero_color": town.get("hero_color", "#e8e5df"),
        "watch": town["watch"],
        "sanctuary_tiles": town.get("sanctuary_tiles", []),
        "water_by_phase": town.get("water_by_phase", {}),
        "flood_tiles": town.get("flood_tiles", []),
        "speakers": [
            {
                "key": key,
                "name": spec["name"],
                "at": spec["at"],
                "near": spec["near"],
                "seeds": spec["seeds"],
            }
            for key, spec in w["speakers"].items()
        ],
        "speaker_color": town.get("speaker_color", "#8b939c"),
        "speaker_head": town.get("speaker_head", "#d8d5cf"),
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
    "the ferryman or the roll-keeper by name, treat those as the people they are. "
    "Never invent facts about the story; when you don't know, ask."
)


class BuilderChatTurn(BaseModel):
    message: str
    history: list[dict] = []  # [{role, content}] pairs
    world: str | None = None  # pack to focus on (None = current)


@app.post("/api/builder/chat")
def builder_chat(turn: BuilderChatTurn):
    """One turn of the builder-mode chat. Stateless."""
    from .chat import ASSISTANT_SYSTEM, draft
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

    # If the chat is about a lore pack, persist the response as a
    # lore note. The author has been doing research and the engine
    # has something to say - both should land in the pack so the
    # export reads them later and the world knows itself better.
    if turn.world:
        from datetime import datetime, timezone
        from .paths import pack_dir
        pack = pack_dir(turn.world)
        if pack.exists():
            notes_path = pack / "lore-notes.md"
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
            entry = f"\n## {ts} (lore: {turn.world})\n\n{text}\n"
            with notes_path.open("a", encoding="utf-8") as f:
                f.write(entry)

    return {"reply": text}


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
def runes_cast():
    """Today's cast - three runes for the current moment.

    Seeded from (world_name, current ISO minute). Same cast within
    a session-minute; new cast every minute. The model sees this
    same cast in its system prompt; the player sees it in the UI.
    """
    from datetime import datetime, timezone
    from .paths import world_name as _world_name
    from .runes import cast_for, render_for_prompt, seed_for

    # Phase comes from the pack's `phases` ordering. The first phase
    # is the canonical "current" one if the client hasn't told us
    # otherwise; clients can pass ?phase=X to override.
    from fastapi import Request as _Req
    # We can't read query params here without changing the signature;
    # the current phase is the first phase in the pack. Clients that
    # want a phase-specific cast can hit this endpoint with the cast
    # baked in - or we can grow it to read query params later.
    pack_phases = list(load_world().get("phases", {}).keys())
    phase = pack_phases[0] if pack_phases else "whispers"
    iso_minute = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    seed = seed_for("api.runes.cast", phase, iso_minute)
    cast_result = cast_for(seed, phase=phase)
    return {
        "phase": phase,
        "seed": seed,
        "iso_minute": iso_minute,
        "positions": [
            {"position": pos, "name": r.name, "stave": r.stave,
             "short": r.short, "long": r.long}
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

    Surfaces sample-world + private-canon + any other import. The page
    uses this to populate the world picker in the Builder tab.
    """
    from .paths import app_home
    base = app_home() / "worlds"
    if not base.exists():
        return {"worlds": []}
    out = []
    for p in sorted(base.iterdir()):
        if (p / "world.json").exists():
            try:
                w = json.loads((p / "world.json").read_text(encoding="utf-8"))
                out.append({
                    "name": p.name,
                    "title": w.get("title", p.name),
                    "phases": list(w.get("phases", {}).keys()),
                    "speakers": list(w.get("speakers", {}).keys()),
                })
            except (json.JSONDecodeError, OSError):
                continue
    return {"worlds": out}


@app.post("/api/builder/import")
def builder_import(payload: dict):
    """Thin wrapper around ratatoskr ferry fetch --pull. {repo: 'owner/name', name: 'private-canon'}"""
    from .cli import cmd_import
    import argparse

    args = argparse.Namespace(
        repo=payload.get("repo", ""),
        name=payload.get("name"),
        base=payload.get("base", "http://192.168.2.216:3000"),
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


@app.get("/api/starred")
def starred_list():
    """Which entries are starred - mirror of the journal/starred pair.

    Surfaced separately so the UI can mark already-starred entries
    on page load without parsing the starred file itself.
    """
    return {"starred": starred.list_starred()}


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
    return FileResponse(WEB / "index.html")
