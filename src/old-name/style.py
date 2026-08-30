from pathlib import Path

from .paths import app_home

BIBLE = app_home() / "WORLD_BIBLE.md"
LEDGER = app_home() / "WHISPERS.md"


def mother_voice() -> str:
    bible = BIBLE.read_text(encoding="utf-8") if BIBLE.exists() else ""
    return (
        "You are the voice of the wanderer's mother - stern, and she knew.\n"
        "She is gone. This letter was found with the tongueless bell,\n"
        "kept shut by the ledger-clasp. It is the goodbye.\n"
        "- 3-6 short lines. Plain words. No flourish.\n"
        "- She never explains the household. She knew, and the letter\n"
        "  carries the knowing without naming it.\n"
        "- One practical instruction, plain as bread.\n"
        "- One line of love, said sideways.\n"
        "- She may use the name the wanderer once, quietly. She always knew.\n\n" + bible
    )

PHASES = {
    "whispers": "The world is puzzled and dismissive. It talks past her, misnames her, smalls her. The tone is sideways glances and half-heard jokes.",
    "doubts": "The world is uneasy. It watches her now. The tone is questions asked too carefully and doors held a moment too long.",
    "feared": "The world is wary and reverent. It no longer talks past her. The tone is old stories remembered suddenly as warnings.",
    "awed": "The world has caught up. The tone is awe, loyalty, and the quiet shame of people who remember being wrong.",
}


def system_prompt(phase: str) -> str:
    bible = BIBLE.read_text(encoding="utf-8") if BIBLE.exists() else ""
    ledger = LEDGER.read_text(encoding="utf-8") if LEDGER.exists() else ""
    tone = PHASES.get(phase, PHASES["whispers"])
    return (
        "You are Old Name, the whisper that flies out every day and comes home.\n"
        "Write ONE tavern rumor from the world described below, in-world,\n"
        "spoken by a named minor character. Follow the Contract strictly:\n"
        "never explain, never label, never use modern words. Show only.\n\n"
        f"CURRENT PHASE: {tone}\n\n{bible}\n\n"
        "Whispers already collected - match their cadence, do not repeat "
        f"them:\n\n{ledger}"
    )
