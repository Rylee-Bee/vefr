from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .generator import generate_rumor

app = FastAPI(title="Old Name", version="0.1.0")
WEB = Path(__file__).resolve().parents[2] / "web"


class RumorRequest(BaseModel):
    phase: str = "whispers"
    theme: str | None = None


@app.get("/api/health")
def health():
    return {"ok": True, "service": "old-name"}


@app.post("/api/rumor")
def rumor(req: RumorRequest):
    return generate_rumor(req.phase, req.theme)


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
