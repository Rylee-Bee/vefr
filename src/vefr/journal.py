"""The session journal - what actually happened, kept on disk.

The vault remembers things carried. The journal remembers the rest:
rumors heard, lines spoken, items forged, the letter if the Stefna
was reached. One flat JSON list, appended to, written the same
atomic tmp+replace way the vault is written - a crash mid-write can
lose the newest entry, never the whole playthrough.

The engine owns the shape; the world owns nothing here. An entry is
always {"at": <UTC ISO>, "kind": <str>, ...fields}.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from .paths import app_home
from .sessions import clean, derive

JOURNAL = Path(
    os.environ.get("VEFR_JOURNAL", str(app_home() / "data" / "journal.json"))
)

KINDS = ("rumor", "npc_line", "item_forged", "stefna_letter")

# How long a `remove()`'d entry stays recoverable. One minute gives
# the player a real undo window for a fat-fingered delete, without
# keeping dead state around forever. After UNDO_WINDOW_S the stash
# is dropped on the next `undo()` call.
UNDO_WINDOW_S = 60

# Per-session stash of the most recently removed entry, keyed by the
# cleaned session id. Single-slot per session is the design: undo is
# "I just clicked the wrong button", not a full undo stack. A second
# remove in the same session overwrites that session's stash.
_LAST_REMOVED: dict[str, dict] = {}
_LAST_REMOVED_AT: dict[str, float] = {}


def journal_path(sid: str | None = None) -> Path:
    """The journal file for a session; the base file when default."""
    return derive(JOURNAL, sid)


def _load(sid: str | None = None) -> list[dict]:
    path = journal_path(sid)
    if not path.exists():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # A half-written or hand-edited journal must never take the
        # game down: an unreadable log reads as an empty one.
        return []
    return entries if isinstance(entries, list) else []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _touch_living_tree(sid: str | None = None) -> None:
    # Local import: export.py imports FROM this module, so a
    # module-level import here would be circular. Failures are
    # swallowed inside refresh_living_tree() itself - a stale or
    # missing living-tree file must never break a journal write.
    from .export import refresh_living_tree

    refresh_living_tree(sid=sid)


def log(kind: str, sid: str | None = None, **fields) -> dict:
    """Append one timestamped entry and return it."""
    entry = {"at": _now(), "kind": kind}
    entry.update(fields)
    entries = _load(sid)
    entries.append(entry)
    path = journal_path(sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    tmp.replace(path)
    _touch_living_tree(sid)
    return entry


def list_entries(sid: str | None = None) -> list[dict]:
    """Every entry, oldest first. An absent journal is an empty one."""
    return _load(sid)


def remove(index: int, sid: str | None = None) -> dict | None:
    """Remove the entry at `index` and stash it for undo().

    Returns None if the index is out of range. Refuses to remove the
    last entry of its kind (a soft invariant: every kind the
    engine writes must remain represented in the journal, so an
    empty journal never pretends a kind never existed). The author
    can still clear the whole journal via `clear()` if they want
    a true wipe.

    Each remove() stashes exactly one entry; calling remove() again
    before the undo window expires overwrites the previous stash.
    """
    key = clean(sid)
    entries = _load(sid)
    if index < 0 or index >= len(entries):
        return None
    target = entries[index]
    kind = target.get("kind", "")
    same_kind = sum(1 for e in entries if e.get("kind") == kind)
    if same_kind <= 1:
        raise ValueError(
            f"refusing to remove the last entry of kind {kind!r} - "
            f"use `clear()` for a full wipe, or star and edit by hand"
        )
    del entries[index]
    path = journal_path(sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    tmp.replace(path)
    # Stash for undo - keep the original index so undo restores
    # position too when possible, otherwise append to the end.
    _LAST_REMOVED[key] = {"entry": target, "index": index}
    _LAST_REMOVED_AT[key] = time.monotonic()
    _touch_living_tree(sid)
    return target


def undo(sid: str | None = None) -> dict | None:
    """Restore the most recently removed entry, if still in window.

    Returns the restored entry, or None if no remove has happened
    in the last UNDO_WINDOW_S seconds (or at all).
    """
    key = clean(sid)
    stash = _LAST_REMOVED.get(key)
    stash_at = _LAST_REMOVED_AT.get(key)
    if stash is None or stash_at is None:
        return None
    if time.monotonic() - stash_at > UNDO_WINDOW_S:
        _LAST_REMOVED.pop(key, None)
        _LAST_REMOVED_AT.pop(key, None)
        return None
    entry = stash["entry"]
    original_index = stash["index"]
    entries = _load(sid)
    # Insert at the original index, clamped to the current length.
    insert_at = min(original_index, len(entries))
    entries.insert(insert_at, entry)
    path = journal_path(sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    tmp.replace(path)
    _LAST_REMOVED.pop(key, None)
    _LAST_REMOVED_AT.pop(key, None)
    _touch_living_tree(sid)
    return entry


def clear(sid: str | None = None) -> None:
    """Start a fresh playthrough - the session's journal is forgotten."""
    path = journal_path(sid)
    if path.exists():
        path.unlink()
    key = clean(sid)
    _LAST_REMOVED.pop(key, None)
    _LAST_REMOVED_AT.pop(key, None)
    _touch_living_tree(sid)
