"""The engine's trace - instrumentation for the Spor panel + handbok."""

import json
from pathlib import Path

import pytest

from vefr import trace


def test_record_appends_and_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(trace, "_events", trace.deque(maxlen=trace.MAX_EVENTS))
    monkeypatch.setattr(trace, "file_path", lambda: tmp_path / "trace.jsonl")
    ev = trace.record("/api/rumor", ms=812.3, phase="whispers", speaker="the ferryman")
    assert ev["ok"] is True
    assert ev["ms"] == 812.3
    assert trace.recent() == [ev]
    lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(lines[0])["speaker"] == "the ferryman"


def test_recent_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(trace, "_events", trace.deque(maxlen=trace.MAX_EVENTS))
    monkeypatch.setattr(trace, "file_path", lambda: tmp_path / "t.jsonl")
    for i in range(5):
        trace.record("/api/rumor", ms=i, n=i)
    assert len(trace.recent(2)) == 2
    assert trace.recent(2)[-1]["n"] == 4
    assert trace.recent(0) == []


def test_span_records_ok_and_error(tmp_path, monkeypatch):
    monkeypatch.setattr(trace, "_events", trace.deque(maxlen=trace.MAX_EVENTS))
    monkeypatch.setattr(trace, "file_path", lambda: tmp_path / "t.jsonl")

    with trace.span("/api/rumor", phase="whispers") as sp:
        sp.set(speaker="the ferryman")

    with pytest.raises(RuntimeError):
        with trace.span("/api/npc", phase="doubts"):
            raise RuntimeError("the well was silent")

    events = trace.recent()
    assert events[0]["ok"] is True
    assert events[0]["speaker"] == "the ferryman"
    assert events[1]["ok"] is False
    assert "the well was silent" in events[1]["error"]
    # The span must re-raise, never swallow.
    assert events[1]["route"] == "/api/npc"


def test_span_never_breaks_persistence(tmp_path, monkeypatch):
    # A read-only trace file must not break the play it observes.
    monkeypatch.setattr(trace, "_events", trace.deque(maxlen=trace.MAX_EVENTS))
    monkeypatch.setattr(trace, "file_path", lambda: tmp_path / "no-dir" / "t.jsonl")
    monkeypatch.setattr(
        Path, "mkdir", lambda *a, **k: (_ for _ in ()).throw(OSError("read-only"))
    )
    with trace.span("/api/forge"):
        pass
    assert len(trace.recent()) == 1  # in-memory ring still has it
