"""old-name chat - the interview never produces an invalid pack.

The model is monkeypatched out entirely: these tests prove the
deterministic scaffolding (rename, write, validate) holds regardless
of what prose comes back, since that's the part the safety promise
depends on.
"""

import json
from pathlib import Path

import pytest

from old-name import chat, maplab

SCAFFOLD = Path(__file__).resolve().parents[1] / 'worlds' / 'sample-world'


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(chat, 'draft', lambda prompt, system=None: 'a drafted line')
    monkeypatch.setattr(
        chat,
        'draft_theme',
        lambda mood: {'bg': '#101010', 'willow_color': '#eeeeee', 'deco_color': '#c9ad6b'},
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
    assert (dest / 'bible.md').exists()
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
    original_map = json.loads((SCAFFOLD / 'world.json').read_text(encoding='utf-8'))['town']['map']
    monkeypatch.setattr(
        'builtins.input',
        _answers('', '', '', 'candlelit and warm'),  # only the theme mood is set
    )
    rc = chat.run_interview(dest, SCAFFOLD)
    assert rc == 0
    w = maplab.load_pack(dest)
    assert w['town']['bg'] == '#101010'
    assert w['town']['willow_color'] == '#eeeeee'
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
    w = json.loads((SCAFFOLD / 'world.json').read_text(encoding='utf-8'))
    maplab.write_pack(dest, w)
    assert not (dest / 'world.json.tmp').exists()
    assert json.loads((dest / 'world.json').read_text(encoding='utf-8'))['title'] == w['title']
