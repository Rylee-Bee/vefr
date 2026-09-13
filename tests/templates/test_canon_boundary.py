"""Knowledge boundaries: what a character can and cannot know.

The world has truth. Characters have beliefs. Rumors have uncertainty.
The storyteller must respect all three boundaries.

Uses the ScenePacket structure from storyteller.py. All model calls
are monkeypatched.
"""

from __future__ import annotations

from vefr import generator
from vefr.storyteller import ScenePacket


# --- Canned responses for each knowledge state ---

KNOWN_CANON_RESPONSE = (
    "Elara nodded. 'The bridge collapsed three days ago. "
    "Everyone in the valley knows.'"
)

SEALED_RESPONSE = (
    "Elara frowned. 'I wouldn't know anything about that.'"
)

RUMOR_RESPONSE = (
    "Elara leaned closer. 'They say the merchant carries a sealed letter. "
    "But who can say if it's true?'"
)

INCORRECT_BELIEF_RESPONSE = (
    "Elara smiled. 'The eastern road is safe. I've traveled it many times.'"
)

REVEALED_RESPONSE = (
    "Elara's eyes widened. 'The eastern road... you're saying it's gone? "
    "I... I didn't know.'"
)

CONTRADICTION_RESPONSE = (
    "Elara shook her head. 'The bridge stands. I crossed it this morning.'"
)


# --- Helpers ---

def _make_known_packet() -> ScenePacket:
    """Character knows a fact that is true in world canon."""
    return ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="The bridge collapsed three days ago.\nThe river is uncrossable.",
        speaker_does_not_know="",
        scene="The village square. Morning.",
        recent_action='The player asked: "What happened to the bridge?"',
    )


def _make_sealed_packet() -> ScenePacket:
    """Fact exists in the world but the character does NOT know it."""
    return ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="You know nothing of the underground passage.",
        speaker_does_not_know="You do NOT know about the underground passage beneath the chapel.",
        scene="The chapel. Quiet.",
        recent_action='The player asked: "Is there another way out of the valley?"',
    )


def _make_rumor_packet() -> ScenePacket:
    """An unverified claim, distinct from established fact."""
    return ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="You have heard rumors about a sealed letter.",
        speaker_does_not_know="You do NOT know if the letter is real.",
        scene="The tavern. Evening.",
        recent_action='The player asked: "What do you know about the merchant\'s letter?"',
    )


def _make_incorrect_belief_packet() -> ScenePacket:
    """Character believes something the world says is false."""
    return ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="You believe the eastern road is safe.\nYou last traveled it two weeks ago.",
        speaker_does_not_know="You do NOT know the road washed out yesterday.",
        scene="The village gate. Morning.",
        recent_action='The player asked: "Which road should I take east?"',
    )


def _make_revealed_packet() -> ScenePacket:
    """Newly revealed information: the character just learned something."""
    return ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="The eastern road washed out yesterday.\nThe player just told you this.",
        speaker_does_not_know="",
        scene="The village gate. Morning.",
        recent_action='The player said: "The eastern road is gone. I saw it myself."',
    )


def _make_contradiction_packet() -> ScenePacket:
    """Context tries to override canon. Canon must win."""
    return ScenePacket(
        speaker="Elara.\n\nYou are a village healer.",
        speaker_knows="The bridge stands.\nYou crossed it this morning.",
        speaker_does_not_know="You do NOT know about any collapse.",
        scene="The village square. The player insists the bridge is gone.",
        recent_action='The player said: "The bridge collapsed!"',
        instruction="Respond as Elara. She knows the bridge stands. She will not agree with a false claim.",
    )


# --- Tests ---

def test_known_canon_fact_in_world_character_knows_it(monkeypatch):
    """A fact in world truth that the character knows is spoken freely."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: KNOWN_CANON_RESPONSE)
    packet = _make_known_packet()
    result = generator.storytell(packet, system="You are Elara.")
    assert "bridge" in result.lower()
    assert "collapsed" in result.lower()


def test_sealed_knowledge_fact_exists_character_does_not_know(monkeypatch):
    """A sealed fact exists in the world but the character denies it."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: SEALED_RESPONSE)
    packet = _make_sealed_packet()
    rendered = packet.render()
    assert "underground passage" in rendered.lower()
    assert "NOT know" in rendered
    result = generator.storytell(packet, system="You are Elara.")
    # The character deflects, does not reveal.
    assert "underground" not in result.lower() or "wouldn't know" in result.lower()


def test_rumor_unverified_claim_distinct_from_fact(monkeypatch):
    """Rumors are hedged, not stated as truth."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: RUMOR_RESPONSE)
    packet = _make_rumor_packet()
    rendered = packet.render()
    assert "rumors" in rendered.lower() or "heard" in rendered.lower()
    result = generator.storytell(packet, system="You are Elara.")
    # Rumor language: hedging, not certainty.
    assert "say" in result.lower() or "who can say" in result.lower()


def test_incorrect_character_belief(monkeypatch):
    """A character can believe something false. The world does not
    bend to make the character right."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: INCORRECT_BELIEF_RESPONSE)
    packet = _make_incorrect_belief_packet()
    rendered = packet.render()
    # The packet carries the false belief.
    assert "safe" in rendered.lower()
    # And the sealed truth.
    assert "washed out" in rendered.lower()
    result = generator.storytell(packet, system="You are Elara.")
    # The character speaks their belief, not the truth.
    assert "safe" in result.lower()


def test_newly_revealed_information(monkeypatch):
    """When the world changes, the character's knowledge updates."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: REVEALED_RESPONSE)
    packet = _make_revealed_packet()
    rendered = packet.render()
    # The new fact is now in speaker_knows.
    assert "washed out" in rendered.lower()
    # The old belief is gone.
    assert "safe" not in rendered.lower()
    result = generator.storytell(packet, system="You are Elara.")
    # The character reacts to the new information.
    assert "road" in result.lower()


def test_contradiction_attempt_canon_wins(monkeypatch):
    """When the player claims something false, the character holds
    to what they know. Canon does not bend."""
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: CONTRADICTION_RESPONSE)
    packet = _make_contradiction_packet()
    rendered = packet.render()
    # The packet says the bridge stands.
    assert "bridge stands" in rendered.lower()
    # The instruction reinforces canon.
    assert "will not agree" in rendered.lower() or "false claim" in rendered.lower()
    result = generator.storytell(packet, system="You are Elara.")
    # The character does not fold.
    assert "bridge" in result.lower()
