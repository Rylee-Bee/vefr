"""maplab - the map toolkit for world packs.

The lab-wrapper pattern, first piece: one validator shared by the
tests and the CLI, so the map can never be wrong in a way the
tests do not also check.

Subcommands:
  validate  [--pack DIR]            run every geometry check offline
  build     --segments FILE         rebuild the map from run-length
                                    segments: {"rows": [[["H", 4], ...], ...]}
  verify    --url URL               validate the map as actually served
                                    by a live deployment (closes the
                                    baked-but-not-deployed gap)

Walkability mirrors town.js exactly: legend solid flag wins, else
the legacy blocked-char fallback. Reachability is checked in the
least restrictive water state (low water everywhere).
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from .paths import world_name as _default_world_name
from .world import VALID_FLOORS, VALID_TONES
from .world import creed_from as _creed_from

BLOCKED_FALLBACK = ['~', 'B', '#', 'T', 'M']

# A `#rule#` reference inside a grammar entry; the same pattern the
# expander (grammar.py) and the woven player walk.
_GRAMMAR_REF = re.compile(r"#([A-Za-z0-9_][A-Za-z0-9_.-]*)#")


def load_pack(pack_dir: Path) -> dict:
    """Read a pack's world.json and return a single shape that the
    validator can consume.

    The on-disk shape is one of two:

      Flat shape (legacy): a single world.json with title, phases,
        voices, bonds, town at the top level.
      Acts shape: a pack-level world.json + acts/<id>/world.json
        per act. The map lives in acts/<id>/<region>/map.md.

    The validator downstream reads `w['town']`, `w['speakers']`,
    `w['phases']`, and `w['voices']`. We build a unified dict so
    the validator never has to know which on-disk shape it came
    from. Acts-shape packs are validated against the current act's
    first region (the town in the canary shape).

    The optional `growth` block (design/growth.md) is carried through
    only when the pack declares it, so a pack without one loads
    exactly as before. The optional `skin` field (design/ui-skin.md)
    is carried the same way: only when the pack declares it, so a pack
    without one loads exactly as before.
    """
    pack = Path(pack_dir)
    config = json.loads((pack / 'world.json').read_text(encoding='utf-8'))
    if 'acts' in config or (pack / 'acts').is_dir():
        acts_dir = pack / 'acts'
        first_act_dir = next(
            (d for d in sorted(acts_dir.iterdir())
             if d.is_dir() and not d.name.startswith('.')),
            None,
        )
        if first_act_dir is None:
            raise SystemExit(f'{pack}/acts has no act directories')
        act = json.loads((first_act_dir / 'world.json').read_text(encoding='utf-8'))
        # Pick the first region for the validator's unified `town` (the
        # canary has only `town`; full per-region geometry is still a
        # follow-on). Transition checks, however, read every region's
        # map + legend, exposed below as `regions`.
        regions_list = list(act.get('regions', {}) or {})
        region_name = regions_list[0] if regions_list else None

        def _region_geo(rname):
            """One region's map rows + contract, read from disk."""
            rdir = first_act_dir / rname
            rcontract: dict = {}
            cp = rdir / 'contract.json'
            if cp.exists():
                rcontract = json.loads(cp.read_text(encoding='utf-8'))
            rows: list[str] = []
            mp = rdir / 'map.md'
            if mp.exists():
                rows = [
                    ln for ln in mp.read_text(encoding='utf-8').splitlines()
                    if ln.strip()
                ]
            if not rows:
                rows = rcontract.get('map', [])
            return rcontract, rows

        contract: dict = {}
        map_lines: list[str] = []
        if region_name:
            contract, map_lines = _region_geo(region_name)
        # Every region's geometry, for the door checks. `map` is the
        # rows; `legend` is what makes a tile walkable.
        regions_geo: dict[str, dict] = {}
        for rname in regions_list:
            rcontract, rrows = _region_geo(rname)
            regions_geo[rname] = {
                'map': rrows,
                'legend': rcontract.get('legend', {}),
                'enemies': rcontract.get('enemies', []),
            }
        # The town's metadata can live in three places, in priority
        # order: the region's contract.json (new, convention-driven),
        # the act's _town_legacy (transitional), or the act's
        # inline `town` block (the very first acts-shape PR had
        # this). Read all three, the highest priority wins.
        region_legacy = act.get('_town_legacy', {}) or act.get('town', {})
        merged = {**region_legacy, **contract}
        # The map lives in acts/<id>/<region>/map.md in the new
        # shape. If it's there, parse it; otherwise fall back to
        # whatever the contract holds.
        if not map_lines:
            map_lines = merged.get('map', [])
        # Every speaker is carried: a book's giver may live in any region.
        # The geometry check below looks only at the first region's own.
        all_speakers = act.get('speakers', {})
        unified = {
            'name': pack.name,
            'title': config.get('title', act.get('title', pack.name)),
            'description': config.get('description', ''),
            'creed': _creed_from(config),
            'phases': config['phases'],
            'voices': config.get('voices', {}),
            'bonds': config.get('bonds', {}),
            'speakers': all_speakers,
            'surface': config.get('surface', 'combat'),
            'grammars': config.get('grammars', {}),
            'town': {
                'map': map_lines,
                'legend': merged.get('legend', {}),
                'pois': merged.get('pois', {}),
                'watch': merged.get('watch', {}),
                'sanctuary_tiles': merged.get('sanctuary_tiles', []),
                'water_by_phase': merged.get('water_by_phase', {}),
                'flood_tiles': merged.get('flood_tiles', []),
                'hero_start': merged.get('hero_start', [1, 1]),
                'tile': merged.get('tile', 32),
                'bg': merged.get('bg', '#131311'),
                'hero_color': merged.get('hero_color', '#e8e5df'),
                'speaker_color': merged.get('speaker_color', '#8b939c'),
                'speaker_head': merged.get('speaker_head', '#d8d5df'),
            },
            '_act_id': first_act_dir.name,
            '_region': region_name,
            'transitions': act.get('transitions', []),
            'regions': regions_geo,
            # the pack's own `player` block, kept for checks (never written back: write_pack names its keys)
            '_player': config.get('player'),
        }
        # The four optional rule-catalog keys, carried through ONLY
        # when the pack declares them: a pack that declares none
        # gets a dict with exactly the keys it had before. Purely
        # additive; nothing else reads them yet. The validator's
        # defaults ({} / []) live beside the validator, not here.
        for key in ('flags', 'claims', 'people', 'rules'):
            if key in config:
                unified[key] = config[key]
        # The optional growth block, carried through ONLY when the
        # pack declares it (design/growth.md).
        if 'growth' in config:
            unified['growth'] = config['growth']
        # The optional skin folder, carried through ONLY when the pack
        # declares it (design/ui-skin.md): a pack with none loads as
        # before, and `world.json` has no `skin` key to bake.
        if 'skin' in config:
            unified['skin'] = config['skin']
        return unified
    config['_player'] = config.get('player')
    return config


def walkable(w: dict, x: int, y: int, flooded: set | None = None) -> bool:
    m = w['town']['map']
    if y < 0 or y >= len(m) or x < 0 or x >= len(m[0]):
        return False
    if flooded and f'{x},{y}' in flooded:
        return False
    e = w['town']['legend'].get(m[y][x], {})
    if isinstance(e.get('solid'), bool):
        return e['solid'] is False
    return m[y][x] not in BLOCKED_FALLBACK


def _map_tile_walkable(map_rows: list, legend: dict,
                       x: int, y: int) -> bool | None:
    """Walkability of one tile on a named region's map. Mirrors
    `walkable`, but takes the map + legend directly (the validator's
    unified `town` is only the first region). Returns None when the
    tile is off the map, so the caller can tell "outside" from
    "solid"."""
    if not map_rows or y < 0 or y >= len(map_rows) or x < 0 or x >= len(map_rows[0]):
        return None
    e = (legend or {}).get(map_rows[y][x], {})
    if isinstance(e.get('solid'), bool):
        return e['solid'] is False
    return map_rows[y][x] not in BLOCKED_FALLBACK


def reach(w: dict, start: tuple, flooded: set | None = None) -> set:
    seen = {tuple(start)}
    stack = [tuple(start)]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in seen and walkable(w, *n, flooded=flooded):
                seen.add(n)
                stack.append(n)
    return seen


def grammar_errors(grammars) -> list[str]:
    """Every problem with a pack's `grammars` block (empty = good).

    The block is optional and additive: a pack with none passes. A
    pack with one gets it checked here rather than at play time,
    because a grammar that cannot expand is a pack-authoring typo, and
    the author should read about it from `norns validate` and not
    from a silent whisper.

    The three laws (see grammar.py): every grammar is an object of
    rules, every rule is a non-empty list of strings, `origin` is
    required, and every `#rule#` names a rule in the same grammar.
    Messages name the grammar and the rule, so one line says which
    `#thing#` to fix.
    """
    errors: list[str] = []
    if not isinstance(grammars, dict):
        return ["grammars must be an object of named grammars"]
    for gname, rules in grammars.items():
        if not isinstance(rules, dict):
            errors.append(f"grammar '{gname}' must be an object of rules")
            continue
        if 'origin' not in rules:
            errors.append(f"grammar '{gname}' needs an 'origin' rule - "
                          'expansion starts there')
        for rname, entries in rules.items():
            if not isinstance(entries, list) or not entries or not all(
                    isinstance(e, str) for e in entries):
                errors.append(f"grammar '{gname}' rule '{rname}' must be a "
                              'non-empty list of strings')
                continue
            for entry in entries:
                for ref in _GRAMMAR_REF.findall(entry):
                    if ref not in rules:
                        errors.append(
                            f"grammar '{gname}' rule '{rname}' references "
                            f"'{ref}', which is not a rule in that grammar")
    return errors


def item_light_errors(item_id, spec) -> list[str]:
    """Every problem with an item's optional `light` field (empty = good).

    `light` is optional and additive: an item without one passes. An
    item with one must name exactly one usable form - a radius form
    (`radius` and `turns` together, in range) or a reveal form
    (`reveal: true`). A pack author reads a clear, named line from
    `norns validate` instead of meeting a torch that does nothing.
    """
    light = spec.get('light')
    if light is None:
        return []
    label = str(spec.get('name') or item_id)
    where = f"item '{label}'"
    if not isinstance(light, dict) or isinstance(light, bool):
        return [f"{where} light must be an object"]
    errors: list[str] = []
    has_radius, has_turns = 'radius' in light, 'turns' in light
    radius, turns = light.get('radius'), light.get('turns')
    reveal = light.get('reveal')
    if has_radius and (isinstance(radius, bool) or not isinstance(radius, int)
                       or not 1 <= radius <= 20):
        errors.append(f"{where} light radius must be an integer 1..20")
    if has_turns and (isinstance(turns, bool) or not isinstance(turns, int)
                      or not 1 <= turns <= 999):
        errors.append(f"{where} light turns must be an integer 1..999")
    if 'reveal' in light and not isinstance(reveal, bool):
        errors.append(f"{where} light reveal must be true or false")
    radius_form = has_radius and has_turns
    reveal_form = reveal is True
    if not radius_form and not reveal_form:
        errors.append(f"{where} light needs radius and turns, or reveal: true")
    return errors


# The speech-box limit the pack contract already uses: a `say` line
# longer than this would be cut off by the woven player's box, so it
# is a pack-authoring error here instead.
RULE_SAY_LIMIT = 280

# A pack may declare this many rules; past it the mistakes in a rule
# stack outweigh any single rule's worth.
RULE_LIMIT = 40

# The six events a rule may fire on became eleven: the first six are
# the original vocabulary; the last five are facts the player already
# performs (a fight won, a thing bought or sold, a book closed, the
# watch turned) so the world can notice them. `says` is deliberately
# absent: the woven player has nowhere to type words, so an event that
# waited on typed speech could never fire.
RULE_EVENTS = ('starts', 'enters', 'comes-near', 'opens', 'picks-up',
               'uses-with', 'defeats', 'buys', 'sells', 'reads',
               'phase-changes')

# The payload each event carries, keyed by event name.
RULE_EVENT_KEYS = {
    'starts': (),
    'enters': ('place',),
    'comes-near': ('who', 'distance'),
    'opens': ('what',),
    'picks-up': ('what',),
    'uses-with': ('item', 'with'),
    'defeats': ('what',),
    'buys': ('what',),
    'sells': ('what',),
    'reads': ('what',),
    'phase-changes': ('to',),
}

# The keys a condition may name. The `flag` form is the one condition
# in the contract with two top-level keys: {"flag": ..., "is": ...}.
RULE_CONDITION_KEYS = ('has', 'flag', 'is', 'believes', 'not-believes',
                       'is-in', 'not', 'all-of')

# The keys an action may name. `takes` is `give`'s pair: remove one
# copy of an item from what the hero carries (a delivery, a turn-in).
RULE_ACTION_KEYS = ('say', 'show', 'hide', 'reveal', 'give', 'takes',
                    'set', 'unset', 'believes', 'stops-believing', 'tells',
                    'weather', 'point-to')


def _rule_known_ids(w: dict, pack_dir: Path | None) -> dict:
    """Every id a rule may name, resolved from the loaded pack.

    One identity model: a rule may name only what the pack declares -
    items (world.json), speakers, regions, POI labels (region
    contracts), library book ids (file stems), and region enemy ids.

    Path safety: only files under pack_dir are read, each resolved and
    checked the same way as the pack's own world.json - no id taken
    from pack data ever becomes a filesystem path.
    """
    pack_cfg: dict = {}
    region_contracts: list[dict] = []
    book_ids: set = set()
    if pack_dir is not None:
        from .cli import _inside

        base = os.path.realpath(str(pack_dir))

        def _read_in(root: str | None, *parts: str) -> dict:
            # Every probe goes through the house guard first (the same
            # shape region_geo uses): a name that would leave its root
            # resolves to nothing at all.
            found = _inside(root, *parts) if root else None
            if found is None or not os.path.isfile(found):
                return {}
            try:
                loaded = json.loads(Path(found).read_text(encoding='utf-8'))
            except ValueError:
                return {}
            return loaded if isinstance(loaded, dict) else {}

        pack_cfg = _read_in(base, 'world.json')
        # acts-shape regions carry their pois/enemies in contract.json;
        # the flat shape keeps them in world.json's `town` block.
        acts_dir = _inside(base, 'acts')
        if acts_dir and os.path.isdir(acts_dir):
            for act in sorted(os.listdir(acts_dir)):
                if act.startswith('.'):
                    continue
                act_real = _inside(acts_dir, act)
                if act_real is None or not os.path.isdir(act_real):
                    continue
                for region in sorted(os.listdir(act_real)):
                    if region.startswith('.'):
                        continue
                    region_real = _inside(act_real, region)
                    if region_real is None or not os.path.isdir(region_real):
                        continue
                    region_contracts.append(_read_in(region_real,
                                                     'contract.json'))
        else:
            town = pack_cfg.get('town')
            if isinstance(town, dict):
                region_contracts.append(town)
        lib_dir = _inside(base, 'library')
        if lib_dir and os.path.isdir(lib_dir):
            for name in sorted(os.listdir(lib_dir)):
                if name.endswith('.md') and not name.startswith('.'):
                    stem = name[:-len('.md')]
                    if stem:
                        book_ids.add(stem)

    items: set = set()
    # An acts-shape pack keeps its items at the pack level and
    # load_pack does not surface them; read them straight from the
    # pack config here rather than changing load_pack's handling.
    for source in (w.get('items'), pack_cfg.get('items')):
        if isinstance(source, dict):
            items |= set(source)
    people = set(w['speakers']) if isinstance(w.get('speakers'), dict) else set()
    regions = w.get('regions')
    if isinstance(regions, dict):
        places = set(regions)
    elif isinstance(regions, list):
        places = {r for r in regions if isinstance(r, str)}
    else:
        # The flat shape declares no `regions` key; rather than guess
        # at a flat pack's place names, none resolve.
        places = set()
    # POI labels are their own ids (the label is what the runtime
    # sends in `comes-near`/`uses-with` payloads); enemy ids come from
    # the same region contracts as pois.
    pois: set = set()
    enemies: set = set()
    for contract in region_contracts:
        p = contract.get('pois')
        if isinstance(p, dict):
            pois |= {str(v) for v in p.values() if str(v)}
        for e in contract.get('enemies') or []:
            if isinstance(e, dict) and isinstance(e.get('id'), str):
                enemies.add(e['id'])
    flags = w.get('flags') if 'flags' in w else {}
    claims = w.get('claims') if 'claims' in w else {}
    phases = w.get('phases')
    return {
        'items': items,
        'people': people,
        'places': places,
        'pois': pois,
        'books': book_ids,
        'enemies': enemies,
        'phases': set(phases) if isinstance(phases, dict) else set(),
        'things': items | people | places | pois | book_ids | enemies,
        # None means "declared but malformed": the shape error in
        # rules_errors already speaks for it, so id checks stay
        # quiet. An absent key defaults to {} and every reference
        # is undeclared.
        'flags': set(flags) if isinstance(flags, dict) else None,
        'claims': set(claims) if isinstance(claims, dict) else None,
    }


def _rule_value_errors(rid: str, where: str, val, kind: str, known: dict) -> list[str]:
    """One id or line value inside a rule, checked against the pack."""
    if kind == 'line':
        if not isinstance(val, str):
            return [f"rule '{rid}' {where} must be words"]
        if len(val) > RULE_SAY_LIMIT:
            return [f"rule '{rid}' {where} is {len(val)} characters - "
                    f"the speech box holds {RULE_SAY_LIMIT}"]
        return []
    if not isinstance(val, str):
        noun = {'person': 'person id', 'claim': 'claim name', 'item': 'item id',
                'place': 'region id', 'thing': 'thing id', 'book': 'book id',
                'enemy': 'enemy id', 'phase': 'phase name'}[kind]
        return [f"rule '{rid}' {where} must be a {noun}"]
    if kind == 'person':
        if val not in known['people']:
            return [f"rule '{rid}' {where} names person '{val}', "
                    "who is not a speaker in this pack"]
        return []
    if kind == 'claim':
        if known['claims'] is not None and val not in known['claims']:
            return [f"rule '{rid}' {where} names unknown claim '{val}'"]
        return []
    if kind == 'item':
        if val not in known['items']:
            return [f"rule '{rid}' {where} names unknown item '{val}'"]
        return []
    if kind == 'place':
        if val not in known['places']:
            return [f"rule '{rid}' {where} names unknown place '{val}'"]
        return []
    if kind == 'book':
        if val not in known['books']:
            return [f"rule '{rid}' {where} names unknown book '{val}'"]
        return []
    if kind == 'enemy':
        if val not in known['enemies']:
            return [f"rule '{rid}' {where} names unknown enemy '{val}'"]
        return []
    if kind == 'phase':
        if val not in known['phases']:
            return [f"rule '{rid}' {where} names unknown phase '{val}'"]
        return []
    if kind == 'thing' and val not in known['things']:
        return [f"rule '{rid}' {where} names unknown thing '{val}'"]
    return []


def _rule_payload_errors(rid: str, verb: str, val, fields, known: dict) -> list[str]:
    """The object payload of one condition or action.

    `fields` is a tuple of (key, kind) pairs naming every key the
    payload may carry and how each value is checked.
    """
    want = [k for k, _ in fields]
    if not isinstance(val, dict):
        listed = ', '.join(f"'{k}'" for k in want)
        return [f"rule '{rid}' '{verb}' must be an object with {listed}"]
    errors: list[str] = []
    for k in val:
        if k not in want:
            errors.append(f"rule '{rid}' '{verb}' has unknown key '{k}'")
    for k in want:
        if k not in val:
            errors.append(f"rule '{rid}' '{verb}' needs '{k}'")
    for k, kind in fields:
        if k in val:
            errors.extend(_rule_value_errors(rid, f"'{verb}' '{k}'", val[k], kind, known))
    return errors


def _rule_event_errors(rid: str, when, known: dict) -> list[str]:
    """The `when` of one rule: exactly one known event, right payload."""
    if not isinstance(when, dict):
        return [f"rule '{rid}' when must be an event object"]
    if len(when) != 1:
        return [f"rule '{rid}' when must name exactly one event"]
    name = next(iter(when))
    if name not in RULE_EVENTS:
        return [f"rule '{rid}' when names unknown event '{name}' - the six events are "
                + ', '.join(RULE_EVENTS)]
    payload = when[name]
    if not isinstance(payload, dict):
        return [f"rule '{rid}' when '{name}' carries an object payload"]
    want = RULE_EVENT_KEYS[name]
    errors: list[str] = []
    for k in payload:
        if k not in want:
            errors.append(f"rule '{rid}' when '{name}' has unknown key '{k}'")
    for k in want:
        if k not in payload:
            errors.append(f"rule '{rid}' when '{name}' needs key '{k}'")
    if errors:
        return errors
    if name == 'starts':
        return []
    if name == 'enters':
        return _rule_value_errors(rid, "when 'enters'", payload['place'], 'place', known)
    if name == 'comes-near':
        errors = _rule_value_errors(rid, "when 'comes-near' who", payload['who'],
                                    'thing', known)
        distance = payload['distance']
        # A bool is not an int: `true` must not pass as distance 1.
        # 0 is standing on the thing: the player fires tile contact at
        # distance 0, so the vocabulary accepts it.
        if isinstance(distance, bool) or not isinstance(distance, int) \
                or not 0 <= distance <= 9:
            errors.append(f"rule '{rid}' when 'comes-near' distance "
                          "must be an integer 0..9 (0 is standing on it)")
        return errors
    if name == 'opens':
        return _rule_value_errors(rid, "when 'opens'", payload['what'], 'thing', known)
    if name == 'picks-up':
        return _rule_value_errors(rid, "when 'picks-up'", payload['what'], 'item', known)
    if name == 'uses-with':
        errors = _rule_value_errors(rid, "when 'uses-with' item", payload['item'],
                                    'item', known)
        errors += _rule_value_errors(rid, "when 'uses-with' with", payload['with'],
                                     'thing', known)
        return errors
    if name == 'defeats':
        return _rule_value_errors(rid, "when 'defeats'", payload['what'], 'enemy', known)
    if name == 'buys':
        return _rule_value_errors(rid, "when 'buys'", payload['what'], 'item', known)
    if name == 'sells':
        return _rule_value_errors(rid, "when 'sells'", payload['what'], 'item', known)
    if name == 'reads':
        return _rule_value_errors(rid, "when 'reads'", payload['what'], 'book', known)
    return _rule_value_errors(rid, "when 'phase-changes'", payload['to'],
                              'phase', known)


def _rule_condition_errors(rid: str, cond, known: dict) -> list[str]:
    """One condition of one rule's `if`: ALL of them must pass."""
    if not isinstance(cond, dict):
        return [f"rule '{rid}' condition must be an object naming one check"]
    keys = list(cond)
    if 'flag' in cond or 'is' in cond:
        # The flag form is the one condition with two top-level keys:
        # {"flag": "<flag>", "is": true | false}.
        errors = [f"rule '{rid}' flag condition has unknown key '{k}'"
                  for k in keys if k not in ('flag', 'is')]
        if errors:
            return errors
        if 'flag' not in cond or 'is' not in cond:
            return [f"rule '{rid}' flag condition needs both 'flag' and 'is'"]
        if not isinstance(cond['is'], bool):
            errors.append(f"rule '{rid}' flag condition 'is' must be true or false")
        fname = cond['flag']
        if not isinstance(fname, str):
            errors.append(f"rule '{rid}' flag condition 'flag' must be a flag name")
        elif known['flags'] is not None and fname not in known['flags']:
            errors.append(f"rule '{rid}' reads flag '{fname}', which is not declared in flags")
        return errors
    if len(keys) != 1:
        unknown = [k for k in keys if k not in RULE_CONDITION_KEYS]
        if unknown:
            return [f"rule '{rid}' condition has unknown key '{unknown[0]}'"]
        return [f"rule '{rid}' condition must name exactly one check"]
    key, val = keys[0], cond[keys[0]]
    if key not in RULE_CONDITION_KEYS:
        return [f"rule '{rid}' condition has unknown key '{key}'"]
    if key == 'has':
        return _rule_value_errors(rid, "condition 'has'", val, 'item', known)
    if key in ('believes', 'not-believes'):
        return _rule_payload_errors(rid, key, val,
                                    (('who', 'person'), ('claim', 'claim')), known)
    if key == 'is-in':
        return _rule_payload_errors(rid, 'is-in', val,
                                    (('who', 'person'), ('place', 'place')), known)
    if key == 'not':
        if not isinstance(val, dict):
            return [f"rule '{rid}' 'not' must wrap a condition"]
        return _rule_condition_errors(rid, val, known)
    # 'all-of': every inner condition must also pass.
    if not isinstance(val, list):
        return [f"rule '{rid}' 'all-of' must be a list of conditions"]
    errors = []
    for sub in val:
        errors.extend(_rule_condition_errors(rid, sub, known))
    return errors


def _rule_action_errors(rid: str, action, known: dict) -> list[str]:
    """One action of one rule's `then`."""
    if not isinstance(action, dict):
        return [f"rule '{rid}' action must be an object naming one thing to do"]
    keys = list(action)
    unknown = [k for k in keys if k not in RULE_ACTION_KEYS]
    if unknown:
        return [f"rule '{rid}' action has unknown key '{unknown[0]}'"]
    if len(keys) != 1:
        return [f"rule '{rid}' action must name exactly one thing to do"]
    key, val = keys[0], action[keys[0]]
    if key == 'say':
        if isinstance(val, str):
            return _rule_value_errors(rid, 'say line', val, 'line', known)
        return _rule_payload_errors(rid, 'say', val,
                                    (('who', 'person'), ('line', 'line')), known)
    if key in ('show', 'hide', 'reveal'):
        return _rule_value_errors(rid, key, val, 'thing', known)
    if key == 'give':
        return _rule_value_errors(rid, 'give', val, 'item', known)
    if key == 'takes':
        return _rule_value_errors(rid, 'takes', val, 'item', known)
    if key in ('set', 'unset'):
        if not isinstance(val, str):
            return [f"rule '{rid}' {key} must name a flag"]
        if known['flags'] is not None and val not in known['flags']:
            return [f"rule '{rid}' {key}s flag '{val}', which is not declared in flags"]
        return []
    if key in ('believes', 'stops-believing'):
        return _rule_payload_errors(rid, key, val,
                                    (('who', 'person'), ('claim', 'claim')), known)
    if key == 'tells':
        return _rule_payload_errors(rid, 'tells', val,
                                    (('who', 'person'), ('claim', 'claim'),
                                     ('to', 'person')), known)
    if key == 'weather':
        if val not in ('fog', 'clear'):
            return [f"rule '{rid}' weather must be 'fog' or 'clear'"]
        return []
    return _rule_value_errors(rid, 'point-to', val, 'place', known)


def _rule_conflict_message(aid: str, bid: str, then_a, then_b) -> str | None:
    """What two rules' actions disagree about, or None when they agree.

    Only the two conflicts the design names are decided here: two
    different weather values on one event, and one thing shown by a
    rule that another hides on the same event. Anything subtler is
    left alone rather than guessed at.
    """
    if not isinstance(then_a, list) or not isinstance(then_b, list):
        return None

    def _values(actions, key):
        return [a.get(key) for a in actions
                if isinstance(a, dict) and key in a]

    for wa in _values(then_a, 'weather'):
        for wb in _values(then_b, 'weather'):
            if wa != wb:
                return (f"rules '{aid}' and '{bid}' fire on the same event with "
                        f"conflicting actions - one sets weather '{wa}' while "
                        f"the other sets '{wb}'")
    for shown in _values(then_a, 'show'):
        if shown in _values(then_b, 'hide'):
            return (f"rules '{aid}' and '{bid}' fire on the same event with "
                    f"conflicting actions - one shows '{shown}' while the other "
                    "hides it")
    for shown in _values(then_b, 'show'):
        if shown in _values(then_a, 'hide'):
            return (f"rules '{aid}' and '{bid}' fire on the same event with "
                    f"conflicting actions - one shows '{shown}' while the other "
                    "hides it")
    return None


GROWTH_MODES = ('levels', 'practice')
GROWTH_STATS = ('hp', 'atk')
GROWTH_BY = ('strikes', 'hits-taken', 'consoles', 'hurls')


def _is_whole(v) -> bool:
    """True for a whole number (not a bool, which `int` also admits)."""
    return isinstance(v, int) and not isinstance(v, bool)


def _levels_growth_errors(levels: dict) -> list[str]:
    """Every problem with a `levels` growth block (empty = good)."""
    errors: list[str] = []
    xp = levels.get('xp')
    if not isinstance(xp, list) or not xp:
        errors.append("levels 'xp' must be a list of rising whole numbers "
                      'starting at 0')
    else:
        if len(xp) > 20:
            errors.append("levels 'xp' has more than 20 entries")
        if not all(_is_whole(v) for v in xp):
            errors.append("levels 'xp' must be whole numbers")
        elif xp[0] != 0:
            errors.append("levels 'xp' must start at 0")
        elif any(b <= a for a, b in zip(xp, xp[1:])):
            errors.append("levels 'xp' must strictly rise")
    gain = levels.get('gain')
    if gain is not None:
        if not isinstance(gain, dict):
            errors.append("levels 'gain' must be an object of 'hp' and 'atk'")
        else:
            for stat, v in gain.items():
                if stat not in GROWTH_STATS:
                    errors.append(
                        f"levels 'gain' names unknown stat '{stat}'")
                elif not _is_whole(v) or not 0 <= v <= 9:
                    errors.append(
                        f"levels 'gain.{stat}' must be a whole number 0 to 9")
    return errors


def _practice_growth_errors(practice: dict) -> list[str]:
    """Every problem with a `practice` growth block (empty = good)."""
    errors: list[str] = []
    for stat, spec in practice.items():
        if stat not in GROWTH_STATS:
            errors.append(f"practice names unknown stat '{stat}'")
            continue
        if not isinstance(spec, dict):
            errors.append(f"practice '{stat}' must be an object")
            continue
        by = spec.get('by')
        if by not in GROWTH_BY:
            errors.append(f"practice '{stat}' 'by' must be one of "
                          'strikes, hits-taken, consoles, hurls')
        every = spec.get('every')
        if not _is_whole(every) or not 1 <= every <= 99:
            errors.append(
                f"practice '{stat}' 'every' must be a whole number 1 to 99")
        gain = spec.get('gain')
        if not _is_whole(gain) or not 0 <= gain <= 9:
            errors.append(
                f"practice '{stat}' 'gain' must be a whole number 0 to 9")
        cap = spec.get('cap')
        if not _is_whole(cap) or cap < 1:
            errors.append(
                f"practice '{stat}' 'cap' must be a whole number of at least 1")
    return errors


def growth_errors(w: dict) -> list[str]:
    """Every problem with a pack's optional `growth` block (empty = good).

    Growth is optional and additive: a pack that declares none gets
    no output at all, exactly as before. A pack that declares one
    picks `levels` or `practice` and carries only that block; every
    other shape is a plain-sentence error naming the field.
    """
    if 'growth' not in w:
        return []
    growth = w.get('growth')
    if not isinstance(growth, dict):
        return ["growth must be an object with a 'mode'"]
    errors: list[str] = []
    mode = growth.get('mode')
    if mode not in GROWTH_MODES:
        errors.append("growth 'mode' must be 'levels' or 'practice'")
        return errors
    block = growth.get(mode)
    if not isinstance(block, dict):
        errors.append(f"growth mode '{mode}' needs a '{mode}' block")
        return errors
    other = 'practice' if mode == 'levels' else 'levels'
    if other in growth:
        errors.append("growth cannot carry both 'levels' and 'practice' "
                      '- choose one mode')
    if mode == 'levels':
        errors.extend(_levels_growth_errors(block))
    else:
        errors.extend(_practice_growth_errors(block))
    return errors


# The parts a skin may name (design/ui-skin.md). Anything else is a
# typo the author should read about, not a part the player silently
# ignores.
SKIN_PARTS = ('panel', 'button', 'tab', 'toggle', 'bar', 'slot', 'speech',
              'tooltip', 'gold-plate', 'divider', 'banner', 'corner', 'cursor')

# Every key of a part whose value is a picture file name. `slice` and
# `hotspot` are the only other keys the contract knows.
SKIN_PICTURE_KEYS = ('file', 'hover', 'pressed', 'disabled', 'selected',
                     'on', 'off', 'frame', 'fill', 'hand')

# The picture suffix a skin may use, and the per-picture size cap.
SKIN_SUFFIXES = ('.png', '.webp')
SKIN_PICTURE_BYTES = 300_000

# The one colour shape `ink` accepts.
_SKIN_INK_RE = re.compile(r'^#[0-9a-fA-F]{6}$')


def _picture_size(path: str) -> tuple[int, int] | None:
    """(width, height) read from a png or webp header, or None.

    PNG dimensions come from the IHDR chunk. WebP is read on a
    best-effort basis (VP8X canvas, VP8 frame header); a picture whose
    header cannot be read returns None, so the caller skips the
    half-slice check rather than guess.
    """
    try:
        with open(path, 'rb') as f:
            head = f.read(32)
    except OSError:
        return None
    # PNG: signature (8) + length (4) + 'IHDR' (4) + width/height (8).
    if len(head) >= 24 and head[:8] == b'\x89PNG\r\n\x1a\n' and head[12:16] == b'IHDR':
        return int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')
    # WebP: RIFF....WEBP then a VP8X/VP8 chunk.
    if len(head) >= 30 and head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        chunk = head[12:16]
        if chunk == b'VP8X':
            w = int.from_bytes(head[24:27], 'little') + 1
            h = int.from_bytes(head[27:30], 'little') + 1
            return w, h
        if chunk == b'VP8 ' and head[23:26] == b'\x9d\x01\x2a':
            w = int.from_bytes(head[26:28], 'little') & 0x3fff
            h = int.from_bytes(head[28:30], 'little') & 0x3fff
            return w, h
    return None


def skin_errors(w: dict, pack_dir: Path | None = None) -> list[str]:
    """Every problem with a pack's optional `skin` (empty = good).

    A `"skin": "skins/<name>"` field names a folder inside the pack
    with a `skin.json` and its pictures (design/ui-skin.md, rules 1, 5,
    6). The field is optional and additive: a pack with none gets no
    output. The path must stay inside the pack; `skin.json` must be a
    JSON object with a non-empty `name` and `credit`; every part key
    must be a known part; every named picture must exist, end in .png
    or .webp, and stay under the size cap; `slice` must fit inside its
    picture; `ink` colours must be `#RRGGBB`. Every message is one
    plain sentence naming the thing to fix.
    """
    if 'skin' not in w:
        return []
    skin_rel = w.get('skin')
    if not isinstance(skin_rel, str) or not skin_rel.strip():
        return ["skin must name a folder inside the pack"]
    # The path stays inside the pack: no absolute path, no '..'.
    if os.path.isabs(skin_rel) or '..' in Path(skin_rel).parts:
        return [f"skin '{skin_rel}' must stay inside the pack"]
    # Everything past here needs the pack on disk (in-memory drafts have
    # no folder to read).
    if pack_dir is None:
        return []
    from .cli import _inside

    base = os.path.realpath(str(pack_dir))
    skin_dir = _inside(base, skin_rel)
    if skin_dir is None or not os.path.isdir(skin_dir):
        return [f"skin folder '{skin_rel}' does not exist inside the pack"]

    skin_json = os.path.join(skin_dir, 'skin.json')
    if not os.path.isfile(skin_json):
        return [f"skin folder '{skin_rel}' has no skin.json"]
    try:
        data = json.loads(Path(skin_json).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return [f"skin.json in '{skin_rel}' is not valid JSON"]
    if not isinstance(data, dict):
        return [f"skin.json in '{skin_rel}' must be a JSON object"]

    errors: list[str] = []
    for field in ('name', 'credit'):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"skin.json needs a non-empty string '{field}'")

    parts = data.get('parts')
    if not isinstance(parts, dict):
        errors.append("skin.json 'parts' must be an object of named parts")
        parts = {}
    for pname, spec in parts.items():
        if pname not in SKIN_PARTS:
            errors.append(f"skin.json part '{pname}' is not a known part")
            continue
        if not isinstance(spec, dict):
            errors.append(f"skin part '{pname}' must be an object")
            continue
        # Every picture a part names: real, webp/png, small enough.
        found: dict[str, str] = {}
        for key in SKIN_PICTURE_KEYS:
            fname = spec.get(key)
            if fname is None:
                continue
            if not isinstance(fname, str) or not fname:
                errors.append(
                    f"skin part '{pname}' {key} must name a picture file")
                continue
            target = _inside(skin_dir, fname)
            if target is None or not os.path.isfile(target):
                errors.append(
                    f"skin part '{pname}' {key} names '{fname}', which "
                    'does not exist in the skin folder')
                continue
            found[key] = target
            if os.path.splitext(fname)[1].lower() not in SKIN_SUFFIXES:
                errors.append(
                    f"skin part '{pname}' {key} names '{fname}', which is "
                    'not a webp or png picture')
                continue
            size = os.path.getsize(target)
            if size > SKIN_PICTURE_BYTES:
                errors.append(
                    f"skin part '{pname}' {key} picture '{fname}' is too "
                    f'big ({size} bytes; the cap is {SKIN_PICTURE_BYTES})')
        # `slice` fits inside the part's main picture: a whole number of
        # at least 1, at most half the smaller side.
        if 'slice' in spec:
            sl = spec['slice']
            # The main picture for the fit check: `file`, else `frame`,
            # else the first picture the part names.
            main = None
            for key in ('file', 'frame', *SKIN_PICTURE_KEYS):
                if key in found:
                    main = found[key]
                    break
            if not _is_whole(sl) or sl < 1:
                errors.append(
                    f"skin part '{pname}' slice must be a whole number "
                    'of at least 1')
            elif main is not None:
                size = _picture_size(main)
                if size is not None and sl * 2 > min(size):
                    errors.append(
                        f"skin part '{pname}' slice {sl} is more than half "
                        f'the smaller side of its picture ({min(size)} px)')
        # `hotspot` is carried through untouched; only its presence has
        # a home in the player.

    ink = data.get('ink')
    if ink is not None:
        if not isinstance(ink, dict):
            errors.append("skin.json 'ink' must be an object of #RRGGBB colours")
        else:
            for name, colour in ink.items():
                if not isinstance(colour, str) or not _SKIN_INK_RE.match(colour):
                    errors.append(
                        f"skin.json ink '{name}' must be a #RRGGBB colour")
    return errors


def rules_errors(w: dict, pack_dir: Path | None = None) -> list[str]:
    """Every problem with a pack's optional flags/claims/people/rules.

    The four keys are optional and additive: a pack that declares
    none of them gets no output at all, exactly as before. A pack
    that declares any of them gets every rule checked here, at
    authoring time, rather than by surprise in play. Messages are
    plain sentences; rule-level ones name the rule id.
    """
    if not any(k in w for k in ('flags', 'claims', 'people', 'rules')):
        return []
    errors: list[str] = []
    if 'flags' in w and not isinstance(w['flags'], dict):
        errors.append('flags must be an object mapping a flag name to one line of text')
    if 'claims' in w:
        if not isinstance(w['claims'], dict):
            errors.append('claims must be an object mapping a claim name to meaning and truth')
        else:
            for cname, spec in w['claims'].items():
                if not isinstance(spec, dict):
                    errors.append(f"claim '{cname}' must be an object with 'meaning' and 'true'")
                    continue
                meaning = spec.get('meaning')
                if not isinstance(meaning, str) or not meaning.strip():
                    errors.append(f"claim '{cname}' needs a non-empty string 'meaning'")
                if not isinstance(spec.get('true'), bool):
                    errors.append(f"claim '{cname}' needs 'true' set to true or false")
    speakers = w.get('speakers') if isinstance(w.get('speakers'), dict) else {}
    if 'people' in w:
        if not isinstance(w['people'], dict):
            errors.append('people must be an object mapping a person id to beliefs')
        else:
            for pid, spec in w['people'].items():
                if pid not in speakers:
                    # A person must be someone the hero can meet.
                    errors.append(f"person '{pid}' in people is not a speaker in this pack")
                if not isinstance(spec, dict):
                    errors.append(f"person '{pid}' in people must be an object with 'believes'")
                    continue
                believes = spec.get('believes')
                if not isinstance(believes, list) or not all(
                        isinstance(c, str) for c in believes):
                    errors.append(f"person '{pid}' in people needs a 'believes' "
                                  'list of claim names')
    if 'rules' in w and not isinstance(w['rules'], list):
        errors.append('rules must be a list')
        return errors
    rules = w.get('rules') or []
    if len(rules) > RULE_LIMIT:
        errors.append(f'this pack declares {len(rules)} rules - the limit is {RULE_LIMIT}')
    known = _rule_known_ids(w, pack_dir)
    seen: set = set()
    fireable: list = []
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f'the rule at position {index} must be an object')
            continue
        rid = rule.get('id')
        if not isinstance(rid, str) or not rid.strip():
            errors.append(f'the rule at position {index} needs a non-empty string id')
            continue
        label = f"rule '{rid}'"
        if rid in seen:
            errors.append(f"two rules share the id '{rid}' - rule ids must be unique")
            continue
        seen.add(rid)
        # `once` absent means true: a rule runs once unless the pack
        # asks otherwise, so only a non-boolean value is an error.
        if 'once' in rule and not isinstance(rule['once'], bool):
            errors.append(f"{label} 'once' must be true or false")
        if 'when' not in rule:
            errors.append(f"{label} needs a 'when' event")
        else:
            errors.extend(_rule_event_errors(rid, rule['when'], known))
        if 'if' in rule and not isinstance(rule['if'], list):
            errors.append(f"{label} 'if' must be a list of conditions")
        elif isinstance(rule.get('if'), list):
            for cond in rule['if']:
                errors.extend(_rule_condition_errors(rid, cond, known))
        then = rule.get('then')
        if not isinstance(then, list) or not then:
            errors.append(f"{label} 'then' must be a non-empty list of actions")
        else:
            for action in then:
                errors.extend(_rule_action_errors(rid, action, known))
        if 'on' in rule:
            on = rule['on']
            if not isinstance(on, str):
                errors.append(f"{label} 'on' must name a thing")
            elif on not in known['things']:
                errors.append(f"{label} 'on' names unknown thing '{on}'")
        fireable.append((rid, rule))
    # CONFLICT: two rules that fire on the same event and can both
    # pass it - same `when`, same `on`, same `if` - may disagree in
    # what they do. Rules with different `if` lists are not compared:
    # the validator cannot honestly decide whether two different
    # conditions overlap in play.
    for i, (aid, arule) in enumerate(fireable):
        for bid, brule in fireable[i + 1:]:
            if not isinstance(arule.get('when'), dict):
                continue
            if arule.get('when') != brule.get('when'):
                continue
            if arule.get('on') != brule.get('on'):
                continue
            if (arule.get('if') or []) != (brule.get('if') or []):
                continue
            message = _rule_conflict_message(aid, bid, arule.get('then'),
                                             brule.get('then'))
            if message:
                errors.append(message)
    return errors


def _iter_conditions(node):
    """Yield every condition inside a rule's `if`, through `not` and `all-of`."""
    if isinstance(node, list):
        for sub in node:
            yield from _iter_conditions(sub)
    elif isinstance(node, dict):
        yield node
        if len(node) == 1 and 'not' in node:
            yield from _iter_conditions(node['not'])
        if len(node) == 1 and 'all-of' in node:
            yield from _iter_conditions(node['all-of'])


def rules_notes(w: dict, pack_dir: Path | None = None) -> list[str]:
    """Two warnings a pack can carry WITHOUT failing validation.

    Deliberately NOT called from validate() or cmd_validate: these
    are notes for a pack author, not errors. A pack with neither
    passes `norns validate` untouched.

    - a claim someone believes that no rule ever makes true or false
      in play: the belief starts and can never move;
    - a belief nothing can ever read: no rule's conditions test it.

    A belief is tracked as the (person, claim) pair. Deciding whether
    two *different* condition lists might overlap in play is not
    attempted here - only what the rules literally say.
    """
    if not any(k in w for k in ('flags', 'claims', 'people', 'rules')):
        return []
    notes: list[str] = []
    rules = w.get('rules') if isinstance(w.get('rules'), list) else []
    people = w.get('people') if isinstance(w.get('people'), dict) else {}
    changed_claims: set = set()   # claims some rule action touches
    born: set = set()             # (person, claim) pairs some rule creates
    read: set = set()             # (person, claim) pairs some condition tests
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if isinstance(rule.get('if'), list):
            for cond in _iter_conditions(rule['if']):
                if not isinstance(cond, dict):
                    continue
                for verb in ('believes', 'not-believes'):
                    payload = cond.get(verb)
                    if isinstance(payload, dict):
                        who, claim = payload.get('who'), payload.get('claim')
                        if isinstance(who, str) and isinstance(claim, str):
                            read.add((who, claim))
        then = rule.get('then')
        if not isinstance(then, list):
            continue
        for action in then:
            if not isinstance(action, dict) or len(action) != 1:
                continue
            key = next(iter(action))
            payload = action[key]
            if not isinstance(payload, dict):
                continue
            claim = payload.get('claim')
            if not isinstance(claim, str):
                continue
            if key in ('believes', 'stops-believing'):
                changed_claims.add(claim)
                if key == 'believes' and isinstance(payload.get('who'), str):
                    born.add((payload['who'], claim))
            elif key == 'tells':
                changed_claims.add(claim)
                if isinstance(payload.get('to'), str):
                    born.add((payload['to'], claim))
    declared: set = set()
    for pid, spec in people.items():
        if isinstance(spec, dict) and isinstance(spec.get('believes'), list):
            for claim in spec['believes']:
                if isinstance(claim, str):
                    declared.add((pid, claim))
    for pid, claim in sorted(declared):
        if claim not in changed_claims:
            notes.append(f"claim '{claim}', believed by '{pid}', is never made "
                         'true or false by any rule in play')
        if (pid, claim) not in read:
            notes.append(f"'{pid}' believes '{claim}' but no rule's conditions "
                         'ever read that belief')
    for pid, claim in sorted(born - declared):
        if (pid, claim) not in read:
            notes.append(f"a rule sets '{pid}' to believe '{claim}' but no rule's "
                         'conditions ever read that belief')
    return notes


def _engine_tiles_dir() -> Path | None:
    """The engine's own ground pictures, found the way the woven
    player finds web/packaged.html: the first candidate whose sibling
    `art/tiles/` directory exists. None when the engine's own web tree
    cannot be resolved at all."""
    from .cli import _template_candidates

    for candidate in _template_candidates():
        tiles = candidate.parent / 'art' / 'tiles'
        if tiles.is_dir():
            return tiles
    # NOTE: an engine tile directory that cannot be found is not a pack
    # error; the caller skips the engine-set half of the check rather
    # than failing every pack.
    return None


def _region_dirs(pack: Path, w: dict, region_geo: dict) -> dict:
    """Map each region name to its on-disk directory.

    Mirrors the loader: the flat shape is the pack root (one implicit
    region); the acts shape is <pack>/acts/<act-dir>/<region>, with
    the act directory resolved by its declared `id` through
    cli._act_dir_for, so an act whose id differs from its directory
    name still resolves. A region whose act directory cannot be
    resolved maps to None - it is read as having no tiles/, never a
    crash.
    """
    from .cli import _act_dir_for, _has_subdir, _inside

    names = list(region_geo)
    if not _has_subdir(pack, 'acts'):
        # NOTE: a flat pack keeps its ground at the pack root; that is
        # the flat-shape equivalent of a region's tiles/ directory.
        return {r: pack for r in names}
    acts = w.get('acts')
    if isinstance(acts, list) and acts and isinstance(acts[0], dict):
        act_id = acts[0].get('id')
    else:
        # The unified load_pack shape carries the act directory name;
        # _act_dir_for accepts it as its own id.
        act_id = w.get('_act_id')
    act_dir = _act_dir_for(pack, act_id)
    # NOTE: region_geo covers the first act's regions (the only ones
    # maplab reads), so one act directory is enough.
    out: dict = {}
    for r in names:
        region = None
        if act_dir is not None and isinstance(r, str) and r and '\0' not in r:
            # the region name comes from pack data: resolve it inside the act directory or not at all
            found = _inside(os.path.realpath(act_dir), r)
            region = Path(found) if found is not None else None
        out[r] = region
    return out


def _tile_errors(pack: Path, w: dict, region_geo: dict) -> list[str]:
    """Every tile-picture problem for a pack on disk (empty = good).

    A region that brings a `tiles/` directory opts into strict checks:
    every explicit legend `tile` must resolve to the region's own
    pictures or the engine set, every numbered variant must sit in an
    unbroken sequence, and every non-dot file must be .webp or .png.
    A region with no `tiles/` keeps the silent engine fallback, so
    existing packs validate green.
    """
    from .cli import _inside
    from .world import (_TILE_GRID_RE, _TILE_SUFFIXES, _TILE_VARIANT_RE,
                        TILE_GRID_MAX, _discover_tiles, tile_grid)

    engine_tiles = _engine_tiles_dir()
    engine_real = os.path.realpath(engine_tiles) if engine_tiles is not None else None
    pack_real = os.path.realpath(pack)
    dirs = _region_dirs(pack, w, region_geo)
    errors: list[str] = []
    for rname, geo in region_geo.items():
        if not isinstance(geo, dict):
            continue
        region_dir = dirs.get(rname)
        if region_dir is None:
            # NOTE: no resolvable act directory means no tiles/ to read;
            # skip the region rather than infer one.
            continue
        region_real = os.path.realpath(region_dir)
        if region_real != pack_real and not region_real.startswith(pack_real + os.sep):
            continue  # a region that resolves outside the pack is never read
        tiles_real = _inside(region_real, 'tiles')
        if tiles_real is None or not os.path.isdir(tiles_real):
            # Compatibility: a region with no tiles/ is unchanged.
            continue
        tiles_dir = Path(tiles_real)
        legend = geo.get('legend')
        legend = legend if isinstance(legend, dict) else {}
        known = set(_discover_tiles(tiles_dir))
        for ch, spec in legend.items():
            if not isinstance(spec, dict):
                continue
            name = spec.get('tile')
            if not (isinstance(name, str) and name):
                continue
            if name in known:
                continue
            if engine_real is None:
                # NOTE: no engine set to consult; the unknown-name check
                # is skipped, never failed (see _engine_tiles_dir).
                continue
            # the tile name comes from pack data: only a plain name inside the engine set can match
            engine_pic = None if '\0' in name else _inside(engine_real, f'{name}.webp')
            if engine_pic is not None and os.path.isfile(engine_pic):
                continue
            errors.append(
                f"region '{rname}': symbol '{ch}' names tile '{name}', which "
                f"is in neither the region's tiles/ nor the engine's art")
        # NOTE: a file the loader cannot read is a pack-authoring error
        # (the more restrictive reading). Dotfiles stay ignored exactly
        # as the loader ignores them.
        variants: dict[str, set[int]] = {}
        grids: set[str] = set()
        for f in sorted(tiles_dir.rglob('*')):
            if not f.is_file():
                continue
            rel = f.relative_to(tiles_dir)
            if any(part.startswith('.') for part in rel.parts):
                continue
            if f.suffix.lower() not in _TILE_SUFFIXES:
                errors.append(
                    f"region '{rname}': tiles/{rel.as_posix()} is not a tile "
                    f"picture (.webp or .png only)")
                continue
            stem = f.name[: -len(f.suffix)]
            if _TILE_GRID_RE.match(stem):
                grid = tile_grid(stem)
                if grid is None:
                    errors.append(
                        f"region '{rname}': tiles/{rel.as_posix()} is not a valid grid picture "
                        f"(each side 1..{TILE_GRID_MAX}, at least 2 cells; e.g. wood.grid3x3.webp)")
                else:
                    grids.add(grid[0])
                continue
            m = _TILE_VARIANT_RE.match(stem)
            if m:
                base, num = m.group('base'), int(m.group('num'))
            else:
                # NOTE: the unnumbered picture is variant 1; a stray
                # `name.1` names the same slot, so neither is a gap.
                base, num = stem, 1
            variants.setdefault(base, set()).add(num)
        for base in sorted(grids & set(variants)):
            errors.append(
                f"region '{rname}': tile '{base}' has a grid picture AND other pictures; "
                f"the grid is the one drawn and the others are ignored - remove one")
        for base, nums in variants.items():
            # NOTE: variant 1 is the unnumbered file and is optional, so
            # the numbered sequence the player walks begins at 2. Only a
            # hole in 2, 3, ... is a gap; a name that simply starts at 2
            # is whole, and the absence of 1 is never a gap.
            missing = sorted(n for n in range(2, max(nums) + 1)
                             if n not in nums)
            if missing:
                # NOTE: one error per tile name, naming the first hole in
                # the numbered sequence (variant 1 is optional).
                errors.append(
                    f"region '{rname}': tile '{base}' has a variant gap - "
                    f"variant {missing[0]} is missing")
    return errors


def _sprite_scale_errors(w: dict) -> list[str]:
    """Plain problems with `player.sprite_scale` (empty = good or absent). Reads the block load_pack already holds."""
    import math

    player = w.get('_player')
    if not isinstance(player, dict) or 'sprite_scale' not in player:
        return []
    scales = player['sprite_scale']
    if not isinstance(scales, dict):
        return ["player.sprite_scale must be an object like {\"hearth-cat\": 0.5}"]
    named = player.get('sprites') if isinstance(player.get('sprites'), dict) else {}
    errors: list[str] = []
    for name, v in scales.items():
        if name not in named:
            errors.append(f"player.sprite_scale names '{name}', which has no picture in player.sprites")
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0.2 <= v <= 2.0:
            errors.append(f"player.sprite_scale for '{name}' must be a number from 0.2 to 2 (1 is the standard size)")
    return errors


def validate(w: dict, pack_dir: Path | None = None) -> list[str]:
    """Every geometry check. Returns a list of problems (empty = good).

    Accepts both shapes:

      Flat shape: w['town'] is the town block directly.
      Acts shape: w['acts'][0]['_town_legacy'] holds the town block
        (preserved for backward compat) and the act's speakers live
        at w['acts'][0]['speakers']. The unified shape produced by
        load_pack() sets w['town'] and w['speakers'] explicitly.
    """
    errors: list[str] = []
    if 'town' not in w and 'acts' in w and w['acts']:
        # Acts shape: synthesize the flat keys the rest of the
        # validator reads, so the same code path works for both.
        act = w['acts'][0]
        w = {
            **w,
            'town': act.get('_town_legacy', {}),
            'speakers': act.get('speakers', w.get('speakers', {})),
        }
    # The pack's grammars (optional): checked first so a broken
    # grammar is reported even when the map is wrong too.
    errors.extend(grammar_errors(w.get('grammars', {})))
    # The item catalog's optional `light` field: checked here so a bad
    # torch is a pack-authoring error, not a silent no-op in play.
    items = w.get('items')
    if isinstance(items, dict):
        for iid, spec in items.items():
            if isinstance(spec, dict):
                errors.extend(item_light_errors(iid, spec))
    # The pack's optional rules/flags/claims/people catalog: checked
    # beside the other optional catalogs so a broken rule is a
    # pack-authoring error, not a surprise in play. A pack that
    # declares none of the four keys gets nothing here.
    errors.extend(rules_errors(w, pack_dir))
    # The pack's optional skin (design/ui-skin.md), checked beside the
    # other optional catalogs. A pack that declares none gets nothing.
    errors.extend(skin_errors(w, pack_dir))
    # The pack's optional growth block (design/growth.md), checked
    # beside the other optional catalogs. A pack that declares none
    # gets nothing here.
    errors.extend(growth_errors(w))
    town = w['town']
    m = town['map']
    legend = town['legend']

    widths = {len(r) for r in m}
    if len(widths) != 1:
        errors.append(f'map rows are not rectangular: widths {sorted(widths)}')
        return errors

    used = set(''.join(m))
    missing_legend = sorted(used - set(legend))
    if missing_legend:
        errors.append(f'map chars missing from legend: {missing_legend}')

    start = tuple(town['hero_start'])
    if not walkable(w, *start):
        errors.append(f'hero_start {start} is not walkable')

    seen = reach(w, start)

    def near_open(x: int, y: int) -> bool:
        """A poi is usable if a walkable tile sits within the renderer's
        poiAt radius (2.4) of the label."""
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if (dx * dx + dy * dy) ** 0.5 <= 2.4 and walkable(w, x + dx, y + dy):
                    return True
        return False

    for key in town.get('pois', {}):
        x, y = (int(v) for v in key.split(','))
        if not near_open(x, y):
            errors.append(f'poi {key} ({town["pois"][key]}) has no reachable tile nearby')

    for x in range(len(m[0])):
        for y in range(len(m)):
            if m[y][x] in ('d', 'D') and (x, y) not in seen:
                errors.append(f'door at ({x},{y}) is unreachable')

    first_region = w.get('_region')
    for s in w.get('speakers', {}).values():
        if first_region and s.get('region', first_region) != first_region:
            continue   # a speaker of another region is checked on that map
        at = tuple(s['at'])
        if not walkable(w, *at):
            errors.append(f'speaker {s["name"]} stands on solid ground at {at}')
        elif at not in seen:
            errors.append(f'speaker {s["name"]} at {at} is unreachable')
        if set(s.get('seeds', {})) != set(w['phases']):
            errors.append(f'speaker {s["name"]} seeds do not cover every phase')

    if not town.get('sanctuary_tiles'):
        errors.append('no sanctuary tiles - the world needs one safe place')

    water = town.get('water_by_phase', {})
    if set(water) != set(w['phases']):
        errors.append('water_by_phase does not cover every phase')
    for x, y in town.get('flood_tiles', []):
        if not (0 <= y < len(m) and 0 <= x < len(m[0])):
            errors.append(f'flood tile ({x},{y}) is out of bounds')
        elif m[y][x] == '~':
            errors.append(f'flood tile ({x},{y}) is already deep water')

    voices = w.get('voices', {})
    stefna_voice = w.get('stefna_voice')
    if stefna_voice is not None:
        if stefna_voice not in voices:
            errors.append(f"stefna_voice '{stefna_voice}' does not resolve to a declared voice")

    for vkey, voice in voices.items():
        if not isinstance(voice, dict) or not str(voice.get('strike', '')).strip():
            errors.append(f"voice '{vkey}' is missing required non-empty 'strike' prompt")

    if pack_dir is not None:
        p = Path(pack_dir)
        # Helper to check if a voice file exists in acts or flat layout
        def find_voice_file(fname: str) -> bool:
            if not fname:
                return False
            basename = Path(fname).name
            acts_dir = p / 'acts'
            if acts_dir.is_dir():
                for act_dir in acts_dir.iterdir():
                    if not act_dir.is_dir():
                        continue
                    for region_dir in act_dir.iterdir():
                        if (region_dir / 'voices' / basename).exists():
                            return True
            if (p / fname).exists() or (p / 'voices' / basename).exists():
                return True
            return False

        for vkey, voice in voices.items():
            # In flat packs or acts packs, check if voice file exists on disk
            vfile = voice.get('file', f'voices/{vkey}.md') if isinstance(voice, dict) else f'voices/{vkey}.md'
            if not find_voice_file(vfile):
                errors.append(f"missing voice file for voice '{vkey}': {vfile}")

        for spec in w.get('speakers', {}).values():
            sfile = spec.get('voice_file', '')
            if not find_voice_file(sfile):
                errors.append(f'missing speaker voice file: {sfile}')

    # Pack law: each act declares how it plays (world.py contract).
    # Shape-checked here; the mechanics land with the ruleset
    # modules. A bad value is a pack authoring error, so it fails
    # validation loudly instead of silently defaulting.
    for act in w.get('acts', []):
        aid = act.get('id', '?')
        floor = act.get('floor', 'costume')
        if floor not in VALID_FLOORS:
            errors.append(f"act '{aid}' floor '{floor}' not in {list(VALID_FLOORS)}")
        tone = act.get('tone', '')
        if tone and tone not in VALID_TONES:
            errors.append(f"act '{aid}' tone '{tone}' not in {list(VALID_TONES)}")
        ruleset = act.get('ruleset', 'ambient')
        if not isinstance(ruleset, str) or not ruleset.strip():
            errors.append(f"act '{aid}' ruleset must be a non-empty string")
        for fname in ('verbs', 'enemies', 'bosses'):
            val = act.get(fname, [])
            if not isinstance(val, list):
                errors.append(f"act '{aid}' {fname} must be a list")
            elif not all(isinstance(x, str) for x in val):
                errors.append(f"act '{aid}' {fname} must be a list of strings")
        # `transitions` is the act's doors now, not a string list; the
        # shape and tiles are checked below.
        if not isinstance(act.get('transitions', []), list):
            errors.append(f"act '{aid}' transitions must be a list")

    # Cooking ruleset content (the act-1 loop): the morning is pack-
    # authored; the engine only resolves it. Orders must reference
    # real pantry ids so a served order can be checked
    # deterministically, and every ticket needs a note - the
    # customer's voice IS the order (reading them is the game).
    for act in w.get('acts', []):
        if act.get('ruleset') != 'cooking':
            continue
        aid = act.get('id', '?')
        block = act.get('cooking') or {}
        if not isinstance(block, dict):
            errors.append(f"act '{aid}' cooking block must be an object")
            continue
        pantry = block.get('pantry', [])
        pids = set()
        if not isinstance(pantry, list) or not pantry:
            errors.append(f"act '{aid}' cooking pantry must be a non-empty list")
        for item in pantry:
            if not isinstance(item, dict) or not str(item.get('id', '')).strip():
                errors.append(f"act '{aid}' pantry entries need an id")
                continue
            pids.add(item['id'])
            if not str(item.get('label', '')).strip():
                errors.append(f"act '{aid}' pantry entry '{item.get('id')}' needs a label")
        tickets = block.get('tickets', [])
        tlist = tickets if isinstance(tickets, list) else []
        if not isinstance(tickets, list) or not tickets:
            errors.append(f"act '{aid}' cooking tickets must be a non-empty list")
        for t in tlist:
            if not isinstance(t, dict) or not str(t.get('id', '')).strip():
                errors.append(f"act '{aid}' tickets need an id")
                continue
            order = t.get('order', [])
            if not isinstance(order, list) or not order:
                errors.append(f"act '{aid}' ticket '{t.get('id')}' needs a non-empty order")
            elif not all(o in pids for o in order):
                errors.append(
                    f"act '{aid}' ticket '{t.get('id')}' order references unknown pantry ids")
            if not str(t.get('note', '')).strip():
                errors.append(f"act '{aid}' ticket '{t.get('id')}' needs a note (the customer's voice)")
        length = block.get('morning_length', len(tlist))
        if not isinstance(length, int) or length < 1 or length > len(tlist):
            errors.append(f"act '{aid}' morning_length must be 1..len(tickets)")
        heads = block.get('headlines', [])
        if (not isinstance(heads, list) or len(heads) < 2
                or not all(isinstance(h, str) and h.strip() for h in heads)):
            errors.append(f"act '{aid}' cooking headlines must be at least two non-empty strings")
        if act.get('ruleset') == 'desk':
            dblock = act.get('desk') or {}
            if not isinstance(dblock, dict):
                errors.append(f"act '{aid}' desk block must be an object")
            else:
                dheads = dblock.get('headlines', [])
                if (not isinstance(dheads, list) or len(dheads) < 2
                        or not all(isinstance(h, str) and h.strip() for h in dheads)):
                    errors.append(
                        f"act '{aid}' desk headlines must be at least two non-empty strings")

    # Transitions: the act's doors between regions. A door is a tile
    # you step on in `from` that lands the hero at `to_at` in `to`.
    # Shape and door tiles are checked here; every region's *full*
    # geometry (reachability, pois, water) is still a follow-on -
    # only the first region's town is validated above.
    transitions = w.get('transitions')
    if transitions is None and w.get('acts'):
        transitions = w['acts'][0].get('transitions', [])
    transitions = transitions or []
    region_geo = w.get('regions')
    if not isinstance(region_geo, dict) and w.get('acts'):
        region_geo = {}
        for rname, rdata in (w['acts'][0].get('regions') or {}).items():
            contract = rdata.get('contract') or {}
            rows = [ln for ln in (rdata.get('map_text') or '').splitlines()
                    if ln.strip()]
            region_geo[rname] = {'map': rows,
                                 'legend': contract.get('legend', {}),
                                 'enemies': contract.get('enemies', [])}
    if not isinstance(region_geo, dict):
        region_geo = {}
    if not region_geo and isinstance(w.get('town'), dict):
        # A flat shape has one implicit region; name it so a door
        # written against it can still be checked.
        region_geo = {w.get('_region') or 'town': {
            'map': w['town'].get('map', []),
            'legend': w['town'].get('legend', {}),
            'enemies': w['town'].get('enemies', []),
        }}

    # A pack may bring its own ground pictures under each region's
    # tiles/. That is on-disk data, so it is only checked when the pack
    # directory is known. Regions without a tiles/ directory keep the
    # silent engine fallback (the compatibility rule).
    if pack_dir is not None:
        errors.extend(_tile_errors(Path(pack_dir), w, region_geo))
        errors.extend(_sprite_scale_errors(w))

    def _door_tile_errors(index, field, rname, at):
        geo = region_geo.get(rname, {})
        rows = geo.get('map') or []
        legend = geo.get('legend') or {}
        if (not isinstance(at, (list, tuple)) or len(at) != 2
                or not all(isinstance(v, (int, float)) for v in at)):
            errors.append(
                f"transition {index} {field} in region '{rname}' "
                f"must be a tile [x, y]")
            return
        x, y = int(at[0]), int(at[1])
        ok = _map_tile_walkable(rows, legend, x, y)
        if ok is None:
            errors.append(
                f"transition {index} {field} ({x},{y}) is off the map "
                f"of region '{rname}'")
        elif not ok:
            errors.append(
                f"transition {index} {field} ({x},{y}) is on a solid "
                f"tile in region '{rname}'")

    for i, t in enumerate(transitions):
        if not isinstance(t, dict):
            errors.append(
                f'transition {i} must be an object with from, to, at, to_at')
            continue
        missing = [k for k in ('from', 'to', 'at', 'to_at') if k not in t]
        if missing:
            errors.append(f'transition {i} is missing {missing}')
            continue
        from_name, to_name = t['from'], t['to']
        if from_name not in region_geo:
            errors.append(
                f"transition {i} leaves region '{from_name}', which is "
                f"not a declared region")
        else:
            _door_tile_errors(i, 'at', from_name, t['at'])
        if to_name not in region_geo:
            errors.append(
                f"transition {i} enters region '{to_name}', which is "
                f"not a declared region")
        else:
            _door_tile_errors(i, 'to_at', to_name, t['to_at'])

    # The region contracts' enemies: each is a named hazard with a
    # walkable tile and real numbers. Every declared region is checked
    # (not just the first); a broken one is named in plain words. An
    # optional `xp` (design/growth.md) is a whole number of at least 0
    # and belongs to `levels` mode only.
    _growth = w.get('growth')
    levels_mode = isinstance(_growth, dict) and _growth.get('mode') == 'levels'
    for rname, geo in region_geo.items():
        if not isinstance(geo, dict):
            continue
        rows = geo.get('map') or []
        legend = geo.get('legend') or {}
        listed = geo.get('enemies')
        if listed is None:
            continue
        if not isinstance(listed, list):
            errors.append(f"region '{rname}' enemies must be a list")
            continue
        seen_ids: set = set()
        for i, e in enumerate(listed):
            if not isinstance(e, dict):
                errors.append(f"region '{rname}' enemy {i} must be an object")
                continue
            who = str(e.get('name') or e.get('id') or f'#{i}')
            eid = e.get('id')
            if not str(eid or '').strip():
                errors.append(f"enemy '{who}' in region '{rname}' needs an id")
            elif eid in seen_ids:
                errors.append(
                    f"enemy '{who}' in region '{rname}' repeats the id '{eid}'")
            else:
                seen_ids.add(eid)
            if not str(e.get('name', '')).strip():
                errors.append(f"enemy '{who}' in region '{rname}' needs a name")
            at = e.get('at')
            if (not isinstance(at, (list, tuple)) or len(at) != 2
                    or not all(isinstance(v, (int, float))
                               and not isinstance(v, bool) for v in at)):
                errors.append(
                    f"enemy '{who}' in region '{rname}' needs a tile [x, y]")
            else:
                x, y = int(at[0]), int(at[1])
                ok = _map_tile_walkable(rows, legend, x, y)
                if ok is None:
                    errors.append(
                        f"enemy '{who}' in region '{rname}' at ({x},{y}) "
                        f"is off the map")
                elif not ok:
                    errors.append(
                        f"enemy '{who}' in region '{rname}' at ({x},{y}) "
                        f"stands on a solid tile")
            for stat in ('hp', 'atk'):
                v = e.get(stat)
                if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                    errors.append(
                        f"enemy '{who}' in region '{rname}' needs a "
                        f"positive {stat}")
            # `xp` names the enemy id (not the display name), so the
            # author can find the exact contract entry to fix.
            xp = e.get('xp')
            if xp is not None:
                if not levels_mode:
                    errors.append(
                        f"enemy '{eid}' in region '{rname}' may only carry "
                        "'xp' in levels mode")
                elif not _is_whole(xp) or xp < 0:
                    errors.append(
                        f"enemy '{eid}' in region '{rname}' needs a whole "
                        "'xp' of 0 or more")

    # The Library: authored books this pack keeps (library/*.md). Needs the
    # pack on disk; in-memory validation (chat drafts) has no books yet.
    if pack_dir is not None:
        from .library import load_library, validate_books
        errors.extend(validate_books(load_library(Path(pack_dir)), town=town,
                                     speakers=w.get('speakers')))

    return errors


def _preserve_unknown(path: Path, known: dict) -> dict:
    """The previous file's keys, with `known` winning on conflict.

    A pack may carry fields the builder does not model: a game's title
    art and accent in `player`, a `stefna_voice`, a key from a future
    engine. A write must never silently drop them, so the file already
    on disk is the base and the writer overwrites only what it owns.
    """
    existing: dict = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding='utf-8'))
        except ValueError:
            existing = {}
    if not isinstance(existing, dict):
        existing = {}
    return {**existing, **known}


def write_pack(pack_dir: Path, w: dict) -> None:
    """Atomic write - an interrupted build must never leave world.json
    truncated.

    Handles both shapes:

      Flat: writes a single world.json with all keys at the top.
      Acts: writes the pack-level world.json with phases/voices/bonds
        and the per-act world.json with the act's region, speakers,
        and town data.

    A unified shape from load_pack() (the path most callers use)
    has w['town'] synthesized; this function demuxes it back into
    the on-disk shape that matches the source pack.
    """
    pack = Path(pack_dir)
    tmp = pack / 'world.json.tmp'
    if 'acts' in w or (pack / 'acts').is_dir():
        # Acts shape: write pack-level + per-act JSONs, with the
        # town metadata in acts/<id>/town/contract.json (the
        # convention-driven home) and the map in acts/<id>/town/map.md.
        act_id = w.get('_act_id') or 'act-1'
        act_dir = pack / 'acts' / act_id
        act_dir.mkdir(parents=True, exist_ok=True)
        town = w.get('town', {})
        # The act contract: id, title, regions, speakers. Town
        # metadata lives in town/contract.json, not inline.
        # NOTE: this used to write 'regions': ['town'] and empty enemies/bosses every time, so a write on a
        # pack with several rooms (Cottage has six) silently threw the room list away. Only what this
        # function actually owns or was given is written; everything else on disk is kept.
        owned = {
            'id': act_id,
            'title': w.get('title', pack.name),
            'speakers': w.get('speakers', {}),
            'transitions': w.get('transitions', []),
        }
        loaded_regions = w.get('regions')
        if isinstance(loaded_regions, dict) and loaded_regions:
            owned['regions'] = list(loaded_regions)          # home room first, in the order loaded
        for key in ('enemies', 'bosses'):
            if key in w:                                      # absent means: keep what the file has
                owned[key] = w[key]
        act_contract = _preserve_unknown(act_dir / 'world.json', owned)
        act_contract.setdefault('regions', ['town'])          # a brand-new pack still gets its one room
        act_contract.setdefault('enemies', [])
        act_contract.setdefault('bosses', [])
        act_tmp = act_dir / 'world.json.tmp'
        act_tmp.write_text(json.dumps(act_contract, indent=2,
                                      ensure_ascii=False) + '\n', encoding='utf-8')
        act_tmp.replace(act_dir / 'world.json')
        # The town contract (every town-metadata field except map).
        town_dir = act_dir / 'town'
        town_dir.mkdir(parents=True, exist_ok=True)
        town_contract = _preserve_unknown(
            town_dir / 'contract.json',
            {k: v for k, v in town.items() if k != 'map'},
        )
        if town_contract:
            (town_dir / 'contract.json').write_text(
                json.dumps(town_contract, indent=2, ensure_ascii=False) + '\n',
                encoding='utf-8',
            )
        # The map moves to acts/<id>/town/map.md.
        if town.get('map'):
            (town_dir / 'map.md').write_text(
                '\n'.join(town['map']) + '\n', encoding='utf-8'
            )
        # The pack-level contract.
        pack_contract = _preserve_unknown(pack / 'world.json', {
            'name': pack.name,
            'title': w.get('title', pack.name),
            'description': w.get('description', ''),
            'creed': _creed_from(w),
            'phases': w.get('phases', {}),
            'surface': w.get('surface', 'combat'),
            'voices': w.get('voices', {}),
            'bonds': w.get('bonds', {}),
            'bond_draw': w.get('bond_draw', ''),
            'forge_texture': w.get('forge_texture', ''),
        })
        tmp.write_text(json.dumps(pack_contract, indent=2,
                                  ensure_ascii=False) + '\n', encoding='utf-8')
        tmp.replace(pack / 'world.json')
    else:
        # Flat shape: a single world.json with the legacy keys.
        legacy = _preserve_unknown(pack / 'world.json', {
            'name': pack.name,
            'title': w.get('title', pack.name),
            'description': w.get('description', ''),
            'creed': _creed_from(w),
            'phases': w.get('phases', {}),
            'surface': w.get('surface', 'combat'),
            'voices': w.get('voices', {}),
            'bonds': w.get('bonds', {}),
            'bond_draw': w.get('bond_draw', ''),
            'forge_texture': w.get('forge_texture', ''),
            'speakers': w.get('speakers', {}),
            'town': w.get('town', {}),
        })
        tmp.write_text(json.dumps(legacy, indent=2,
                                  ensure_ascii=False) + '\n', encoding='utf-8')
        tmp.replace(pack / 'world.json')


def build_map(segments: list) -> list[str]:
    rows = []
    for row_parts in segments:
        row = ''.join(ch * n for ch, n in row_parts)
        rows.append(row)
    widths = {len(r) for r in rows}
    if len(widths) != 1:
        raise SystemExit(f'segment rows are not rectangular: {sorted(widths)}')
    return rows


def cmd_validate(args) -> int:
    from .cli import pack_root
    pack_arg = Path(args.pack)
    if pack_arg.is_absolute():
        pack = pack_arg
    else:
        # Accept a bare name ("sample-world"), a worlds-relative path
        # ("worlds/foo"), or an absolute path. Matches the resolution
        # the other verbs (handbok, doctor, export) use.
        if (pack_arg / 'world.json').exists():
            pack = pack_arg
        elif (pack_root() / 'worlds' / pack_arg / 'world.json').exists():
            pack = pack_root() / 'worlds' / pack_arg
        else:
            print(
                f'pack not found: {pack_arg} '
                f'(looked at {pack_arg} and {pack_root() / "worlds" / pack_arg})'
            )
            return 1
    w = load_pack(pack)
    errors = validate(w, pack_dir=pack)
    if errors:
        for e in errors:
            print(f'FAIL: {e}')
        return 1
    print(f'ok: {pack} - geometry, reachability, voices all pass')
    return 0


def cmd_build(args) -> int:
    pack = Path(args.pack)
    w = load_pack(pack)
    spec = json.loads(Path(args.segments).read_text(encoding='utf-8'))
    w['town']['map'] = build_map(spec['rows'])
    errors = validate(w, pack_dir=pack)
    if errors and not args.force:
        for e in errors:
            print(f'FAIL: {e}')
        return 1
    write_pack(pack, w)
    print(f"built: {len(w['town']['map'])} x {len(w['town']['map'][0])} -> {pack / 'world.json'}")
    for e in errors:
        print(f'WARN: {e}')
    return 0


def cmd_verify(args) -> int:
    ok, errors = verify_live(args.url)
    if not ok:
        for e in errors:
            print(f'FAIL: {e}')
        return 1
    print(f'ok: {args.url} - the deployed world passes validation')
    return 0


def verify_live(url: str) -> tuple[bool, list[str]]:
    """Validate a live deployment's served /api/world payload.

    Used by both the maplab CLI ('verify') and the builder web UI
    ('/api/builder/verify'). Returns (ok, errors).

    Note: /api/world serves phases, speakers, and town geometry; pack-level
    voices are omitted from offline validation during live verification as
    they are internal prompt templates.
    """
    with urllib.request.urlopen(f'{url.rstrip("/")}/api/world', timeout=15) as r:
        served = json.loads(r.read().decode('utf-8'))
    town_keys = ('tile', 'map', 'legend', 'pois', 'watch', 'sanctuary_tiles',
                 'water_by_phase', 'flood_tiles', 'hero_start')
    w = {
        'phases': served['phases'],
        'speakers': {
            s['key']: {'name': s['name'], 'at': s['at'], 'near': s['near'],
                       'seeds': s.get('seeds', {})}
            for s in served['speakers']
        },
        'town': {k: served[k] for k in town_keys if k in served},
    }
    errors = validate(w)
    return (not errors), errors


def main(argv=None) -> int:
    default_pack = f'worlds/{_default_world_name()}'
    ap = argparse.ArgumentParser(prog='maplab', description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)

    v = sub.add_parser('validate', help='validate a world pack offline')
    v.add_argument('--pack', default=default_pack)
    v.set_defaults(fn=cmd_validate)

    b = sub.add_parser('build', help='rebuild the map from segment rows')
    b.add_argument('--segments', required=True)
    b.add_argument('--pack', default=default_pack)
    b.add_argument('--force', action='store_true', help='write even if validation fails')
    b.set_defaults(fn=cmd_build)

    r = sub.add_parser('verify', help='validate a live deployment')
    r.add_argument('--url', required=True)
    r.set_defaults(fn=cmd_verify)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == '__main__':
    sys.exit(main())
