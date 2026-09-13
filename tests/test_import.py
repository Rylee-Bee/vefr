"""ratatoskr ferry fetch - clone or pull a story repo into worlds/<name>/.

Tests the URL resolution, the action choice (clone vs pull), the
local-vs-ssh dispatch, and the dry-run early return. The actual
git/subprocess invocations are monkeypatched - these tests prove
the decision logic, not network reachability.
"""

import subprocess

import pytest

from vefr import cli


# ---- _import_url ----

def test_import_url_shorthand():
    assert cli._import_url(
        'http://198.51.100.10:3000', 'example/sample-pack'
    ) == 'http://198.51.100.10:3000/example/sample-pack.git'


def test_import_url_shorthand_trims_trailing_slash():
    assert cli._import_url(
        'http://198.51.100.10:3000/', 'example/sample-pack'
    ) == 'http://198.51.100.10:3000/example/sample-pack.git'


def test_import_url_full_https_passthrough():
    url = 'https://gitea.example.test/example/sample-pack.git'
    assert cli._import_url('http://wrong.base', url) == url


def test_import_url_full_ssh_passthrough():
    url = 'git@github.com:foo/bar.git'
    assert cli._import_url('http://wrong.base', url) == url


def test_import_url_rejects_garbage():
    with pytest.raises(SystemExit):
        cli._import_url('http://x', 'not-a-slash-separated-name')


# ---- _import_target ----

def test_import_target_local_returns_pack_root(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, 'pack_root', lambda: tmp_path)
    host, worlds_dir = cli._import_target(_args(target='local'))
    assert host == 'local'
    assert worlds_dir == str(tmp_path / 'worlds')


def test_import_target_ssh_returns_vefr_layout():
    host, worlds_dir = cli._import_target(_args(target='ssh-host'))
    assert host == 'ssh-host'
    assert worlds_dir == '~/vefr/worlds'


# ---- cmd_import: end-to-end behavior, subprocess mocked ----

class _Args:
    def __init__(self, **kw):
        self.repo = 'example/sample-pack'
        self.name = None
        self.base = 'http://198.51.100.10:3000'
        self.target = 'local'
        self.pull = False
        self.dry_run = False
        for k, v in kw.items():
            setattr(self, k, v)


def _args(**kw):
    return _Args(**kw)


@pytest.fixture
def no_validate(monkeypatch):
    """Stub out the post-import validate step so tests can use a
    stub world.json without satisfying the full maplab contract."""
    monkeypatch.setattr(cli, 'load_pack', lambda p: {})
    monkeypatch.setattr(cli, 'validate', lambda w, pack_dir=None: [])


def test_dry_run_returns_zero_without_subprocess(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli, 'pack_root', lambda: tmp_path)
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, '', '')

    monkeypatch.setattr(cli.subprocess, 'run', fake_run)
    rc = cli.cmd_import(_args(name='new-world', dry_run=True))
    assert rc == 0
    captured = capsys.readouterr().out
    assert 'dry-run: would' in captured
    assert 'clone http://198.51.100.10:3000/example/sample-pack.git' in captured
    assert calls == [], 'dry-run must not invoke git'


def test_local_clone_invokes_git_clone(monkeypatch, tmp_path, no_validate):
    monkeypatch.setattr(cli, 'pack_root', lambda: tmp_path)
    target = tmp_path / 'worlds' / 'new-world'
    target.parent.mkdir(parents=True)
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        # Simulate the clone succeeding by creating the target dir.
        if cmd[:2] == ['git', 'clone']:
            target.mkdir()
        return subprocess.CompletedProcess(cmd, 0, '', '')

    monkeypatch.setattr(cli.subprocess, 'run', fake_run)

    rc = cli.cmd_import(_args(name='new-world'))
    assert rc == 0
    assert any(cmd[:2] == ['git', 'clone'] for cmd in calls), calls


def test_local_pull_when_world_exists(monkeypatch, tmp_path, no_validate):
    monkeypatch.setattr(cli, 'pack_root', lambda: tmp_path)
    target = tmp_path / 'worlds' / 'existing-world'
    target.mkdir(parents=True)

    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, '', '')

    monkeypatch.setattr(cli.subprocess, 'run', fake_run)

    rc = cli.cmd_import(_args(name='existing-world', pull=True))
    assert rc == 0
    assert any('pull' in cmd and '--ff-only' in cmd for cmd in calls), calls
    assert not any(cmd[:2] == ['git', 'clone'] for cmd in calls), calls


def test_local_existing_without_pull_refuses(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, 'pack_root', lambda: tmp_path)
    target = tmp_path / 'worlds' / 'existing-world'
    target.mkdir(parents=True)

    rc = cli.cmd_import(_args(name='existing-world'))
    assert rc == 1
    captured = capsys.readouterr().out
    assert 'already exists' in captured
    assert 'pass --pull' in captured


def test_ssh_target_uses_ssh_not_local_subprocess(monkeypatch, no_validate):
    calls = []

    def fake_sh(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, '', '')

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, '', '')

    monkeypatch.setattr(cli, 'sh', fake_sh)
    monkeypatch.setattr(cli.subprocess, 'run', fake_run)

    rc = cli.cmd_import(_args(name='sample-world', target='ssh-host', pull=True))
    assert rc == 0
    # First call should be ssh, never local git
    ssh_calls = [c for c in calls if c and c[0] == 'ssh']
    assert ssh_calls, calls
    assert not any(c[:2] == ['git', 'clone'] for c in calls)