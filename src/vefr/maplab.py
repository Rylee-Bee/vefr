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
        return {
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
        }
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
    # (not just the first); a broken one is named in plain words.
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
        act_contract = _preserve_unknown(act_dir / 'world.json', {
            'id': act_id,
            'title': w.get('title', pack.name),
            'regions': ['town'],
            'speakers': w.get('speakers', {}),
            'enemies': w.get('enemies', []),
            'bosses': w.get('bosses', []),
            'transitions': w.get('transitions', []),
        })
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
