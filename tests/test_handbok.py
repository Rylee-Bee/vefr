"""norns handbok - the mechanics manual generated from real play."""

import json

from vefr import journal, trace
from vefr.cli import cmd_handbok


def _fake_world(monkeypatch, pack):
    from vefr import world as world_mod

    monkeypatch.setattr(
        world_mod, "load_world",
        lambda name=None: json.loads((pack / "world.json").read_text(encoding="utf-8")),
    )


def test_handbok_writes_mechanics_and_examples(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr(trace, "file_path", lambda: tmp_path / "trace.jsonl")

    trace.record("/api/rumor", ms=812.0, phase="whispers", speaker="Old Sela")
    trace.record("/api/rumor", ms=900.0, phase="doubts", ok=False, error="cold")
    trace.record("/api/npc", ms=500.0, phase="whispers", speaker="Katla")
    journal.log("rumor", phase="whispers", speaker="Old Sela",
                whisper="the well remembers", is_true=True)
    journal.log("item_forged", name="knife", bond="assigned", lore="heavy")

    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "world.json").write_text(
        json.dumps({"title": "Testworld", "phases": {"whispers": ""}}),
        encoding="utf-8",
    )
    _fake_world(monkeypatch, pack)

    args = type("A", (), {"pack": str(pack), "session": None})()
    rc = cmd_handbok(args)
    assert rc == 0

    text = (pack / "handbok.md").read_text(encoding="utf-8")
    assert "# Testworld - handbok" in text
    assert "| /api/rumor | 2 | 856ms | 900ms | 1 |" in text
    assert "**whispers**" in text
    assert "the well remembers" in text
    assert "heavy" in text
    assert "- 1 rumor" in text


def test_handbok_without_trace_still_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr(trace, "file_path", lambda: tmp_path / "absent.jsonl")

    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "world.json").write_text(
        json.dumps({"title": "Empty", "phases": {}}), encoding="utf-8"
    )
    _fake_world(monkeypatch, pack)

    args = type("A", (), {"pack": str(pack), "session": None})()
    rc = cmd_handbok(args)
    assert rc == 0
    text = (pack / "handbok.md").read_text(encoding="utf-8")
    assert "No trace yet" in text
    assert "Nothing yet" in text
