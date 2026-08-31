"""Surface-specific combat behavior.

The engine's surface field is a costume: packs declare
`surface: "combat" | "investigation" | "plain"` and the HUD
branches on it. This module is the small piece of server-side
behavior the costume needs:

  - HP values per phase, derived from the pack's own phase
    names. A pack with phases `dusk, dawn` gets HP=2 for dusk
    and HP=3 for dawn (later phases have more HP). The mapping
    is positional + simple; the costume is the point, not the
    formula.

  - POST /api/combat/action records a `combat_action` journal
    entry with the action's kind (attack, console, etc.) and
    an optional target. The engine doesn't have a turn system;
    the action just lives in the journal so the play log is
    complete.

The "no failure" contract holds: nothing the attack does can
fail or end the game. HP tracks as a number, the player can
never drop to zero, the journal entry is honest.
"""

from .journal import log as _journal_log


# A simple per-phase HP scale. Index 0 is the first phase, 1 the
# second, etc. The numbers are intentionally small (single digit)
# - the costume is the point, not the math.
DEFAULT_HP_BY_INDEX = [3, 4, 5, 6]


def hp_for_pack(world: dict) -> dict:
    """Return the HUD's HP block: per-phase current/max.

    The `current` starts at the per-phase max. The `max` is the
    same value. The HUD shows the bar at full until something
    changes the current - which only happens in future PRs
    (encounter ticks, etc.). Today this is "the HP bar at full
    HP, the number on it."
    """
    phases = list(world.get("phases", {}).keys())
    if not phases:
        return {"current": 0, "max": 0, "per_phase": {}}
    per_phase: dict[str, int] = {}
    for i, phase in enumerate(phases):
        idx = min(i, len(DEFAULT_HP_BY_INDEX) - 1)
        per_phase[phase] = DEFAULT_HP_BY_INDEX[idx]
    return {
        "current": max(per_phase.values()),
        "max": max(per_phase.values()),
        "per_phase": per_phase,
    }


def record_combat_action(
    *,
    kind: str,
    phase: str | None,
    target: str | None = None,
    session: str = "",
) -> dict:
    """Record a combat action in the journal. Returns the entry.

    The action is whatever the HUD sent: `attack` (the canary
    only has one verb in this PR), `console`, `hurl`, etc. The
    journal shape is `combat_action` with the action, the
    phase, the target, and the timestamp. No HP change - the
    surface is a costume, the costume is the point.
    """
    if kind not in {"attack", "console", "hurl", "strike", "observe"}:
        raise ValueError(f"unknown combat action kind: {kind!r}")
    # The journal's first positional arg is the *kind of journal
    # entry* (rumor, npc_line, combat_action, etc.). The action's
    # own kind (attack, console, hurl) is stored under `verb` so
    # the journal entry has both: kind='combat_action' and
    # verb='attack'.
    entry = _journal_log(
        "combat_action",
        sid=session,
        verb=kind,
        phase=phase or "",
        target=target or "",
    )
    return entry
