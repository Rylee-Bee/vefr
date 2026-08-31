from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import json
from pathlib import Path

from . import combat, forge, inspect as inspect_mod, journal, lore, sessions, starred, trace
from .stefna import generate_letter
from .export import export_story
from .forge import forge_item, keep_item, list_vault
from .generator import generate_rumor
from .npc import generate_line
from .paths import app_home
from .world import load_world, current_act, current_town

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
    with trace.span("/api/rumor", phase=req.phase, session=session or "default") as sp:
        card = generate_rumor(req.phase, req.theme)
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
    with trace.span("/api/stefna", session=session or "default"):
        letter = generate_letter()
    journal.log("stefna_letter", sid=session, letter=letter.letter)
    return letter


@app.post("/api/npc")
def npc(req: NpcRequest, session: str = ""):
    with trace.span("/api/npc", phase=req.phase, session=session or "default") as sp:
        spoken = generate_line(req.phase, req.speaker)
        sp.set(speaker=spoken.speaker)
    journal.log(
        "npc_line", sid=session, phase=req.phase, speaker=spoken.speaker, line=spoken.line
    )
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
    with trace.span("/api/combat/action", kind=req.kind,
                     phase=req.phase or "default",
                     session=session or "default"):
        try:
            entry = combat.record_combat_action(
                kind=req.kind, phase=req.phase, target=req.target,
                session=session,
            )
        except ValueError as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=str(e))
    return entry


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
        "gold_rule": w.get("gold_rule", ""),
        "phases": list(w["phases"].keys()),
        "surface": w["surface"],
        "hp": combat.hp_for_pack(w) if w["surface"] == "combat" else None,
        "act": {"id": act["id"], "title": act["title"]},
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
            out.append({
                "name": entry["name"],
                "title": w.get("title", entry["name"]),
                "phases": list(w.get("phases", {}).keys()),
                "speakers": speakers,
                "source": entry["source"],
            })
        except (json.JSONDecodeError, OSError):
            continue
    return {"worlds": out}


@app.post("/api/builder/import")
def builder_import(payload: dict):
    """Thin wrapper around ratatoskr ferry fetch --pull. {repo: 'owner/name', name: 'private-canon'}"""
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
    from datetime import datetime
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
                {"at": e.get("at", ""), "phase": e.get("phase", ""),
                 "line": e.get("line", "")}
            )
    characters = []
    for key, spec in speakers.items():
        spoken = by_speaker.get(spec["name"], [])
        characters.append({
            "key": key,
            "name": spec["name"],
            "lines": len(spoken),
            "recent": spoken[-3:],
        })
    # A journal speaker the canon doesn't name still belongs here -
    # generated whispers sometimes speak through strangers.
    known = {spec["name"] for spec in speakers.values()}
    for speaker, spoken in by_speaker.items():
        if speaker not in known:
            characters.append({
                "key": "",
                "name": speaker,
                "lines": len(spoken),
                "recent": spoken[-3:],
            })
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
    return FileResponse(WEB / "index.html")
