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


def test_woven_file_bakes_the_packs_books():
    """The sample pack's books ride into the file in the reader's shape."""
    pack = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"
    books = _baked_library(cli.weave_html(pack))
    by_id = {b["id"]: b for b in books}
    assert set(by_id) == {"a-note-by-the-path", "the-keepers-ledger", "writing-a-book"}
    for b in books:
        assert list(b) == ["id", "title", "kind", "found", "at",
                           "speaker", "when", "pages", "found_words"]
        assert b["title"] and b["pages"] and b["found_words"]
    note = by_id["a-note-by-the-path"]
    assert note["found"] == "map" and note["at"] == [2, 2]
    assert "2, 2" in note["found_words"]
    assert by_id["the-keepers-ledger"]["speaker"] == "keeper"


def test_woven_file_without_a_library_bakes_an_empty_list(woven):
    """A pack with no library/ folder bakes [] (never a missing global)."""
    assert _baked_library(cli.weave_html(woven)) == []


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
