"""Engine config comes from the environment - no LAN identity in source."""

import importlib

import vefr.cli as cli


def test_gitea_base_and_live_url_env_overrides(monkeypatch):
    monkeypatch.setenv('VEFR_GITEA_URL', 'https://gitea.example.com')
    monkeypatch.setenv('VEFR_LIVE_URL', 'http://stack.local:9999')
    importlib.reload(cli)
    try:
        assert cli.GITEA_BASE == 'https://gitea.example.com'
        assert cli.DEFAULT_URL == 'http://stack.local:9999'
    finally:
        monkeypatch.delenv('VEFR_GITEA_URL')
        monkeypatch.delenv('VEFR_LIVE_URL')
        importlib.reload(cli)


def test_neutral_defaults_without_env(monkeypatch):
    monkeypatch.delenv('VEFR_GITEA_URL', raising=False)
    monkeypatch.delenv('VEFR_LIVE_URL', raising=False)
    importlib.reload(cli)
    assert cli.GITEA_BASE == 'http://localhost:3000'
    assert cli.DEFAULT_URL == 'http://127.0.0.1:8820'
