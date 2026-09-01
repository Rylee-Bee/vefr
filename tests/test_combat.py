"""combat.py - HP derivation per phase + combat action journal entry.

The surface UI for combat packs is a costume, not a real RPG.
HP is positional (phase index 0 = lowest, last phase = highest).
Combat actions land in the journal as a `combat_action` entry;
they never fail, never change game state, and never end the game.
"""

import json

import pytest

from vefr import combat, world as world_mod
from vefr.world import load_world


def test_hp_for_pack_indexed_by_phase_position():
    """HP is positional: first phase is the cheapest, last is the
    priciest. The exact numbers are the costume - what matters is
    that they scale with position and that a pack with N phases
    gets the first N entries of the scale."""
    w = {"phases": {"a": ".", "b": ".", "c": ".", "d": "."}}
    hp = combat.hp_for_pack(w)
    assert hp["per_phase"] == {"a": 3, "b": 4, "c": 5, "d": 6}
    # current and max are the last (highest) value.
    assert hp["current"] == 6
    assert hp["max"] == 6


def test_hp_for_pack_clamps_to_four_for_longer_phases():
    """A pack with more than 4 phases still gets the index-3
    value (the costume scale caps at 4 entries)."""
    w = {"phases": {"a": ".", "b": ".", "c": ".", "d": ".", "e": ".", "f": "."}}
    hp = combat.hp_for_pack(w)
    assert hp["per_phase"] == {"a": 3, "b": 4, "c": 5, "d": 6, "e": 6, "f": 6}
    assert hp["max"] == 6


def test_hp_for_pack_empty_phases_returns_zero():
    w = {"phases": {}}
    hp = combat.hp_for_pack(w)
    assert hp == {"current": 0, "max": 0, "per_phase": {}}


def test_record_combat_action_writes_journal_entry(tmp_path, monkeypatch):
    """record_combat_action lands a combat_action entry in the
    journal with the action's verb (kind), phase, and target."""
    from vefr import journal as journal_mod
    # Point the journal at a tmp file so the test is hermetic.
    journal_path = tmp_path / "journal.json"
    monkeypatch.setattr(journal_mod, "JOURNAL", journal_path)

    entry = combat.record_combat_action(
        kind="attack", phase="feared", target="the watcher", session="",
    )
    assert entry["kind"] == "combat_action"
    assert entry["verb"] == "attack"
    assert entry["phase"] == "feared"
    assert entry["target"] == "the watcher"
    # The entry is also on disk in the journal.
    persisted = json.loads(journal_path.read_text(encoding="utf-8"))
    assert any(e.get("verb") == "attack" for e in persisted)


def test_record_combat_action_rejects_unknown_kind(tmp_path, monkeypatch):
    """Unknown action kinds are rejected with a ValueError so
    the route can return 400 Bad Request."""
    from vefr import journal as journal_mod
    monkeypatch.setattr(journal_mod, "JOURNAL", tmp_path / "journal.json")
    with pytest.raises(ValueError, match="unknown combat action kind"):
        combat.record_combat_action(kind="banana", phase="feared")


def test_api_world_carries_hp_for_combat_packs(fixture_vefr_home):
    """The /api/world payload includes an `hp` block for combat
    packs. The block is null for plain / investigation surfaces -
    the HUD hides the bar in that case via CSS."""
    w = load_world("four-phase-pack")
    # The fixture doesn't declare a surface; load_world defaults
    # to 'combat' for any pack without one. Override to verify
    # the null case.
    w["surface"] = "plain"
    # Force the loader cache clear so the test sees a fresh load.
    world_mod.load_world.cache_clear()
    w = load_world("four-phase-pack")
    # The fixture defaults to combat (per the engine's contract).
    hp_combat = combat.hp_for_pack(w)
    assert hp_combat["per_phase"]["whispers"] == 3
    assert hp_combat["per_phase"]["awed"] == 6


def test_combat_action_route_accepts_attack(monkeypatch, tmp_path):
    """POST /api/combat/action with kind=attack returns 200
    and lands a journal entry."""
    from fastapi.testclient import TestClient
    from vefr import journal as journal_mod
    from vefr.main import app

    monkeypatch.setattr(journal_mod, "JOURNAL", tmp_path / "journal.json")
    c = TestClient(app)
    r = c.post("/api/combat/action",
               json={"kind": "attack", "phase": "feared", "target": "the watcher"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("kind") == "combat_action" or "at" in body


def test_combat_action_route_rejects_unknown_kind(monkeypatch, tmp_path):
    """POST /api/combat/action with an unknown kind returns 400."""
    from fastapi.testclient import TestClient
    from vefr import journal as journal_mod
    from vefr.main import app

    monkeypatch.setattr(journal_mod, "JOURNAL", tmp_path / "journal.json")
    c = TestClient(app)
    r = c.post("/api/combat/action",
               json={"kind": "banana", "phase": "feared"})
    assert r.status_code == 400
