"""The weave log - the engine's own record of what it did, in order.

The trace module (trace.py) records API calls: who hit which route,
how long it took, what the model returned. The weave log is a
sibling: it records engine internals - the loader's discoveries,
the validator's findings, the build steps. Where the trace is
"what the player did," the weave is "what the engine did in
response."

The log is a JSONL file on disk (data/weave.jsonl) and a ring in
memory (last 500 events). It is exposed at /api/weave and rendered
in the builder's Weave tab. It is the source of truth for the
"what does the engine see?" question.

The log is fire-and-forget: every call is atomic, every entry is
self-contained, the file is append-only. A future session can
diff two logs to answer "what changed between this run and the
last one?" The handoff bundle (handoff.py) reads both this log
and the trace to assemble the full context for an AI-buddy
debugging handoff.
"""

import json
import os
import threading
import time
from collections import deque
from pathlib import Path

from .paths import app_home

RING_SIZE = 500
_file_lock = threading.Lock()
_ring_lock = threading.Lock()
_ring: deque = deque(maxlen=RING_SIZE)
_path: Path | None = None


def file_path() -> Path:
    """Where the JSONL log lives. data/weave.jsonl under the engine
    home, overridable with VEFR_WEAVE for testing."""
    global _path
    if _path is not None:
        return _path
    env = os.environ.get("VEFR_WEAVE")
    if env:
        _path = Path(env)
    else:
        _path = app_home() / "data" / "weave.jsonl"
    _path.parent.mkdir(parents=True, exist_ok=True)
    return _path


def reset_path_for_testing(path: Path | None) -> None:
    """Tests want a fresh log per scenario. Callers must also
    clear the ring."""
    global _path
    _path = path
    with _ring_lock:
        _ring.clear()


def weave(event: str, **fields) -> None:
    """Record one event. Best-effort: a logging failure never raises
    to the caller, because a logging failure must never break the
    engine. The fields are merged into the event's JSON body.

    Reserved keys (overwritten by this function, ignored if a
    caller passes them): 'event', 'at', 'pid'.
    """
    entry = {
        "event": event,
        "at": time.time(),
        "pid": os.getpid(),
    }
    entry.update(fields)
    with _ring_lock:
        _ring.append(entry)
    try:
        _append_line(entry)
    except OSError:
        # Disk full, permission denied, race with another process.
        # The ring still has the event; the file is best-effort.
        pass


def _append_line(entry: dict) -> None:
    line = json.dumps(entry, ensure_ascii=False)
    path = file_path()
    with _file_lock:
        # POSIX O_APPEND is atomic for files under 2GB on Linux,
        # so a single-line append is crash-safe: the kernel moves
        # the write offset to end-of-file before each write, and
        # the write itself is one syscall. The earlier
        # temp-file-then-rename pattern was atomic *but* it
        # overwrote the file with just the new entry, so the
        # on-disk log only ever had the last event. The ring kept
        # the full history; the file did not.
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
                f.write("\n")
        except OSError:
            raise


def recent(limit: int = 100) -> list[dict]:
    """Return the most recent events from the in-memory ring, newest
    first. Limit is clamped to RING_SIZE."""
    with _ring_lock:
        items = list(_ring)
    items.reverse()
    return items[:max(1, min(limit, RING_SIZE))]


def from_disk(limit: int = 200) -> list[dict]:
    """Read recent events from the JSONL file. Used for the handoff
    bundle and for the full-history view. Tolerant: a malformed
    line is skipped, not raised.
    """
    path = file_path()
    if not path.exists():
        return []
    out = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines()[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def clear() -> None:
    """Erase the on-disk log and the ring. Useful for tests; should
    not be called from production code paths."""
    global _path
    with _file_lock:
        path = file_path()
        if path.exists():
            path.unlink()
    with _ring_lock:
        _ring.clear()
