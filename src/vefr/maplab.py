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
import sys
import urllib.request
from pathlib import Path

from .paths import world_name as _default_world_name
from .world import VALID_FLOORS, VALID_TONES
from .world import creed_from as _creed_from

BLOCKED_FALLBACK = ['~', 'B', '#', 'T', 'M']


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
        # Pick the first region for the validator (the canary has
        # only `town`; multi-region acts will need a flag or a
        # per-region validation in a follow-on).
        region_name = next(iter(act.get('regions', {})), None)
        # The town's metadata can live in three places, in priority
        # order: the region's contract.json (new, convention-driven),
        # the act's _town_legacy (transitional), or the act's
        # inline `town` block (the very first acts-shape PR had
        # this). Read all three, the highest priority wins.
        contract: dict = {}
        if region_name:
            cp = first_act_dir / region_name / 'contract.json'
            if cp.exists():
                contract = json.loads(cp.read_text(encoding='utf-8'))
        region_legacy = act.get('_town_legacy', {}) or act.get('town', {})
        merged = {**region_legacy, **contract}
        # The map lives in acts/<id>/<region>/map.md in the new
        # shape. If it's there, parse it; otherwise fall back to
        # whatever the contract holds.
        map_lines: list[str] = []
        if region_name:
            map_path = first_act_dir / region_name / 'map.md'
            if map_path.exists():
                map_lines = [
                    ln for ln in map_path.read_text(encoding='utf-8').splitlines()
                    if ln.strip()
                ]
        if not map_lines:
            map_lines = merged.get('map', [])
        return {
            'name': pack.name,
            'title': config.get('title', act.get('title', pack.name)),
            'description': config.get('description', ''),
            'creed': _creed_from(config),
            'phases': config['phases'],
            'voices': config.get('voices', {}),
            'bonds': config.get('bonds', {}),
            'speakers': act.get('speakers', {}),
            'surface': config.get('surface', 'combat'),
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

    for s in w.get('speakers', {}).values():
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
        for fname in ('verbs', 'enemies', 'bosses', 'transitions'):
            val = act.get(fname, [])
            if not isinstance(val, list):
                errors.append(f"act '{aid}' {fname} must be a list")
            elif not all(isinstance(x, str) for x in val):
                errors.append(f"act '{aid}' {fname} must be a list of strings")

    # Cooking ruleset content (the act-1 loop): the morning is pack-
    # authored; the engine only resolves it. Orders must reference
    # real pantry ids so a served burrito can be checked
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

    return errors


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
        act_contract = {
            'id': act_id,
            'title': w.get('title', pack.name),
            'regions': ['town'],
            'speakers': w.get('speakers', {}),
            'enemies': w.get('enemies', []),
            'bosses': w.get('bosses', []),
            'transitions': w.get('transitions', []),
        }
        act_tmp = act_dir / 'world.json.tmp'
        act_tmp.write_text(json.dumps(act_contract, indent=2,
                                      ensure_ascii=False), encoding='utf-8')
        act_tmp.replace(act_dir / 'world.json')
        # The town contract (every town-metadata field except map).
        town_dir = act_dir / 'town'
        town_dir.mkdir(parents=True, exist_ok=True)
        town_contract = {k: v for k, v in town.items() if k != 'map'}
        if town_contract:
            (town_dir / 'contract.json').write_text(
                json.dumps(town_contract, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
        # The map moves to acts/<id>/town/map.md.
        if town.get('map'):
            (town_dir / 'map.md').write_text(
                '\n'.join(town['map']) + '\n', encoding='utf-8'
            )
        # The pack-level contract.
        pack_contract = {
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
        }
        tmp.write_text(json.dumps(pack_contract, indent=2,
                                  ensure_ascii=False), encoding='utf-8')
        tmp.replace(pack / 'world.json')
    else:
        # Flat shape: a single world.json with the legacy keys.
        legacy = {
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
        }
        tmp.write_text(json.dumps(legacy, indent=2,
                                  ensure_ascii=False), encoding='utf-8')
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
