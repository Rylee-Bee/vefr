"""The edit log - the studio's private record of kept edits, and EDITS.md.

Two places, one per kept edit (design/named-edits.md, decided 2026-10-01):

  data/edits.jsonl   the full private log in the studio's data dir
                     (paths.data_dir(), the same helper achievements uses).
                     One JSON line per KEPT edit; a preview writes none.
                     It carries a human `note` so the summary and undo can
                     speak the exact same sentence from the log alone.

  <pack>/EDITS.md    a short readable summary inside the game folder. It is
                     a PACK-CONTRACT ADDITION: a pack with no EDITS.md is
                     unchanged, and one that already has it is never rewritten
                     from scratch. We APPEND one line per kept edit and never
                     rebuild, so a hand-written EDITS.md survives. Undo removes
                     exactly the last line that matches the one it added.

Plain files, no database. No model call lives here.
"""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from .paths import data_dir

_lock = threading.Lock()

# A backup name made by main._backup_map_file(): <name>.bak-YYYYmmdd-HHMMSS,
# with a -N suffix when a fast second write collided. Undo strips it to find
# the file the backup came from.
_BACKUP_SUFFIX = re.compile(r"\.bak-\d{8}-\d{6}(?:-\d+)?$")

SUMMARY_FILE = "EDITS.md"


def _log_path() -> Path:
    return data_dir() / "edits.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def summary(entry: dict) -> str:
    """The one readable line an edit contributes to EDITS.md.

    The date leads, so the file reads as a short change history. `note` is
    written with the edit; `edit` is the fallback when an old line has none.
    """
    day = str(entry.get("ts", ""))[:10]
    return f"{day}: {entry.get('note') or entry.get('edit', 'edited the game')}"


def entries() -> list[dict]:
    """Every parsed log line, in order, silently skipping unreadable ones."""
    try:
        text = _log_path().read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _write_all(rows: list[dict]) -> None:
    """Rewrite the log atomically - a crash must not truncate it."""
    p = _log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in rows),
        encoding="utf-8",
    )
    os.replace(tmp, p)


def append_summary(pack: Path, entry: dict) -> None:
    """Add one line to the pack's EDITS.md, never rewriting what is there.

    Appending (not rebuilding) is the chosen behaviour: a pack whose EDITS.md
    was hand-edited keeps its words, and a second edit never corrupts the file
    it grew from. Undo removes the exact line it added (drop_summary).
    """
    path = Path(pack) / SUMMARY_FILE
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError:
        existing = ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + summary(entry) + "\n", encoding="utf-8")


def drop_summary(pack: Path, entry: dict) -> None:
    """Remove the last line EDITS.md gained for `entry`; delete it when empty."""
    path = Path(pack) / SUMMARY_FILE
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    line = summary(entry)
    lines = text.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if lines[i] == line:
            del lines[i]
            break
    rest = "\n".join(lines)
    if rest.strip():
        path.write_text(rest + "\n", encoding="utf-8")
    else:
        try:
            path.unlink()
        except OSError:
            pass


def record(
    who: str,
    edit: str,
    world: str,
    files: list[str],
    backup: str | None,
    note: str,
    pack: Path,
) -> dict:
    """Log one kept edit and add its summary line. Returns the log entry."""
    entry = {
        "ts": _now(),
        "who": who,
        "edit": edit,
        "world": world,
        "files": list(files),
        "backup": backup,
        "note": note,
    }
    with _lock:
        p = _log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    append_summary(pack, entry)
    return entry


def last_for(world: str) -> dict | None:
    """The most recent kept edit for one world, or None."""
    rows = entries()
    for entry in reversed(rows):
        if entry.get("world") == world:
            return entry
    return None


def drop_last(world: str) -> dict | None:
    """Remove and return the most recent kept edit for one world."""
    with _lock:
        rows = entries()
        idx = None
        for i in range(len(rows) - 1, -1, -1):
            if rows[i].get("world") == world:
                idx = i
                break
        if idx is None:
            return None
        entry = rows.pop(idx)
        _write_all(rows)
        return entry


def backup_source(backup_rel: str) -> str | None:
    """The pack-relative file a backup name came from, or None.

    `world.json.bak-20261001-120000` -> `world.json`; a name this studio did
    not make (no .bak-<stamp> suffix) returns None so undo refuses it.
    """
    stripped = _BACKUP_SUFFIX.sub("", backup_rel)
    return stripped if stripped != backup_rel else None
