import json
import os
from pathlib import Path

import httpx
from pydantic import BaseModel, ValidationError

from .bonds import bond_keys, bond_prompt
from .generator import KEEP_ALIVE, MODEL, OLLAMA_URL
from .paths import app_home
from .saga import system_prompt
from .world import load_world

VAULT = Path(os.environ.get("MUNR_VAULT", str(app_home() / "data" / "vault.json")))


class ItemCard(BaseModel):
    name: str
    kind: str
    bond: str  # the pack's bond keys, in pack order
    enchant: str | None = None
    curse: str | None = None
    lore: str


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "kind": {"type": "string"},
            "bond": {"type": "string", "enum": bond_keys()},
            "enchant": {"type": "string"},
            "curse": {"type": "string"},
            "lore": {"type": "string"},
        },
        "required": ["name", "kind", "bond", "lore"],
    }


def build_payload() -> dict:
    texture = load_world().get(
        "forge_texture",
        "Items carry the world's texture. Curses are quiet, never gory.",
    )
    return {
        "model": MODEL,
        "system": _system(texture),
        "prompt": (
            "Forge ONE item from the world described below - whatever "
            "the world would put in the protagonist's hands. Decide its "
            "bond honestly: rarity is the point. Reply with only the "
            "JSON object."
        ),
        "format": _schema(),
        "stream": False,
        "think": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": 0.95},
    }


def _system(texture: str) -> str:
    return system_prompt("whispers") + (
        "\n\nYou are now the forge. " + texture + "\n\n" + bond_prompt()
    )


def forge_item() -> ItemCard:
    payload = build_payload()
    last_err: Exception | None = None
    for _ in range(2):
        r = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=180)
        r.raise_for_status()
        raw = json.loads(r.text)["response"]
        try:
            return ItemCard.model_validate_json(raw)
        except ValidationError as e:
            last_err = e
    raise RuntimeError(f"forge output failed schema twice: {last_err}")


def _load_vault() -> list[dict]:
    if not VAULT.exists():
        return []
    return json.loads(VAULT.read_text(encoding="utf-8"))


def keep_item(item: ItemCard) -> dict:
    vault = _load_vault()
    vault.append(item.model_dump())
    VAULT.parent.mkdir(parents=True, exist_ok=True)
    tmp = VAULT.with_suffix(".tmp")
    tmp.write_text(json.dumps(vault, indent=2), encoding="utf-8")
    tmp.replace(VAULT)
    return {"kept": True, "bond": item.bond, "count": len(vault)}


def list_vault() -> list[dict]:
    return _load_vault()
