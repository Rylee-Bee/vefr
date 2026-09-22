"""The woven pool - real generations, baked in for serverless play.

The packaged game normally points at a live OpenAI-compatible
endpoint. The pool is the offline answer: during authoring, the
same live model that powers the desktop pre-generates several real
outputs per (mechanic, phase, speaker) combination, and `ratatoskr
weave --pool` bakes them into the single HTML file. Mobile play
draws from the pool - every line is real model output in the pack's
own voice, just precomputed instead of live. See ROADMAP.md for the
numbers (5 samples per combo, ~70KB inline).

The pool is NOT a phrase bank: it is built by the engine's own
generation path, so the voices, canon, ledger, and lore all shape
it exactly as live play would.

A generation failure (model cold, endpoint down) shortens that
combo's list and moves on - a smaller pool beats a failed weave.
"""

import os


def build_pool(
    samples: int = 5, specials: int = 3, progress=None,
    pack_name: str | None = None,
) -> dict:
    """Pre-generate real outputs for every combination the game can hit.

    Keys mirror the live API's shapes:
      rumor:<phase>      {speaker, whisper, is_true, phase}
      npc:<phase>:<key>  {speaker, line, phase}
      letter             {letter}
      forge              full ItemCard dict

    `progress(combo, count)` is called after each combo is filled,
    for the weave command's console output.
    """
    from .forge import forge_item
    from .generator import generate_rumor
    from .npc import generate_line
    from .stefna import generate_letter
    from .world import current_act, load_world

    # Explicit name, not the env-resolved no-arg call: load_world is
    # lru_cached on its name argument, so load_world() would keep
    # returning whichever world the process cached first (the server's
    # default, a prior test's, whatever). The pool must read the pack
    # it was asked to weave, by name; None falls back to the env
    # default for direct callers.
    world = load_world(pack_name)
    phases = list(world.get("phases", {}).keys())
    # Mirror the live NPC path (npc.py reads the current act's
    # speakers): root-level speakers moved into acts/ in the
    # always-array shape, so reading the root gave every acts-shape
    # pack an empty npc pool.
    speakers = list(current_act(world)["speakers"].keys())

    pool: dict[str, list] = {}

    def fill(key: str, tries: int, gen, shape) -> None:
        out: list = pool.setdefault(key, [])
        for _ in range(tries):
            try:
                out.append(shape(gen()))
            except Exception:  # noqa: BLE001 - model down: shorter pool
                break
        if progress:
            progress(key, len(out))

    for ph in phases:
        fill(
            f"rumor:{ph}", samples,
            lambda ph=ph: generate_rumor(ph),
            lambda c, ph=ph: {
                "speaker": c.speaker, "whisper": c.whisper,
                "is_true": c.is_true, "phase": ph,
            },
        )

    for ph in phases:
        for key in speakers:
            fill(
                f"npc:{ph}:{key}", samples,
                lambda ph=ph, key=key: generate_line(ph, key),
                lambda line, ph=ph: {"speaker": line.speaker,
                                     "line": line.line, "phase": ph},
            )

    fill("letter", specials, generate_letter,
         lambda letter: {"letter": letter.letter})
    fill("forge", specials, forge_item, lambda c: c.model_dump())

    return pool


def ensure_current_world(pack_name: str) -> None:
    """Point the generation path at the pack being woven.

    The generators read the current world (VEFR_WORLD) at call
    time; weaving a named pack with a pool requires the generation
    to happen IN that world's voice.
    """
    if os.environ.get("VEFR_WORLD") != pack_name:
        os.environ["VEFR_WORLD"] = pack_name
