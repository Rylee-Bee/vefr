"""Star / remove / undo - the player-driven journal and vault control.

The journal and the vault both grew a star button, a remove button,
and a 60-second undo window this session. These tests prove the
server-side invariants: refuse-removal-of-last-of-kind, the single-
slot undo stash, and the star-file append.
"""

import json
import time

import pytest

from norn import forge, journal, starred


# ---- journal.remove + journal.undo ----

@pytest.fixture
def tmp_journal(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, 'JOURNAL', tmp_path / 'journal.json')
    monkeypatch.setattr(journal, '_LAST_REMOVED', None)
    monkeypatch.setattr(journal, '_LAST_REMOVED_AT', None)


def _seed(entries):
    """Write a journal file directly so tests don't depend on the engine."""
    journal.JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    journal.JOURNAL.write_text(json.dumps(entries), encoding='utf-8')


def test_remove_drops_the_entry(tmp_journal):
    _seed([{'at': 'a', 'kind': 'rumor', 'whisper': 'one'},
           {'at': 'b', 'kind': 'rumor', 'whisper': 'two'}])
    removed = journal.remove(0)
    assert removed['whisper'] == 'one'
    assert [e['whisper'] for e in journal.list_entries()] == ['two']


def test_remove_refuses_last_of_kind(tmp_journal):
    _seed([{'at': 'a', 'kind': 'rumor', 'whisper': 'one'},
           {'at': 'b', 'kind': 'npc_line', 'line': 'hello'}])
    with pytest.raises(ValueError, match='last entry of kind'):
        journal.remove(0)
    # The bell_letter-style 'no entries of kind X' path:
    _seed([{'at': 'a', 'kind': 'bell_letter', 'letter': 'For you.'}])
    with pytest.raises(ValueError):
        journal.remove(0)


def test_remove_out_of_range_returns_none(tmp_journal):
    _seed([{'at': 'a', 'kind': 'rumor', 'whisper': 'one'}])
    assert journal.remove(5) is None
    assert journal.remove(-1) is None


def test_undo_restores_within_window(tmp_journal):
    _seed([{'at': 'a', 'kind': 'rumor', 'whisper': 'one'},
           {'at': 'b', 'kind': 'rumor', 'whisper': 'two'}])
    journal.remove(1)
    assert len(journal.list_entries()) == 1
    restored = journal.undo()
    assert restored is not None
    assert restored['whisper'] == 'two'
    assert [e['whisper'] for e in journal.list_entries()] == ['one', 'two']


def test_undo_returns_none_outside_window(tmp_journal):
    _seed([{'at': 'a', 'kind': 'rumor', 'whisper': 'one'},
           {'at': 'b', 'kind': 'rumor', 'whisper': 'two'}])
    journal.remove(1)
    # Force the timestamp to be older than UNDO_WINDOW_S
    journal._LAST_REMOVED_AT = time.monotonic() - journal.UNDO_WINDOW_S - 1
    assert journal.undo() is None


def test_undo_with_no_prior_remove_returns_none(tmp_journal):
    assert journal.undo() is None


def test_second_remove_overwrites_first_stash(tmp_journal):
    """A second remove() before the undo window expires overwrites
    the previous stash - undo is single-slot by design. The second
    remove still uses the *current* index, which shifts each time."""
    _seed([{'at': 'a', 'kind': 'rumor', 'whisper': 'one'},
           {'at': 'b', 'kind': 'rumor', 'whisper': 'two'},
           {'at': 'c', 'kind': 'rumor', 'whisper': 'three'}])
    journal.remove(0)  # stashes 'one' at index 0; journal = [two, three]
    journal.remove(0)  # stashes 'two' at index 0; journal = [three]
    restored = journal.undo()
    assert restored['whisper'] == 'two'
    # Undo restores 'two' at its *original* index (0), not at the
    # current end - so the post-undo journal is [two, three].
    assert [e['whisper'] for e in journal.list_entries()] == ['two', 'three']


# ---- starred.star ----

@pytest.fixture
def tmp_pack(tmp_path, monkeypatch):
    # pack_dir() uses app_home()/worlds/<resolved>, so point both at tmp.
    monkeypatch.setattr(journal, 'JOURNAL', tmp_path / 'journal.json')
    pack = tmp_path / 'worlds' / 'private-canon'
    pack.mkdir(parents=True)
    (pack / 'world.json').write_text('{"title": "t", "phases": {}, "voices": {}, "bonds": {}, "town": {}}')
    from norn.paths import pack_dir
    monkeypatch.setattr('norn.starred.pack_dir', lambda *a, **k: pack)
    return pack


def test_star_appends_to_section(tmp_pack):
    result = starred.star({
        'kind': 'rumor', 'phase': 'awed',
        'speaker': 'the ferryman',
        'whisper': 'A shadow walked past the bell tower last night.',
        'at': '2026-08-31T03:24:59',
    })
    assert result['starred'] is True
    assert result['section'] == 'awed'
    text = (tmp_pack / 'starred-whispers.md').read_text(encoding='utf-8')
    assert '## awed' in text
    assert 'the ferryman' in text
    assert 'shadow walked past the bell tower' in text
    assert 'kept 2026-08-31T03:24:59' in text


def test_star_groups_by_phase(tmp_pack):
    starred.star({'kind': 'rumor', 'phase': 'whispers', 'whisper': 'one', 'speaker': 'A'})
    starred.star({'kind': 'rumor', 'phase': 'whispers', 'whisper': 'two', 'speaker': 'B'})
    starred.star({'kind': 'rumor', 'phase': 'awed', 'whisper': 'three', 'speaker': 'C'})
    text = (tmp_pack / 'starred-whispers.md').read_text(encoding='utf-8')
    # Each phase gets exactly one heading
    assert text.count('## whispers') == 1
    assert text.count('## awed') == 1
    assert 'one' in text and 'two' in text and 'three' in text


def test_star_routes_item_forged_to_kept_items(tmp_pack):
    starred.star({
        'kind': 'item_forged',
        'name': 'Bell-Key',
        'lore': 'Forged from bell-metal of the old church.',
    })
    assert '## kept-items' in (tmp_pack / 'starred-whispers.md').read_text(encoding='utf-8')


def test_star_routes_bell_letter_to_awed(tmp_pack):
    starred.star({
        'kind': 'bell_letter',
        'letter': 'For you.\nMend the hem.',
    })
    text = (tmp_pack / 'starred-whispers.md').read_text(encoding='utf-8')
    assert '## awed' in text
    assert 'Mend' in text


def test_star_empty_entry_is_rejected(tmp_pack):
    result = starred.star({'kind': 'rumor', 'phase': 'whispers', 'whisper': ''})
    assert result['starred'] is False
    assert not (tmp_pack / 'starred-whispers.md').exists()


def test_list_starred_round_trip(tmp_pack):
    starred.star({'kind': 'rumor', 'phase': 'whispers', 'whisper': 'alpha', 'speaker': 'X'})
    starred.star({'kind': 'rumor', 'phase': 'awed', 'whisper': 'beta', 'speaker': 'Y'})
    starred_entries = starred.list_starred()
    assert len(starred_entries) == 2
    sections = {s['section'] for s in starred_entries}
    assert sections == {'whispers', 'awed'}


# ---- vault parity ----

@pytest.fixture
def tmp_vault(tmp_path, monkeypatch):
    monkeypatch.setattr(forge, 'VAULT', tmp_path / 'vault.json')
    monkeypatch.setattr(forge, '_LAST_REMOVED', None)
    monkeypatch.setattr(forge, '_LAST_REMOVED_AT', None)


def test_vault_remove_and_undo(tmp_vault):
    forge.VAULT.write_text(json.dumps([{'name': 'a'}, {'name': 'b'}]), encoding='utf-8')
    removed = forge.remove(0)
    assert removed == {'name': 'a'}
    assert forge.list_vault() == [{'name': 'b'}]
    restored = forge.undo()
    assert restored == {'name': 'a'}
    assert forge.list_vault() == [{'name': 'a'}, {'name': 'b'}]


def test_vault_remove_out_of_range(tmp_vault):
    forge.VAULT.write_text(json.dumps([{'name': 'a'}]), encoding='utf-8')
    assert forge.remove(5) is None


def test_vault_undo_outside_window(tmp_vault):
    forge.VAULT.write_text(json.dumps([{'name': 'a'}]), encoding='utf-8')
    forge.remove(0)
    forge._LAST_REMOVED_AT = time.monotonic() - forge.UNDO_WINDOW_S - 1
    assert forge.undo() is None