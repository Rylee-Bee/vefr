import os
from pathlib import Path


def app_home() -> Path:
    """Where web/ and WORLD_BIBLE.md live.

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
        if (cand / "WORLD_BIBLE.md").exists():
            return cand
    return dev
