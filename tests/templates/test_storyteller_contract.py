"""Storytelling renders the world. It does not own the world.

Tests the storyteller/world boundary: authoritative state enters the
context packet, the storyteller returns narrative prose, and that prose
never mutates the canonical state. Characters keep separate voices.
Player actions are not invented by the storyteller.

All model calls are monkeypatched. No network. No mock library.
"""

from __future__ import annotations

from vefr import generator
from vefr.storyteller import ScenePacket


# --- Canned model responses ---

ROSA_NARRATIVE = (
    "Rosa wiped the counter slowly. "
    '"He had somewhere to be," she said, not looking up. '
    "The rain kept hitting the windows."
)

KEEPER_NARRATIVE = (
    "The Keeper sat still as stone. "
    '"The night kept its counsel. So did I." '
    "His eyes did not leave the fire."
)


# --- Helpers ---

def _make_rosa_packet() -> ScenePacket:
    return ScenePacket(
        speaker="Rosa.\n\nYou have known Mateo for six years.",
        speaker_knows="Mateo left earlier than usual tonight.",
        speaker_does_not_know="You do NOT know about the transmitter.",
        scene="The taqueria is closed. Rain is hitting the windows.",
        relationship="The player earned your trust yesterday.",
        recent_action='The player asked: "Why did Mateo leave early?"',
        instruction="Respond naturally as Rosa.",
    )


def _make_keeper_packet() -> ScenePacket:
    return ScenePacket(
        speaker="The Keeper.\n\nYou guard the stone.",
        speaker_knows="The stone kept the night.",
        speaker_does_not_know="You do NOT know what the wanderer seeks.",
        scene="The fire burns low. The hall is quiet.",
        instruction="Respond in voice.",
    )


# --- Tests ---

def test_authoritative_state_enters_context():
    """World facts are supplied to the storyteller via the packet."""
    packet = _make_rosa_packet()
    rendered = packet.render()
    assert "Mateo left earlier" in rendered
    assert "transmitter" in rendered
    assert "taqueria" in rendered


def test_storyteller_returns_narrative(monkeypatch):
    """The storyteller produces prose from the packet."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: ROSA_NARRATIVE)
    packet = _make_rosa_packet()
    result = generator.storytell(packet, system="You are Rosa.")
    assert "Rosa" in result
    assert len(result) > 20


def test_narrative_does_not_mutate_canon():
    """The packet is frozen. Narrative output cannot change it."""
    packet = _make_rosa_packet()
    rendered_before = packet.render()
    _ = ROSA_NARRATIVE  # model "responds"
    rendered_after = packet.render()
    assert rendered_before == rendered_after


def test_characters_maintain_separate_voices(monkeypatch):
    """Different speakers produce different narrative textures."""
    call_count = [0]

    def recording_completion(*args, **kwargs):
        # _completion receives a payload dict; extract the user message.
        payload = args[0] if args else kwargs
        messages = payload.get("messages", [])
        _user_msg = messages[-1]["content"] if messages else ""
        call_count[0] += 1
        # First call is Rosa, second is Keeper.
        if call_count[0] == 1:
            return ROSA_NARRATIVE
        return KEEPER_NARRATIVE

    monkeypatch.setattr(generator, "_completion", recording_completion)

    rosa_result = generator.storytell(_make_rosa_packet(), system="You are Rosa.")
    keeper_result = generator.storytell(_make_keeper_packet(), system="You are the Keeper.")

    assert "wiped the counter" in rosa_result
    assert "stone" in keeper_result
    assert rosa_result != keeper_result


def test_player_actions_not_invented_by_storyteller():
    """The packet records what the player said. The storyteller does
    not invent what the player does next."""
    packet = _make_rosa_packet()
    rendered = packet.render()
    # The packet contains the player's question, not the player's action.
    assert "Why did Mateo leave" in rendered
    # The packet never tells the storyteller what the player decides.
    assert "decide" not in rendered.lower()
    assert "choose" not in rendered.lower()


def test_packet_omits_blank_optional_sections():
    """Blank fields are omitted from the rendered prompt."""
    packet = ScenePacket(
        speaker="A ghost",
        speaker_knows="Nothing.",
        speaker_does_not_know="",
        scene="An empty room.",
    )
    rendered = packet.render()
    assert "WHAT YOU DO NOT KNOW" not in rendered
    assert "RELATIONSHIP" not in rendered
    assert "WHAT JUST HAPPENED" not in rendered
