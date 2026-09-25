"""The served builder can start and switch worlds without a terminal.

A phone user with no terminal uses these routes the way `norns chat`
uses run_interview. The same safety rules hold: a name is a bare pack
name (never a path), an existing pack is never overwritten, and the
active choice lives under the app's own data dir - a request never
names a path. Everything runs in tmp homes; the real worlds/ is
never touched.
"""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vefr import paths
from vefr import world as world_mod
from vefr.main import app

ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "worlds" / "sample-world"


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A tmp VEFR_HOME holding the shipped sample-world scaffold.

    VEFR_WORLD is cleared so the active-override path is the one
    under test; the module's in-memory override is reset before and
    after so no choice leaks between tests.
    """
    h = tmp_path / "vefr-home"
    worlds = h / "worlds"
    worlds.mkdir(parents=True)
    shutil.copytree(SCAFFOLD, worlds / "sample-world")
    monkeypatch.setenv("VEFR_HOME", str(h))
    monkeypatch.delenv("VEFR_WORLD", raising=False)
    monkeypatch.setattr(paths, "_ACTIVE_WORLD", None)
    world_mod.load_world.cache_clear()
    yield h
    monkeypatch.setattr(paths, "_ACTIVE_WORLD", None)
    world_mod.load_world.cache_clear()


def test_create_world_writes_a_pack_and_serves_it(home):
    client = TestClient(app)
    r = client.post(
        "/api/builder/worlds",
        json={"name": "ashfall", "title": "Ashfall", "premise": "A town under quiet ash."},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"name": "ashfall", "title": "Ashfall"}

    pack = home / "worlds" / "ashfall"
    assert (pack / "world.json").is_file()
    cfg = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    assert cfg["title"] == "Ashfall"
    assert cfg["description"] == "A town under quiet ash."

    # Creating a world makes it the active one the engine serves.
    assert client.get("/api/world").json()["title"] == "Ashfall"


def test_create_without_title_keeps_the_scaffold_title(home):
    client = TestClient(app)
    r = client.post("/api/builder/worlds", json={"name": "quiet-copy"})
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "Emberfield"


def test_existing_name_is_refused_and_untouched(home):
    client = TestClient(app)
    before = (home / "worlds" / "sample-world" / "world.json").read_text(encoding="utf-8")
    r = client.post("/api/builder/worlds", json={"name": "sample-world", "title": "Nope"})
    assert r.status_code == 409
    after = (home / "worlds" / "sample-world" / "world.json").read_text(encoding="utf-8")
    assert after == before


@pytest.mark.parametrize(
    "bad",
    ["", "../escape", "has space", "slash/name", ".hidden", "-dashfirst", "dot.name"],
)
def test_bad_names_are_refused(home, bad):
    client = TestClient(app)
    r = client.post("/api/builder/worlds", json={"name": bad, "title": "X"})
    assert r.status_code == 400, f"{bad!r} -> {r.status_code}"
    assert not (home / "escape").exists()
    assert not (home / "worlds" / "dot.name").exists()


def test_active_switch_changes_the_served_world(home):
    client = TestClient(app)
    assert client.post(
        "/api/builder/worlds", json={"name": "zulu", "title": "Zulu"}
    ).status_code == 200

    r = client.post("/api/builder/worlds/active", json={"name": "sample-world"})
    assert r.status_code == 200, r.text
    assert client.get("/api/world").json()["title"] == "Emberfield"

    r = client.post("/api/builder/worlds/active", json={"name": "zulu"})
    assert r.status_code == 200
    assert r.json()["name"] == "zulu"
    assert client.get("/api/world").json()["title"] == "Zulu"


def test_active_choice_persists_to_the_data_dir(home):
    client = TestClient(app)
    client.post("/api/builder/worlds/active", json={"name": "sample-world"})
    f = home / "data" / "active-world"
    assert f.is_file()
    assert f.read_text(encoding="utf-8").strip() == "sample-world"


def test_switch_to_a_missing_world_is_404(home):
    client = TestClient(app)
    assert client.post("/api/builder/worlds/active", json={"name": "nowhere"}).status_code == 404


def test_bad_active_name_is_400(home):
    client = TestClient(app)
    assert client.post("/api/builder/worlds/active", json={"name": "../sample-world"}).status_code == 400


def test_vefr_world_env_beats_the_override(home, monkeypatch):
    client = TestClient(app)
    assert client.post(
        "/api/builder/worlds", json={"name": "zulu", "title": "Zulu"}
    ).status_code == 200
    # No env yet: the freshly created world is what's served.
    assert client.get("/api/world").json()["title"] == "Zulu"

    monkeypatch.setenv("VEFR_WORLD", "sample-world")
    world_mod.load_world.cache_clear()
    assert client.get("/api/world").json()["title"] == "Emberfield"


def test_stale_override_falls_back_to_alphabetical(home, monkeypatch):
    monkeypatch.setattr(paths, "_ACTIVE_WORLD", "ghost-pack")
    assert paths.world_name() == "sample-world"

def test_tampered_active_world_file_is_ignored(tmp_path, monkeypatch):
    """A hand-edited data/active-world can't point outside worlds/."""
    from vefr import paths

    monkeypatch.delenv("VEFR_WORLD", raising=False)
    monkeypatch.setattr(paths, "_ACTIVE_WORLD", None)
    monkeypatch.setattr(paths, "active_world_file", lambda: tmp_path / "active-world")
    (tmp_path / "active-world").write_text("../../etc\n", encoding="utf-8")
    assert paths.active_world() is None
