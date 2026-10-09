"""Story status (vefr #339): an optional `status: draft | approved` on the
places a pack keeps words, and the `vefr check --release` gate.

The four acceptance claims, one test each:

1. a pack with one draft book beside a book without the key validates
   clean, and the gate lists exactly the first one;
2. the gate on a pack with no drafts prints one short line and exits 0;
3. `--strict` prints the same list and exits non-zero when a draft
   exists;
4. a `status` written as anything else is a validation error naming the
   file.

Plus the promises around them: the key is optional and defaults to
`approved`, all five word surfaces carry it, and no player-facing file
is touched. No model call anywhere.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import maplab, story_status
from vefr.library import parse_book

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "make_story_status_pack", ROOT / "tests/fixtures/make_story_status_pack.py")
_mk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mk)

CLI = ("import sys; from vefr.cli import vefr_main; "
       "sys.argv = ['vefr'] + sys.argv[1:]; sys.exit(vefr_main())")


def vefr(*args):
    """The real `vefr` front door in a subprocess: (returncode, stdout+stderr)."""
    proc = subprocess.run([sys.executable, "-c", CLI, *map(str, args)],
                          capture_output=True, text=True, cwd=ROOT)
    return proc.returncode, proc.stdout + proc.stderr


def _good(tmp_path) -> Path:
    return _mk.build(tmp_path)


def _drafts(tmp_path) -> Path:
    return _mk.build(tmp_path, drafts=True)


def _errors(pack: Path) -> list[str]:
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


# --- 1. one draft beside no key: clean validation, exactly one listed --------

def test_one_draft_book_is_listed_and_the_pack_still_validates(tmp_path):
    pack = _good(tmp_path)
    assert story_status.drafts(pack) == []
    (pack / 'library' / f"{_mk.DRAFT_BOOK[0]}.md").write_text(
        _mk.DRAFT_BOOK[1], encoding='utf-8')
    assert _errors(pack) == [], "a draft word is not a validation error"
    rc, out = vefr('check', '--pack', str(pack), '--release')
    assert rc == 0, out
    assert out.count(' is a draft') == 1
    assert "library/a-draft-book.md:3" in out
    # The book that carries no key at all, and the one that says
    # `approved`, are not drafts and are not listed.
    assert 'a-shelf-book' not in out and 'an-approved-book' not in out


def test_every_word_surface_carries_a_status(tmp_path):
    """All five surfaces, and the two ways a pack names a voice file."""
    listed = {(d.surface, d.file) for d in story_status.drafts(_drafts(tmp_path))}
    assert listed == {
        ('book', 'library/a-draft-book.md'),      # front matter
        ('voice', 'world.json'),                  # voices.<id>
        ('speaker', 'acts/act-1/world.json'),      # speakers.<id>
        ('rule', 'world.json'),                   # a say rule
        ('sticker', 'world.json'),                 # album sticker name
        ('item', 'world.json'),                    # item name
    }


# --- 2. a pack with no drafts ----------------------------------------------

def test_no_drafts_prints_one_line_and_exits_zero(tmp_path):
    pack = _good(tmp_path)
    assert _errors(pack) == []
    rc, out = vefr('check', '--pack', str(pack), '--release')
    assert rc == 0, out
    assert out.count('no drafts') == 1
    assert 'draft word(s)' not in out


def test_a_pack_that_writes_no_status_says_nothing(tmp_path):
    """The compatibility promise: an absent key means `approved`."""
    assert story_status.drafts(ROOT / 'worlds' / 'sample-world') == []
    assert story_status.errors(ROOT / 'worlds' / 'sample-world') == []
    assert parse_book('---\ntitle: X\n---\nWords.', 'x')['status'] == 'approved'


# --- 3. --strict fails on a draft, after printing the list ------------------

def test_strict_lists_every_draft_and_exits_non_zero(tmp_path):
    pack = _drafts(tmp_path)
    rc, out = vefr('check', '--pack', str(pack), '--release', '--strict')
    assert rc != 0
    # The full list is printed BEFORE the failure: a human sees what is
    # in the way, not just that something is.
    for draft in story_status.drafts(pack):
        assert f"{draft.file}:{draft.line}  {draft.label} is a draft" in out
        # The line it names is the line the `status` is written on, so
        # the file:line is something a human can open.
        here = (pack / draft.file).read_text(encoding='utf-8').splitlines()
        assert 'status' in here[draft.line - 1]


def test_release_without_strict_only_lists(tmp_path):
    rc, out = vefr('check', '--pack', str(_drafts(tmp_path)), '--release')
    assert rc == 0, out


def test_strict_on_a_clean_pack_exits_zero(tmp_path):
    rc, out = vefr('check', '--pack', str(_good(tmp_path)),
                   '--release', '--strict')
    assert rc == 0, out


# --- 4. an unknown value is refused, naming the file ------------------------

def test_an_unknown_status_is_a_validation_error_naming_the_file(tmp_path):
    pack = _mk.build_unknown(tmp_path)
    errors = _errors(pack)
    assert len(errors) == 1, errors
    assert errors[0].startswith('world.json: ')
    assert '"draft" or "approved"' in errors[0] and 'maybe' in errors[0]


def test_an_unknown_status_in_a_book_front_matter_names_the_book_file(tmp_path):
    pack = _good(tmp_path)
    (pack / 'library' / 'a-confused-book.md').write_text(
        '---\ntitle: A Confused Book\nstatus: nearly\n---\nWords.\n',
        encoding='utf-8')
    errors = _errors(pack)
    assert [e for e in errors if e.startswith('library/a-confused-book.md: ')], errors


# --- the gate is a gate, not a mode -----------------------------------------

def test_a_draft_word_plays_exactly_as_an_approved_one(tmp_path):
    """No draft mode: `status` is not read by the pack loader, so a book
    with the key and a book without it load to the same words."""
    with_key = parse_book('---\ntitle: A Note\nstatus: draft\n---\nWords.\n', 'a')
    without = parse_book('---\ntitle: A Note\n---\nWords.\n', 'a')
    assert with_key['pages'] == without['pages']
    assert with_key['title'] == without['title']
    assert with_key['status'] == 'draft' and without['status'] == 'approved'
    # `status` is a known key now, so it never rides along as `extra`.
    assert with_key['extra'] == {} and without['extra'] == {}


def test_the_gate_touches_no_player_facing_file():
    # The gate is a build-time check: nothing the player runs may know
    # the key exists (a draft word has to play exactly like any other).
    web = list((ROOT / 'web').rglob('*.js')) + list((ROOT / 'web').rglob('*.html'))
    assert not [p for p in web if 'story_status' in p.read_text(encoding='utf-8')]


@pytest.mark.parametrize('flag', ['--release', '--strict'])
def test_a_missing_pack_is_reported_not_crashed(tmp_path, flag):
    rc, out = vefr('check', '--pack', str(tmp_path / 'nowhere'), flag)
    assert rc != 0 and out.strip()