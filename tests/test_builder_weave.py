"""The served builder's "Make shareable file" pair.

`ratatoskr weave` is terminal-only; a phone user with no terminal gets
the same packaging through POST /api/builder/weave (build the current
world into a server-owned file, return metadata) and GET
/api/builder/weave/file/{name} (attachment download). These pins cover
the metadata, a real downloadable body, filename-traversal refusal,
the one-weave-at-a-time lock, and CLI parity: the file cmd_build_web
writes is byte-identical to one made through the shared build_web core.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from vefr import cli
from vefr.main import _WEAVE_LOCK, app, builder_weave_file

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "four-phase-pack"


@pytest.fixture
def woven(tmp_path, monkeypatch):
    """The smallest fixture pack + a temp, server-owned output dir."""
    pack = tmp_path / "worlds" / "four-phase-pack"
    shutil.copytree(FIXTURE, pack, dirs_exist_ok=True)
    monkeypatch.setenv("VEFR_WEAVE_DIR", str(tmp_path / "out"))
    monkeypatch.setattr("vefr.paths.pack_dir", lambda name=None: pack)
    return pack


def test_woven_file_inlines_the_legend_tiles(woven):
    """The shipped player draws the same ground tiles the Map Room does."""
    import json as _json
    import re

    html = cli.weave_html(woven)
    m = re.search(r"window\.VEFR_TILES = (\{.*?\});", html, re.S)
    assert m, "the woven file must carry the tiles global"
    tiles = _json.loads(m.group(1))
    assert tiles, "a legend with mappable symbols must inline its tiles"
    assert all(v.startswith("data:image/webp;base64,") for v in tiles.values())


def _baked_library(html):
    """The JSON on the woven file's single `window.VEFR_LIBRARY = ...;` line."""
    import json as _json

    prefix = "window.VEFR_LIBRARY = "
    line = next(ln for ln in html.splitlines() if ln.startswith(prefix))
    return _json.loads(line[len(prefix):].rstrip(";"))


def _baked(html, name):
    """The JSON on the woven file's single `window.<name> = ...;` line."""
    import json as _json

    prefix = f"window.{name} = "
    line = next(ln for ln in html.splitlines() if ln.startswith(prefix))
    return _json.loads(line[len(prefix):].rstrip(";"))


def _two_region_pack(root):
    """A two-region acts pack (town + a smaller cottage room) with one door."""
    import json as _json

    pack = root / "worlds" / "regions-pack"
    (pack / "acts" / "act-1" / "town").mkdir(parents=True)
    (pack / "acts" / "act-1" / "cottage").mkdir(parents=True)
    (pack / "world.json").write_text(_json.dumps({
        "name": pack.name, "title": "Regions Pack",
        "phases": {"dusk": "quiet", "dawn": "warm"}, "voices": {},
    }), encoding="utf-8")
    (pack / "acts" / "act-1" / "world.json").write_text(_json.dumps({
        "id": "act-1", "title": "Regions Pack",
        "regions": ["town", "cottage"],
        "speakers": {
            "keeper": {"name": "Keeper", "at": [1, 1], "region": "town",
                       "voice_file": "voices/keeper.md",
                       "seeds": {"dusk": "a", "dawn": "b"}},
            "cook": {"name": "Cook", "at": [1, 1], "region": "cottage",
                     "voice_file": "voices/cook.md",
                     "seeds": {"dusk": "c", "dawn": "d"}},
        },
        "transitions": [
            {"from": "town", "at": [2, 3], "to": "cottage", "to_at": [1, 1]},
        ],
    }), encoding="utf-8")
    for name, rows in (("town", ["#####", "#...#", "#...#", "#...#", "#####"]),
                       ("cottage", ["#####", "#...#", "#####"])):
        region = pack / "acts" / "act-1" / name
        (region / "map.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
        (region / "contract.json").write_text(_json.dumps({
            "tile": 32, "bg": "#131311", "hero_start": [1, 1],
            "legend": {".": {"base": ["#212a20"]},
                       "#": {"base": ["#2a2e33"], "solid": True}},
            "sanctuary_tiles": ["."],
            "water_by_phase": {"dusk": "low", "dawn": "low"},
            "flood_tiles": [], "pois": {},
        }), encoding="utf-8")
    return pack


def test_woven_file_bakes_regions_transitions_and_grouped_speakers(tmp_path):
    """A two-region pack bakes every region's map, its doors, and the
    act's speakers grouped by the region they name."""
    pack = _two_region_pack(tmp_path)
    html = cli.weave_html(pack)

    regions = _baked(html, "VEFR_REGIONS")
    assert set(regions) == {"town", "cottage"}
    assert regions["town"]["map"] == ["#####", "#...#", "#...#", "#...#", "#####"]
    assert regions["cottage"]["map"] == ["#####", "#...#", "#####"]
    assert regions["cottage"]["hero_start"] == [1, 1]
    assert regions["cottage"]["legend"]["#"]["solid"] is True

    assert _baked(html, "VEFR_TRANSITIONS") == [
        {"from": "town", "at": [2, 3], "to": "cottage", "to_at": [1, 1]},
    ]

    speakers = _baked(html, "VEFR_SPEAKERS")
    assert set(speakers) == {"town", "cottage"}
    assert set(speakers["town"]) == {"keeper"}
    assert set(speakers["cottage"]) == {"cook"}
    assert set(speakers["cottage"]["cook"]) == {"name", "at", "seeds", "voice_file"}
    assert speakers["cottage"]["cook"]["name"] == "Cook"


def test_the_woven_file_carries_the_book_markers():
    """A book you have not found is marked where it can be found."""
    pack = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"
    html = cli.weave_html(pack)
    icons = _baked(html, "VEFR_BOOK_ICONS")
    assert set(icons) == {"map", "resident"}
    assert all(v.startswith("data:image/webp;base64,") for v in icons.values())
    note = next(b for b in _baked(html, "VEFR_LIBRARY") if b["id"] == "a-note-by-the-path")
    assert note["region"] == "town"


def test_the_woven_file_carries_the_door_picture():
    """A transition is drawn with the door art, so it is not invisible."""
    pack = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"
    assert _baked(cli.weave_html(pack), "VEFR_DOOR").startswith("data:image/webp;base64,")


def test_each_region_keeps_its_own_tiles(tmp_path):
    """Tiles travel with the region.

    The same symbol can mean different ground on two maps (a town's '.' is
    grass, a dungeon's '.' is stone floor), so a merged set would draw the
    wrong picture on one of them.
    """
    import json as _json

    pack = _two_region_pack(tmp_path)
    cottage = pack / "acts" / "act-1" / "cottage" / "contract.json"
    contract = _json.loads(cottage.read_text(encoding="utf-8"))
    contract["legend"]["."] = {"base": ["#332e26"], "tile": "table"}
    cottage.write_text(_json.dumps(contract), encoding="utf-8")

    by_region = _baked(cli.weave_html(pack), "VEFR_REGION_TILES")
    assert set(by_region) == {"town", "cottage"}
    assert "." in by_region["cottage"] and "." in by_region["town"]
    assert by_region["cottage"]["."] != by_region["town"]["."]


def test_the_woven_file_bakes_where_the_game_starts(tmp_path):
    """An act can say where the game begins; a silent act falls back."""
    import json as _json

    pack = _two_region_pack(tmp_path)
    act = pack / "acts" / "act-1" / "world.json"
    cfg = _json.loads(act.read_text(encoding="utf-8"))
    cfg["start"] = {"region": "cottage", "at": [1, 1]}
    act.write_text(_json.dumps(cfg), encoding="utf-8")
    assert _baked(cli.weave_html(pack), "VEFR_START") == {"region": "cottage", "at": [1, 1]}

    sample = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"
    assert _baked(cli.weave_html(sample), "VEFR_START") == {}


def test_woven_file_bakes_the_packs_books():
    """The sample pack's books ride into the file in the reader's shape."""
    pack = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"
    books = _baked_library(cli.weave_html(pack))
    by_id = {b["id"]: b for b in books}
    assert set(by_id) == {"a-note-by-the-path", "the-keepers-ledger", "writing-a-book"}
    for b in books:
        assert list(b) == ["id", "title", "kind", "found", "at", "speaker",
                           "when", "pages", "region", "chest", "found_words"]
        assert b["title"] and b["pages"] and b["found_words"]
    note = by_id["a-note-by-the-path"]
    assert note["found"] == "map" and note["at"] == [2, 2]
    assert "2, 2" in note["found_words"]
    assert by_id["the-keepers-ledger"]["speaker"] == "keeper"


def test_woven_file_without_a_library_bakes_an_empty_list(woven):
    """A pack with no library/ folder bakes [] (never a missing global)."""
    assert _baked_library(cli.weave_html(woven)) == []


def test_woven_file_bakes_pack_sprites(woven):
    """A pack's named character sprites ride into the file, keyed by name."""
    import base64 as _b64
    import json as _json

    png = _b64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )
    (woven / "sprites").mkdir()
    (woven / "sprites" / "hero.png").write_bytes(png)
    (woven / "sprites" / "keeper.png").write_bytes(png)
    cfg = _json.loads((woven / "world.json").read_text(encoding="utf-8"))
    cfg.setdefault("player", {})["sprites"] = {
        "hero": "sprites/hero.png", "keeper": "sprites/keeper.png"}
    (woven / "world.json").write_text(_json.dumps(cfg), encoding="utf-8")

    html = cli.weave_html(woven)
    line = next(ln for ln in html.splitlines() if ln.startswith("window.VEFR_SPRITES = "))
    data = _json.loads(line[len("window.VEFR_SPRITES = "):].rstrip(";"))
    assert set(data) == {"hero", "keeper"}
    assert all(v.startswith("data:image/png;base64,") for v in data.values())


def test_a_sprite_path_outside_the_pack_is_skipped(woven):
    """Only a file inside the pack is read; a traversing path is dropped."""
    import json as _json

    cfg = _json.loads((woven / "world.json").read_text(encoding="utf-8"))
    cfg.setdefault("player", {})["sprites"] = {"hero": "../../etc/passwd"}
    (woven / "world.json").write_text(_json.dumps(cfg), encoding="utf-8")

    html = cli.weave_html(woven)
    line = next(ln for ln in html.splitlines() if ln.startswith("window.VEFR_SPRITES = "))
    assert _json.loads(line[len("window.VEFR_SPRITES = "):].rstrip(";")) == {}


def test_weave_returns_metadata_and_a_real_download(woven):
    client = TestClient(app)
    r = client.post("/api/builder/weave", json={})
    assert r.status_code == 200, r.text
    info = r.json()
    assert info["name"].endswith(".html")
    assert info["size_bytes"] > 0
    assert info["built_at"]
    assert info["download_url"] == f"/api/builder/weave/file/{info['name']}"

    dl = client.get(info["download_url"])
    assert dl.status_code == 200
    assert dl.headers["content-disposition"].startswith("attachment")
    head = dl.text.lstrip().lower()
    assert head.startswith("<!doctype") or head.startswith("<html")


def test_weave_refuses_a_second_concurrent_build(woven):
    client = TestClient(app)
    assert _WEAVE_LOCK.acquire(blocking=False)
    try:
        r = client.post("/api/builder/weave", json={})
    finally:
        _WEAVE_LOCK.release()
    assert r.status_code == 409


def test_missing_pack_is_404(tmp_path, monkeypatch):
    monkeypatch.setenv("VEFR_WEAVE_DIR", str(tmp_path / "out"))
    monkeypatch.setattr(
        "vefr.paths.pack_dir", lambda name=None: tmp_path / "nope")
    r = TestClient(app).post("/api/builder/weave", json={})
    assert r.status_code == 404


@pytest.mark.parametrize(
    "bad",
    [
        "..%2fworld.json",
        "..%2F..%2Fetc%2Fpasswd",
        "a%2Fb.html",
        "nope.txt",
        ".hidden.html",
        "absent.html",  # well-formed name, no such file
    ],
)
def test_download_refuses_bad_names(woven, bad):
    r = TestClient(app).get(f"/api/builder/weave/file/{bad}")
    assert r.status_code in (400, 404)


def test_download_route_blocks_traversal_before_disk(woven):
    """The route's own guard (not just the router) refuses traversal."""
    for bad in ["../world.json", "..\\escape.html", "/etc/passwd", "..", ""]:
        with pytest.raises(HTTPException) as excinfo:
            builder_weave_file(bad)
        assert excinfo.value.status_code in (400, 404)


def test_cli_build_web_matches_the_shared_core(woven, tmp_path):
    """cmd_build_web's file is byte-identical to build_web's.

    Proves the refactor didn't fork the CLI's output: both paths go
    through weave_html, so a served weave and a terminal weave agree.
    """
    import argparse

    cli_out = tmp_path / "cli.html"
    args = argparse.Namespace(
        pack=str(woven), out=str(cli_out), pool=0, with_bundle=False,
        vault=None, journal=None, from_live=None,
    )
    assert cli.cmd_build_web(args) == 0

    core_out = cli.build_web(woven, tmp_path / "core")
    assert core_out.is_file()
    assert cli_out.read_bytes() == core_out.read_bytes()

def test_weave_refuses_world_paths(woven) -> None:
    client = TestClient(app)
    for bad in ("../sample-world", "/etc", "a/b", ".hidden"):
        r = client.post("/api/builder/weave", json={"world": bad})
        assert r.status_code == 400, (bad, r.status_code)


def test_a_book_can_be_in_a_chest(tmp_path):
    """`chest: yes` marks a book as opened (used), and bakes the chest art."""
    pack = _two_region_pack(tmp_path)
    lib = pack / "library"
    lib.mkdir(exist_ok=True)
    (lib / "in-a-chest.md").write_text(
        "---\ntitle: In a Chest\nfound: map\nat: [1, 1]\nchest: yes\nkind: note\n---\nwords\n",
        encoding="utf-8")
    html = cli.weave_html(pack)
    books = {b["id"]: b for b in _baked(html, "VEFR_LIBRARY")}
    assert books["in-a-chest"]["chest"] is True
    assert _baked(html, "VEFR_CHEST_ICON").startswith("data:image/webp;base64,")
