from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import forge, journal, starred
from .bell import generate_letter
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
    return {"ok": True, "service": "norn", "purpose": PURPOSE}


@app.post("/api/rumor")
def rumor(req: RumorRequest):
    card = generate_rumor(req.phase, req.theme)
    journal.log(
        "rumor",
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
def vault_keep(item: dict):
    from .forge import ItemCard

    card = ItemCard.model_validate(item)
    result = keep_item(card)
    # Only a kept item is journalled - a forge roll nobody took is a
    # thing that never happened.
    journal.log("item_forged", name=card.name, bond=card.bond, lore=card.lore)
    return result


@app.get("/api/vault")
def vault_list():
    items = list_vault()
    return {"items": items, "starred": starred.list_starred()}


@app.post("/api/vault/star/{index}")
def vault_star(index: int):
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
def vault_remove(index: int):
    """Drop a kept item from the vault; undoable for 60s."""
    from fastapi import HTTPException
    removed = forge.remove(index)
    if removed is None:
        raise HTTPException(status_code=404, detail=f"no vault item at index {index}")
    return {"removed": True, "item": removed, "undo_window_s": forge.UNDO_WINDOW_S}


@app.post("/api/vault/undo")
def vault_undo():
    """Restore the most recently removed vault item."""
    from fastapi import HTTPException
    restored = forge.undo()
    if restored is None:
        raise HTTPException(
            status_code=400,
            detail="nothing to undo - either nothing was removed, "
                   f"or the {forge.UNDO_WINDOW_S}s window has elapsed",
        )
    return {"restored": True, "item": restored}


@app.post("/api/bell")
def bell():
    letter = generate_letter()
    journal.log("bell_letter", letter=letter.letter)
    return letter


@app.post("/api/npc")
def npc(req: NpcRequest):
    spoken = generate_line(req.phase, req.speaker)
    journal.log(
        "npc_line", phase=req.phase, speaker=spoken.speaker, line=spoken.line
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
        "willow_start": town["willow_start"],
        "willow_color": town.get("willow_color", "#e8e5df"),
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
def journal_list():
    entries = journal.list_entries()
    return {
        "entries": entries,
        "starred": starred.list_starred(),
    }


@app.post("/api/journal/star/{index}")
def journal_star(index: int):
    """Append the entry at `index` to starred-whispers.md in the pack.

    The file lands on disk in the same place as bible.md - next
    `old-name import --pull` ships it to the deploy host. Idempotent:
    starring the same entry twice appends a second line.
    """
    entries = journal.list_entries()
    if index < 0 or index >= len(entries):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"no journal entry at index {index}")
    return starred.star(entries[index])


@app.post("/api/journal/remove/{index}")
def journal_remove(index: int):
    """Remove one journal entry. Refuses the last entry of its kind.

    The removed entry is stashed server-side for one minute; call
    /api/journal/undo within that window to bring it back.
    """
    from fastapi import HTTPException
    try:
        removed = journal.remove(index)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if removed is None:
        raise HTTPException(status_code=404, detail=f"no journal entry at index {index}")
    return {"removed": True, "entry": removed, "undo_window_s": journal.UNDO_WINDOW_S}


@app.post("/api/journal/undo")
def journal_undo():
    """Restore the most recently removed entry, if still in the undo window."""
    from fastapi import HTTPException
    restored = journal.undo()
    if restored is None:
        raise HTTPException(
            status_code=400,
            detail="nothing to undo - either nothing was removed, "
                   f"or the {journal.UNDO_WINDOW_S}s window has elapsed",
        )
    return {"restored": True, "entry": restored}


@app.post("/api/journal/clear")
def journal_clear():
    journal.clear()
    return {"cleared": True}


@app.get("/api/starred")
def starred_list():
    """Which entries are starred - mirror of the journal/starred pair.

    Surfaced separately so the UI can mark already-starred entries
    on page load without parsing the starred file itself.
    """
    return {"starred": starred.list_starred()}


@app.get("/api/export", response_class=PlainTextResponse)
def export():
    """The whole playthrough as markdown - raw text, easy to download."""
    return PlainTextResponse(export_story(), media_type="text/markdown")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
