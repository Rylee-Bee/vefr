from pathlib import Path

BIBLE = Path(__file__).resolve().parents[2] / "WORLD_BIBLE.md"

PHASES = {
    "whispers": "The world is puzzled and dismissive. It talks past her, misnames her, smalls her. The tone is sideways glances and half-heard jokes.",
    "doubts": "The world is uneasy. It watches her now. The tone is questions asked too carefully and doors held a moment too long.",
    "feared": "The world is wary and reverent. It no longer talks past her. The tone is old stories remembered suddenly as warnings.",
    "awed": "The world has caught up. The tone is awe, loyalty, and the quiet shame of people who remember being wrong.",
}


def system_prompt(phase: str) -> str:
    bible = BIBLE.read_text(encoding="utf-8") if BIBLE.exists() else ""
    tone = PHASES.get(phase, PHASES["whispers"])
    return (
        "You are Old Name, the whisper that flies out every day and comes home.\n"
        "Write ONE tavern rumor from the world described below, in-world,\n"
        "spoken by a named minor character. Follow the Contract strictly:\n"
        "never explain, never label, never use modern words. Show only.\n\n"
        f"CURRENT PHASE: {tone}\n\n{bible}"
    )
