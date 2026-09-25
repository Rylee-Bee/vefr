"""Every builder route that takes a pack name from the request guards it.

A pack name is joined under worlds/ (or templates/) by pack_dir(); a
value like "../elsewhere" must never resolve outside the pack roots.
The rule lives once in paths.safe_pack_name(); these pins prove every
request-facing builder route applies it - 400 on a traversal-shaped
name, still works on a real bare name.

The woven-file download route (/api/builder/weave/file/{name}) is not
here: its `name` is a server-written *.html filename, already pinned by
test_builder_weave.py's `_WEAVE_NAME_RE` tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vefr import chat as chat_mod
from vefr.lore import LorePreviewResponse
from vefr.main import app
from vefr.paths import safe_pack_name

BAD_NAMES = ["../x", "/etc", "a/b", ".hidden"]

# Every route that reads a pack/world name out of the request body.
BAD_CASES = [
    "/api/builder/validate",
    "/api/builder/import",
    "/api/builder/map/propose",
    "/api/builder/map/check",
    "/api/builder/face/roll",
    "/api/builder/weave",
    "/api/builder/chat",
    "/api/builder/lore",
]


def _request_body(path: str, bad: str) -> dict:
    """The body each route needs so the pack name is what fails, not a
    missing required field (chat needs `message`, lore needs `lore`)."""
    if path == "/api/builder/chat":
        return {"message": "a stray world name", "world": bad}
    if path == "/api/builder/weave":
        return {"world": bad}
    if path == "/api/builder/lore":
        return {"lore": bad}
    return {"name": bad}


@pytest.mark.parametrize("bad", BAD_NAMES)
@pytest.mark.parametrize("path", BAD_CASES)
def test_bad_pack_name_is_400(fixture_vefr_home, path, bad):
    r = TestClient(app).post(path, json=_request_body(path, bad))
    assert r.status_code == 400, (path, bad, r.status_code, r.text)
    assert r.json()["detail"] == "world must be a bare pack name"


def test_safe_pack_name_passes_defaults_and_rejects_traversal():
    assert safe_pack_name(None) is None
    assert safe_pack_name("") is None
    assert safe_pack_name("sample-world") == "sample-world"
    for bad in [*BAD_NAMES, "x/../y", ".."]:
        with pytest.raises(ValueError):
            safe_pack_name(bad)


# ---- a good bare name still reaches the route's real work ----


def test_validate_accepts_a_bare_pack_name(fixture_vefr_home):
    r = TestClient(app).post(
        "/api/builder/validate", json={"name": "four-phase-pack"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


def test_import_accepts_a_bare_pack_name(fixture_vefr_home, monkeypatch):
    monkeypatch.setattr("vefr.cli.cmd_import", lambda args: 0)
    r = TestClient(app).post(
        "/api/builder/import", json={"repo": "example/sample-pack", "name": "sample-world"}
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"rc": 0}


def test_map_propose_accepts_a_bare_pack_name(fixture_vefr_home, monkeypatch):
    rows = ["###.###", "#.....#", "#.p...#", "#######"]
    monkeypatch.setattr(chat_mod, "propose_map", lambda story, mood, w, dest: rows)
    r = TestClient(app).post(
        "/api/builder/map/propose",
        json={"name": "four-phase-pack", "story": "a quiet hollow"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


def test_map_check_accepts_a_bare_pack_name(fixture_vefr_home):
    r = TestClient(app).post(
        "/api/builder/map/check",
        json={"name": "four-phase-pack", "grid": ["###", "#.#", "###"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


def test_face_roll_accepts_a_bare_pack_name(fixture_vefr_home, monkeypatch):
    monkeypatch.setattr(chat_mod, "_pick_tile", lambda w: (0, 0))
    monkeypatch.setattr(
        chat_mod,
        "propose_face",
        lambda story, mood, w: {"name": "Moss", "role": "the gate-tender", "seed": "Heavy dusk."},
    )
    r = TestClient(app).post(
        "/api/builder/face/roll", json={"name": "four-phase-pack", "mood": "quiet"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


def test_weave_accepts_a_bare_pack_name(fixture_vefr_home, monkeypatch, tmp_path):
    monkeypatch.setenv("VEFR_WEAVE_DIR", str(tmp_path / "out"))
    r = TestClient(app).post("/api/builder/weave", json={"world": "four-phase-pack"})
    assert r.status_code == 200, r.text
    assert r.json()["name"].endswith(".html")


def test_chat_accepts_a_bare_pack_name(fixture_vefr_home, monkeypatch):
    monkeypatch.setattr(chat_mod, "draft", lambda prompt, system=None: "proposal only")
    r = TestClient(app).post(
        "/api/builder/chat", json={"message": "make it stranger", "world": "four-phase-pack"}
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"reply": "proposal only"}


def test_lore_accepts_a_bare_pack_name(fixture_vefr_home, monkeypatch):
    def fake_preview(req):
        return LorePreviewResponse(lore=req.lore, textures="t", names=["n"], questions=["q"])

    monkeypatch.setattr("vefr.lore.preview_lore", fake_preview)
    r = TestClient(app).post("/api/builder/lore", json={"lore": "norse", "seeds": []})
    assert r.status_code == 200, r.text
    assert r.json()["lore"] == "norse"

def test_non_string_name_is_a_400_not_a_crash():
    from fastapi.testclient import TestClient
    from vefr.main import app

    r = TestClient(app).post("/api/builder/validate", json={"name": 42})
    assert r.status_code == 400
