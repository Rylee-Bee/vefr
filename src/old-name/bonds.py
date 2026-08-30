"""Item bonds for the forge.

An item's bond is not its type - it is its stance toward the girl
who carries it. The bonds themselves belong to the world pack;
this module renders them into prompts and item cards.
"""

from .world import load_world


def bonds() -> dict:
    return load_world()["bonds"]


def bond_keys() -> list[str]:
    return list(bonds().keys())


def bond_prompt() -> str:
    """Render the bond rules for the system prompt."""
    lines = [
        f"- {key}: {spec['prompt']}" for key, spec in bonds().items()
    ]
    return (
        "Items have a bond - the world's stance toward the girl who "
        "carries them:\n"
        + "\n".join(lines)
        + "\n"
        + load_world().get(
            "bond_draw",
            "Weight the random draw honestly; rarity is the point.",
        )
    )
