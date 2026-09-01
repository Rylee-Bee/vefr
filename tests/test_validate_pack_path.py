"""`norns validate --pack <name>` resolves bare names through pack_root.

Regression: the pre-flight in `ratatoskr ferry deploy` failed because
the bare name `sample-world` wasn't resolved to `worlds/sample-world/`.
The fixer added the same path resolution to `maplab.cmd_validate` that
the other verbs (handbok, doctor, export) already use.
"""

import argparse

import vefr.cli as cli
import vefr.maplab as maplab


def test_validate_resolves_bare_pack_name():
    """`norns validate --pack sample-world` from any CWD finds the pack."""
    args = argparse.Namespace(pack='sample-world')
    rc = maplab.cmd_validate(args)
    assert rc == 0


def test_validate_accepts_absolute_path(tmp_path):
    """Passing the resolved path still works (handbok/exports use this)."""
    args = argparse.Namespace(pack=str(cli.pack_root() / 'worlds' / 'sample-world'))
    rc = maplab.cmd_validate(args)
    assert rc == 0


def test_validate_reports_missing_pack(capsys):
    """A name that resolves to neither path gives a clean error, not a traceback."""
    args = argparse.Namespace(pack='definitely-not-a-pack-xyz')
    rc = maplab.cmd_validate(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert 'pack not found' in out
    assert 'definitely-not-a-pack-xyz' in out
