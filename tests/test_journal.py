"""The journal - pure file I/O, no model, no network.

Every test points the journal at tmp_path, so a real playthrough on
disk is never touched.
"""

import json

import pytest

from vefr import journal


@pytest.fixture()
def log_file(tmp_path, monkeypatch):
    path = tmp_path / "data" / "journal.json"
    monkeypatch.setattr(journal, "JOURNAL", path)
    return path


def test_missing_journal_reads_as_empty(log_file):
    assert not log_file.exists()
    assert journal.list_entries() == []


def test_log_appends_in_order_and_persists(log_file):
    journal.log("rumor", speaker="Katla", whisper="the mill ran dry", is_true=True)
    journal.log("npc_line", speaker="the ferryman", line="stay off the reeds")
    journal.log("item_forged", name="The Ledger-Ribbon", bond="attuned", lore="tied once")
    journal.log("stefna_letter", letter="For you.\n\nbring the pail in")

    entries = journal.list_entries()
    assert [e["kind"] for e in entries] == [
        "rumor",
        "npc_line",
        "item_forged",
        "stefna_letter",
    ]
    assert entries[0]["speaker"] == "Katla"
    assert entries[3]["letter"].startswith("For you.")

    # the same list is on disk, and no tmp file was left behind
    on_disk = json.loads(log_file.read_text(encoding="utf-8"))
    assert on_disk == entries
    assert not log_file.with_suffix(".tmp").exists()


def test_log_returns_the_entry_with_a_timestamp(log_file):
    entry = journal.log("rumor", speaker="Katla", whisper="a whisper", is_true=False)
    assert entry["kind"] == "rumor"
    assert entry["is_true"] is False
    assert "at" in entry
    # UTC ISO, parseable
    from datetime import datetime

    parsed = datetime.fromisoformat(entry["at"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_clear_removes_the_file_and_is_safe_when_absent(log_file):
    journal.log("rumor", speaker="Katla", whisper="a whisper", is_true=True)
    assert log_file.exists()
    journal.clear()
    assert not log_file.exists()
    assert journal.list_entries() == []
    journal.clear()  # already gone - never raises


def test_a_corrupt_journal_reads_as_empty(log_file):
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("{ not json at all", encoding="utf-8")
    assert journal.list_entries() == []
    # and logging heals it back into a valid list
    journal.log("rumor", speaker="Katla", whisper="again", is_true=True)
    assert len(journal.list_entries()) == 1


def test_every_hooked_kind_is_a_known_kind():
    assert set(journal.KINDS) == {
        "rumor",
        "npc_line",
        "item_forged",
        "stefna_letter",
        "move",
        "fork",
    }
