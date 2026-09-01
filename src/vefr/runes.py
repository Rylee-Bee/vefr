"""The rune cast - the engine's one stochastic surface.

The lore, the logbok, the journey, the surface, the contract, the
tree, the journal, the export, the backup - all deterministic,
all replayable. The runes are the exception. After everything
has been laid down (lore pack chosen, logbok.md written, journey
mapped), the cast is the one moment where what happens is *up
to the world*.

**The rune cast is not a memory.** The engine's journal is the
memory: atomic, dated, replayable. The rune cast is what memory
can't capture. Same seed -> same cast - within a session-minute -
but the seed changes every minute, so the cast is never the same
twice across sessions. The tree is the memory. The runes are
the *absence* of one.

The Hero's Journey *is* the deterministic backbone. The four
phases anchored to four runes (Fehu, Thurisaz, Kenaz, Sowilo)
are the bones. The cast is what lives *outside* the journey: the
two free runes in every cast (what_is, what_asks) are the
random cards the deterministic structure leaves room for.
**The journey is the shape. The cast is the surprise inside
the shape.**

The runes are 24 Elder Futhark runes in three aettir (groups of
eight). The cast is three runes in three positions:

  what_was    - the past, what the world is rooted in
  what_is     - the present, what the world is speaking through
  what_asks   - the question, what the world wants from the player

Same seed -> same cast. The seed is derived from (world, time,
session) so different playthroughs vary but a given playthrough is
consistent - the same cast for the same moment, so the player
can replay and find the same world.
"""

import hashlib
import random
from dataclasses import dataclass


# The 24 Elder Futhark runes. Each has a name, the stave (the
# shape carved into wood), the aettir it belongs to, a short meaning
# (one line for the engine prompt), a long meaning (the lore
# pack's prose interpretation from cards.md), and the engine
# phase this rune anchors in the Hero's Journey.
#
# Staves are the Unicode Runic block (U+16A0 - U+16F0); the
# codepoints used here are the standard Elder Futhark.
@dataclass(frozen=True)
class Rune:
    name: str
    stave: str
    aettir: int  # 1, 2, or 3
    short: str
    long: str
    engine_phase: str | None  # None = the rune isn't a journey anchor


RUNES: tuple[Rune, ...] = (
    # First aettir (the gods / the call)
    Rune("Fehu", "\u16A0", 1, "wealth, the seed-fire",
         "the first gift that asks something of the player",
         "whispers"),
    Rune("Uruz", "\u16A2", 1, "the aurochs, the wild ox",
         "strength that doesn't know it's strength yet",
         None),
    Rune("Thurisaz", "\u16A6", 1, "the thorn, the giant",
         "the world says no - the player must touch the no to pass",
         "doubts"),
    Rune("Ansuz", "\u16A8", 1, "the god, the word, the message",
         "a witness speaks; a keeper listens",
         None),
    Rune("Raido", "\u16B1", 1, "the ride, the road",
         "the player's first going",
         None),
    Rune("Kenaz", "\u16B2", 1, "the torch, the ulcer",
         "what is revealed by the burning",
         "feared"),
    Rune("Gebo", "\u16B3", 1, "the gift, the exchange",
         "the keeper gives; the player receives; both are changed",
         None),
    Rune("Wunjo", "\u16B9", 1, "joy, the wind-smooth stone",
         "the moment of unexpected welcome",
         None),

    # Second aettir (the natural world / the tests)
    Rune("Hagalaz", "\u16BA", 2, "hail, the seed-grain",
         "the event that breaks the cycle",
         None),
    Rune("Nauthiz", "\u16BE", 2, "need, the constraint",
         "the wall; also the door",
         None),
    Rune("Isa", "\u16C1", 2, "ice, the stillness",
         "the held breath between two phases",
         None),
    Rune("Jera", "\u16C3", 2, "the year, the harvest",
         "what was sown is reaped",
         None),
    Rune("Eihwaz", "\u16C4", 2, "the yew, the axis",
         "the long walk; what endures",
         None),
    Rune("Perthro", "\u16CA", 2, "the dice-cup, the hidden",
         "the lot is cast",
         None),
    Rune("Algiz", "\u16CE", 2, "the elk-sedge, the sanctuary",
         "the hearth; the room that stays shut",
         None),
    Rune("Sowilo", "\u16F0", 2, "the sun, the whirling",
         "the gold moment; the warmth earned by the journey back",
         "awed"),

    # Third aettir (the deep / the return)
    Rune("Tiwaz", "\u16DF", 3, "Tyr, the star, the right hand",
         "the vow; the word that cannot be taken back",
         None),
    Rune("Berkano", "\u16D2", 3, "the birch, the birth",
         "the second birth; the new self",
         None),
    Rune("Ehwaz", "\u16D3", 3, "the horse, the partnership",
         "whoever walks alongside",
         None),
    Rune("Mannaz", "\u16D7", 3, "the human, the self",
         "the protagonist themselves",
         None),
    Rune("Laguz", "\u16DA", 3, "the water, the leek",
         "the crossing; the gold in the water",
         None),
    Rune("Ingwaz", "\u16DC", 3, "the seed, the gestation",
         "the time before the journey begins",
         None),
    Rune("Othala", "\u16DF", 3, "the heritage, the homeland",
         "the home that was changed by being left",
         None),
    Rune("Dagaz", "\u16E1", 3, "the day, the dawn",
         "the morning the protagonist walks into",
         None),
)


# The cast has three positions. Each has a name the lore pack
# uses, and a short engine phrase that goes in the system prompt.
POSITIONS: tuple[tuple[str, str], ...] = (
    ("what_was", "the past - what the world is rooted in"),
    ("what_is", "the present - what the world is speaking through"),
    ("what_asks", "the question - what the world wants from the player"),
)


# Phase -> deterministic rune. Phases not in this map fall through
# to a fully random cast (so custom packs with extra phases still
# get stochastic surfaces, just without the journey-anchor rune).
#
# This is the same map as journey.PHASE_JOURNEY_RUNE, but as a
# direct Rune lookup for the cast machinery (so the rune registry
# is the single source of truth for the shape).
PHASE_ANCHOR: dict[str, Rune] = {
    r.engine_phase: r for r in RUNES if r.engine_phase
}


def seed_for(*parts: str | int) -> int:
    """Derive a deterministic integer seed from any number of parts.

    Same inputs -> same seed -> same cast. Authors can replay a
    moment by remembering the parts that fed the seed.
    """
    raw = "|".join(str(p) for p in parts)
    h = hashlib.sha256(raw.encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big")


def cast(seed: int, n: int = 3) -> list[Rune]:
    """Cast n runes with the given seed. Same seed -> same cast.

    The default n=3 matches the three positions (what_was, what_is,
    what_asks). Custom positions are possible but the engine's
    system prompts assume three.
    """
    rng = random.Random(seed)
    return rng.sample(RUNES, n)


def cast_for(seed: int, phase: str | None = None) -> list[tuple[str, Rune]]:
    """A cast with positions filled in.

    If `phase` matches a journey anchor (one of the engine's four
    phases), the *first* rune (what_was) is that anchor - the world
    is rooted in that phase's rune. The remaining positions draw
    from the full 24, with the anchor excluded.

    If `phase` is None or unknown, all three positions draw freely
    from the full 24.
    """
    anchored = PHASE_ANCHOR.get(phase) if phase else None
    pool = [r for r in RUNES if r is not anchored]
    rng = random.Random(seed)
    # Pick n-1 extra runes (or n if no anchor) - never reusing the
    # anchor. n=3 with anchor means pool.sample(2); n=3 without
    # anchor means pool.sample(3).
    need = 2 if anchored else 3
    rest = rng.sample(pool, need)
    runes: list[Rune] = ([anchored] if anchored else []) + rest
    out: list[tuple[str, Rune]] = []
    for i, (pos_name, pos_phrase) in enumerate(POSITIONS):
        if i < len(runes):
            out.append((pos_name, runes[i]))
    return out


def render_for_prompt(cast_result: list[tuple[str, Rune]]) -> str:
    """Render a cast for inclusion in a system prompt.

    Short, dense. The model reads the rune names and the position
    meanings and weaves the cast into its voice. The model doesn't
    need the prose interpretations - the cast carries shape, the
    lore pack carries voice.
    """
    lines = ["CAST FOR THIS TURN (runes that landed today):"]
    for pos_name, rune in cast_result:
        phrase = next(p for n, p in POSITIONS if n == pos_name)
        lines.append(f"  {rune.stave} {rune.name} ({pos_name}) - {rune.short}")
        lines.append(f"    {phrase}")
    return "\n".join(lines)