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

The world's words live in the pack (bible, ledger, voices);
this module only ever teaches the engine how to speak.
"""

from .paths import pack_file
from .world import load_world, phase_tone


def sealed_voice(key: str) -> str:
    """A world-owned voice: rules from the pack, world from the bible."""
    voice = load_world()["voices"][key]
    rules = pack_file(voice["file"]).read_text(encoding="utf-8")
    bible = _bible()
    return rules + "\n\n" + bible


def mother_voice() -> str:
    """Back-compat alias: the mother is the pack's sealed voice."""
    return sealed_voice("mother")


def system_prompt(phase: str) -> str:
    tone = phase_tone(phase)
    from .journey import journey_for
    jr = journey_for(phase)
    rune_line = (
        f"JOURNEY STAGE: {jr['stage']} (rune: {jr['rune']} - {jr['rune_meaning']})\n"
    )
    return (
        "You are the whisper that flies out every day and comes home.\n"
        "Write ONE tavern rumor from the world described below, in-world,\n"
        "spoken by a named minor character. Follow the Contract strictly:\n"
        "never explain, never label, never use modern words. Show only.\n\n"
        f"CURRENT PHASE: {tone}\n"
        f"{rune_line}\n"
        f"{_bible()}\n\n"
        "Whispers already collected - match their cadence, do not repeat "
        f"them:\n\n{_ledger()}"
    )


def bible(name: str | None = None) -> str:
    """The world's canon text, or "" when the pack keeps none."""
    path = pack_file("bible.md", name)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _bible() -> str:
    return bible()


def _ledger() -> str:
    path = pack_file("ledger.md")
    return path.read_text(encoding="utf-8") if path.exists() else ""
