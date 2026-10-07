"""Per-session play state.

The journal and the vault are keyed by an optional ?session=<id>
query parameter on the API. No parameter (or "default") resolves to
the exact pre-session files - VEFR_JOURNAL / VEFR_VAULT or their
defaults - so a deployed quadlet keeps reading the journal it
already has, and every existing test, script, and import path keeps
working unchanged.

A named session derives sibling files: for VEFR_JOURNAL=/app/data/
journal.json, session "a1b2c3d4" reads/writes journal-a1b2c3.json.
Sessions are browser-minted (the page's New game button), so ids
are short hex strings; anything that is not [A-Za-z0-9_-]{1,64}
falls back to the default session rather than becoming a path.

Session ids are not identity and carry no secrets - they are a
label on a playthrough, nothing more.
"""

import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .paths import data_dir, resolve_under

DEFAULT = "default"
UNDO_WINDOW_S = 60

_SID_OK = re.compile(r"[A-Za-z0-9_-]{1,64}")


class UndoBuffer:
    """Shared single-slot, time-bounded undo buffer for journal and vault removals."""

    def __init__(self, window_s: float = UNDO_WINDOW_S):
        self.window_s = window_s
        self._stash: dict[str, dict] = {}
        self._stash_at: dict[str, float] = {}

    def remove(
        self,
        index: int,
        load_fn: Callable[[str | None], list[dict]],
        save_fn: Callable[[list[dict], str | None], None],
        sid: str | None = None,
        touch_fn: Callable[[str | None], None] | None = None,
    ) -> dict | None:
        key = clean(sid)
        items = load_fn(sid)
        if index < 0 or index >= len(items):
            return None
        target = items[index]
        del items[index]
        save_fn(items, sid)
        self._stash[key] = {"item": target, "index": index}
        self._stash_at[key] = time.monotonic()
        if touch_fn:
            touch_fn(sid)
        return target

    def undo(
        self,
        load_fn: Callable[[str | None], list[dict]],
        save_fn: Callable[[list[dict], str | None], None],
        sid: str | None = None,
        touch_fn: Callable[[str | None], None] | None = None,
    ) -> dict | None:
        key = clean(sid)
        stash = self._stash.get(key)
        stash_at = self._stash_at.get(key)
        if stash is None or stash_at is None:
            return None
        if time.monotonic() - stash_at > self.window_s:
            self._stash.pop(key, None)
            self._stash_at.pop(key, None)
            return None
        item = stash.get("item") if "item" in stash else stash.get("entry")
        original_index = stash["index"]
        items = load_fn(sid)
        insert_at = min(original_index, len(items))
        items.insert(insert_at, item)
        save_fn(items, sid)
        self._stash.pop(key, None)
        self._stash_at.pop(key, None)
        if touch_fn:
            touch_fn(sid)
        return item

    def clear(self, sid: str | None = None) -> None:
        key = clean(sid)
        self._stash.pop(key, None)
        self._stash_at.pop(key, None)


def clean(sid: str | None) -> str:
    """A session label safe to put in a filename."""
    return sid if sid and _SID_OK.fullmatch(sid) else DEFAULT


def is_default(sid: str | None) -> bool:
    """True when no session was asked for."""
    return not sid or sid == DEFAULT


def new_id() -> str:
    """A fresh playthrough label."""
    return secrets.token_hex(4)


def derive(base: Path, sid: str | None) -> Path:
    """The per-session file for a base path; the base itself when default.

    journal.json -> journal-<sid>.json, sitting beside it. Explicit
    VEFR_* env paths derive the same way, so the quadlet's mounted
    data dir keeps holding every session.

    clean() is what keeps an id a filename - anything with a
    separator, a dot or over 64 chars falls back to the default
    session. resolve_under() is the second layer over the join
    itself: a bare relative base ("journal.json", relative cwd) has
    no directory to check against and no separator to climb out
    with, so it keeps with_name's answer.
    """
    if is_default(sid):
        return base
    name = f"{base.stem}-{clean(sid)}{base.suffix}"
    if base.parent == Path() and not os.path.isabs(base):
        return base.with_name(name)
    return resolve_under(base.parent, name)


def sessions_dir() -> Path:
    """Where per-session metadata lives."""
    return data_dir() / "sessions"


def meta_path(sid: str) -> Path:
    return resolve_under(data_dir(), "sessions", f"{clean(sid)}.meta.json")


def write_meta(sid: str, meta: dict) -> None:
    """Persist one session's metadata, atomic tmp+replace like the journal."""
    p = meta_path(sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    tmp.replace(p)


def read_meta(sid: str) -> dict:
    """A session's metadata, or {} - absent and unreadable read the same."""
    p = meta_path(sid)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
