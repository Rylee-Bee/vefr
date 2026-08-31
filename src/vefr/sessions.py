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
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from .paths import app_home

DEFAULT = "default"

_SID_OK = re.compile(r"[A-Za-z0-9_-]{1,64}")


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
    """
    if is_default(sid):
        return base
    return base.with_name(f"{base.stem}-{clean(sid)}{base.suffix}")


def sessions_dir() -> Path:
    """Where per-session metadata lives."""
    return app_home() / "data" / "sessions"


def meta_path(sid: str) -> Path:
    return sessions_dir() / f"{clean(sid)}.meta.json"


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
