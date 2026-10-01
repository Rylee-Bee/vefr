"""`vefr find` - the local, read-only search over pack + journal.

Runs against the tracked sample pack (worlds/sample-world) with the
journal redirected into tmp_path, so nothing here reads or writes the
real data/. The two failure shapes stay distinct: a refused pack is
exit 1 with a named message, a search with no hits is exit 0 with
UNKNOWN on its own line.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from vefr import journal
from vefr.cli import EXIT_ERROR, EXIT_OK, cmd_find
from vefr.find import EXCERPT_MAX

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'worlds' / 'sample-world'


@pytest.fixture(autouse=True)
def _isolated_journal(tmp_path, monkeypatch):
    """The journal lives in tmp_path (absent = empty unless a test
    writes it); the legacy world keeps world_scoped() from renaming
    the file under a different world name."""
    monkeypatch.setattr(journal, 'JOURNAL', tmp_path / 'journal.json')
    monkeypatch.setenv('VEFR_WORLD', 'sample-world')


def _find(query, pack=PACK):
    return cmd_find(SimpleNamespace(query=query, pack=str(pack)))


def _parts(hit):
    """One printed hit -> (path:line, source, excerpt)."""
    loc, rest = hit.split(' [', 1)
    source, excerpt = rest.split('] ', 1)
    return loc, source, excerpt


def test_present_term_hits_the_right_line(capsys):
    rc = _find('keeper')
    out = capsys.readouterr().out

    want_line = next(
        n for n, ln in enumerate(
            (PACK / 'logbok.md').read_text(encoding='utf-8').splitlines(), 1)
        if 'keeper' in ln.lower())
    hit = next(ln for ln in out.splitlines() if f'logbok.md:{want_line}' in ln)
    loc, source, excerpt = _parts(hit)
    assert loc.endswith(f'logbok.md:{want_line}')
    assert source == 'logbok'
    assert excerpt.strip()
    assert len(excerpt.strip()) <= EXCERPT_MAX
    assert rc == EXIT_OK


def test_every_excerpt_is_capped(capsys):
    rc = _find('keeper')
    out = capsys.readouterr().out
    assert rc == EXIT_OK
    for ln in out.splitlines():
        _loc, _source, excerpt = _parts(ln)
        assert len(excerpt) <= EXCERPT_MAX


def test_absent_term_prints_unknown_and_exits_zero(capsys):
    rc = _find('zzzznotinthepack')
    out = capsys.readouterr().out
    assert rc == EXIT_OK
    assert out.strip() == 'UNKNOWN'


def test_results_are_ordered_deterministically(capsys):
    _find('keeper')
    first = [ln for ln in capsys.readouterr().out.splitlines()]
    _find('keeper')
    second = [ln for ln in capsys.readouterr().out.splitlines()]

    assert first == second and first
    keyed = []
    for ln in first:
        loc, _source, _excerpt = _parts(ln)
        path, _, line = loc.rpartition(':')
        keyed.append((path, int(line)))
    assert keyed == sorted(keyed)


def test_missing_pack_is_refused_distinctly(capsys):
    missing = ROOT / 'worlds' / 'no-such-pack'
    rc = _find('keeper', pack=missing)
    out = capsys.readouterr().out
    assert rc == EXIT_ERROR
    assert 'pack not found' in out
    assert 'UNKNOWN' not in out  # a missing pack is not a zero-hit search


def test_journal_is_searched(capsys, tmp_path):
    sentinel = 'quuxsentinel'
    (tmp_path / 'journal.json').write_text(
        json.dumps([{'at': '2026-01-01T00:00:00+00:00', 'kind': 'rumor',
                     'whisper': f'the walls heard {sentinel} pass'}]),
        encoding='utf-8')

    rc = _find(sentinel)
    out = capsys.readouterr().out
    assert rc == EXIT_OK
    hit = next(ln for ln in out.splitlines() if _parts(ln)[1] == 'journal')
    loc, _source, excerpt = _parts(hit)
    assert loc.endswith('journal.json:1')  # entry ordinal, 1-based
    assert sentinel in excerpt


def test_missing_journal_is_empty_not_a_crash(capsys, tmp_path):
    """No journal file at all: entries() reads [] and the search runs
    on - the pack alone answers, and an absent term still UNKNOWNs."""
    assert not (tmp_path / 'journal.json').exists()

    rc = _find('keeper')
    out = capsys.readouterr().out
    assert rc == EXIT_OK
    assert not any(_parts(ln)[1] == 'journal' for ln in out.splitlines())
    assert out.strip() != 'UNKNOWN'

    rc = _find('zzzznotinthepack')
    out = capsys.readouterr().out
    assert rc == EXIT_OK
    assert out.strip() == 'UNKNOWN'


def test_a_symlink_that_leaves_the_pack_is_never_indexed(tmp_path, capsys):
    """A downloaded pack must not make `vefr find` print a file from outside it."""
    import shutil

    pack = tmp_path / 'pack'
    shutil.copytree(PACK, pack)
    secret = tmp_path / 'private-notes.md'
    secret.write_text('the zebra password is hunter2\n', encoding='utf-8')
    (pack / 'library').mkdir(exist_ok=True)
    (pack / 'library' / 'innocent.md').symlink_to(secret)
    (pack / 'ledger.md').unlink(missing_ok=True)
    (pack / 'ledger.md').symlink_to(secret)

    rc = _find('zebra password', pack)
    out = capsys.readouterr().out
    assert rc == EXIT_OK
    assert 'hunter2' not in out
    assert 'UNKNOWN' in out
