"""The Library: authored books a world keeps, and the studio's own shelf.

Pins the book format (front matter + '* * *' pages), every validator
rule for how a book is found, the studio handbook shelf, the loader's
`world["library"]`, and GET /api/library. No model call anywhere.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vefr import maplab
from vefr.library import (found_words, load_library, load_shelf, parse_book,
                          studio_shelf_dir, validate_books)

ROOT = Path(__file__).resolve().parents[1]

# The fixture builder is a script (like make_desk_pack.py); load it by path.
_spec = importlib.util.spec_from_file_location("make_library_pack", ROOT / "tests/fixtures/make_library_pack.py")
_make = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_make)
BOOKS, build = _make.BOOKS, _make.build


def _errors(pack: Path) -> list[str]:
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def test_parse_front_matter_pages_and_defaults():
    b = parse_book("---\ntitle: A Note # with a hash\nfound: map   # where\nat: [7, 4]\nmood: calm\n---\nOne.\n\n* * *\n\nTwo.\n", "a-note")
    assert b["title"] == "A Note # with a hash"
    assert b["found"] == "map" and b["at"] == [7, 4]
    assert b["pages"] == ["One.", "Two."]
    assert b["kind"] == "book" and b["region"] == "town"
    assert b["extra"] == {"mood": "calm"}
    plain = parse_book("Just words.", "plain")
    assert plain["found"] == "shelf" and plain["title"] == "" and plain["pages"] == ["Just words."]


def test_fixture_library_validates_clean(tmp_path):
    pack = build(tmp_path)
    assert _errors(pack) == []
    books = load_library(pack)
    assert [b["id"] for b in books] == sorted(BOOKS)


@pytest.mark.parametrize("name,text,expect", [
    ("no-title", "---\nfound: shelf\n---\nWords.", "needs a title"),
    ("bad-found", "---\ntitle: X\nfound: sky\n---\nWords.", "found must be one of"),
    ("no-at", "---\ntitle: X\nfound: map\n---\nWords.", "needs at: [x, y]"),
    ("off-map", "---\ntitle: X\nfound: map\nat: [99, 99]\n---\nWords.", "off the map or not walkable"),
    ("on-a-wall", "---\ntitle: X\nfound: map\nat: [0, 0]\n---\nWords.", "off the map or not walkable"),
    ("no-speaker", "---\ntitle: X\nfound: resident\n---\nWords.", "needs speaker"),
    ("stranger", "---\ntitle: X\nfound: resident\nspeaker: nobody\n---\nWords.", "is not one of this act's residents"),
    ("bad-when", "---\ntitle: X\nfound: earned\nwhen: someday\n---\nWords.", "when must be one of"),
    ("missing-sequel", "---\ntitle: X\nfound: earned\nwhen: book:nope\n---\nWords.", "names a book this library doesn't have"),
    ("empty-page", "---\ntitle: X\n---\nOne.\n\n* * *\n\n", "every page needs words"),
    ("bad-kind", "---\ntitle: X\nkind: scroll\n---\nWords.", "kind must be one of"),
    ("Bad_Name", "---\ntitle: X\n---\nWords.", "lowercase letters, digits and dashes"),
])
def test_validator_names_each_broken_book(tmp_path, name, text, expect):
    pack = build(tmp_path, books={name: text})
    errors = _errors(pack)
    assert any(expect in e for e in errors), errors


def test_studio_shelf_is_the_handbook_and_validates():
    shelf = load_shelf(studio_shelf_dir())
    assert len(shelf) == 8
    assert shelf[0]["title"] == "The Seven Stages"
    assert validate_books(shelf) == []
    assert all(b["found"] == "shelf" and len(b["pages"]) >= 2 for b in shelf)


def test_found_words_say_it_plainly():
    assert found_words({"found": "map", "at": [3, 4]}) == "lies on the map at 3, 4"
    assert found_words({"found": "resident", "speaker": "keeper"}) == "given by keeper"
    assert found_words({"found": "earned", "when": "bell"}) == "earned when the bell rings"
    assert found_words({"found": "earned", "when": "book:intro"}) == "earned after reading 'intro'"
    assert found_words({"found": "shelf"}) == "on the shelf from the start"


def test_loader_carries_the_library(tmp_path, monkeypatch):
    pack = build(tmp_path)
    monkeypatch.setattr("vefr.paths.pack_dir", lambda name=None: pack)
    from vefr.world import load_world
    load_world.cache_clear()
    try:
        assert len(load_world("library-test")["library"]) == len(BOOKS)
    finally:
        load_world.cache_clear()


def test_api_library_serves_world_and_studio_shelves(tmp_path, monkeypatch):
    pack = build(tmp_path)
    monkeypatch.setattr("vefr.paths.pack_dir", lambda name=None: pack)
    from vefr.main import app
    from vefr.world import load_world
    load_world.cache_clear()
    r = TestClient(app).get("/api/library")
    assert r.status_code == 200
    data = r.json()
    assert len(data["books"]) == len(BOOKS) and len(data["studio"]) == 8
    note = next(b for b in data["books"] if b["id"] == "a-map-note")
    assert note["found_words"] == "lies on the map at 1, 1" and note["pages"] == ["It lay on the ground."]
    assert TestClient(app).get("/api/library", params={"world": "../x"}).status_code == 400


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_reader_logic_harness():
    out = subprocess.run(["node", str(ROOT / "tests/fixtures/library_harness.mjs"),
                          str(ROOT / "web/js/library.js")], capture_output=True, text=True, timeout=20)
    assert out.returncode == 0 and "ALL PASS" in out.stdout, out.stdout + out.stderr


def test_the_book_export_carries_the_library(tmp_path, monkeypatch):
    from vefr import forge, journal
    from vefr.export import export_story
    from vefr.world import load_world
    pack = build(tmp_path)
    monkeypatch.setattr("vefr.paths.pack_dir", lambda name=None: pack)
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr(forge, "VAULT", tmp_path / "vault.json")
    load_world.cache_clear()
    try:
        out = export_story("library-test")
    finally:
        load_world.cache_clear()
    assert "## The Library" in out
    assert "### A Shelf Book" in out and "The first page.\n\n* * *\n\nThe second page." in out
    assert "_lies on the map at 1, 1_" in out
