import json
import os
from pathlib import Path

import httpx
from pydantic import BaseModel, ValidationError

from .generator import KEEP_ALIVE, MODEL, OLLAMA_URL
from .paths import app_home

VAULT = Path(os.environ.get("MUNR_VAULT", str(app_home() / "data" / "vault.json")))


class ItemCard(BaseModel):
    name: str
    kind: str
    bond: str  # assigned | attuned | cold
    enchant: str | None = None
    curse: str | None = None
    lore: str


SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "kind": {"type": "string"},
        "bond": {"type": "string", "enum": ["assigned", "attuned", "cold"]},
        "enchant": {"type": "string"},
        "curse": {"type": "string"},
        "lore": {"type": "string"},
    },
    "required": ["name", "kind", "bond", "lore"],
}


def build_payload() -> dict:
    return {
        "model": MODEL,
        "system": _system(),
        "prompt": (
            "Forge ONE item from the world of the world bible - a sword, "
            "a hammer, a ribbon, a ledger-clasp, whatever the world would "
            "put in her hands. Decide its bond honestly: the assigned ones "
            "are common, the attuned ones are rare, and rarity is the "
            "point. Reply with only the JSON object."
        ),
        "format": SCHEMA,
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": 0.95},
    }


def _system() -> str:
    from .bonds import bond_prompt
    from .style import system_prompt

    return system_prompt("whispers") + (
        "\n\nYou are now the forge. Items carry the world's texture: "
        "ledger paper, bog iron, river glass, bell-metal. Names are "
        "kenning-flavored. Curses are quiet, never gory - and an "
        "assigned item's curse is simply that it was never hers.\n\n"
        + bond_prompt()
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
