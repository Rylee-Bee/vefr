"""ferry scaffold - export the active pack as a standalone git repo."""

import subprocess

from vefr import journal
from vefr.cli import cmd_scaffold


def _git(dest: str, *argv: str) -> str:
    r = subprocess.run(('git', '-C', dest) + argv, capture_output=True, text=True)
    return r.stdout.strip()


def test_scaffold_copies_pack_and_inits_git(tmp_path, monkeypatch):
    pack = tmp_path / "worlds" / "pack"
    pack.mkdir(parents=True)
    (pack / "world.json").write_text('{"title": "T"}', encoding="utf-8")
    (pack / "logbok.md").write_text("# canon", encoding="utf-8")
    voices = pack / "voices"
    voices.mkdir()
    (voices / "ferry.md").write_text("voice text", encoding="utf-8")
    # Derived + transient files must not ship.
    (pack / "world-tree.md").write_text("derived", encoding="utf-8")
    (pack / "handbok.md").write_text("derived", encoding="utf-8")
    (pack / "journal-a1b2.rewind.json").write_text("transient", encoding="utf-8")

    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    from vefr import world as world_mod

    monkeypatch.setattr(
        world_mod, "load_world",
        lambda name=None: {"title": "T", "phases": {}},
    )
    monkeypatch.setattr("vefr.cli.pack_root", lambda: tmp_path)

    dest = tmp_path / "out"
    args = type("A", (), {"dest": str(dest), "name": "pack", "push": False})()
    rc = cmd_scaffold(args)
    assert rc == 0

    assert (dest / "world.json").exists()
    assert (dest / "logbok.md").exists()
    assert (dest / "voices" / "ferry.md").exists()
    assert (dest / "README.md").exists()
    assert (dest / "LICENSE.md").exists()
    assert not (dest / "world-tree.md").exists()
    assert not (dest / "handbok.md").exists()
    assert "vefr" in (dest / "README.md").read_text(encoding="utf-8")

    # A real git history: main, one commit, clean tree.
    assert _git(str(dest), "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert _git(str(dest), "rev-list", "--count", "HEAD") == "1"
    assert "world pack pack" in _git(str(dest), "log", "--format=%s")


def test_scaffold_readme_links_engine_origin(tmp_path, monkeypatch):
    """The README points at this checkout's own origin - runtime
    identity, never a hardcoded one."""
    from vefr.cli import repo_root

    root = repo_root()
    origin = subprocess.run(
        ('git', '-C', str(root), 'remote', 'get-url', 'origin'),
        capture_output=True, text=True,
    ).stdout.strip()
    if not origin:
        import pytest
        pytest.skip('checkout has no origin remote')

    pack = tmp_path / "worlds" / "pack"
    pack.mkdir(parents=True)
    (pack / "world.json").write_text('{"title": "T"}', encoding="utf-8")
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    from vefr import world as world_mod
    monkeypatch.setattr(
        world_mod, "load_world",
        lambda name=None: {"title": "T", "phases": {}},
    )
    monkeypatch.setattr("vefr.cli.pack_root", lambda: tmp_path)

    dest = tmp_path / "out"
    args = type("A", (), {"dest": str(dest), "name": "pack", "push": False})()
    assert cmd_scaffold(args) == 0

    expected = origin.removesuffix('.git')
    assert expected in (dest / "README.md").read_text(encoding="utf-8")


def test_scaffold_refuses_nonempty_dest(tmp_path, monkeypatch):
    dest = tmp_path / "out"
    dest.mkdir()
    (dest / "occupied.txt").write_text("x", encoding="utf-8")
    args = type("A", (), {"dest": str(dest), "name": "whatever", "push": False})()
    assert cmd_scaffold(args) == 1


def test_scaffold_missing_pack(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr("vefr.cli.pack_root", lambda: tmp_path)
    dest = tmp_path / "out"
    args = type("A", (), {"dest": str(dest), "name": "no-such-pack", "push": False})()
    assert cmd_scaffold(args) == 1
    assert not dest.exists()


def test_scaffold_nongit_fallback(tmp_path, monkeypatch):
    """When running outside a git checkout, engine_sha falls back to
    'unknown' rather than raising NameError."""
    pack = tmp_path / "worlds" / "pack"
    pack.mkdir(parents=True)
    (pack / "world.json").write_text('{"title": "T"}', encoding="utf-8")
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    from vefr import world as world_mod
    monkeypatch.setattr(
        world_mod, "load_world",
        lambda name=None: {"title": "T", "phases": {}},
    )
    monkeypatch.setattr("vefr.cli.pack_root", lambda: tmp_path)

    real_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if isinstance(cmd, tuple) and cmd[:2] == ("git", "rev-parse"):
            return subprocess.CompletedProcess(cmd, 1, "", "not a git repo")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)

    dest = tmp_path / "out"
    args = type("A", (), {"dest": str(dest), "name": "pack", "push": False})()
    rc = cmd_scaffold(args)
    assert rc == 0
    readme = (dest / "README.md").read_text(encoding="utf-8")
    assert "`unknown`" in readme

