"""Can this pack be finished? Follow the locks from the start region.

`findings(pack_dir)` returns plain sentences naming a lock whose key
cannot be reached before it; an empty list means every item-locked door
can be opened with a key the hero can obtain first. A pack with no
`requires` at all produces no findings.

The model is the pack's own data, read through the loaders the rest of
the engine already uses: the acts tree (`maplab.load_pack`), the
Library's books (`library.load_library`), and the item catalog. A key
can be obtained from an enemy's `drops`, a book/chest's `drops` on the
map, a shop's `stock`, or a rule that `give`s it (rules are not
regional). Reachability and obtainability are grown to a fixpoint.

Flag locks (`requires: {"flag": ...}`) are out of scope: a rule may set
the flag, so they are treated as always open and never reported. No
model call, no write, no clock - this is a deterministic surface.
"""

from __future__ import annotations

from pathlib import Path

from . import library
from .maplab import load_pack


def _item_ids(value) -> list[str]:
    """The item ids a `drops`/`stock` value names.

    An enemy `drops` is a list; a book's is a comma-separated string in
    its front matter. A shop `stock` may be either, or a mapping whose
    keys are the ids. Blank parts are skipped, first-seen order kept.
    """
    if isinstance(value, str):
        parts = value.split(",")
    elif isinstance(value, (list, tuple)):
        parts = list(value)
    elif isinstance(value, dict):
        parts = list(value)
    else:
        return []
    out: list[str] = []
    for part in parts:
        pid = str(part).strip()
        if pid and pid not in out:
            out.append(pid)
    return out


def _rule_gives(rules) -> set[str]:
    """Every item a rule `give`s. Rules are not regional, so these count
    as obtainable from the start."""
    given: set[str] = set()
    if not isinstance(rules, list):
        return given
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        effects = rule.get("then")
        if not isinstance(effects, list):
            continue
        for effect in effects:
            if not isinstance(effect, dict):
                continue
            item = effect.get("give")
            if isinstance(item, str) and item:
                given.add(item)
    return given


def _region_sources(acts, books) -> dict[str, set[str]]:
    """Every item obtainable by visiting a region: enemy drops, a
    book/chest's drops, and a shop's stock, keyed by region name."""
    sources: dict[str, set[str]] = {}

    def add(region, ids):
        if not region:
            return
        sources.setdefault(region, set()).update(i for i in ids if i)

    for act in acts:
        regions = act.get("regions")
        if not isinstance(regions, dict):
            continue
        names = list(regions)
        first = names[0] if names else None
        for name, rdata in regions.items():
            contract = (rdata or {}).get("contract") if isinstance(rdata, dict) else None
            contract = contract if isinstance(contract, dict) else {}
            for enemy in (contract.get("enemies") or []):
                if isinstance(enemy, dict):
                    add(name, _item_ids(enemy.get("drops")))
        speakers = act.get("speakers")
        if isinstance(speakers, dict):
            for speaker in speakers.values():
                if not isinstance(speaker, dict) or "shop" not in speaker:
                    continue
                region = speaker.get("region")
                if not isinstance(region, str) or not region:
                    region = first
                add(region, _item_ids(speaker.get("stock")))

    for book in books:
        if not isinstance(book, dict):
            continue
        extra = book.get("extra") if isinstance(book.get("extra"), dict) else {}
        region = book.get("region")
        if not isinstance(region, str) or not region:
            region = "town"
        add(region, _item_ids(extra.get("drops")))
    return sources


def _opens(requires, obtainable: set[str]) -> bool:
    """Whether a transition's `requires` is satisfied.

    No `requires`, a flag lock, or an unknown shape all open (only item
    locks can hold the hero back here); an item lock opens once its id
    has been obtained.
    """
    if not isinstance(requires, dict):
        return True
    if "flag" in requires:
        return True
    item = requires.get("item")
    if isinstance(item, str):
        return item in obtainable
    return True


def _closure(transitions, sources, start, rule_items, *, skip=(), force=()):
    """Grow reachable regions and obtainable items to a fixpoint.

    `skip` holds transition indices treated as shut; `force` holds ones
    opened without their key (used to ask what lies behind a lock).
    Returns `(reachable_regions, obtainable_items)`.
    """
    reachable: set[str] = {start} if start else set()
    obtainable: set[str] = set(rule_items)
    skip = set(skip)
    force = set(force)
    while True:
        changed = False
        for region in list(reachable):
            for item in sources.get(region, ()):  # type: ignore[arg-type]
                if item not in obtainable:
                    obtainable.add(item)
                    changed = True
        for i, t in enumerate(transitions):
            if i in skip:
                continue
            frm, to = t.get("from"), t.get("to")
            if not isinstance(frm, str) or not isinstance(to, str):
                continue
            if frm not in reachable or to in reachable:
                continue
            if i in force or _opens(t.get("requires"), obtainable):
                reachable.add(to)
                changed = True
        if not changed:
            break
    return reachable, obtainable


def _acts(world: dict) -> list[dict]:
    return [a for a in (world.get("acts") or []) if isinstance(a, dict)]


def findings(pack_dir) -> list[str]:
    """Every lock-reachability problem in `pack_dir`, as plain sentences.

    Empty when the pack carries no `requires`, when every item lock's
    key can be obtained in a region reached before it, and when no key
    has a `value` (which would let a trader buy the way forward).

    A key that exists only behind its own lock is reported as "behind
    its own lock" rather than a second "unreachable" finding.
    """
    pack = Path(pack_dir)
    if not (pack / "world.json").is_file():
        return []
    try:
        world = load_pack(pack)
    except (OSError, ValueError, KeyError, SystemExit):
        return []

    acts = _acts(world)
    if not acts:
        return []

    regions: list[str] = []
    transitions: list[dict] = []
    for act in acts:
        act_regions = act.get("regions")
        if isinstance(act_regions, dict):
            for name in act_regions:
                if name not in regions:
                    regions.append(name)
        for t in (act.get("transitions") or []):
            if isinstance(t, dict):
                transitions.append(t)

    locks = [(i, t) for i, t in enumerate(transitions)
             if isinstance(t.get("requires"), dict)
             and isinstance(t["requires"].get("item"), str)
             and t["requires"]["item"]]
    if not locks:
        return []

    player = world.get("_player") if isinstance(world.get("_player"), dict) else {}
    wake = player.get("wake") if isinstance(player.get("wake"), dict) else {}
    start = wake.get("region")
    if not isinstance(start, str) or start not in regions:
        start = regions[0] if regions else None
    if start is None:
        return []

    books = library.load_library(pack)
    sources = _region_sources(acts, books)
    rule_items = _rule_gives(world.get("rules"))

    items = world.get("items") if isinstance(world.get("items"), dict) else {}

    out: list[str] = []
    seen: set[str] = set()
    key_items: list[str] = []

    def emit(sentence: str) -> None:
        if sentence not in seen:
            seen.add(sentence)
            out.append(sentence)

    for i, t in locks:
        key = t["requires"]["item"]
        if key not in key_items:
            key_items.append(key)
        frm, to = t.get("from"), t.get("to")
        _reach, before = _closure(transitions, sources, start, rule_items,
                                  skip=(i,))
        if key in before:
            continue  # the key can be obtained before this lock: fine
        _reach, behind = _closure(transitions, sources, start, rule_items,
                                  force=(i,))
        where = f"from '{frm}' to '{to}'"
        if key in behind:
            emit(f"the key '{key}' can only be found behind its own lock, "
                 f"at the door {where}")
        else:
            emit(f"the key '{key}' is unreachable: it cannot be obtained in "
                 f"any region reached before the door {where}")

    for key in key_items:
        spec = items.get(key)
        value = spec.get("value") if isinstance(spec, dict) else None
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            emit(f"the key item '{key}' has a value, so it can be sold to a "
                 f"trader - a sold key would break the pack")
    return out
