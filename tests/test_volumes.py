"""Volume split: ro engine template + rw author canon, merged at load time."""

import json
import shutil
from pathlib import Path

import pytest

from vefr import cli, paths, volumes as vol_mod, world as world_mod
from vefr.world import discover_packs, load_world


@pytest.fixture(autouse=True)
def _clear_world_cache():
    """Each test gets a fresh load_world() cache."""
    world_mod.load_world.cache_clear()
    yield
    world_mod.load_world.cache_clear()


@pytest.fixture
def fake_app_home(tmp_path, monkeypatch):
    """Point app_home() at tmp_path with both worlds/ and
    worlds-template/ subdirs. Returns the tmp_path so the test
    can populate them."""
    ro = tmp_path / "worlds-template"
    rw = tmp_path / "worlds"
    ro.mkdir()
    rw.mkdir()
    monkeypatch.setenv("VEFR_HOME", str(tmp_path))
    # `paths.app_home()` reads VEFR_HOME first; we don't need to
    # patch the function. Same for template_dir / worlds_dir -
    # they read app_home() each time, so the env override
    # propagates.
    world_mod.load_world.cache_clear()
    yield tmp_path
    world_mod.load_world.cache_clear()


def _make_pack(pack_root: Path, name: str, *, title: str, phases: dict,
               body: str = "engine-owned") -> Path:
    d = pack_root / name
    d.mkdir(parents=True, exist_ok=True)
    d.joinpath("world.json").write_text(
        json.dumps({
            "name": name, "title": title, "phases": phases,
            "voices": {"mother": {"file": "voices/keeper.md",
                                   "strike": "write a letter"}},
            "bonds": {
                "given": {"card": "Given.", "prompt": "given."},
                "cold": {"card": "Cold.", "prompt": "cold."},
            },
            "town": {"tile": 32, "map": ["#.#"]},
            "_class": body,
        }, indent=2),
        encoding="utf-8",
    )
    return d


def test_discover_packs_walks_both_mounts(fake_app_home):
    ro = fake_app_home / "worlds-template"
    rw = fake_app_home / "worlds"
    _make_pack(ro, "lore", title="Lore", phases={"a": "."})
    _make_pack(ro, "sample-world", title="Emberfield",
               phases={"dusk": "."})
    _make_pack(rw, "private-canon", title="Private Canon",
               phases={"whispers": "."})

    packs = discover_packs()
    by_name = {p["name"]: p for p in packs}
    assert set(by_name) == {"lore", "sample-world", "private-canon"}
    assert by_name["lore"]["source"] == "template"
    assert by_name["sample-world"]["source"] == "template"
    assert by_name["private-canon"]["source"] == "canon"


def test_discover_packs_canon_wins_on_conflict(fake_app_home):
    ro = fake_app_home / "worlds-template"
    rw = fake_app_home / "worlds"
    _make_pack(ro, "ambiguous", title="Template version", phases={"a": "."})
    _make_pack(rw, "ambiguous", title="Author version", phases={"b": "."})

    packs = discover_packs()
    assert len(packs) == 1
    assert packs[0]["source"] == "canon"
    w = load_world("ambiguous")
    assert w["title"] == "Author version"
    assert w["phases"] == {"b": "."}


def test_pack_dir_prefers_canon_then_template(fake_app_home):
    ro = fake_app_home / "worlds-template"
    rw = fake_app_home / "worlds"
    (ro / "engine-only").mkdir()
    (rw / "author-only").mkdir()
    assert "engine-only" in str(paths.pack_dir("engine-only"))
    assert "author-only" in str(paths.pack_dir("author-only"))
    # Both: rw wins.
    (ro / "both").mkdir()
    (rw / "both").mkdir()
    resolved = paths.pack_dir("both")
    assert resolved.parent == rw, f"expected rw, got {resolved}"


def test_load_world_records_source_in_weave(fake_app_home):
    from vefr import weave as weave_mod
    rw = fake_app_home / "worlds"
    _make_pack(rw, "canon-pack", title="Canon",
               phases={"dusk": ".", "dawn": "."})

    log_path = fake_app_home / "weave.jsonl"
    weave_mod.reset_path_for_testing(log_path)
    try:
        load_world("canon-pack")
        events = weave_mod.from_disk(limit=20)
        starts = [e for e in events if e.get("event") == "pack.load.start"]
        assert starts, "expected a pack.load.start weave event"
        assert starts[0].get("source") == "canon"
    finally:
        weave_mod.reset_path_for_testing(None)


def test_classify_pack_known_engine_packs():
    for name in ("lore", "sample-world", "poolworld"):
        assert vol_mod._classify_pack(name) == "engine", name
    for name in ("private-canon", "my-canon", "anything-else"):
        assert vol_mod._classify_pack(name) == "author", name


def test_volumes_migrate_is_idempotent(tmp_path, monkeypatch):
    """A quadlet that already references vefr-template is the
    idempotency signal. Re-running migrate() on such a host
    returns 0 without touching anything."""
    quadlet = tmp_path / "vefr.container"
    # tmp_path already exists; create only the file's parent dir.
    quadlet.parent.mkdir(exist_ok=True)
    quadlet.write_text(
        "Volume=vefr-template:/app/worlds-template:ro\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    rc = vol_mod.migrate(dry_run=True)
    assert rc == 0


def test_volumes_migrate_dry_run_creates_no_volumes(tmp_path, monkeypatch):
    """Dry-run reports what it would do; no podman invocations,
    no quadlet writes, no service restarts."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    calls: list[tuple[str, ...]] = []

    def _tracking_run(cmd, **kw):
        calls.append(tuple(cmd))
        return None

    monkeypatch.setattr(vol_mod, "_run", _tracking_run)
    rc = vol_mod.migrate(dry_run=True)
    assert rc == 0
    # No systemd invocations under dry-run.
    assert not any("systemctl" in str(c) for c in calls)
    # No `podman volume create` either - the real podman command
    # is gated by the dry_run check inside _volume_create.
    assert not any("volume" in str(c) and "create" in str(c)
                   for c in calls)


def test_volumes_list_empty_returns_zero_rc(fake_app_home):
    """An empty world (no packs at all) prints 'no packs found'
    and exits 0 - not an error."""
    import argparse
    rc = cli.cmd_volumes_list(argparse.Namespace())
    assert rc == 0


def test_volumes_list_returns_visible_packs(fake_app_home, capsys):
    """The CLI's `volumes list` subcommand prints a small table."""
    ro = fake_app_home / "worlds-template"
    rw = fake_app_home / "worlds"
    _make_pack(ro, "sample-world", title="Emberfield", phases={"dusk": "."})
    _make_pack(rw, "private-canon", title="Private Canon",
               phases={"whispers": "."})

    import argparse
    rc = cli.cmd_volumes_list(argparse.Namespace())
    assert rc == 0
    out = capsys.readouterr().out
    assert "sample-world" in out
    assert "template" in out
    assert "private-canon" in out
    assert "canon" in out
