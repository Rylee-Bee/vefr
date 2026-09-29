"""The commission board: the studio-is-a-game loop, rules-only.

A resident posts a small commission, the maker accepts or defers it, and the
engine notices when the pack already satisfies it. These pins cover the
registry, the map-sketches rule, deferral persistence, and the three routes.
No network, no model call.
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vefr import commissions, maplab
from vefr import world as world_mod
from vefr.main import app

CARD_KEYS = {"id", "name", "resident", "room", "tier", "choosing", "home",
             "see_how", "offline", "done", "deferred", "ask"}


def _make_pack(root: Path, *, rows: list[str], pois: dict) -> Path:
    """A minimal acts-shape pack: enough for load_pack + the commission rule.

    `needs()` reads the unified town dict, so the pack needs the pack-level
    world.json, the act's world.json naming a region, and that region's
    contract.json + map.md. Nothing here is validated - the rule must hold
    on a bare pack.
    """
    (root / "acts" / "act-1" / "town").mkdir(parents=True)
    (root / "world.json").write_text(json.dumps({
        "name": root.name,
        "title": "Commission Test",
        "phases": {"dusk": "quiet", "dawn": "warm"},
        "voices": {},
    }), encoding="utf-8")
    (root / "acts" / "act-1" / "world.json").write_text(json.dumps({
        "id": "act-1", "title": "Commission Test", "regions": ["town"], "speakers": {},
    }), encoding="utf-8")
    (root / "acts" / "act-1" / "town" / "contract.json").write_text(json.dumps({
        "tile": 32,
        "bg": "#131311",
        "hero_start": [1, 1],
        "legend": {
            ".": {"base": ["#212a20"]},
            "p": {"base": ["#332e26"]},
            "#": {"base": ["#2a2e33"], "solid": True},
            "S": {"base": ["#212a20"], "deco": "gold"},
        },
        "pois": pois,
    }), encoding="utf-8")
    (root / "acts" / "act-1" / "town" / "map.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return root


@pytest.fixture
def commission_home(tmp_path, monkeypatch):
    """A temp home + active bare pack + a temp data dir, so no real state is touched."""
    pack = _make_pack(tmp_path / "home" / "worlds" / "commission-test",
                      rows=["###", "#.#", "###"], pois={})
    monkeypatch.setenv("VEFR_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("VEFR_WORLD", pack.name)
    monkeypatch.setenv("VEFR_DATA_DIR", str(tmp_path / "data"))
    world_mod.load_world.cache_clear()
    yield pack
    world_mod.load_world.cache_clear()


# --- the registry ------------------------------------------------------------

def test_every_module_declares_every_field():
    assert commissions.MODULES, "the board must offer at least one commission"
    for m in commissions.MODULES:
        assert isinstance(m, commissions.Module)
        for f in fields(commissions.Module):
            value = getattr(m, f.name)
            assert isinstance(value, str) and value.strip(), f"{m.id} is missing {f.name}"
        assert m.tier in commissions.TIERS
        assert m.resident.strip() and m.room.strip()


def test_module_lookup_by_id_and_unknown_is_keyerror():
    assert commissions.module("map-sketches").name == "Map sketches"
    with pytest.raises(KeyError):
        commissions.module("no-such-module")


# --- the rule ----------------------------------------------------------------

def test_bare_pack_leaves_the_commission_open(tmp_path):
    pack = _make_pack(tmp_path / "bare", rows=["###", "#.#", "###"], pois={})
    w = maplab.load_pack(pack)
    reason = commissions.needs(w)
    assert isinstance(reason, str) and reason.strip()
    assert commissions.state(w) == {"map-sketches": reason}


def test_a_marked_place_and_three_grounds_satisfy_the_commission(tmp_path):
    pack = _make_pack(tmp_path / "ready", rows=["###", "#.#", "#S#"], pois={})
    w = maplab.load_pack(pack)
    assert commissions.needs(w) is None
    assert commissions.state(w) == {"map-sketches": None}


def test_three_grounds_with_no_marked_place_leave_it_open(tmp_path):
    """A named `pois` entry needs a route the Map Room does not have; the mark
    that satisfies the commission must be one a maker can actually paint."""
    pack = _make_pack(tmp_path / "nomark", rows=["#p#", "#.#", "#.#"], pois={"1,1": "a landmark"})
    w = maplab.load_pack(pack)
    reason = commissions.needs(w)
    assert isinstance(reason, str) and "landmark" in reason


@pytest.mark.parametrize("w", [{}, {"town": {}}, {"town": {"map": ["#"], "legend": {}}},
                               {"town": {"map": ["#"], "legend": {"#": {}}, "pois": {"0,0": "x"}}}])
def test_needs_is_defensive_never_raises(w):
    reason = commissions.needs(w)
    assert isinstance(reason, str) and reason.strip()


# --- defer / resume ----------------------------------------------------------

def test_defer_and_resume_persist_under_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("VEFR_DATA_DIR", str(tmp_path / "data"))
    commissions.resume("map-sketches")  # start clean whatever ran before
    assert commissions.is_deferred("map-sketches") is False

    commissions.defer("map-sketches")
    assert commissions.is_deferred("map-sketches") is True
    store = tmp_path / "data" / "commissions.json"
    assert store.is_file()
    assert "map-sketches" in json.loads(store.read_text(encoding="utf-8"))["deferred"]

    commissions.resume("map-sketches")
    assert commissions.is_deferred("map-sketches") is False
    assert "map-sketches" not in json.loads(store.read_text(encoding="utf-8"))["deferred"]


def test_deferring_an_unknown_module_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("VEFR_DATA_DIR", str(tmp_path / "data"))
    with pytest.raises(KeyError):
        commissions.defer("no-such-module")


def test_a_done_commission_reads_done_even_if_it_was_deferred(tmp_path, monkeypatch):
    monkeypatch.setenv("VEFR_DATA_DIR", str(tmp_path / "data"))
    commissions.defer("map-sketches")
    pack = _make_pack(tmp_path / "ready", rows=["###", "#.#", "#S#"], pois={"1,1": "a landmark"})
    card = commissions.board(maplab.load_pack(pack))[0]
    assert card["done"] is True
    assert card["deferred"] is False


# --- the routes --------------------------------------------------------------

def test_commissions_route_returns_the_declared_shape(commission_home):
    r = TestClient(app).get("/api/builder/commissions")
    assert r.status_code == 200
    body = r.json()
    assert body["world"] == "commission-test"
    assert len(body["commissions"]) == 1
    card = body["commissions"][0]
    assert set(card) == CARD_KEYS
    assert card["id"] == "map-sketches"
    assert card["resident"] == "map" and card["room"] == "map"
    assert card["done"] is False and card["deferred"] is False
    assert card["ask"]


def test_defer_and_resume_routes(commission_home):
    client = TestClient(app)
    r = client.post("/api/builder/commissions/defer", json={"module": "map-sketches"})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "module": "map-sketches", "deferred": True}
    assert client.get("/api/builder/commissions").json()["commissions"][0]["deferred"] is True

    r = client.post("/api/builder/commissions/resume", json={"module": "map-sketches"})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "module": "map-sketches", "deferred": False}
    assert client.get("/api/builder/commissions").json()["commissions"][0]["deferred"] is False


def test_unknown_module_on_defer_or_resume_is_400(commission_home):
    client = TestClient(app)
    for path in ("/api/builder/commissions/defer", "/api/builder/commissions/resume"):
        r = client.post(path, json={"module": "no-such-module"})
        assert r.status_code == 400
        assert "no-such-module" in r.json()["detail"]


def test_a_pack_that_cannot_be_read_is_an_empty_board(tmp_path, monkeypatch):
    """A missing pack leaves the Hall open and quiet, never a 500."""
    monkeypatch.setenv("VEFR_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("VEFR_WORLD", "not-there")
    monkeypatch.setenv("VEFR_DATA_DIR", str(tmp_path / "data"))
    world_mod.load_world.cache_clear()
    try:
        r = TestClient(app).get("/api/builder/commissions")
    finally:
        world_mod.load_world.cache_clear()
    assert r.status_code == 200
    assert r.json() == {"world": "not-there", "commissions": []}
