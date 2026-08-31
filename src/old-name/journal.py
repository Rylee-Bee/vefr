"""The session journal - what actually happened, kept on disk.

The vault remembers things carried. The journal remembers the rest:
rumors heard, lines spoken, items forged, the bell's letter if the
bell was reached. One flat JSON list, appended to, written the same
atomic tmp+replace way the vault is written - a crash mid-write can
lose the newest entry, never the whole playthrough.

The engine owns the shape; the world owns nothing here. An entry is
always {"at": <UTC ISO>, "kind": <str>, ...fields}.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .paths import app_home

JOURNAL = Path(
    os.environ.get("NORN_JOURNAL", str(app_home() / "data" / "journal.json"))
)

KINDS = ("rumor", "npc_line", "item_forged", "bell_letter")


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
    return entry


def list_entries() -> list[dict]:
    """Every entry, oldest first. An absent journal is an empty one."""
    return _load()


def clear() -> None:
    """Start a fresh playthrough - the journal is forgotten."""
    if JOURNAL.exists():
        JOURNAL.unlink()
