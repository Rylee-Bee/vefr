"""norns doctor - the session-start health check.

One command instead of the manual checklist: git sync state, the
working tree, the test gate, the current pack's geometry, and (when
VEFR_LIVE_URL is set) a running stack's /api/health. Neutral words
only - status lives in the text, never in color. Exit 1 only when
something local is broken; a remote that answers slowly is
reported, not failed.
"""

from types import SimpleNamespace

import vefr.cli as cli


def _patch(monkeypatch, tmp_path, **overrides):
    """Pin every check so doctor runs hermetically."""
    monkeypatch.setattr(
        cli, 'q1_sync', lambda: ('in-sync', 'local == remote @ abc1234'))
    monkeypatch.setattr(cli, 'q2_dirty', lambda: ('clean', '0 changes'))
    monkeypatch.setattr(cli, 'repo_root', lambda: tmp_path)
    monkeypatch.setattr(
        cli, '_pytest_summary',
        lambda repo: ('ok', 'passed tests in 0.5s'))
    monkeypatch.setattr(cli, 'load_pack', lambda pack: {'title': 't'})
    monkeypatch.setattr(cli, 'validate', lambda w, pack_dir=None: [])
    monkeypatch.delenv('VEFR_LIVE_URL', raising=False)
    for name, value in overrides.items():
        monkeypatch.setattr(cli, name, value)
    return SimpleNamespace(pack=tmp_path / 'sample-world')


def test_doctor_all_ok_reports_and_exits_zero(monkeypatch, tmp_path, capsys):
    args = _patch(monkeypatch, tmp_path)
    rc = cli.cmd_doctor(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert '4 ok, 0 failed, 1 skipped' in out
    assert 'set VEFR_LIVE_URL' in out


def test_doctor_reports_a_broken_pack_and_exits_one(monkeypatch, tmp_path,
                                                     capsys):
    args = _patch(monkeypatch, tmp_path,
                  validate=lambda w, pack_dir=None: ['row 3 walks into water'])
    rc = cli.cmd_doctor(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert '1 failed' in out
    assert 'norns validate' in out


def test_doctor_reports_failing_tests_and_exits_one(monkeypatch, tmp_path,
                                                     capsys):
    args = _patch(monkeypatch, tmp_path,
                  _pytest_summary=lambda repo: ('FAIL', '3 failed in 1.0s'))
    rc = cli.cmd_doctor(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert '3 failed' in out


def test_doctor_live_down_is_reported_not_failed(monkeypatch, tmp_path,
                                                  capsys):
    def boom(url, timeout=8):
        raise OSError('refused')

    args = _patch(monkeypatch, tmp_path, fetch=boom)
    monkeypatch.setenv('VEFR_LIVE_URL', 'http://127.0.0.1:9')
    rc = cli.cmd_doctor(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert 'DOWN' in out


def test_doctor_live_ok_when_stack_answers(monkeypatch, tmp_path, capsys):
    args = _patch(monkeypatch, tmp_path,
                  fetch=lambda url, timeout=8: {'ok': True})
    monkeypatch.setenv('VEFR_LIVE_URL', 'http://bazzite:8820')
    rc = cli.cmd_doctor(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert 'live' in out and 'ok' in out


def test_doctor_live_falls_back_to_deploy_toml(monkeypatch, tmp_path, capsys):
    """No VEFR_LIVE_URL? deploy.toml's url is the operator's declared
    live endpoint - doctor uses it instead of skipping."""
    args = _patch(monkeypatch, tmp_path)
    (tmp_path / 'deploy.toml').write_text(
        'url = "http://toml-host:8820"\n', encoding='utf-8')
    monkeypatch.setattr(cli, 'fetch',
                        lambda url, timeout=5: {'ok': True, 'purpose': 'p'})
    rc = cli.cmd_doctor(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert 'http://toml-host:8820' in out
    assert 'skip' not in out.split('live')[1].split('\n')[0]


def test_doctor_live_still_skips_without_toml(monkeypatch, tmp_path, capsys):
    args = _patch(monkeypatch, tmp_path)
    rc = cli.cmd_doctor(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert 'add url to deploy.toml' in out


def test_q3_flags_engine_pack_shadows(monkeypatch, tmp_path):
    """An engine-shipped pack in the deploy host's rw bind shadows
    the template: skipa must name it, not wave a green flag at a
    stale pack (the 2026-09-01 deploy-day find)."""
    monkeypatch.setattr(cli, 'fetch', lambda url, **k: {'ok': True, 'purpose': 'p'})
    monkeypatch.setattr(
        cli.subprocess, 'run',
        lambda *a, **k: SimpleNamespace(returncode=0, stdout='sample-world\nmy-pack\n'))
    status, answer = cli.q3_deployment('http://x:8820', 'my-stack')
    assert status == 'shadowed'
    assert 'sample-world' in answer


def test_q3_shadow_check_stays_quiet_when_clean(monkeypatch):
    monkeypatch.setattr(cli, 'fetch', lambda url, **k: {'ok': True, 'purpose': 'p'})
    monkeypatch.setattr(
        cli.subprocess, 'run',
        lambda *a, **k: SimpleNamespace(returncode=0, stdout='my-canon\n'))
    status, answer = cli.q3_deployment('http://x:8820', 'my-stack')
    assert status == 'healthy'
    assert 'no pack shadows' in answer


def test_q2_reports_reading_fonts(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, 'git_quiet', lambda *a, **k: '')
    monkeypatch.setattr(cli, 'repo_root', lambda: tmp_path)
    fonts = tmp_path / 'web' / 'fonts'
    fonts.mkdir(parents=True)
    for n in range(4):
        (fonts / f'f{n}.woff2').write_bytes(b'wOF2')
    assert 'fonts ok' in cli.q2_dirty()[1]
    for f in fonts.glob('*.woff2'):
        f.unlink()
    assert 'fonts 0/4' in cli.q2_dirty()[1]
