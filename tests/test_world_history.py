"""Each world keeps its own play history: kept items and whispers never
bleed between worlds (Rylee's walkthrough, 2026-09-26: Emberfield's old
whispers turned up in Cottage of the Breeze's Chronicle and world tree)."""

import pytest

from vefr import forge, journal, paths


@pytest.fixture()
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr(forge, "VAULT", tmp_path / "vault.json")
    # the living tree writes into a pack; not what's under test here
    monkeypatch.setattr(journal, "_touch_living_tree", lambda sid=None: None)
    return tmp_path


def _serve(monkeypatch, world):
    monkeypatch.setenv("VEFR_WORLD", world)


def test_legacy_world_keeps_the_base_files(data, monkeypatch):
    _serve(monkeypatch, paths.LEGACY_HISTORY_WORLD)
    assert journal.journal_path() == data / "journal.json"
    assert forge.vault_path() == data / "vault.json"


def test_other_worlds_get_their_own_files(data, monkeypatch):
    _serve(monkeypatch, "cottage-of-the-breeze")
    assert journal.journal_path() == data / "journal.cottage-of-the-breeze.json"
    assert forge.vault_path() == data / "vault.cottage-of-the-breeze.json"


def test_whispers_stay_in_their_world(data, monkeypatch):
    _serve(monkeypatch, "sample-world")
    journal.log("rumor", speaker="Ironfoot", whisper="from Emberfield")
    _serve(monkeypatch, "cottage-of-the-breeze")
    assert journal.entries() == []
    journal.log("rumor", speaker="The Keeper", whisper="from the Cottage")
    assert [e["whisper"] for e in journal.entries()] == ["from the Cottage"]
    _serve(monkeypatch, "sample-world")
    assert [e["whisper"] for e in journal.entries()] == ["from Emberfield"]


def test_sessions_nest_inside_the_world(data, monkeypatch):
    _serve(monkeypatch, "cottage-of-the-breeze")
    assert journal.journal_path("alpha").name == "journal.cottage-of-the-breeze-alpha.json"


def test_scoping_can_be_bypassed_for_explicit_files(data, monkeypatch):
    _serve(monkeypatch, "cottage-of-the-breeze")
    monkeypatch.setattr(journal, "SCOPE_BY_WORLD", False)
    assert journal.journal_path() == data / "journal.json"
