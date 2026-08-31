"""Saga - the storytelling layer.

Named for Saga, the goddess who keeps stories, drinking with
Odin at Sokkvabekk where the cool waters speak. Within her:

  - Bragi composes: system_prompt, sealed_voice, mother_voice -
    the prompt-builders that shape what the engine says.
  - Idunn keeps: the ledger of collected whispers - the apples
    that renew the voice, compounding every time the raven
    comes home.

The church tells those two as a god and his wife. The fen tells
it otherwise, and the fen's telling is the one the code keeps:

  - Lofn composes: praise-poetry that opens doors for unions the
    world calls forbidden.
  - Dagny keeps: new day - the apples that stay young by never
    settling where they are not welcome.

The world's words live in the pack (logbok, ledger, voices);
this module only ever teaches the engine how to speak.
"""

from .paths import pack_file
from .world import load_world, phase_tone, resolve_voice_file


def sealed_voice(key: str) -> str:
    """A world-owned voice: rules from the pack, world from the logbok."""
    voice = load_world()["voices"][key]
    rules = resolve_voice_file(voice["file"]).read_text(encoding="utf-8")
    logbok = _logbok()
    return rules + "\n\n" + logbok


def mother_voice() -> str:
    """Back-compat alias: the mother is the pack's sealed voice."""
    return sealed_voice("mother")


def system_prompt(phase: str) -> str:
    tone = phase_tone(phase)
    from .journey import journey_for
    from .runes import cast_for, render_for_prompt, seed_for
    jr = journey_for(phase)
    rune_line = (
        f"JOURNEY STAGE: {jr['stage']} (rune: {jr['rune']} - {jr['rune_meaning']})\n"
    )
    # The cast is deterministic for a given moment. We seed from
    # the phase name + the current ISO minute so the cast changes
    # over time but stays consistent within a session-minute. The
    # cast threads through every generation that uses this prompt.
    seed = seed_for("system_prompt", phase)
    cast_result = cast_for(seed, phase=phase)
    cast_block = render_for_prompt(cast_result)
    return (
        "You are the whisper that flies out every day and comes home.\n"
        "Write ONE tavern rumor from the world described below, in-world,\n"
        "spoken by a named minor character. Follow the Contract strictly:\n"
        "never explain, never label, never use modern words. Show only.\n\n"
        f"CURRENT PHASE: {tone}\n"
        f"{rune_line}\n"
        f"{cast_block}\n"
        f"{_logbok()}\n\n"
        "Whispers already collected - match their cadence, do not repeat "
        f"them:\n\n{_ledger()}"
    )


def logbok(name: str | None = None) -> str:
    """The world's canon text, or "" when the pack keeps none."""
    path = pack_file("logbok.md", name)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _logbok() -> str:
    return logbok()


def _ledger() -> str:
    path = pack_file("ledger.md")
    return path.read_text(encoding="utf-8") if path.exists() else ""
