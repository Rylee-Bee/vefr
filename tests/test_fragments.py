"""The offline whisper banks - per-speaker fragments.

The convention: voices/<name>.fragments.md beside a voice file
carries that speaker's speakable lines - bullet lines speak,
everything else is an author note. The loader strips the suffix,
merges banks across act regions, and never registers a fragments
file as a voice. A pack without banks keeps the honest silence
it has always had.
"""

import shutil
from pathlib import Path

from vefr import world as world_mod
from vefr.world import fragments_for_pack, load_world

SAMPLE = Path(__file__).resolve().parents[1] / 'worlds' / 'sample-world'


def test_canary_bank_is_discovered():
    w = load_world('sample-world')
    bank = w['fragments'].get('keeper') or []
    assert len(bank) >= 2
    assert all(isinstance(ln, str) and ln for ln in bank)
    # bullet lines speak; the author-note header lines do not leak in
    assert all(not ln.startswith(('#', 'The Keeper')) for ln in bank)


def test_fragments_file_is_never_registered_as_a_voice():
    """The stem trap: keeper.fragments.md must not become a voice
    named 'keeper.fragments' - the generation path would inherit it
    as a second speaker's prompt."""
    w = load_world('sample-world')
    town = w['acts'][0]['regions'].get('town', {})
    assert 'keeper.fragments' not in (town.get('voices') or {})
    assert 'keeper' in (town.get('voices') or {})


def test_banks_merge_across_act_regions(tmp_path, monkeypatch):
    """A region-level bank travels with its own voices: the same
    speaker key at the pack root and inside a region merges in file
    order, deduplicated."""
    home = tmp_path / 'vefr-home'
    (home / 'worlds').mkdir(parents=True)
    shutil.copytree(SAMPLE, home / 'worlds' / 'sample-world')
    region_voices = (home / 'worlds' / 'sample-world'
                     / 'acts' / 'act-1' / 'town' / 'voices')
    region_voices.mkdir(parents=True, exist_ok=True)
    (region_voices / 'keeper.fragments.md').write_text(
        '- The hill remembers the sound before the word.\n'
        '- The stone keeps what is brought to it.\n',
        encoding='utf-8')
    monkeypatch.setenv('VEFR_HOME', str(home))
    world_mod.load_world.cache_clear()
    try:
        bank = fragments_for_pack(home / 'worlds' / 'sample-world')['keeper']
        assert 'The stone keeps what is brought to it.' in bank
        assert bank.count('The stone keeps what is brought to it.') == 1
        assert any('before the word' in ln for ln in bank)
    finally:
        world_mod.load_world.cache_clear()


def test_absent_banks_resolve_to_nothing():
    """A pack with no fragments files yields no banks - the composer
    keeps the honest silence, exactly as before this convention."""
    home = tmp_home_without_fragments()
    bank = fragments_for_pack(home)
    assert bank == {} or all(not lines for lines in bank.values())


def tmp_home_without_fragments():
    """A copy of sample-world with the canary bank removed."""
    import tempfile
    home = Path(tempfile.mkdtemp()) / 'worlds' / 'sample-world'
    shutil.copytree(SAMPLE, home)
    (home / 'voices' / 'keeper.fragments.md').unlink()
    return home
