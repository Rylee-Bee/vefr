"""Per-session play state: journal + vault keyed by ?session=<id>.

The default session must stay byte-for-byte compatible with the
pre-session files - the deployed quadlet reads VEFR_JOURNAL /
VEFR_VAULT and every script that ever touched those paths keeps
working. Named sessions derive sibling files and never see each
other's entries.
"""



from vefr import forge, journal
from vefr.sessions import DEFAULT, clean, derive, is_default, new_id


def test_derive_default_returns_base():
    base = journal.JOURNAL
    assert derive(base, None) == base
    assert derive(base, "") == base
    assert derive(base, DEFAULT) == base


def test_derive_named_sibling_file(tmp_path):
    base = tmp_path / "journal.json"
    p = derive(base, "a1b2c3d4")
    assert p == tmp_path / "journal-a1b2c3d4.json"
    assert p.parent == base.parent


def test_clean_falls_back_on_bad_ids():
    assert clean(None) == DEFAULT
    assert clean("") == DEFAULT
    assert clean("../evil") == DEFAULT
    assert clean("a" * 65) == DEFAULT
    assert clean("Good-Id_1") == "Good-Id_1"


def test_new_id_is_short_hex():
    sid = new_id()
    assert clean(sid) == sid
    assert len(sid) <= 16


def test_log_sessions_are_isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    journal.log("rumor", sid="s1", whisper="one")
    journal.log("rumor", sid="s2", whisper="two")
    journal.log("rumor", whisper="default")

    assert [e["whisper"] for e in journal.list_entries(sid="s1")] == ["one"]
    assert [e["whisper"] for e in journal.list_entries(sid="s2")] == ["two"]
    assert [e["whisper"] for e in journal.list_entries()] == ["default"]
    assert (tmp_path / "journal-s1.json").exists()
    assert (tmp_path / "journal-s2.json").exists()


def test_remove_undo_stashes_are_per_session(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    for sid in ("s1", "s2"):
        journal.log("rumor", sid=sid, whisper=f"{sid}-a")
        journal.log("rumor", sid=sid, whisper=f"{sid}-b")

    assert journal.remove(1, sid="s1")["whisper"] == "s1-b"
    # A remove in s1 must not touch s2's stash or entries.
    assert journal.undo(sid="s2") is None
    assert len(journal.list_entries(sid="s2")) == 2
    restored = journal.undo(sid="s1")
    assert restored["whisper"] == "s1-b"
    assert len(journal.list_entries(sid="s1")) == 2


def test_vault_sessions_are_isolated(tmp_path, monkeypatch):
    from vefr.forge import ItemCard

    monkeypatch.setattr(forge, "VAULT", tmp_path / "vault.json")
    card = ItemCard(name="knife", kind="tool", bond="assigned", lore="heavy")
    forge.keep_item(card, sid="s1")

    assert len(forge.list_vault(sid="s1")) == 1
    assert forge.list_vault(sid="s2") == []
    assert forge.list_vault() == []


def test_vault_remove_undo_per_session(tmp_path, monkeypatch):
    from vefr.forge import ItemCard

    monkeypatch.setattr(forge, "VAULT", tmp_path / "vault.json")
    card = ItemCard(name="knife", kind="tool", bond="assigned", lore="kept")
    forge.keep_item(card, sid="s1")
    forge.keep_item(card, sid="s1")

    assert forge.remove(0, sid="s1") is not None
    assert forge.undo(sid="s2") is None
    assert forge.undo(sid="s1") is not None
    assert len(forge.list_vault(sid="s1")) == 2


def test_api_journal_session_isolation(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    from vefr.main import app

    c = TestClient(app)
    r1 = c.post("/api/journal/remove/999", params={"session": "api1"})
    assert r1.status_code == 404  # empty session - nothing to remove

    # The rumor route calls the model, so journal directly through the
    # route shape instead: the isolation contract is the query param.
    import vefr.main as m

    m.journal.log("rumor", sid="api1", whisper="hello")
    got = c.get("/api/journal", params={"session": "api1"}).json()
    assert [e["whisper"] for e in got["entries"]] == ["hello"]
    assert c.get("/api/journal").json()["entries"] == []


def test_undo_buffer_helper():
    """Verify UndoBuffer helper independently."""
    from vefr.sessions import UndoBuffer
    buf = UndoBuffer(window_s=60)
    store = [{"id": "1"}, {"id": "2"}]

    def load_fn(sid):
        return list(store)

    def save_fn(items, sid):
        nonlocal store
        store = list(items)

    removed = buf.remove(0, load_fn=load_fn, save_fn=save_fn, sid="test-sid")
    assert removed == {"id": "1"}
    assert store == [{"id": "2"}]

    restored = buf.undo(load_fn=load_fn, save_fn=save_fn, sid="test-sid")
    assert restored == {"id": "1"}
    assert store == [{"id": "1"}, {"id": "2"}]


def test_is_default_and_env_paths_derive():
    assert is_default(None) and is_default("") and is_default(DEFAULT)
    assert not is_default("abc")
    base = journal.JOURNAL
    named = derive(base, "abc")
    assert named.stem.startswith(base.stem + "-")
    assert named.suffix == base.suffix
