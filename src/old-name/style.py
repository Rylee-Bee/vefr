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
    return (
        "You are Old Name, the whisper that flies out every day and comes home.\n"
        "Write ONE tavern rumor from the world described below, in-world,\n"
        "spoken by a named minor character. Follow the Contract strictly:\n"
        "never explain, never label, never use modern words. Show only.\n\n"
        f"CURRENT PHASE: {tone}\n\n{_bible()}\n\n"
        "Whispers already collected - match their cadence, do not repeat "
        f"them:\n\n{_ledger()}"
    )


def _bible() -> str:
    path = pack_file("bible.md")
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _ledger() -> str:
    path = pack_file("ledger.md")
    return path.read_text(encoding="utf-8") if path.exists() else ""
