import json
import os
import time
from pathlib import Path

import httpx
from pydantic import BaseModel, ValidationError

from . import generator
from .bonds import bond_keys, bond_prompt
from .paths import app_home
from .sessions import clean, derive
from .saga import system_prompt
from .world import load_world

VAULT = Path(os.environ.get("VEFR_VAULT", str(app_home() / "data" / "vault.json")))

UNDO_WINDOW_S = 60
_LAST_REMOVED: dict[str, dict] = {}
_LAST_REMOVED_AT: dict[str, float] = {}


def vault_path(sid: str | None = None) -> Path:
    """The vault file for a session; the base file when default."""
    return derive(VAULT, sid)


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


def _load_vault(sid: str | None = None) -> list[dict]:
    path = vault_path(sid)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def _touch_living_tree(sid: str | None = None) -> None:
    # Local import: export.py imports FROM this module, so a
    # module-level import here would be circular. Failures are
    # swallowed inside refresh_living_tree() itself.
    from .export import refresh_living_tree

    refresh_living_tree(sid=sid)


def keep_item(item: ItemCard, sid: str | None = None) -> dict:
    vault = _load_vault(sid)
    vault.append(item.model_dump())
    path = vault_path(sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(vault, indent=2), encoding="utf-8")
    tmp.replace(path)
    _touch_living_tree(sid)
    return {"kept": True, "bond": item.bond, "count": len(vault)}


def list_vault(sid: str | None = None) -> list[dict]:
    return _load_vault(sid)


def set_vault(items: list[dict], sid: str | None = None) -> None:
    """Replace a session's whole vault - the fork's write path."""
    path = vault_path(sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2), encoding="utf-8")
    tmp.replace(path)


def remove(index: int, sid: str | None = None) -> dict | None:
    """Remove the kept item at `index` and stash it for undo().

    Vault items are the player's possessions, so removal is rarer
    than journal removal. Still: same single-slot, 60s undo window.
    """
    key = clean(sid)
    items = _load_vault(sid)
    if index < 0 or index >= len(items):
        return None
    target = items[index]
    del items[index]
    path = vault_path(sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2), encoding="utf-8")
    tmp.replace(path)
    _LAST_REMOVED[key] = {"item": target, "index": index}
    _LAST_REMOVED_AT[key] = time.monotonic()
    _touch_living_tree(sid)
    return target


def undo(sid: str | None = None) -> dict | None:
    """Restore the most recently removed vault item, if still in window."""
    key = clean(sid)
    stash = _LAST_REMOVED.get(key)
    stash_at = _LAST_REMOVED_AT.get(key)
    if stash is None or stash_at is None:
        return None
    if time.monotonic() - stash_at > UNDO_WINDOW_S:
        _LAST_REMOVED.pop(key, None)
        _LAST_REMOVED_AT.pop(key, None)
        return None
    item = stash["item"]
    original_index = stash["index"]
    items = _load_vault(sid)
    insert_at = min(original_index, len(items))
    items.insert(insert_at, item)
    path = vault_path(sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2), encoding="utf-8")
    tmp.replace(path)
    _LAST_REMOVED.pop(key, None)
    _LAST_REMOVED_AT.pop(key, None)
    _touch_living_tree(sid)
    return item
