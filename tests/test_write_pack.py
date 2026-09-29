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
