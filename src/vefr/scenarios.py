"""Scenarios: open the woven game in a named state (ADR 0016, slice P2).

A scenario is one pack file, `scenarios/<name>.json`: where the hero
stands and what they carry, for example "on the fifth floor down, with 120
gold, a ladle and three potions". `vefr look --scenario NAME` and
`vefr probe --scenario NAME` open the woven game in that state, so a deep
room can be seen and tested without playing the way down to it (Cottage
Release 1 needed 1,651 keypresses for one screenshot; issue #260).

It is the Player Driver's Session Capsule written by hand. The state is
the player's OWN save keys, in the formats the player itself reads and
writes (`180-gold.js`, `160-the-bag.js`, `170-what-is-worn.js`,
`220-growth.js`, `397-the-descent.js`); nothing here is a second save
format, and the woven game is not changed at all. The dev tools write
these keys before the page loads, press Begin, and walk the hero in
through the player's own arrival paths (`VEFR_ENTER_REGION`, and the
descent's `enterDescentFloor`), so a scenario arrives the way a player
does.

`shapes` speaks for a scenario's shape; `errors` checks it against the
pack (the region, the tile, the descent, the items) and `vefr check`
runs it. A pack that ships no `scenarios/` directory checks exactly as
before.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import delve, maplab, shapes

SCENARIOS_DIR = 'scenarios'
NAME = re.compile(r'[a-z0-9][a-z0-9-]{0,39}')

# The player's own save keys a scenario may set, each followed by the
# world's name. The twin of the parts named in the module docstring;
# `tests/test_scenarios.py` reads the parts and fails if one drifts.
KEYS = {
    'gold': 'vefr-gold-',
    'bag': 'vefr-bag-',
    'equipped': 'vefr-equipped-',
    'xp': 'vefr-growth-',
    'hp': 'vefr-hp-',
}
DESCENT_KEY = 'vefr-descent-'
# The version of the descent's save document (`DOC_VERSION` in
# `397-the-descent.js`). A scenario writes a current document so the game
# does not take the planted state for a Release 1 save and offer the
# one-time generation card.
DESCENT_DOC_VERSION = 1


def names(pack_dir) -> list[str]:
    """The scenario names a pack ships, sorted (file stems of `scenarios/*.json`)."""
    folder = Path(pack_dir) / SCENARIOS_DIR
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob('*.json') if p.is_file())


def load(pack_dir, name: str):
    """`(scenario, None)`, or `(None, sentence)` when it cannot be read."""
    if not NAME.fullmatch(name or ''):
        return None, (f'scenario {name!r} is not a scenario name: lowercase '
                      'letters, digits and dashes, starting with a letter or '
                      'digit, at most 40')
    if not (Path(pack_dir) / SCENARIOS_DIR / f'{name}.json').is_file():
        have = names(pack_dir)
        return None, (f'this pack has no scenario {name!r}; it has '
                      + (', '.join(have) if have else 'none'))
    data, why = maplab._pack_json(pack_dir, f'{SCENARIOS_DIR}/{name}.json')
    if why is not None:
        return None, f'{SCENARIOS_DIR}/{name}.json: {why}'
    return data, None


def check(w: dict, scenario) -> list[str]:
    """Every problem with one scenario, its shape first, then the pack."""
    problems = [p.sentence for p in shapes.check(shapes.SCENARIO, scenario)]
    if problems:
        return problems
    out: list[str] = []
    start = scenario['start']
    has_region, has_depth = 'region' in start, 'depth' in start
    if has_region == has_depth:
        out.append('scenario start must name a region or a depth, not both '
                   'and not neither, such as {"depth": 5}')
    elif has_depth:
        if 'at' in start:
            out.append('scenario start.at goes with a region; a depth is '
                       'entered at its stairs, the way the hero arrives')
        if not isinstance(w.get('descent'), dict):
            out.append('scenario start.depth needs a descent, and this pack '
                       'declares none in world.json')
    else:
        out.extend(_region_problems(w, start))
    out.extend(_item_problems(w, scenario))
    return out


def _region_problems(w: dict, start: dict) -> list[str]:
    regions = maplab.region_geometry(w)
    name = start['region']
    if name not in regions:
        return [f'scenario start.region {name!r} is not a region of this '
                f'pack; it has {", ".join(sorted(regions)) or "none"}']
    if 'at' not in start:
        return []
    x, y = start['at']
    geo = regions[name]
    ok = maplab._map_tile_walkable(geo.get('map') or [], geo.get('legend') or {}, x, y)
    if ok is None:
        rows = geo.get('map') or []
        size = f'{len(rows[0]) if rows else 0}x{len(rows)}'
        return [f'scenario start.at {[x, y]} is outside {name} ({size} tiles)']
    if not ok:
        return [f'scenario start.at {[x, y]} is not a tile the hero can '
                f'stand on in {name}']
    return []


def _item_problems(w: dict, scenario: dict) -> list[str]:
    items = w.get('items') if isinstance(w.get('items'), dict) else {}
    out: list[str] = []
    for i, item in enumerate(scenario.get('bag', [])):
        if not isinstance(item, str):
            out.append(f'scenario.bag[{i}] must be an item id, such as "potion"')
        elif item not in items:
            out.append(f'scenario.bag[{i}] {item!r} is not an item this pack '
                       'defines')
    for slot, item in (scenario.get('equipped') or {}).items():
        if slot not in maplab.SLOTS:
            out.append(f'scenario.equipped slot {slot!r} is not a slot; the '
                       f'slots are {", ".join(maplab.SLOTS)}')
        elif not isinstance(item, str) or item not in items:
            out.append(f'scenario.equipped.{slot} {item!r} is not an item '
                       'this pack defines')
        elif (items[item] or {}).get('slot') != slot:
            worn = (items[item] or {}).get('slot')
            out.append(f'scenario.equipped.{slot} {item!r} is worn on '
                       + (f'the {worn} slot' if worn else 'no slot'))
    return out


def errors(w: dict, pack_dir) -> list[str]:
    """Every problem with every scenario a pack ships, each with its file."""
    folder = Path(pack_dir) / SCENARIOS_DIR
    if not folder.is_dir():
        return []
    out: list[str] = []
    for path in sorted(folder.iterdir()):
        rel = f'{SCENARIOS_DIR}/{path.name}'
        if path.suffix != '.json' or not path.is_file():
            out.append(f'{rel}: a scenario is a .json file')
            continue
        data, why = load(pack_dir, path.stem)
        if why is not None:
            out.append(why if why.startswith(SCENARIOS_DIR) else f'{rel}: {why}')
            continue
        out.extend(f'{rel}: {sentence}' for sentence in check(w, data))
    return out


def world_name(w: dict) -> str:
    """The name the woven game knows the world by (`VEFR_WORLD.name`).

    The weave bakes `{**world.json, **load_pack(pack)}`, so the loader's
    name wins; the player falls back to 'world' when there is none.
    """
    return str(w.get('name') or 'world')


def storage(w: dict, scenario: dict) -> dict[str, str]:
    """The player's save keys a scenario sets, as the player stores them.

    Only the keys the scenario names, plus - when the pack has a descent -
    a fresh descent document marked with the current generation, so the
    planted state reads as a current save rather than a Release 1 one.
    """
    name = world_name(w)
    out: dict[str, str] = {}
    if 'gold' in scenario:
        out[KEYS['gold'] + name] = str(scenario['gold'])
    if 'bag' in scenario:
        out[KEYS['bag'] + name] = json.dumps(scenario['bag'])
    if 'equipped' in scenario:
        out[KEYS['equipped'] + name] = json.dumps(scenario['equipped'])
    if 'xp' in scenario:
        out[KEYS['xp'] + name] = json.dumps({'xp': scenario['xp'], 'counts': {}})
    if 'hp' in scenario:
        out[KEYS['hp'] + name] = str(scenario['hp'])
    descent = w.get('descent')
    if isinstance(descent, dict) and descent.get('run_seed'):
        out[DESCENT_KEY + name] = json.dumps({
            'v': DESCENT_DOC_VERSION, 'gen': delve.GEN_VERSION, 'run': 0,
            'seed': descent['run_seed'], 'order': [], 'floors': {},
            'flags': {}, 'card': delve.GEN_VERSION,
        })
    return out
