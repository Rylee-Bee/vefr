import os
from pathlib import Path


def app_home() -> Path:
    """Where web/ and worlds/ live.

    Container installs put the package in site-packages, so the dev-box
    parent trick points at the wrong tree. OLD-NAME-HOME (set in the
    Containerfile) wins; otherwise fall back to /app, then the repo
    checkout (dev runs).
    """
    env = os.environ.get("OLD-NAME-HOME")
    if env:
        return Path(env)
    dev = Path(__file__).resolve().parents[2]
    for cand in (Path("/app"), dev):
        if (cand / "worlds").is_dir():
            return cand
    return dev


def world_name() -> str:
    """Which world pack is loaded. One repo can carry many; the
    container serves exactly one."""
    return os.environ.get("MUNR_WORLD", "private-canon")


def pack_dir(name: str | None = None) -> Path:
    """The world pack directory: bible, ledger, map, voices, config."""
    return app_home() / "worlds" / (name or world_name())


def pack_file(rel: str, name: str | None = None) -> Path:
    return pack_dir(name) / rel
