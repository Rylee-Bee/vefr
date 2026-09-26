"""Committing a sketch: POST /api/builder/map/build.

The drawing table proposes (map/propose) and checks (map/check); this
is the one builder route that writes the map into the world pack.
These pins cover the contract the owner asked for:

  - an invalid draft is refused with the validator's errors, 422,
    and nothing on disk changes;
  - a valid draft is written through the CLI's own path
    (maplab.write_pack), byte-for-byte what `norns build-map` would
    write for the same input;
  - an existing map is never clobbered without `force` (409), and a
    forced replace keeps the previous map file beside it as
    <name>.bak-<timestamp>;
  - a traversal-shaped world name is a 400 (pinned centrally in
    tests/test_builder_pack_names.py).
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vefr import maplab
from vefr import world as world_mod
from vefr.main import app

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "four-phase-pack"
SAMPLE_WORLD = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"

# A valid 5x5 town for the flat fixture: hero_start (1,1) stands on
# open ground and every open tile reaches every other.
VALID = ["#####", "#...#", "#.#.#", "#...#", "#####"]

ORIGINAL_FLAT_MAP = ["###", "#.#", "###"]


def _pack(home) -> Path:
    return home / "worlds" / "four-phase-pack"


@pytest.fixture
def acts_home(tmp_path, monkeypatch):
    """A temp home whose world is the acts-shape sample-world pack.

    The served builder's own worlds are acts shape (copied from
    sample-world), so the map lives in acts/<act>/<region>/map.md -
    the file this route must back up and overwrite.
    """
    home = tmp_path / "vefr-home"
    (home / "worlds").mkdir(parents=True)
    shutil.copytree(SAMPLE_WORLD, home / "worlds" / "sample-world")
    monkeypatch.setenv("VEFR_HOME", str(home))
    world_mod.load_world.cache_clear()
    yield home
    world_mod.load_world.cache_clear()


def test_invalid_grid_is_422_with_errors_and_writes_nothing(fixture_vefr_home):
    pack = _pack(fixture_vefr_home)
    before = (pack / "world.json").read_text(encoding="utf-8")

    r = TestClient(app).post(
        "/api/builder/map/build",
        json={"name": "four-phase-pack", "grid": ["###", "###", "###"], "force": True},
    )

    assert r.status_code == 422, r.text
    assert "not walkable" in r.json()["detail"]
    assert (pack / "world.json").read_text(encoding="utf-8") == before
    assert not list(pack.glob("world.json.bak-*"))


def test_non_rectangular_grid_is_422(fixture_vefr_home):
    r = TestClient(app).post(
        "/api/builder/map/build",
        json={"name": "four-phase-pack", "grid": ["###", "##"], "force": True},
    )
    assert r.status_code == 422
    assert "rectangular" in r.json()["detail"]


def test_missing_grid_is_422(fixture_vefr_home):
    r = TestClient(app).post("/api/builder/map/build", json={"name": "four-phase-pack"})
    assert r.status_code == 422
    assert "grid" in r.json()["detail"]


def test_existing_map_without_force_is_409_and_unchanged(fixture_vefr_home):
    pack = _pack(fixture_vefr_home)
    before = (pack / "world.json").read_text(encoding="utf-8")

    r = TestClient(app).post(
        "/api/builder/map/build",
        json={"name": "four-phase-pack", "grid": VALID},
    )

    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "a map already exists — send force to replace it"
    assert (pack / "world.json").read_text(encoding="utf-8") == before


def test_valid_grid_written_and_matches_the_cli(fixture_vefr_home, tmp_path):
    """The served build is the CLI's build - same bytes for same input."""
    pack = _pack(fixture_vefr_home)

    r = TestClient(app).post(
        "/api/builder/map/build",
        json={"name": "four-phase-pack", "grid": VALID, "force": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["written"] is True
    assert body["path_rel"] == "world.json"
    assert body["backup_rel"] and body["backup_rel"].startswith("world.json.bak-")

    served = (pack / "world.json").read_text(encoding="utf-8")
    assert json.loads(served)["town"]["map"] == VALID

    # The CLI's own path, same input, into a pristine copy of the pack.
    # Same directory name: world.json's `name` field is the pack dir.
    cli_pack = tmp_path / "cli" / "four-phase-pack"
    shutil.copytree(FIXTURE, cli_pack)
    segments = tmp_path / "segments.json"
    segments.write_text(
        json.dumps({"rows": [[[ch, 1] for ch in row] for row in VALID]}),
        encoding="utf-8",
    )
    args = argparse.Namespace(pack=str(cli_pack), segments=str(segments), force=True)
    assert maplab.cmd_build(args) == 0
    assert (cli_pack / "world.json").read_text(encoding="utf-8") == served


def test_force_keeps_a_backup_of_the_previous_map(fixture_vefr_home):
    pack = _pack(fixture_vefr_home)
    before = (pack / "world.json").read_text(encoding="utf-8")

    r = TestClient(app).post(
        "/api/builder/map/build",
        json={"name": "four-phase-pack", "grid": VALID, "force": True},
    )
    assert r.status_code == 200, r.text
    backup = pack / r.json()["backup_rel"]
    assert backup.is_file()
    assert backup.read_text(encoding="utf-8") == before
    # The original map is still readable from the backup.
    assert json.loads(before)["town"]["map"] == ORIGINAL_FLAT_MAP


def test_segments_build_a_valid_map(fixture_vefr_home):
    """The run-length input `norns build-map` takes is accepted verbatim."""
    spec = {"rows": [[[ch, 1] for ch in row] for row in VALID]}
    r = TestClient(app).post(
        "/api/builder/map/build",
        json={"name": "four-phase-pack", "segments": spec, "force": True},
    )
    assert r.status_code == 200, r.text
    pack = _pack(fixture_vefr_home)
    assert json.loads((pack / "world.json").read_text(encoding="utf-8"))["town"]["map"] == VALID


def test_acts_pack_writes_map_md_backs_it_up_and_refreshes_the_view(acts_home):
    """The served builder's acts-shape worlds write + back up map.md."""
    pack = acts_home / "worlds" / "sample-world"
    map_path = pack / "acts" / "act-1" / "town" / "map.md"
    original = map_path.read_text(encoding="utf-8")

    rows = [ln for ln in original.splitlines() if ln.strip()]
    row = rows[8]
    rows[8] = row[:5] + "#" + row[6:]  # a changed, still-connected ground

    client = TestClient(app)
    r = client.post(
        "/api/builder/map/build",
        json={"name": "sample-world", "grid": rows, "force": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["path_rel"] == "acts/act-1/town/map.md"
    assert body["backup_rel"].startswith("acts/act-1/town/map.md.bak-")

    assert (pack / body["backup_rel"]).read_text(encoding="utf-8") == original
    assert map_path.read_text(encoding="utf-8") == "\n".join(rows) + "\n"

    # The write cleared load_world's cache, so the served world is fresh.
    served = client.get("/api/world").json()
    assert served["regions"]["town"]["map_text"] == rows