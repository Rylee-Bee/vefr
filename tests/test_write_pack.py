"""A pack write keeps every key it does not own.

2026-09-29: building a map through the studio silently dropped a game's
`player` block (its title picture and accent colour) - `load_pack` never read
unknown pack-level fields and `write_pack` wrote a fixed set, so saving the
map ate the maker's own settings. The one-field regression lives in
`test_map_build.py`; this is the class guard. Whichever shape a pack is in, a
write must never lose a top-level key the pack started with.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from vefr import maplab

HERE = Path(__file__).resolve().parent
SHIPPED = [
    HERE.parent / "worlds" / "sample-world",          # acts shape
    HERE / "fixtures" / "four-phase-pack",            # flat shape
]


def _snapshot(pack: Path) -> set[str]:
    """Every JSON key the pack holds, as `relative/path::key` strings."""
    keys: set[str] = set()
    for f in sorted(pack.rglob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(data, dict):
            rel = f.relative_to(pack)
            keys.update(f"{rel}::{k}" for k in data)
    return keys


@pytest.mark.parametrize("src", SHIPPED, ids=lambda p: p.name)
def test_a_write_preserves_every_key_the_pack_started_with(tmp_path, src):
    pack = tmp_path / src.name
    shutil.copytree(src, pack)
    before = _snapshot(pack)

    maplab.write_pack(pack, maplab.load_pack(pack))

    lost = sorted(before - _snapshot(pack))
    assert not lost, f"{src.name}: a write dropped {lost}"


# ---- a pack with several rooms (found 2026-10-01 when placing a character in Cottage, which has six) ----


def _two_room_pack(tmp_path: Path) -> Path:
    """sample-world plus a second room, `cellar`, joined to the town by doors both ways."""
    pack = tmp_path / "two-rooms"
    shutil.copytree(HERE.parent / "worlds" / "sample-world", pack)
    act = pack / "acts" / "act-1"
    shutil.copytree(act / "town", act / "cellar")
    data = json.loads((act / "world.json").read_text(encoding="utf-8"))
    data["regions"] = ["town", "cellar"]
    data["transitions"] = [
        {"from": "town", "at": [9, 8], "to": "cellar", "to_at": [2, 2]},
        {"from": "cellar", "at": [9, 8], "to": "town", "to_at": [8, 8]},
    ]
    data["bosses"] = ["the-old-king"]
    data["x_future_key"] = {"kept": True}
    (act / "world.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return pack


def test_a_write_keeps_every_room_boss_and_unknown_key(tmp_path):
    pack = _two_room_pack(tmp_path)
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []   # the fixture itself is a good pack

    maplab.write_pack(pack, maplab.load_pack(pack))

    act = json.loads((pack / "acts" / "act-1" / "world.json").read_text(encoding="utf-8"))
    assert act["regions"] == ["town", "cellar"]            # the room list survives (it used to become ['town'])
    assert act["bosses"] == ["the-old-king"]               # and so do bosses (they used to become [])
    assert act["x_future_key"] == {"kept": True}
    assert len(act["transitions"]) == 2
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []   # the pack still validates after the write


def test_a_brand_new_pack_still_gets_one_room_and_empty_enemy_lists(tmp_path):
    pack = tmp_path / "fresh"
    (pack / "acts" / "act-1").mkdir(parents=True)
    w = {"title": "Fresh", "phases": {"dusk": "quiet"}, "speakers": {}, "voices": {}, "bonds": {},
         "town": {"map": ["###", "#.#", "###"], "legend": {".": {}, "#": {"solid": True}}, "hero_start": [1, 1]},
         "_act_id": "act-1"}
    maplab.write_pack(pack, w)
    act = json.loads((pack / "acts" / "act-1" / "world.json").read_text(encoding="utf-8"))
    assert act["regions"] == ["town"]
    assert act["enemies"] == [] and act["bosses"] == []


def test_internal_keys_are_never_written_back(tmp_path):
    """load_pack adds underscore-named helpers (for example `_player`); a write must not put them in world.json."""
    for src in SHIPPED:
        pack = tmp_path / src.name
        shutil.copytree(src, pack)
        maplab.write_pack(pack, maplab.load_pack(pack))
        for f in pack.rglob("world.json"):
            leaked = [k for k in json.loads(f.read_text(encoding="utf-8")) if k.startswith("_")]
            assert leaked == [], f"{f}: {leaked}"
