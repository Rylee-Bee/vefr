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

JOURNAL = Path(
    os.environ.get("VEFR_JOURNAL", str(app_home() / "data" / "journal.json"))
)

KINDS = ("rumor", "npc_line", "item_forged", "stefna_letter")

# How long a `remove()`'d entry stays recoverable. One minute gives
# the player a real undo window for a fat-fingered delete, without
# keeping dead state around forever. After UNDO_WINDOW_S the stash
# is dropped on the next `undo()` call.
UNDO_WINDOW_S = 60

# Module-level stash of the most recently removed entry. Single-slot
# is the design: undo is "I just clicked the wrong button", not a
# full undo stack. A second remove overwrites the first.
_LAST_REMOVED: dict | None = None
_LAST_REMOVED_AT: float | None = None


def _load() -> list[dict]:
    if not JOURNAL.exists():
        return []
    try:
        entries = json.loads(JOURNAL.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # A half-written or hand-edited journal must never take the
        # game down: an unreadable log reads as an empty one.
        return []
    return entries if isinstance(entries, list) else []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _touch_living_tree() -> None:
    # Local import: export.py imports FROM this module, so a
    # module-level import here would be circular. Failures are
    # swallowed inside refresh_living_tree() itself - a stale or
    # missing living-tree file must never break a journal write.
    from .export import refresh_living_tree

    refresh_living_tree()


def log(kind: str, **fields) -> dict:
    """Append one timestamped entry and return it."""
    entry = {"at": _now(), "kind": kind}
    entry.update(fields)
    entries = _load()
    entries.append(entry)
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    tmp = JOURNAL.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    tmp.replace(JOURNAL)
    _touch_living_tree()
    return entry


def list_entries() -> list[dict]:
    """Every entry, oldest first. An absent journal is an empty one."""
    return _load()


def remove(index: int) -> dict | None:
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
    global _LAST_REMOVED, _LAST_REMOVED_AT
    entries = _load()
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
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    tmp = JOURNAL.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    tmp.replace(JOURNAL)
    # Stash for undo - keep the original index so undo restores
    # position too when possible, otherwise append to the end.
    _LAST_REMOVED = {"entry": target, "index": index}
    _LAST_REMOVED_AT = time.monotonic()
    _touch_living_tree()
    return target


def undo() -> dict | None:
    """Restore the most recently removed entry, if still in window.

    Returns the restored entry, or None if no remove has happened
    in the last UNDO_WINDOW_S seconds (or at all).
    """
    global _LAST_REMOVED, _LAST_REMOVED_AT
    if _LAST_REMOVED is None or _LAST_REMOVED_AT is None:
        return None
    if time.monotonic() - _LAST_REMOVED_AT > UNDO_WINDOW_S:
        _LAST_REMOVED = None
        _LAST_REMOVED_AT = None
        return None
    entry = _LAST_REMOVED["entry"]
    original_index = _LAST_REMOVED["index"]
    entries = _load()
    # Insert at the original index, clamped to the current length.
    insert_at = min(original_index, len(entries))
    entries.insert(insert_at, entry)
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    tmp = JOURNAL.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    tmp.replace(JOURNAL)
    _LAST_REMOVED = None
    _LAST_REMOVED_AT = None
    _touch_living_tree()
    return entry


def clear() -> None:
    """Start a fresh playthrough - the journal is forgotten."""
    global _LAST_REMOVED, _LAST_REMOVED_AT
    if JOURNAL.exists():
        JOURNAL.unlink()
    _LAST_REMOVED = None
    _LAST_REMOVED_AT = None
    _touch_living_tree()
