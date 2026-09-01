"""`ratatoskr ferry deploy` refuses the silent bazzite default and can
generate a deploy.toml.example via --init. The full live-deploy path
needs an SSH-reachable host and is exercised by hand against bazzite."""

import importlib

import pytest

import vefr.cli as cli


@pytest.fixture
def fresh_cli(monkeypatch):
    """Reload cli with no VEFR_DEPLOY_HOST in env so the guard triggers."""
    monkeypatch.delenv('VEFR_DEPLOY_HOST', raising=False)
    monkeypatch.delenv('VEFR_DEPLOY_IMAGE', raising=False)
    importlib.reload(cli)
    return cli


def test_deploy_refuses_silent_bazzite_default(fresh_cli, capsys):
    """A fresh checkout with no VEFR_DEPLOY_HOST must NOT ssh bazzite."""
    args = fresh_cli.argparse.Namespace(
        init=False, skip_tests=True, rebuild=False, no_health=True,
        deploy_host=fresh_cli.DEFAULT_DEPLOY_HOST,  # 'bazzite' with env unset
        url=fresh_cli.DEFAULT_URL,
    )
    rc = fresh_cli.cmd_deploy(args)
    assert rc == 2
    out = capsys.readouterr().out
    assert 'VEFR_DEPLOY_HOST' in out
    assert 'ferry deploy --init' in out


def test_deploy_runs_when_host_declared(fresh_cli, monkeypatch):
    """Once VEFR_DEPLOY_HOST is set, the guard passes and we reach the
    rsync step. We mock sh() to short-circuit before touching SSH."""
    calls = []
    def fake_sh(cmd, **kwargs):
        calls.append(cmd)
        # Pre-flight skipped; rsync succeeds; no rebuild; restart succeeds;
        # volume creates succeed; --no-health returns early.
        return type('R', (), {'returncode': 0})()
    monkeypatch.setattr(fresh_cli, 'sh', fake_sh)
    args = fresh_cli.argparse.Namespace(
        init=False, skip_tests=True, rebuild=False, no_health=True,
        deploy_host='my-stack', url='http://my-stack:8820',
    )
    rc = fresh_cli.cmd_deploy(args)
    assert rc == 0
    # rsync, restart, two volume checks - the guard let us through.
    ssh_cmds = [c for c in calls if c and c[0] == 'ssh']
    assert any('restart vefr' in ' '.join(c) for c in ssh_cmds)


def test_deploy_init_writes_toml_example(fresh_cli, tmp_path, monkeypatch, capsys):
    """--init writes deploy.toml.example and prints the next-step hints."""
    monkeypatch.setattr(fresh_cli, 'need_repo', lambda: tmp_path)
    args = fresh_cli.argparse.Namespace(
        init=True, skip_tests=False, rebuild=False, no_health=False,
        deploy_host='bazzite', url='http://bazzite:8820',
    )
    rc = fresh_cli.cmd_deploy(args)
    assert rc == 0
    target = tmp_path / 'deploy.toml.example'
    assert target.exists()
    text = target.read_text(encoding='utf-8')
    assert 'host' in text
    assert 'image' in text
    out = capsys.readouterr().out
    assert 'wrote' in out
    assert 'next:' in out


def test_deploy_init_refuses_to_overwrite(fresh_cli, tmp_path, monkeypatch, capsys):
    """If deploy.toml.example already exists, --init errors out cleanly."""
    monkeypatch.setattr(fresh_cli, 'need_repo', lambda: tmp_path)
    (tmp_path / 'deploy.toml.example').write_text('existing content')
    args = fresh_cli.argparse.Namespace(
        init=True, skip_tests=False, rebuild=False, no_health=False,
        deploy_host='bazzite', url='http://bazzite:8820',
    )
    rc = fresh_cli.cmd_deploy(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert 'already exists' in out
