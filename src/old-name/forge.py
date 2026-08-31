import json
import os
import time
from pathlib import Path

import httpx
from pydantic import BaseModel, ValidationError

from . import generator
from .bonds import bond_keys, bond_prompt
from .paths import app_home
from .saga import system_prompt
from .world import load_world

VAULT = Path(os.environ.get("NORN_VAULT", str(app_home() / "data" / "vault.json")))

UNDO_WINDOW_S = 60
_LAST_REMOVED: dict | None = None
_LAST_REMOVED_AT: float | None = None


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
        "model": generator.MODEL,
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
        "keep_alive": generator.KEEP_ALIVE,
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
        try:
            raw = generator._completion(payload)
            return ItemCard.model_validate_json(raw)
        except (httpx.HTTPError, ValidationError, KeyError, ValueError) as e:
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


def remove(index: int) -> dict | None:
    """Remove the kept item at `index` and stash it for undo().

    Vault items are the player's possessions, so removal is rarer
    than journal removal. Still: same single-slot, 60s undo window.
    """
    global _LAST_REMOVED, _LAST_REMOVED_AT
    items = _load_vault()
    if index < 0 or index >= len(items):
        return None
    target = items[index]
    del items[index]
    VAULT.parent.mkdir(parents=True, exist_ok=True)
    tmp = VAULT.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2), encoding="utf-8")
    tmp.replace(VAULT)
    _LAST_REMOVED = {"item": target, "index": index}
    _LAST_REMOVED_AT = time.monotonic()
    return target


def undo() -> dict | None:
    """Restore the most recently removed vault item, if still in window."""
    global _LAST_REMOVED, _LAST_REMOVED_AT
    if _LAST_REMOVED is None or _LAST_REMOVED_AT is None:
        return None
    if time.monotonic() - _LAST_REMOVED_AT > UNDO_WINDOW_S:
        _LAST_REMOVED = None
        _LAST_REMOVED_AT = None
        return None
    item = _LAST_REMOVED["item"]
    original_index = _LAST_REMOVED["index"]
    items = _load_vault()
    insert_at = min(original_index, len(items))
    items.insert(insert_at, item)
    VAULT.parent.mkdir(parents=True, exist_ok=True)
    tmp = VAULT.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2), encoding="utf-8")
    tmp.replace(VAULT)
    _LAST_REMOVED = None
    _LAST_REMOVED_AT = None
    return item
