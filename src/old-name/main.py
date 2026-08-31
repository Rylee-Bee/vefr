from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import journal
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
    return list_vault()


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
    return journal.list_entries()


@app.post("/api/journal/clear")
def journal_clear():
    journal.clear()
    return {"cleared": True}


@app.get("/api/export", response_class=PlainTextResponse)
def export():
    """The whole playthrough as markdown - raw text, easy to download."""
    return PlainTextResponse(export_story(), media_type="text/markdown")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
