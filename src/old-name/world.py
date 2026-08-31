"""The world pack loader - the seam between the engine and the story.

The engine (src/norn) never hardcodes world content. Everything the
story owns - phases, voices, bonds, the town, the surface - lives
in a pack directory: worlds/<name>/{world.json, bible.md, ledger.md,
map.md, voices/}. Take the bones, grow your own flesh.

SURFACE: world.json may declare a 'surface' field - one of
'combat', 'investigation', 'plain'. The surface is the *grammar*
the player sees (HP bars, encounter prompts, investigation dice),
not the engine's actual behavior. The engine never gates the
player on HP, attack, or roll results - the surface is a costume
over the Old Name way. Default surface is 'combat' for back-compat
with existing packs that don't declare one.

JOURNEY: the engine's story structure is the Hero's Journey,
told through four Elder Futhark runes. The mapping lives in
journey.py. Packs can rename their phases (any keys the author
wants) but the journey-stage anchors are positional - first
phase in `phases` maps to the first rune, and so on. The engine
never enforces the journey as a gate; it uses it as the bones
of the system prompts that shape every generation.
"""

import json
from functools import lru_cache

from .paths import pack_dir

REQUIRED = ["title", "phases", "voices", "bonds", "town"]
VALID_SURFACES = ("combat", "investigation", "plain")


@lru_cache(maxsize=8)
def load_world(name: str | None = None) -> dict:
    d = pack_dir(name)
    config = json.loads((d / "world.json").read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in config]
    if missing:
        raise RuntimeError(
            f"world pack '{d.name}' is missing required keys: {missing}"
        )
    # Default surface is 'combat' so packs that predate the concept
    # render with HP bars and encounter prompts by default.
    if "surface" not in config:
        config["surface"] = "combat"
    elif config["surface"] not in VALID_SURFACES:
        raise RuntimeError(
            f"world pack '{d.name}' has invalid surface {config['surface']!r}; "
            f"expected one of {VALID_SURFACES}"
        )
    # Attach the journey-stage anchors to each phase by position.
    # The pack's `phases` dict is ordered (Python 3.7+ preserves
    # insertion order); we zip it with journey.py's DEFAULT_PHASES.
    # Packs that rename phases still get the engine's bones.
    from .journey import DEFAULT_PHASES
    phase_keys = list(config["phases"].keys())
    if len(phase_keys) >= len(DEFAULT_PHASES):
        config["_journey"] = []
        for i, stage_key in enumerate(DEFAULT_PHASES):
            pack_phase = phase_keys[i]
            from .journey import PHASE_JOURNEY_RUNE
            config["_journey"].append({
                "pack_phase": pack_phase,
                **PHASE_JOURNEY_RUNE[stage_key],
            })
    return config


def phase_tone(phase: str) -> str:
    phases = load_world()["phases"]
    if phase in phases:
        return phases[phase]
    return next(iter(phases.values()))


def pack_phase_to_journey(phase_key: str) -> dict[str, str] | None:
    """Look up the journey-stage for a pack's phase key by position.

    Returns None if the pack has fewer phases than journey stages
    (a partial pack is allowed but doesn't anchor every stage).
    """
    w = load_world()
    for entry in w.get("_journey", []):
        if entry["pack_phase"] == phase_key:
            return entry
    return None
