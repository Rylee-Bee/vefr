"""The served builder's "Play it here" route.

POST /api/builder/weave writes the file; GET
/api/builder/weave/play/{name} serves that same server-written file
inline so the Desk can show it in a pane. This pins the inline
Content-Disposition, the sandbox CSP header, and the same strict
filename lookup as the download route: a name is matched against
_WEAVE_NAME_RE and then found among the files the server wrote, so a
request string is never joined onto a path (traversal never reaches
disk).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from vefr.main import app, builder_weave_file, builder_weave_play

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "four-phase-pack"


@pytest.fixture
def woven(tmp_path, monkeypatch):
    """The smallest fixture pack + a temp, server-owned output dir."""
    pack = tmp_path / "worlds" / "four-phase-pack"
    shutil.copytree(FIXTURE, pack, dirs_exist_ok=True)
    monkeypatch.setenv("VEFR_WEAVE_DIR", str(tmp_path / "out"))
    monkeypatch.setattr("vefr.paths.pack_dir", lambda name=None: pack)
    return pack


def _weave(client) -> dict:
    r = client.post("/api/builder/weave", json={})
    assert r.status_code == 200, r.text
    return r.json()


def test_play_serves_the_woven_file_inline_with_the_sandbox_csp(woven):
    client = TestClient(app)
    info = _weave(client)

    play = client.get(f"/api/builder/weave/play/{info['name']}")
    assert play.status_code == 200
    disposition = play.headers["content-disposition"]
    assert disposition.startswith("inline")
    assert "attachment" not in disposition
    assert f'filename="{info["name"]}"' in disposition
    assert play.headers["content-security-policy"] == (
        "sandbox allow-scripts")
    body = play.text.lstrip().lower()
    assert body.startswith("<!doctype") or body.startswith("<html")


def test_the_download_route_still_attaches(woven):
    """Play must not have moved the download route's disposition."""
    client = TestClient(app)
    info = _weave(client)
    dl = client.get(f"/api/builder/weave/file/{info['name']}")
    assert dl.status_code == 200
    assert dl.headers["content-disposition"].startswith("attachment")


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
def test_play_refuses_bad_names(woven, bad):
    r = TestClient(app).get(f"/api/builder/weave/play/{bad}")
    assert r.status_code in (400, 404)


def test_play_route_blocks_traversal_before_disk(woven):
    """The route's own guard (not just the router) refuses traversal."""
    for bad in ["../world.json", "..\\escape.html", "/etc/passwd", "..", ""]:
        with pytest.raises(HTTPException) as excinfo:
            builder_weave_play(bad)
        assert excinfo.value.status_code in (400, 404)


def test_play_never_serves_a_file_outside_the_output_dir(woven, tmp_path):
    """A matching-name file just outside the server-owned dir stays invisible.

    The route looks the name up among the files it wrote rather than
    joining the request onto a path, so a real file beside the dir is
    never reachable even when its name satisfies the pattern.
    """
    client = TestClient(app)
    _weave(client)  # make the output dir real
    (tmp_path / "escape.html").write_text("<html>secret</html>", encoding="utf-8")
    r = client.get("/api/builder/weave/play/escape.html")
    assert r.status_code == 404


def test_both_routes_share_one_lookup(woven):
    """The play and download routes resolve the same name to the same file."""
    client = TestClient(app)
    info = _weave(client)
    name = info["name"]
    # Direct helper: both public functions take the same guard.
    with pytest.raises(HTTPException):
        builder_weave_file("no-such-file.html")
    with pytest.raises(HTTPException):
        builder_weave_play("no-such-file.html")
    assert client.get(f"/api/builder/weave/play/{name}").status_code == 200
    assert client.get(f"/api/builder/weave/file/{name}").status_code == 200
