"""The world pack loader - the seam between the engine and the story.

The engine (src/norn) never hardcodes world content. Everything the
story owns - phases, voices, bonds, the town - lives in a pack
directory: worlds/<name>/{world.json, bible.md, ledger.md, map.md,
voices/}. Take the bones, grow your own flesh.
"""

import json
from functools import lru_cache

from .paths import pack_dir

REQUIRED = ["title", "phases", "voices", "bonds", "town"]


@lru_cache(maxsize=8)
def load_world(name: str | None = None) -> dict:
    d = pack_dir(name)
    config = json.loads((d / "world.json").read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in config]
    if missing:
        raise RuntimeError(
            f"world pack '{d.name}' is missing required keys: {missing}"
        )
    return config


def phase_tone(phase: str) -> str:
    phases = load_world()["phases"]
    if phase in phases:
        return phases[phase]
    return next(iter(phases.values()))
