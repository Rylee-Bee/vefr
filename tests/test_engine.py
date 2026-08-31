"""Engine tests - run for ANY world pack, no story required.

These prove the bones alone: loader, validator, maplab, and the
sample world that ships with the framework.
"""

import copy

from norn import maplab
from norn.paths import pack_dir
from norn.world import load_world


def test_sample_world_validates():
    errors = maplab.validate(load_world(), pack_dir=pack_dir())
    assert errors == []


def test_maplab_flags_broken_maps():
    w = copy.deepcopy(load_world())
    town = w['town']
    solid_xy = next(
        (x, y)
        for y, row in enumerate(town['map'])
        for x, ch in enumerate(row)
        if town['legend'].get(ch, {}).get('solid') is True
    )
    x, y = solid_xy
    town['willow_start'] = [x, y]              # a known-solid tile
    town['map'][0] = town['map'][0][:-1] + 'Q'  # an unknown char
    errors = maplab.validate(w)
    assert any('not walkable' in e for e in errors)
    assert any('missing from legend' in e for e in errors)


def test_bond_schema_follows_the_pack():
    from norn.forge import build_payload
    from norn.world import load_world

    p = build_payload()
    assert p['format']['properties']['bond']['enum'] == list(
        load_world()['bonds'].keys()
    )
    assert 'rarity is the point' in p['prompt']


def test_seeds_cover_every_phase():
    from norn.world import load_world

    w = load_world()
    for key, spec in w['speakers'].items():
        assert set(spec['seeds'].keys()) == set(w['phases'].keys()), key
