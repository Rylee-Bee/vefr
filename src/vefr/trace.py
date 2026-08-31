"""The engine's trace - what actually ran, kept so the author can see it.

Every model-generation call (rumor, npc, stefna, forge) records one
event: when, how long, what shaped it (phase, speaker, lore pack),
and whether it landed. The trace is the raw material for two
consumers: the Spor panel in the dev UI (live, in-memory) and
`norns handbok` (persistent - the JSONL file survives restarts, so
a session's trace can be walked after the fact to write mechanics
documentation from real play).

The trace is instrumentation, not story. It never enters the
journal, the export, or the world tree; the packaged game has no
server and therefore no trace at all.
"""

import json
import os
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from .paths import app_home

MAX_EVENTS = 500
MAX_FILE_BYTES = 2_000_000

_events: deque = deque(maxlen=MAX_EVENTS)


def file_path() -> Path:
    env = os.environ.get("VEFR_TRACE")
    if env:
        return Path(env)
    return app_home() / "data" / "trace.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _persist(ev: dict) -> None:
    """Append one event to the JSONL. Failures are swallowed - the
    trace must never break the play it observes."""
    try:
        p = file_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and p.stat().st_size > MAX_FILE_BYTES:
            p.replace(p.with_suffix(".old.jsonl"))
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except OSError:
        pass


def record(route: str, ms: float, ok: bool = True, **detail) -> dict:
    ev = {
        "at": _now(),
        "route": route,
        "ms": round(ms, 1),
        "ok": ok,
    }
    ev.update(detail)
    _events.append(ev)
    _persist(ev)
    return ev


def recent(limit: int = 100) -> list[dict]:
    """The newest events, oldest first."""
    if limit <= 0:
        return []
    return list(_events)[-limit:]


class span:
    """Time one engine call and record the outcome.

    with trace.span("/api/rumor", phase="whispers") as sp:
        card = generate_rumor(...)
        sp.set(speaker=card.speaker)

    An exception marks the event not-ok with the error text and is
    re-raised - recording never swallows.
    """

    def __init__(self, route: str, **detail):
        self.route = route
        self.detail = detail
        self._t0 = time.perf_counter()

    def set(self, **detail) -> None:
        self.detail.update(detail)

    def __enter__(self) -> "span":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        ms = (time.perf_counter() - self._t0) * 1000.0
        if exc is not None:
            record(self.route, ms=ms, ok=False, error=str(exc)[:200], **self.detail)
        else:
            record(self.route, ms=ms, **self.detail)
        return False
