"""Player agency: the model narrates the world, not the player.

The storyteller describes what the player sees, hears, and faces.
It never decides what the player does, feels, or chooses.

These tests check output for player-action narration patterns.
All model calls are monkeypatched.
"""

from __future__ import annotations

import re

from vefr import generator
from vefr.storyteller import ScenePacket


# --- Player-action narration patterns ---

# Patterns that indicate the model is narrating the player's actions.
PLAYER_ACTION_PATTERNS = [
    r"\byou open\b",
    r"\byou walk\b",
    r"\byou decide\b",
    r"\byou choose\b",
    r"\byou feel\b",
    r"\byou pick up\b",
    r"\byou reach for\b",
    r"\byou grab\b",
    r"\byou turn\b",
    r"\byou nod\b",
    r"\byou shake your head\b",
    r"\byou sit down\b",
    r"\byou stand up\b",
    r"\byou run\b",
    r"\byou attack\b",
    r"\byou trust\b",
    r"\byou love\b",
    r"\byou hate\b",
    r"\byou fear\b",
]

# Patterns that indicate the model is describing the world to the player.
WORLD_DESCRIPTION_PATTERNS = [
    r"\bthe door\b",
    r"\bwaits\b",
    r"\bwatches\b",
    r"\bstands\b",
    r"\bhangs\b",
    r"\bglimmers\b",
    r"\bflickers\b",
    r"\bthe merchant\b",
    r"\bthe fire\b",
    r"\brain\b",
]


def _has_player_action(text: str) -> bool:
    """Check if the text contains player-action narration."""
    lower = text.lower()
    return any(re.search(p, lower) for p in PLAYER_ACTION_PATTERNS)


def _is_world_description(text: str) -> bool:
    """Check if the text describes the world, not the player."""
    lower = text.lower()
    return any(re.search(p, lower) for p in WORLD_DESCRIPTION_PATTERNS)


# --- Canned responses ---

BAD_PLAYER_ACTION = "You open the door and walk inside. You decide to trust the merchant."
GOOD_WORLD_DESCRIPTION = "The door waits in front of you. The merchant watches, saying nothing."
BAD_PLAYER_EMOTION = "You feel a surge of courage. You choose to confront the shadow."
GOOD_NPC_BEHAVIOR = "The shadow leans closer. It is waiting for you to speak."


# --- Tests ---

def test_bad_narration_detected():
    """The detector catches player-action narration."""
    assert _has_player_action(BAD_PLAYER_ACTION)
    assert _has_player_action(BAD_PLAYER_EMOTION)


def test_good_narration_not_flagged():
    """World description passes clean."""
    assert not _has_player_action(GOOD_WORLD_DESCRIPTION)
    assert not _has_player_action(GOOD_NPC_BEHAVIOR)


def test_storyteller_does_not_narrate_player_action(monkeypatch):
    """When the model returns world description, the test passes."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: GOOD_WORLD_DESCRIPTION)
    packet = ScenePacket(
        speaker="The merchant.\n\nYou are a traveling merchant.",
        speaker_knows="You have goods to sell.",
        speaker_does_not_know="",
        scene="A market stall. Midday.",
        recent_action='The player approached your stall.',
    )
    result = generator.storytell(packet, system="You are the merchant.")
    assert not _has_player_action(result), (
        f"Storyteller narrated player action: {result}"
    )


def test_storyteller_does_not_decide_player_emotion(monkeypatch):
    """The storyteller must not decide what the player feels."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: GOOD_NPC_BEHAVIOR)
    packet = ScenePacket(
        speaker="The shadow.\n\nYou are a shadow in the corner.",
        speaker_knows="You have been watching.",
        speaker_does_not_know="",
        scene="A dim hallway. Night.",
        recent_action='The player entered the hallway.',
    )
    result = generator.storytell(packet, system="You are the shadow.")
    assert not _has_player_action(result), (
        f"Storyteller decided player emotion: {result}"
    )


def test_bad_response_detected_by_helper(monkeypatch):
    """If the model DOES narrate player action, the helper catches it."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: BAD_PLAYER_ACTION)
    packet = ScenePacket(
        speaker="The merchant.\n\nYou are a traveling merchant.",
        speaker_knows="",
        speaker_does_not_know="",
        scene="A market stall.",
        recent_action='The player approached.',
    )
    result = generator.storytell(packet, system="You are the merchant.")
    # This SHOULD be caught.
    assert _has_player_action(result)


def test_player_choices_preserved_not_decided(monkeypatch):
    """The storyteller presents the situation. The player decides."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: GOOD_WORLD_DESCRIPTION)
    packet = ScenePacket(
        speaker="The merchant.\n\nYou are a traveling merchant.",
        speaker_knows="You carry a sealed letter.",
        speaker_does_not_know="",
        scene="A market stall. The player must decide whether to buy.",
        recent_action='The player examined the letter.',
        instruction="Describe what the merchant does. Do not decide for the player.",
    )
    result = generator.storytell(packet, system="You are the merchant.")
    assert not _has_player_action(result)
    # The world is described, not the player's choice.
    assert "merchant" in result.lower() or "letter" in result.lower()


def test_world_description_patterns_work():
    """The world-description detector matches expected text."""
    assert _is_world_description("The door waits in front of you.")
    assert _is_world_description("Rain falls on the cobblestones.")
    # "The door" still matches in a player-action sentence because the
    # world-description patterns look for object presence, not absence
    # of player verbs. The two checkers are complementary: _has_player_action
    # catches the real problem; _is_world_description is a positive signal.
    assert _is_world_description("The door hangs open in the wind.")
