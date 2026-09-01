import os
import shutil
from pathlib import Path

import pytest
from vefr import world as world_mod

# The pack resolves before any ratatoskr ferry fetch: the author's world when
# present, the demonstration world otherwise. The bones never require
# the flesh to prove themselves.
#
# Tests use `worlds/private-canon/` as a known-good canonical pack
# (the author's private story pack). It is the most thoroughly
# voiced pack we have; using it as a test fixture proves the
# engine surfaces a pack's voices, phases, and speakers intact.
# The engine itself doesn't know the name - the loader reads
# whatever pack the env var points at.
_pack = Path(__file__).resolve().parents[1] / 'worlds' / 'private-canon'
os.environ.setdefault(
    'VEFR_WORLD',
    'private-canon' if (_pack / 'world.json').exists() else 'sample-world',
)


@pytest.fixture
def fixture_vefr_home(monkeypatch, tmp_path):
    """Point VEFR_HOME at a temp tree with the four-phase fixture
    pack so journey tests don't depend on any canon pack being
    on disk. The fixture is at tests/fixtures/four-phase-pack/;
    we copy it into a tmpdir's worlds/ so load_world() sees it.
    """
    fixture_src = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "four-phase-pack"
    home = tmp_path / "vefr-home"
    (home / "worlds" / "four-phase-pack").mkdir(parents=True)
    shutil.copytree(fixture_src, home / "worlds" / "four-phase-pack",
                    dirs_exist_ok=True)
    monkeypatch.setenv("VEFR_HOME", str(home))
    world_mod.load_world.cache_clear()
    yield home
    world_mod.load_world.cache_clear()
