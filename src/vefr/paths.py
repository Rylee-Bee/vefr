import os
from pathlib import Path


def app_home() -> Path:
    """Where web/ and worlds/ live.

    Container installs put the package in site-packages, so the dev-box
    parent trick points at the wrong tree. VEFR_HOME (set in the
    Containerfile) wins; otherwise fall back to /app, then the repo
    checkout (dev runs).
    """
    env = os.environ.get("VEFR_HOME")
    if env:
        return Path(env)
    dev = Path(__file__).resolve().parents[2]
    for cand in (Path("/app"), dev):
        if (cand / "worlds").is_dir():
            return cand
    return dev


def world_name() -> str:
    """Which world pack is loaded.

    VEFR_WORLD wins. Otherwise the first pack alphabetically under
    worlds/ - the bones boot with any flesh, or none at all beyond
    the sample that ships with the engine. No pack name is ever
    special-cased here; the engine doesn't know or care whose story
    it's running.
    """
    env = os.environ.get('VEFR_WORLD')
    if env:
        return env
    base = app_home() / 'worlds'
    packs = sorted(base.glob('*/world.json'))
    if packs:
        return packs[0].parent.name
    return 'sample-world'


def pack_dir(name: str | None = None) -> Path:
    """The world pack directory: logbok, ledger, map, voices, config."""
    return app_home() / "worlds" / (name or world_name())


def pack_file(rel: str, name: str | None = None) -> Path:
    return pack_dir(name) / rel
