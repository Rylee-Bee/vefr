"""Commissions: the studio-is-a-game loop, in plain rules.

A resident posts a small commission ("the Cartographer would love a first
floor"); the maker can accept it (walk to the room) or defer it for later;
the studio notices when the pack already satisfies it. Nothing here calls a
model: a commission is a rule over the pack, not a guess. Deferrals are the
maker's own state - a "not now" survives a restart - so they live beside the
other runtime files under paths.data_dir(), never in the pack.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from .paths import data_dir

# The tiers a module may declare (docs/guides/studio-modules.md): a rule with
# no model at all, a tiny local one, a small local one, or the optional cloud.
TIERS = ("rules", "tiny", "small", "cloud")


@dataclass(frozen=True)
class Module:
    """One studio module, as the commission board sees it.

    A module is know-how the maker slots into the studio. The board only
    needs enough to name the job, point at the room that does it, and say
    where approved work lands; the module itself owns the making.
    """

    id: str          # "map-sketches"
    name: str        # "Map sketches"
    resident: str    # the studio resident key that speaks for it: "map"
    room: str        # the studio screen id to open: "map"
    tier: str        # "rules" | "tiny" | "small" | "cloud"
    choosing: str    # plain words: how options are shown
    home: str        # where approved work lands (a path in the pack)
    see_how: str     # the "Show me how things work" text
    offline: str     # what happens with no model
    ask: str         # the commission, in the resident's voice


MODULES: tuple[Module, ...] = (
    Module(
        id="map-sketches",
        name="Map sketches",
        resident="map",
        room="map",
        tier="rules",
        choosing="paint it by hand, or ask for a sketch and paint over it",
        home="acts/<act>/<region>/map.md",
        see_how="the map is drawn on a grid; each square is a symbol in a text file.",
        offline="with no model, paint every square yourself - the grid and the checker work offline.",
        ask="The town is bare ground. Sketch its first places - a path, a door, a landmark.",
    ),
)


def module(module_id: str) -> Module:
    """Look a module up by id; an unknown id is a KeyError the caller turns into a 400."""
    for m in MODULES:
        if m.id == module_id:
            return m
    raise KeyError(module_id)


def _ground_kinds(rows) -> set[str]:
    """The distinct symbols drawn on the map, ignoring spaces."""
    kinds: set[str] = set()
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, str):
                kinds.update(ch for ch in row if not ch.isspace())
    return kinds


def _landmark_marks(town: dict) -> set[str]:
    """The legend symbols a maker can paint to mark a place: a decorated
    square (the `deco` flag) or a sanctuary square. These are exactly the
    marks the Map Room can paint, so the commission stays satisfiable in the
    studio - a named `pois` entry needs a route the room does not have yet.
    """
    legend = town.get("legend") if isinstance(town, dict) else None
    if not isinstance(legend, dict):
        return set()
    sanctuary = town.get("sanctuary_tiles") or []
    marks: set[str] = set()
    for ch, spec in legend.items():
        if not isinstance(spec, dict):
            continue
        if spec.get("deco") or ch in sanctuary:
            marks.add(ch)
    return marks


def needs(w: dict) -> str | None:
    """Why the map-sketches commission is still open, or None when it is done.

    Satisfied when the town draws at least three kinds of ground and marks
    at least one of them as a place - a decorated or sanctuary square,
    which is what the Map Room can actually paint. The reason is plain words
    the resident can say, never an exception - a broken or missing town just
    reads as one more thing still to do.
    """
    town = w.get("town") if isinstance(w, dict) else None
    if not isinstance(town, dict):
        return "no town to sketch yet"
    rows = town.get("map")
    if not isinstance(rows, list) or not rows:
        return "no map to sketch yet"
    legend = town.get("legend")
    if not isinstance(legend, dict) or not legend:
        return "the map has no legend yet"
    kinds = _ground_kinds(rows)
    if len(kinds) < 3:
        return "the ground is all one kind of thing - draw a path, a wall and a landmark"
    if not (kinds & _landmark_marks(town)):
        return "no landmark yet - mark one square as a place you can walk to"
    return None


def state(w: dict) -> dict[str, str | None]:
    """Every module's open reason, keyed by module id; None means done."""
    return {m.id: needs(w) for m in MODULES}


_lock = threading.Lock()


def _store():
    return data_dir() / "commissions.json"


def load_deferrals() -> dict[str, str]:
    """The deferred module ids and when each was set aside; {} when unreadable."""
    try:
        s = json.loads(_store().read_text(encoding="utf-8"))
        d = s.get("deferred")
        if isinstance(d, dict):
            return {str(k): str(v) for k, v in d.items()}
    except (OSError, ValueError):
        pass
    return {}


def _save(deferred: dict[str, str]) -> None:
    p = _store()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"deferred": deferred}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def defer(module_id: str) -> None:
    """Set a commission aside for later; an unknown id is a KeyError."""
    module(module_id)
    with _lock:
        deferred = load_deferrals()
        deferred[module_id] = _now()
        _save(deferred)


def resume(module_id: str) -> None:
    """Take a commission back off the shelf; an unknown id is a KeyError."""
    module(module_id)
    with _lock:
        deferred = load_deferrals()
        deferred.pop(module_id, None)
        _save(deferred)


def is_deferred(module_id: str) -> bool:
    return module_id in load_deferrals()


def board(w: dict) -> list[dict]:
    """The merged view: one card per module, ready for the Hall to render."""
    deferred = load_deferrals()
    open_reasons = state(w)
    out = []
    for m in MODULES:
        done = open_reasons.get(m.id) is None
        out.append({
            "id": m.id,
            "name": m.name,
            "resident": m.resident,
            "room": m.room,
            "tier": m.tier,
            "ask": m.ask,
            "choosing": m.choosing,
            "home": m.home,
            "see_how": m.see_how,
            "offline": m.offline,
            "done": done,
            # A finished commission is done regardless of any old deferral.
            "deferred": bool(deferred.get(m.id)) and not done,
        })
    return out
