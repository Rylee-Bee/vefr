"""Fork + rewind on the journal timeline.

Forking branches: journal[:at] + the vault are copied into a new
session, the current session untouched, the parent recorded. Rewind
cuts in place and stashes the tail for one undo inside the window.
"""

import json

import pytest

from vefr import forge, journal
from vefr.sessions import meta_path, read_meta


@pytest.fixture
def tmp_journal(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr(journal, "_LAST_REMOVED", {})
    monkeypatch.setattr(journal, "_LAST_REMOVED_AT", {})


def _seed(sid=None):
    journal.log("rumor", sid=sid, whisper="one")
    journal.log("rumor", sid=sid, whisper="two")
    journal.log("rumor", sid=sid, whisper="three")


def test_rewind_cuts_and_stashes(tmp_journal):
    _seed()
    result = journal.rewind(1)
    assert result == {"rewound_to": 1, "dropped": 2}
    assert [e["whisper"] for e in journal.list_entries()] == ["one"]
    stash = journal.journal_path().with_suffix(".rewind.json")
    assert stash.exists()
    tail = json.loads(stash.read_text(encoding="utf-8"))
    assert len(tail["entries"]) == 2


def test_rewind_undo_restores_within_window(tmp_journal):
    _seed()
    journal.rewind(1)
    restored = journal.rewind_undo()
    assert restored == {"restored": 2}
    assert len(journal.list_entries()) == 3
    assert not journal.journal_path().with_suffix(".rewind.json").exists()


def test_rewind_undo_outside_window_drops_stash(tmp_journal):
    _seed()
    journal.rewind(1)
    stash = journal.journal_path().with_suffix(".rewind.json")
    data = json.loads(stash.read_text(encoding="utf-8"))
    data["at"] = "2000-01-01T00:00:00+00:00"
    stash.write_text(json.dumps(data), encoding="utf-8")
    assert journal.rewind_undo() is None
    assert not stash.exists()
    assert len(journal.list_entries()) == 1


def test_rewind_out_of_range(tmp_journal):
    _seed()
    assert journal.rewind(99) is None
    assert journal.rewind(-1) is None


def test_fork_copies_entries_and_vault(tmp_journal, tmp_path, monkeypatch):
    monkeypatch.setattr(forge, "VAULT", tmp_path / "vault.json")
    from vefr.forge import ItemCard

    _seed("s1")
    forge.keep_item(
        ItemCard(name="knife", kind="tool", bond="assigned", lore="heavy"),
        sid="s1",
    )

    from vefr.main import journal_fork

    req = type("F", (), {"at": 2})()
    result = journal_fork(req, session="s1")

    new_sid = result["session"]
    assert result["parent"] == "s1"
    assert result["fork_at"] == 2
    assert result["url"] == f"/?session={new_sid}"

    # The fork's journal: two kept entries + the fork entry that
    # says where it came from.
    entries = journal.list_entries(sid=new_sid)
    assert [e["whisper"] for e in entries[:2]] == ["one", "two"]
    assert entries[2]["kind"] == "fork"
    assert entries[2]["parent"] == "s1"
    # The fork count is 3: two whispers + the fork marker.
    assert len(entries) == 3

    # The vault was copied; the parent session is untouched.
    assert len(forge.list_vault(sid=new_sid)) == 1
    assert len(forge.list_vault(sid="s1")) == 1
    assert len(journal.list_entries(sid="s1")) == 3

    meta = read_meta(new_sid)
    assert meta["parent"] == "s1"
    assert meta["fork_at"] == 2
    assert meta_path(new_sid).exists()


def test_fork_from_default_names_it(tmp_journal):
    _seed()
    from vefr.main import journal_fork

    req = type("F", (), {"at": 1})()
    result = journal_fork(req, session="")
    assert result["parent"] == "default"
    assert result["kept"] == 1
    fork_entry = journal.list_entries(sid=result["session"])[1]
    assert "default playthrough" in fork_entry["note"]


def test_fork_at_zero_starts_blank(tmp_journal, tmp_path, monkeypatch):
    monkeypatch.setattr(forge, "VAULT", tmp_path / "vault.json")
    _seed("s1")
    from vefr.main import journal_fork

    req = type("F", (), {"at": 0})()
    result = journal_fork(req, session="s1")
    entries = journal.list_entries(sid=result["session"])
    # No whispers carried - only the fork marker itself.
    assert len(entries) == 1
    assert entries[0]["kind"] == "fork"
    assert forge.list_vault(sid=result["session"]) == []
