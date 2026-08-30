from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .bell import generate_letter
from .forge import forge_item, keep_item, list_vault
from .generator import generate_rumor
from .npc import generate_line
from .paths import app_home
from .world import load_world

PURPOSE = "it gives the hellos that never happened"

app = FastAPI(title="Old Name", version="2.0.0", description=PURPOSE.capitalize())
WEB = app_home() / "web"
app.mount("/static", StaticFiles(directory=str(WEB)), name="static")


class RumorRequest(BaseModel):
    phase: str = "whispers"
    theme: str | None = None


class NpcRequest(BaseModel):
    phase: str = "whispers"
    speaker: str = "the ferryman"


@app.get("/api/health")
def health():
    return {"ok": True, "service": "old-name", "purpose": PURPOSE}


@app.post("/api/rumor")
def rumor(req: RumorRequest):
    return generate_rumor(req.phase, req.theme)


@app.post("/api/forge")
def forge():
    return forge_item()


@app.post("/api/vault")
def vault_keep(item: dict):
    from .forge import ItemCard

    return keep_item(ItemCard.model_validate(item))


@app.get("/api/vault")
def vault_list():
    return list_vault()


@app.post("/api/bell")
def bell():
    return generate_letter()


@app.post("/api/npc")
def npc(req: NpcRequest):
    return generate_line(req.phase, req.speaker)


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
        "speakers": [
            {
                "key": key,
                "name": spec["name"],
                "at": spec["at"],
                "near": spec["near"],
            }
            for key, spec in w["speakers"].items()
        ],
        "speaker_color": town.get("speaker_color", "#8b939c"),
        "speaker_head": town.get("speaker_head", "#d8d5cf"),
    }


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
