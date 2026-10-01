"""The edit log: data/edits.jsonl, the pack's EDITS.md, and one-level undo.

Every kept builder edit writes one private JSON line in the studio's data dir
and one readable line in the pack's EDITS.md. Undo puts the last one back from
the backup the write route already made, drops both lines, and says what it
undid. A preview keeps nothing and writes nothing.

These pins cover: place + undo byte-for-byte; preview writes no log line;
map/build logs under "map_build"; a pack without EDITS.md loads unchanged and
an existing EDITS.md is never corrupted; undo with nothing to undo; and the
path guard on a log line whose backup points outside the pack.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vefr import edits, maplab
from vefr import world as world_mod
from vefr.main import app

SAMPLE_WORLD = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"


# ------------------------------------------------------------- fixtures


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A temp home whose world is the acts-shape sample pack, plus a temp
    VEFR_DATA_DIR so the private log never touches the real data/ tree."""
    home = tmp_path / "vefr-home"
    (home / "worlds").mkdir(parents=True)
    shutil.copytree(SAMPLE_WORLD, home / "worlds" / "sample-world")
    monkeypatch.setenv("VEFR_HOME", str(home))
    monkeypatch.setenv("VEFR_DATA_DIR", str(tmp_path / "data"))
    world_mod.load_world.cache_clear()
    yield home
    world_mod.load_world.cache_clear()


# -------------------------------------------------------------- helpers


def _pack(home: Path) -> Path:
    return home / "worlds" / "sample-world"


def _snapshot(pack: Path) -> dict[str, bytes]:
    """Every file under the pack, by relative path - a byte fingerprint."""
    return {
        str(p.relative_to(pack)): p.read_bytes()
        for p in sorted(pack.rglob("*"))
        if p.is_file()
    }


def _log() -> list[dict]:
    from vefr.paths import data_dir

    path = data_dir() / "edits.jsonl"
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _place(**over) -> dict:
    body = {
        "name": "sample-world",
        "id": "stern",
        "display_name": "Stern",
        "role": "guard",
        "near": "the gate",
        "seeds": {"dusk": "Halt. ...oh, it's you.", "dawn": "Morning."},
        "voice": "You are Stern, a big burly guard who is secretly very soft...",
        "region": "town",
    }
    body.update(over)
    return body


# --------------------------------------------------- 1. log and undo


def test_place_then_undo_matches_the_backup_and_drops_both_lines(home):
    pack = _pack(home)
    client = TestClient(app)
    before = _snapshot(pack)

    r = client.post("/api/builder/character/place", json=_place(at=[4, 4]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["written"] is True
    backup = pack / body["backup"]
    assert backup.is_file()

    # One kept edit: one private log line and one summary line.
    assert [e["edit"] for e in _log()] == ["place_character"]
    assert _log()[0]["world"] == "sample-world"
    md = (pack / "EDITS.md").read_text(encoding="utf-8")
    assert md.count("\n") == 1
    assert "Stern" in md

    # The backup is the pre-edit speakers file, byte for byte.
    backup_bytes = backup.read_bytes()
    assert backup_bytes == before["acts/act-1/world.json"]

    u = client.post("/api/builder/edits/undo", json={"name": "sample-world"})
    assert u.status_code == 200, u.text
    assert u.json()["ok"] is True
    assert "Undid the last edit" in u.json()["message"]

    # The restored file equals the backup byte for byte - the backup the write
    # route took is what undo puts back.
    assert (pack / "acts" / "act-1" / "world.json").read_bytes() == backup_bytes
    # The created voice file, the backup and the summary are all gone, so the
    # folder has no new file the edit left behind. (write_pack normalizes the
    # pack's other JSON - a pre-existing behaviour, not this slice's - so byte
    # equality is asserted for the file the backup owns.)
    assert not (pack / "acts" / "act-1" / "town" / "voices" / "stern.md").exists()
    assert not backup.exists()
    assert set(_snapshot(pack)) == set(before)

    # Both records dropped the line.
    assert _log() == []
    assert not (pack / "EDITS.md").exists()


# -------------------------------------------------------- 2. preview


def test_preview_writes_no_log_line_and_no_edits_md(home):
    pack = _pack(home)
    before = _snapshot(pack)

    r = TestClient(app).post(
        "/api/builder/character/place", json=_place(preview=True, at=[4, 4])
    )

    assert r.status_code == 200, r.text
    assert r.json()["written"] is False
    assert _log() == []
    assert not (pack / "EDITS.md").exists()
    assert _snapshot(pack) == before


# ------------------------------------------------------ 3. map/build


def test_map_build_appends_a_map_build_log_line(home):
    pack = _pack(home)
    map_path = pack / "acts" / "act-1" / "town" / "map.md"
    rows = [ln for ln in map_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    row = rows[8]
    rows[8] = row[:5] + "#" + row[6:]  # a changed, still-connected ground

    r = TestClient(app).post(
        "/api/builder/map/build",
        json={"name": "sample-world", "grid": rows, "force": True},
    )
    assert r.status_code == 200, r.text

    logged = _log()
    assert len(logged) == 1
    assert logged[0]["edit"] == "map_build"
    assert logged[0]["world"] == "sample-world"
    assert logged[0]["backup"].startswith("acts/act-1/town/map.md.bak-")
    assert "painted the map" in (pack / "EDITS.md").read_text(encoding="utf-8")


# ---------------------------------------------------- 4. compatibility


def test_a_pack_without_edits_md_loads_unchanged(home):
    pack = _pack(home)
    before = _snapshot(pack)
    assert not (pack / "EDITS.md").exists()
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []

    # A preview is a no-op: no new file appears and the pack still validates.
    r = TestClient(app).post(
        "/api/builder/character/place", json=_place(preview=True, at=[4, 4])
    )
    assert r.status_code == 200, r.text
    assert _snapshot(pack) == before
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []


def test_an_existing_edits_md_is_not_corrupted(home):
    pack = _pack(home)
    original = "# Emberfield change history\n\nwe wrote this by hand\n"
    (pack / "EDITS.md").write_text(original, encoding="utf-8")

    r = TestClient(app).post("/api/builder/character/place", json=_place(at=[4, 4]))
    assert r.status_code == 200, r.text

    after = (pack / "EDITS.md").read_text(encoding="utf-8")
    assert after.startswith(original)  # the hand-written words survive
    assert after.count("\n") == original.count("\n") + 1  # one line appended
    assert "Stern" in after
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []


# --------------------------------------------------------- 5. empty


def test_undo_with_an_empty_log_is_a_plain_sentence(home):
    pack = _pack(home)
    before = _snapshot(pack)

    r = TestClient(app).post("/api/builder/edits/undo", json={"name": "sample-world"})

    assert r.status_code == 404
    assert "nothing to undo" in r.json()["detail"]
    assert _snapshot(pack) == before
    assert _log() == []


# --------------------------------------------------------- 6. safety


def test_undo_refuses_a_backup_outside_the_pack(home):
    pack = _pack(home)
    # A line a corrupted file (or a hostile caller) could plant: the backup
    # names a real backup shape but climbs out of the pack.
    edits.record(
        "crew",
        "place_character",
        "sample-world",
        ["acts/act-1/world.json"],
        "../../outside/world.json.bak-20261001-120000",
        "put a stranger at the gate",
        pack,
    )
    before = _snapshot(pack)

    r = TestClient(app).post("/api/builder/edits/undo", json={"name": "sample-world"})

    assert r.status_code == 409, r.text
    assert "outside the game folder" in r.json()["detail"]
    assert _snapshot(pack) == before  # nothing was touched
    assert len(_log()) == 1  # the line was not silently dropped
