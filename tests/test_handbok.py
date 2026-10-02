"""norns handbok - the mechanics manual generated from real play.

Scoped to one pack, and honest about it: the trace names its world,
the journal is world-scoped, and a pack with no applicable history
fails closed rather than borrowing another world's numbers.
"""

import json

from vefr import journal, trace
from vefr.cli import cmd_handbok


def _pack(tmp_path, title="Testworld"):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "world.json").write_text(
        json.dumps({"title": title, "phases": {"whispers": ""}}),
        encoding="utf-8",
    )
    return pack


def _args(pack):
    return type("A", (), {"pack": str(pack), "session": None})()


def test_handbok_writes_mechanics_and_examples(tmp_path, monkeypatch):
    monkeypatch.setenv("VEFR_WORLD", "pack")
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr(trace, "file_path", lambda: tmp_path / "trace.jsonl")

    trace.record("/api/rumor", ms=812.0, phase="whispers", speaker="Old Sela")
    trace.record("/api/rumor", ms=900.0, phase="doubts", ok=False, error="cold")
    trace.record("/api/npc", ms=500.0, phase="whispers", speaker="Katla")
    journal.log("rumor", phase="whispers", speaker="Old Sela",
                whisper="the well remembers", is_true=True)
    journal.log("item_forged", name="knife", bond="assigned", lore="heavy")

    pack = _pack(tmp_path)
    rc = cmd_handbok(_args(pack))
    assert rc == 0

    text = (pack / "handbok.md").read_text(encoding="utf-8")
    assert "# Testworld - handbok" in text
    assert "| /api/rumor | 2 | 856ms | 900ms | 1 |" in text
    assert "**whispers**" in text
    assert "the well remembers" in text
    assert "heavy" in text
    assert "- 1 rumor" in text


def test_handbok_with_journal_but_no_trace_writes_a_shorter_manual(
        tmp_path, monkeypatch):
    monkeypatch.setenv("VEFR_WORLD", "pack")
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr(trace, "file_path", lambda: tmp_path / "absent.jsonl")

    journal.log("rumor", phase="whispers", whisper="the tide is out")
    pack = _pack(tmp_path)
    assert cmd_handbok(_args(pack)) == 0
    text = (pack / "handbok.md").read_text(encoding="utf-8")
    assert "No trace for this pack yet" in text
    assert "the tide is out" in text


def test_handbok_with_no_history_fails_closed(tmp_path, monkeypatch):
    # No applicable play history: no manual at all. UNKNOWN beats a
    # plausible-looking manual made of nothing.
    monkeypatch.setenv("VEFR_WORLD", "pack")
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr(trace, "file_path", lambda: tmp_path / "absent.jsonl")

    pack = _pack(tmp_path)
    assert cmd_handbok(_args(pack)) == 1
    assert not (pack / "handbok.md").exists()


def test_handbok_never_quotes_another_worlds_play(tmp_path, monkeypatch):
    # The cross-pack isolation regression: another world has rich
    # history. A handbok scoped to "pack" must not borrow any of it -
    # not its title, not its numbers, not its words.
    monkeypatch.setenv("VEFR_WORLD", "other")
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr(trace, "file_path", lambda: tmp_path / "trace.jsonl")

    trace.record("/api/rumor", ms=5000.0, phase="whispers")
    journal.log("rumor", phase="whispers", whisper="the other world's secret")

    pack = _pack(tmp_path, title="Testworld")
    monkeypatch.setenv("VEFR_WORLD", "pack")   # now handbok for "pack"
    assert cmd_handbok(_args(pack)) == 1
    assert not (pack / "handbok.md").exists()
