from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .forge import forge_item, keep_item, list_vault
from .generator import generate_rumor
from .paths import app_home

app = FastAPI(title="Old Name", version="0.1.0")
WEB = app_home() / "web"


class RumorRequest(BaseModel):
    phase: str = "whispers"
    theme: str | None = None


@app.get("/api/health")
def health():
    return {"ok": True, "service": "old-name"}


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


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
