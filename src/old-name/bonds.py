"""Item bonds for the forge.

An item's bond is not its type - it is its stance toward the girl
who carries it.
"""

from pydantic import BaseModel

# The three bonds, in the order the world teaches them.
BONDS = {
    "assigned": (
        "The church's hand-me-down. Given with one hand, the other "
        "holding a ledger. It works, mostly. It never asks what she "
        "wants. The weight is the point."
    ),
    "attuned": (
        "Hers before she touched it. It was always going to be here, "
        "waiting. The world calls this improbable; the item calls it "
        "Tuesday."
    ),
    "cold": (
        "Neither gift nor burden. A tool that does not care who holds "
        "it - which is its own strange mercy."
    ),
}


def bond_prompt() -> str:
    """Render the bond rules for the system prompt."""
    return (
        "Items have a bond - the world's stance toward the girl who "
        "carries them:\n"
        "- assigned: given to her by the church's expectation. Heavy, "
        "well-made, never asked for. Works perfectly, fits badly.\n"
        "- attuned: made for her hands before she knew she needed them. "
        "Rare. The world side-eyes these.\n"
        "- cold: a tool. Neither blesses nor curses. It simply works, "
        "for anyone, which is its own quiet kindness.\n"
        "Weight the random draw: most items are assigned or cold. "
        "Attuned is rare - maybe one in five. Rarity is the point."
    )
