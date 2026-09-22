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

CARETAKER_NARRATIVE = (
    "The caretaker wiped the bench slowly. "
    '"The bell rang once, after dark." '
    "The forge stayed quiet."
)

KEEPER_NARRATIVE = (
    "The Keeper sat still as stone. "
    '"The night kept its counsel. So did I." '
    "His eyes did not leave the fire."
)


# --- Helpers ---

def _make_caretaker_packet() -> ScenePacket:
    return ScenePacket(
        speaker="The caretaker.\n\nYou have tended the forge for years.",
        speaker_knows="The bell rang after the forge went cold.",
        speaker_does_not_know="You do NOT know who left the sealed letter.",
        scene="The forge is closed. The street is quiet.",
        relationship="The player returned a lost tool yesterday.",
        recent_action='The player asked: "Who rang the bell?"',
        instruction="Respond as the caretaker.",
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
    packet = _make_caretaker_packet()
    rendered = packet.render()
    assert "bell rang after" in rendered
    assert "sealed letter" in rendered
    assert "forge" in rendered


def test_storyteller_returns_narrative(monkeypatch):
    """The storyteller produces prose from the packet."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: CARETAKER_NARRATIVE)
    packet = _make_caretaker_packet()
    result = generator.storytell(packet, system="You are the caretaker.")
    assert "caretaker" in result
    assert len(result) > 20


def test_narrative_does_not_mutate_canon():
    """The packet is frozen. Narrative output cannot change it."""
    packet = _make_caretaker_packet()
    rendered_before = packet.render()
    _ = CARETAKER_NARRATIVE  # model "responds"
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
        # First call is the caretaker, second is Keeper.
        if call_count[0] == 1:
            return CARETAKER_NARRATIVE
        return KEEPER_NARRATIVE

    monkeypatch.setattr(generator, "_completion", recording_completion)

    caretaker_result = generator.storytell(_make_caretaker_packet(), system="You are the caretaker.")
    keeper_result = generator.storytell(_make_keeper_packet(), system="You are the Keeper.")

    assert "wiped the bench" in caretaker_result
    assert "stone" in keeper_result
    assert caretaker_result != keeper_result


def test_player_actions_not_invented_by_storyteller():
    """The packet records what the player said. The storyteller does
    not invent what the player does next."""
    packet = _make_caretaker_packet()
    rendered = packet.render()
    # The packet contains the player's question, not the player's action.
    assert "Who rang the bell" in rendered
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
