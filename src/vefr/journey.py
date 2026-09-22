"""The journey - the engine's story structure.

The engine is Norse-coded and tells its stories on the bones of
the Hero's Journey. Both commitments are *part of the skeleton*:
not a flavor toggle, not a pack-level setting, but a structural
choice the engine makes and the lore packs inherit.

This module is the single source of truth for:

  - the four Hero's Journey stages the engine runs through
  - the Elder Futhark rune that anchors each stage
  - the canonical journey-stage description that the lore
    packs can quote and the system prompts can use

Why a single data module: the lore packs (worlds/lore/norse-runes/,
worlds/lore/historical-event/, worlds/lore/norse/) all need to be
able to say "this phase is X, this rune is Y". Putting that map
in code means every lore pack can import it - no copy-paste, no
drift.

The Hero's Journey stages below are Joseph Campbell's, in their
public-domain formulation. The rune anchors are our own
arrangement - the runes are public-domain, but the mapping is
the pack's original creative work (CC BY-SA 4.0).
"""

# Engine phases -> Hero's Journey stage -> Elder Futhark rune.
#
# Why four stages and not the canonical twelve: the engine's
# `phases` array on a world pack is the player's emotional
# weather. Four phases maps cleanly to "ordinary / threshold /
# tests / return" - the four-act shape the engine was already
# running on before this module existed. A finer breakdown
# (call / refusal / mentor / threshold / ...) is the lore
# packs' job - they add the texture, the journey gives the bones.
PHASE_JOURNEY_RUNE: dict[str, dict[str, str]] = {
    "whispers": {
        "stage": "the call to adventure",
        "rune": "Fehu",
        "rune_meaning": "wealth, the seed-fire - the first gift that asks something of the player",
        "journey_question": "what small thing has changed in the town that only the protagonist notices?",
    },
    "doubts": {
        "stage": "the refusal / the threshold",
        "rune": "Thurisaz",
        "rune_meaning": "the thorn - the world says no, the player must touch the no to pass",
        "journey_question": "what does the player refuse, and what does the refusal cost?",
    },
    "feared": {
        "stage": "the tests, the allies, the enemies",
        "rune": "Kenaz",
        "rune_meaning": "the torch - what is revealed by the burning",
        "journey_question": "what is known now that wasn't known before?",
    },
    "awed": {
        "stage": "the revelation / the return",
        "rune": "Sowilo",
        "rune_meaning": "the sun - the warmth earned by the journey back",
        "journey_question": "what does the protagonist carry home that they did not carry out?",
    },
}


# Canonical journey-stage descriptions, used by lore packs and
# system prompts. Short prose, not templates.
JOURNEY_STAGE_PROSE: dict[str, str] = {
    "whispers": (
        "The town is still. The protagonist notices a small change "
        "- a bell rope moved, a name called wrong, a stranger who "
        "did not come home. The call is small. The call is real."
    ),
    "doubts": (
        "The world says no. The protagonist must answer the no to "
        "pass through. The refusal is the threshold - what they "
        "give up to go further, and what they keep that the no "
        "doesn't know about."
    ),
    "feared": (
        "The town watches. The allies and the enemies are the "
        "same people from different angles. What the protagonist "
        "learns in this act is what they did not know they were "
        "looking for."
    ),
    "awed": (
        "The return. The world is the same and not the same. What "
        "the water kept, what the fire kept, what the protagonist "
        "carries home: the same thing, changed. The home is the "
        "home. The protagonist is not."
    ),
}


# Names of the four phases the engine expects as the bones' default
# structure. A pack's `phases` dict in world.json may have any keys
# the pack author chooses; this list is what the engine uses when
# no pack is loaded (or when a pack omits `phases`).
DEFAULT_PHASES: tuple[str, ...] = ("whispers", "doubts", "feared", "awed")


def journey_for(phase: str) -> dict[str, str]:
    """Return the journey-stage + rune anchor for an engine phase.

    Falls back to a generic 'unknown phase' record for phases
    the engine doesn't know about (custom packs). Lore packs that
    want to extend the map should override PHASE_JOURNEY_RUNE in
    their own data module rather than mutate this one.
    """
    return PHASE_JOURNEY_RUNE.get(
        phase,
        {
            "stage": "an unknown passage",
            "rune": "?",
            "rune_meaning": "this phase is outside the engine's bones",
            "journey_question": "what does the world want to ask?",
        },
    )


def journey_prose_for(phase: str) -> str:
    """Return the canonical journey-stage prose for a phase."""
    return JOURNEY_STAGE_PROSE.get(phase, "(no journey prose for this phase)")


def all_phases_with_journey() -> list[tuple[str, dict[str, str]]]:
    """Every phase the engine bones know about, in journey order.

    Order is canonical: ordinary -> threshold -> tests -> return.
    Custom packs that introduce extra phases can interpolate
    between these in their own lore pack; the engine itself
    runs on these four.
    """
    return [(p, PHASE_JOURNEY_RUNE[p]) for p in DEFAULT_PHASES]