"""norns chat - the interview never produces an invalid pack.

The model is monkeypatched out entirely: these tests prove the
deterministic scaffolding (rename, write, validate) holds regardless
of what prose comes back, since that's the part the safety promise
depends on.
"""

import json
import shutil
from pathlib import Path

import pytest

from vefr import chat, maplab

SCAFFOLD = Path(__file__).resolve().parents[1] / 'worlds' / 'sample-world'


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(chat, 'draft', lambda prompt, system=None: 'a drafted line')
    monkeypatch.setattr(
        chat,
        'draft_theme',
        lambda mood: {'bg': '#101010', 'hero_color': '#eeeeee', 'deco_color': '#c9ad6b'},
    )


def _answers(*replies):
    it = iter(replies)

    def _input(_prompt):
        return next(it, '')

    return _input


def test_interview_produces_a_valid_pack(tmp_path, monkeypatch):
    dest = tmp_path / 'my-world'
    monkeypatch.setattr(
        'builtins.input',
        _answers(
            'Emberholt',            # title
            'A quiet town keeps a secret.',  # premise
            'a wanderer',           # protagonist
            'candlelit and warm',   # theme mood
            'day, night',           # rename phases
            'sleepy',               # day tone hint
            'restless',             # night tone hint
            'gifted, kept, spare',  # rename bonds
            'warm',                 # gifted flavor
            'heavy',                # kept flavor
            'plain',                # spare flavor
            '',                     # map mood (blank keeps the scaffold map)
            '',                     # speaker count (blank = 1)
            'The Keeper',           # speaker name (keep default)
            'quiet and kind',       # speaker personality
        ),
    )
    rc = chat.run_interview(dest, SCAFFOLD)
    assert rc == 0

    w = maplab.load_pack(dest)
    assert w['title'] == 'Emberholt'
    assert set(w['phases']) == {'day', 'night'}
    assert set(w['bonds']) == {'gifted', 'kept', 'spare'}
    assert (dest / 'logbok.md').exists()
    errors = maplab.validate(w, pack_dir=dest)
    assert errors == []


def test_blank_answers_keep_the_scaffold_valid(tmp_path, monkeypatch):
    dest = tmp_path / 'plain-world'
    monkeypatch.setattr('builtins.input', _answers())  # every answer blank
    rc = chat.run_interview(dest, SCAFFOLD)
    assert rc == 0
    w = maplab.load_pack(dest)
    errors = maplab.validate(w, pack_dir=dest)
    assert errors == []


def test_refuses_to_overwrite_an_existing_world(tmp_path, monkeypatch):
    dest = tmp_path / 'taken'
    dest.mkdir()
    monkeypatch.setattr('builtins.input', _answers())
    rc = chat.run_interview(dest, SCAFFOLD)
    assert rc == 1


def test_mismatched_rename_count_keeps_originals(tmp_path, monkeypatch):
    dest = tmp_path / 'mismatch-world'
    monkeypatch.setattr(
        'builtins.input',
        _answers(
            '', '', '', '',   # title/premise/protagonist/theme blank
            'only-one-name',  # wrong count for 2 phases -> ignored
        ),
    )
    rc = chat.run_interview(dest, SCAFFOLD)
    assert rc == 0
    w = maplab.load_pack(dest)
    assert set(w['phases']) == {'dusk', 'dawn'}


def test_theme_updates_colors_but_never_map_chars(tmp_path, monkeypatch):
    dest = tmp_path / 'themed-world'
    # Read the scaffold as a unified shape (handles flat or acts
    # on-disk layouts). The new-shape sample-world stores town
    # metadata in acts/act-1/town/contract.json equivalent; maplab
    # synthesizes w['town'] for the validator and consumer.
    original_map = maplab.load_pack(SCAFFOLD)['town']['map']
    monkeypatch.setattr(
        'builtins.input',
        _answers('', '', '', 'candlelit and warm'),  # only the theme mood is set
    )
    rc = chat.run_interview(dest, SCAFFOLD)
    assert rc == 0
    w = maplab.load_pack(dest)
    assert w['town']['bg'] == '#101010'
    assert w['town']['hero_color'] == '#eeeeee'
    assert w['town']['map'] == original_map  # geometry untouched
    for entry in w['town']['legend'].values():
        if 'deco' in entry:
            assert entry['deco_color'] == '#c9ad6b'


def test_theme_draft_failure_keeps_scaffold_colors(tmp_path, monkeypatch):
    dest = tmp_path / 'failed-theme-world'
    monkeypatch.setattr(chat, 'draft_theme', lambda mood: None)
    monkeypatch.setattr('builtins.input', _answers('', '', '', 'a mood'))
    rc = chat.run_interview(dest, SCAFFOLD)
    assert rc == 0
    w = maplab.load_pack(dest)
    assert w['town']['bg'] == '#131311'  # the scaffold's own default


def test_slugify_handles_spaces_and_punctuation():
    assert chat.slugify("Rylee's World!") == 'rylee-s-world'
    assert chat.slugify('   ') == 'my-world'


def test_write_pack_is_atomic(tmp_path):
    dest = tmp_path / 'pack'
    dest.mkdir()
    w = maplab.load_pack(SCAFFOLD)
    maplab.write_pack(dest, w)
    assert not (dest / 'world.json.tmp').exists()
    assert json.loads((dest / 'world.json').read_text(encoding='utf-8'))['title'] == w['title']


# ---- v2: the interview grows the map and the town's people ----------

def _runlen(row: str) -> list:
    """Encode one map row the way build_map reads it."""
    parts = []
    for ch in row:
        if parts and parts[-1][0] == ch:
            parts[-1][1] += 1
        else:
            parts.append([ch, 1])
    return parts


def test_propose_map_accepts_a_valid_proposal(tmp_path, monkeypatch):
    from vefr import generator

    w = maplab.load_pack(SCAFFOLD)
    # The model echoes the scaffold's own map back as run-length rows:
    # the one proposal that must always validate.
    monkeypatch.setattr(
        generator, '_completion',
        lambda payload: json.dumps({'rows': [_runlen(r) for r in w['town']['map']]}),
    )
    rows = chat.propose_map('a quiet town', 'tight lanes', w, tmp_path)
    assert rows == w['town']['map'], 'the echoed map must round-trip'


def test_propose_map_rejects_a_wrong_width(tmp_path, monkeypatch):
    from vefr import generator

    w = maplab.load_pack(SCAFFOLD)
    # One tile too few in the first row - the gate must refuse it.
    short = [r[:-1] for r in w['town']['map']]
    monkeypatch.setattr(
        generator, '_completion',
        lambda payload: json.dumps({'rows': [_runlen(r) for r in short]}),
    )
    assert chat.propose_map('a story', 'a mood', w, tmp_path) is None


def test_propose_map_never_returns_an_invalid_map(tmp_path, monkeypatch):
    from vefr import generator

    w = maplab.load_pack(SCAFFOLD)
    # Wall the hero in on every side: rectangular, correct width,
    # legend chars - but the hero can never move. The gate must refuse.
    m = [list(r) for r in w['town']['map']]
    hx, hy = w['town']['hero_start']
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        m[hy + dy][hx + dx] = '#'
    bricked = [''.join(r) for r in m]
    monkeypatch.setattr(
        generator, '_completion',
        lambda payload: json.dumps({'rows': [_runlen(r) for r in bricked]}),
    )
    assert chat.propose_map('a story', 'a mood', w, tmp_path) is None


def test_add_speaker_lands_on_walkable_reachable_ground(tmp_path):
    dest = tmp_path / 'pack'
    shutil.copytree(SCAFFOLD, dest)
    w = maplab.load_pack(dest)
    before = {tuple(s['at']) for s in w['speakers'].values()}

    assert chat._add_speaker(w, dest, 'the ferryman', 'a bright ferry-hand') is True
    added = [s for s in w['speakers'].values() if s['name'] == 'the ferryman']
    assert len(added) == 1
    at = tuple(added[0]['at'])
    assert at not in before, 'the new speaker must not stand on anyone'
    assert maplab.walkable(w, *at), 'the new speaker must stand on walkable ground'
    assert at in maplab.reach(w, tuple(w['town']['hero_start'])), (
        'the new speaker must be reachable from the hero start'
    )
    assert set(added[0]['seeds']) == set(w['phases']), 'seeds cover every phase'
    assert (dest / 'voices' / (added[0]['voice_file'].split('/')[-1])).exists()
    # And the whole pack, new voice included, still validates.
    errors = maplab.validate(w, pack_dir=dest)
    assert errors == [], errors


def test_add_speaker_fails_honestly_when_the_town_is_full(tmp_path, monkeypatch):
    dest = tmp_path / 'pack'
    shutil.copytree(SCAFFOLD, dest)
    w = maplab.load_pack(dest)
    # No free tile anywhere: the town has no room, and the function
    # says so without touching the pack.
    before = {k: dict(v) for k, v in w['speakers'].items()}
    monkeypatch.setattr(chat, '_pick_tile', lambda w: None)
    assert chat._add_speaker(w, dest, 'Two', 'x') is False
    assert set(w['speakers']) == set(before), 'no speaker may be added'
    assert list(w['speakers'].values())[0]['name'] == 'The Keeper'


def test_interview_grows_the_map_when_asked(tmp_path, monkeypatch):
    dest = tmp_path / 'grown-world'
    w0 = maplab.load_pack(SCAFFOLD)
    # A tiny, still-valid change: one ground tile becomes path.
    rows = list(w0['town']['map'])
    for y, row in enumerate(rows):
        x = row.find('.')
        if x > -1:
            rows[y] = row[:x] + 'p' + row[x + 1:]
            break
    monkeypatch.setattr(chat, 'propose_map', lambda story, mood, w, d: rows)
    monkeypatch.setattr(
        'builtins.input',
        _answers(
            '', '', '',               # title/premise/protagonist blank
            '',                       # theme mood blank
            '',                       # phase rename blank
            '', '',                   # phase tone hints blank
            '',                       # bond rename blank
            '', '', '',               # bond flavors blank
            'tight lanes',            # map mood - non-blank triggers the grow
            '',                       # speaker count
            '', '',                   # speaker name/personality (defaults)
        ),
    )
    rc = chat.run_interview(dest, SCAFFOLD)
    assert rc == 0
    w = maplab.load_pack(dest)
    assert w['town']['map'] == rows, 'the interview wrote the proposed map'
    assert maplab.validate(w, pack_dir=dest) == []


def test_interview_blank_map_mood_keeps_the_scaffold_map(tmp_path, monkeypatch):
    dest = tmp_path / 'kept-world'
    original = maplab.load_pack(SCAFFOLD)['town']['map']
    monkeypatch.setattr('builtins.input', _answers())  # all blank
    rc = chat.run_interview(dest, SCAFFOLD)
    assert rc == 0
    assert maplab.load_pack(dest)['town']['map'] == original
