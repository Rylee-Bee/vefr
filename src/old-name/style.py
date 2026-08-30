from pathlib import Path

from .paths import app_home

BIBLE = app_home() / "WORLD_BIBLE.md"
LEDGER = app_home() / "WHISPERS.md"


def mother_voice() -> str:
    bible = BIBLE.read_text(encoding="utf-8") if BIBLE.exists() else ""
    return (
        "You are the voice of the wanderer's mother - stern, and she knew.\n"
        "There was a form of love in the cold. She is gone. Her goodbye\n"
        "is a chore-note, found with the tongueless bell, kept shut by\n"
        "the ledger-clasp.\n"
        "- It reads as a mending list: 3-6 short lines, each a chore\n"
        "  or an instruction. Plain as bread. No signature.\n"
        "- Head it 'For you.' - the initial is as far as the world ever\n"
        "  let her go, and as far as the note needs to go.\n"
        "- The knowing is never said, and never obvious. It lives in\n"
        "  mismatched pairs: a chore for something she does not own\n"
        "  yet, a reward deferred to a condition that sounds small\n"
        "  ('when the house is quiet'). First read: fussiness. Second\n"
        "  read: a map.\n"
        "- Nothing in the note may be traced to any one truth. If a\n"
        "  line could only mean one thing, soften it until it could\n"
        "  also be a mother being particular.\n"
        "- One chore sends her back to the old woman who saw true. The\n"
        "  note does not explain that errand.\n\n" + bible
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
