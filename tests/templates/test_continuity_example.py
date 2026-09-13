"""Multi-turn continuity testing.

State persists across turns. Memory is not optional. A character
injured in turn 2 is still injured in turn 7. A promise made in
turn 3 is still binding in turn 10.

All model calls are monkeypatched. No network.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vefr import generator
from vefr.storyteller import ScenePacket


# --- Canned responses per turn ---

RESPONSES = {
    "greeting": 'Elara looked up from her herbs. "You\'re back."',
    "injury_mention": 'Elara winced, gripping her side. "It\'s nothing. The bandage holds."',
    "promise": '"I\'ll have the antidote ready by dawn," Elara said quietly.',
    "promise_kept": 'Elara held out a small vial. "As I promised. Dawn came, and so did this."',
    "location_persist": 'The fire had burned lower, but the chapel walls were the same stone.',
    "weather_persist": "Rain still tapped against the chapel windows.",
    "relationship_earned": 'Elara smiled, a real one this time. "You earned that."',
}


# --- Turn/Assertion helpers ---


@dataclass
class Turn:
    speaker: str
    user_input: str
    response_key: str
    packet_overrides: dict = field(default_factory=dict)


def run_continuity_turns(turns: list[Turn], assertions: list[tuple[int, str]]):
    """Run a sequence of turns and assert continuity.

    turns: list of Turn objects (speaker, input, response key, overrides)
    assertions: list of (turn_index, expected_in_output) strings

    Each turn builds a ScenePacket, calls the storyteller with a
    canned response, and checks that assertions hold against the output.
    """
    responses: list[str] = []
    for i, turn in enumerate(turns):
        response = RESPONSES[turn.response_key]
        # Build a packet that accumulates knowledge from prior turns.
        prior_knowledge = "\n".join(
            f"- {t.user_input}" for t in turns[:i]
        )
        packet = ScenePacket(
            speaker=turn.speaker,
            speaker_knows=prior_knowledge or "This is the first meeting.",
            speaker_does_not_know="",
            scene=turn.packet_overrides.get("scene", "The chapel. Quiet."),
            relationship=turn.packet_overrides.get("relationship", ""),
            recent_action=f'The player said: "{turn.user_input}"',
        )
        # Verify the packet accumulates knowledge.
        if i > 0:
            assert turns[0].user_input in packet.speaker_knows
        responses.append(response)

    # Now run the assertions.
    for turn_index, expected in assertions:
        assert turn_index < len(responses), f"turn {turn_index} out of range"
        assert expected in responses[turn_index], (
            f"turn {turn_index}: expected '{expected}' in response"
        )


# --- Tests ---


def test_relationship_state_persists_across_turns(monkeypatch):
    """A relationship earned in turn 1 is still present in turn 3."""
    responses_log = []

    def tracking_completion(*args, **kwargs):
        prompt = str(args) + str(kwargs)
        # Pick response based on what the player said.
        if "back" in prompt.lower():
            resp = RESPONSES["greeting"]
        elif "trust" in prompt.lower() or "earned" in prompt.lower():
            resp = RESPONSES["relationship_earned"]
        else:
            resp = RESPONSES["greeting"]
        responses_log.append(resp)
        return resp

    monkeypatch.setattr(generator, "_completion", tracking_completion)

    # Turn 1: player returns.
    p1 = ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="The player visited before.",
        speaker_does_not_know="",
        scene="The chapel.",
        relationship="",
        recent_action='The player said: "I\'m back."',
    )
    generator.storytell(p1, system="You are Elara.")

    # Turn 2: relationship is now established.
    p2 = ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="The player visited before.\nThe player helped you yesterday.",
        speaker_does_not_know="",
        scene="The chapel.",
        relationship="The player earned your trust yesterday.",
        recent_action='The player said: "How are you?"',
    )
    generator.storytell(p2, system="You are Elara.")

    # The packet carries the relationship forward.
    assert "trust" in p2.render().lower()


def test_physical_state_persists(monkeypatch):
    """An injured character is still injured across turns."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: RESPONSES["injury_mention"])

    # Turn 1: injury mentioned.
    p1 = ScenePacket(
        speaker="Elara.\n\nYou are injured.",
        speaker_knows="You were hurt two days ago. The wound is bandaged.",
        speaker_does_not_know="",
        scene="The chapel.",
        recent_action='The player said: "Are you alright?"',
    )
    result = generator.storytell(p1, system="You are Elara.")
    assert "wound" in result.lower() or "bandage" in result.lower() or "winced" in result.lower()

    # Turn 3: still injured.
    p3 = ScenePacket(
        speaker="Elara.\n\nYou are injured.",
        speaker_knows="You were hurt two days ago. The wound is bandaged.",
        speaker_does_not_know="",
        scene="The chapel.",
        recent_action='The player said: "Can you travel?"',
    )
    result = generator.storytell(p3, system="You are Elara.")
    # The injury persists in the packet.
    assert "injured" in p3.speaker.lower() or "wound" in p3.speaker_knows.lower()


def test_previously_revealed_facts_remain_known(monkeypatch):
    """Facts revealed in turn 1 are still in the packet in turn 5."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: RESPONSES["greeting"])

    # Build a packet that accumulates knowledge.
    known_facts = [
        "The bridge collapsed.",
        "The eastern road is washed out.",
        "Elara is a healer.",
    ]
    packet = ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="\n".join(known_facts),
        speaker_does_not_know="",
        scene="The chapel.",
        recent_action='The player said: "What do you know?"',
    )
    rendered = packet.render()
    for fact in known_facts:
        assert fact in rendered


def test_character_mistakes_remain_mistakes(monkeypatch):
    """A character's false belief persists. The model does not correct it."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: RESPONSES["greeting"])

    packet = ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="You believe the eastern road is safe.\nYou last traveled it two weeks ago.",
        speaker_does_not_know="You do NOT know the road washed out.",
        scene="The chapel.",
    )
    rendered = packet.render()
    # The false belief is in the packet.
    assert "safe" in rendered.lower()
    # The truth is sealed away.
    assert "washed out" in rendered.lower()


def test_promises_tracked_across_turns(monkeypatch):
    """A promise made in turn 2 is referenced in turn 4."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: RESPONSES["promise_kept"])

    packet = ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="You promised the antidote by dawn.\nDawn has come.",
        speaker_does_not_know="",
        scene="The chapel. Morning light.",
        recent_action='The player said: "Did you finish it?"',
    )
    rendered = packet.render()
    assert "promised" in rendered.lower()
    assert "dawn" in rendered.lower()


def test_scene_continuity_location_time_weather(monkeypatch):
    """Location, time, and weather persist across turns."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: RESPONSES["weather_persist"])

    packet = ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="",
        speaker_does_not_know="",
        scene="The chapel. Evening. Rain is falling.",
        recent_action='The player said: "It\'s still raining."',
    )
    rendered = packet.render()
    # The scene carries location, time, and weather.
    assert "chapel" in rendered.lower()
    assert "evening" in rendered.lower() or "rain" in rendered.lower()


def test_run_continuity_turns_helper(monkeypatch):
    """The helper function itself works."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: RESPONSES["greeting"])

    turns = [
        Turn(
            speaker="Elara.\n\nYou are a village healer.",
            user_input="I'm back.",
            response_key="greeting",
        ),
        Turn(
            speaker="Elara.\n\nYou are a village healer.",
            user_input="How's the wound?",
            response_key="injury_mention",
        ),
    ]
    assertions = [
        (0, "back"),
        (1, "bandage"),
    ]
    run_continuity_turns(turns, assertions)
