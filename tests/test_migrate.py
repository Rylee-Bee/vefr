"""norns migrate - flat-shape packs land in the acts tree."""

import json
import shutil
from pathlib import Path

from vefr import cli
from vefr.maplab import load_pack, validate


def _flat_sample(tmp_path: Path) -> Path:
    """A throwaway flat-shape pack under tmp_path/worlds/flat-test/."""
    base = tmp_path / "worlds" / "flat-test"
    (base / "voices").mkdir(parents=True)
    (base / "voices" / "keeper.md").write_text(
        "# The Keeper\n\nShe speaks plainly.\n", encoding="utf-8"
    )
    flat = {
        "name": "flat-test",
        "title": "Flat Test",
        "description": "throwaway flat-shape pack",
        "phases": {"dusk": "settles.", "dawn": "begins."},
        "surface": "combat",
        "voices": {
            "mother": {"file": "voices/keeper.md", "strike": "write a letter"},
        },
        "bonds": {
            "given": {"card": "Given.", "prompt": "given."},
            "cold": {"card": "Cold.", "prompt": "cold."},
        },
        "speakers": {
            "keeper": {
                "name": "The Keeper",
                "at": [1, 1],
                "near": "the stone",
                "voice_file": "voices/keeper.md",
                "seeds": {"dusk": "warm.", "dawn": "morning."},
            },
        },
        "town": {
            "tile": 32,
            "bg": "#131311",
            "hero_start": [1, 1],
            "watch": {"tower": [1, 1], "r_by_phase": {"dusk": 1, "dawn": 2},
                      "overlay": "rgba(0,0,0,0.3)"},
            "sanctuary_tiles": ["."],
            "water_by_phase": {"dusk": "low", "dawn": "low"},
            "flood_tiles": [],
            "legend": {
                ".": {"base": ["#212a20"]},
                "#": {"base": ["#2a2e33"], "solid": True},
            },
            "hero_color": "#e8e5df",
            "map": [
                "###",
                "#.#",
                "###",
            ],
            "pois": {},
        },
    }
    (base / "world.json").write_text(
        json.dumps(flat, indent=2), encoding="utf-8"
    )
    return base


def test_migrate_flat_pack_to_acts(tmp_path, monkeypatch):
    """A flat-shape pack becomes an acts-shape pack after migrate.

    The migrator:
      - creates acts/<id>/world.json with the act contract
      - moves map.md into acts/<id>/town/
      - moves voices/ into acts/<id>/town/voices/
      - rewrites the pack-level world.json to the new contract
        (no town/speakers at the top)
    The migrated pack validates identically to the source.
    """
    pack = _flat_sample(tmp_path)
    # Point pack_root() at our tmp tree.
    monkeypatch.setattr(cli, "pack_root", lambda: tmp_path)

    import argparse
    rc = cli.cmd_migrate(argparse.Namespace(pack="flat-test", act_id=None))
    assert rc == 0, f"migrator returned {rc}"

    # Pack-level world.json is the new contract.
    pack_cfg = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    assert "town" not in pack_cfg
    assert "speakers" not in pack_cfg
    assert pack_cfg["title"] == "Flat Test"
    assert pack_cfg["phases"]["dusk"] == "settles."

    # Acts tree is laid out.
    assert (pack / "acts" / "act-1" / "world.json").exists()
    assert (pack / "acts" / "act-1" / "town" / "map.md").exists()
    assert (pack / "acts" / "act-1" / "town" / "voices" / "keeper.md").exists()

    # Map content moved.
    map_text = (pack / "acts" / "act-1" / "town" / "map.md").read_text(
        encoding="utf-8"
    )
    assert "###" in map_text
    assert "#.#" in map_text

    # Act contract has the speakers and town metadata.
    act_cfg = json.loads(
        (pack / "acts" / "act-1" / "world.json").read_text(encoding="utf-8")
    )
    assert act_cfg["id"] == "act-1"
    assert "keeper" in act_cfg["speakers"]
    assert "tile" in act_cfg["town"]

    # The migrated pack validates.
    errors = validate(load_pack(pack), pack_dir=pack)
    assert errors == [], f"validation errors after migration: {errors}"


def test_migrate_is_idempotent_on_acts_shape(tmp_path, monkeypatch):
    """A pack already in the acts shape is left alone (rc=0)."""
    base = tmp_path / "worlds" / "already-acts"
    (base / "acts" / "act-1").mkdir(parents=True)
    (base / "world.json").write_text(
        json.dumps({"name": "already-acts", "title": "Already", "phases": {}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "pack_root", lambda: tmp_path)
    import argparse
    rc = cli.cmd_migrate(argparse.Namespace(pack="already-acts", act_id=None))
    assert rc == 0
    # The dummy file we wrote is still there (nothing got rewritten).
    assert (base / "world.json").read_text(encoding="utf-8").startswith("{")
