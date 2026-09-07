"""Volume export / import: round-trip the canary between disk and a
host-side git repo.

The author flow is: export a pack to a directory, edit in vim,
git commit, import back into the rw volume. The round-trip must
be lossless: export -> import -> export produces the same
files (modulo timestamps + git metadata).
"""

import shutil
from pathlib import Path

import pytest

from vefr import volumes as vol_mod


@pytest.fixture
def sample_pack_root(tmp_path, monkeypatch):
    """Point the export/import at a fresh tmp copy of sample-world
    so the engine's own worlds/ is left untouched."""
    src = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"
    dest = tmp_path / "worlds" / "sample-world"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    # The export/import helpers use `_default_worlds_root()` which
    # looks for a few candidates in order. The first that matches
    # wins, so the test sets the engines to the tmp world root.
    return tmp_path / "worlds"


def test_export_creates_git_repo_with_engine_native_layout(sample_pack_root, tmp_path):
    """`volumes export` writes a real git repo with the pack's
    file tree in engine-native layout (acts shape, in the canary's
    case) plus a README and an initial commit.

    The export's root IS the pack - so `dest/world.json`, not
    `dest/worlds/<pack>/world.json`. The author can `cd dest &&
    $EDITOR` and commit.
    """
    dest = tmp_path / "exported"
    result = vol_mod.export_pack("sample-world", dest,
                                 worlds_root=sample_pack_root)
    assert result == dest
    # Git repo present.
    assert (dest / ".git").is_dir()
    # README + the pack's file tree at the dest root.
    assert (dest / "README.md").exists()
    assert (dest / "world.json").exists()  # the pack-level contract
    # In the acts shape, the tree is under acts/ at the dest root.
    contract = dest / "acts" / "act-1" / "town" / "contract.json"
    assert contract.exists(), f"expected contract at {contract}"
    # The initial commit happened.
    import subprocess
    log = subprocess.run(
        ["git", "-C", str(dest), "log", "--oneline"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "export sample-world" in log


def test_export_then_import_round_trip_losslessly(sample_pack_root, tmp_path):
    """export -> import -> export produces the same file tree."""
    # First export.
    dest1 = tmp_path / "export-1"
    vol_mod.export_pack("sample-world", dest1, worlds_root=sample_pack_root)

    # Import into a different worlds root (so we know the import
    # is reading from dest1, not from somewhere cached).
    second_root = tmp_path / "worlds-2"
    second_root.mkdir()
    vol_mod.import_pack("sample-world", dest1, worlds_root=second_root)

    # Second export from the imported location.
    dest2 = tmp_path / "export-2"
    vol_mod.export_pack("sample-world", dest2, worlds_root=second_root)

    # The two exports should have the same file tree (modulo
    # timestamps, the README which carries a timestamp, and the
    # .git/ internals which have different commit hashes).
    def _tree(p: Path, *, skip=("README.md", ".git")) -> set[str]:
        out = set()
        for f in p.rglob("*"):
            if f.is_file() and f.name not in skip:
                rel = f.relative_to(p)
                # Drop any path under a skipped dir.
                if any(part in skip for part in rel.parts):
                    continue
                out.add(str(rel))
        return out

    assert _tree(dest1) == _tree(dest2)


def test_import_validates_before_writing(sample_pack_root, tmp_path):
    """A pack that fails maplab is rejected before the import
    writes to the destination - so a bad pack can't clobber a
    good one."""
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "world.json").write_text(
        '{"name":"bad","title":"Bad","phases":{}',  # truncated, not valid JSON
        encoding="utf-8",
    )
    # Also missing voices / bonds / town - even valid JSON would fail.
    (bad / "world.json").write_text(
        '{"name":"bad","title":"Bad","phases":{}}',
        encoding="utf-8",
    )
    # The dest is fresh - should not be written.
    dest_root = tmp_path / "dest"
    with pytest.raises(ValueError, match="fails the engine contract"):
        vol_mod.import_pack("bad", bad, worlds_root=dest_root)
    # The bad pack should not have been written.
    assert not (dest_root / "bad").exists()


def test_import_dry_run_does_not_write(sample_pack_root, tmp_path):
    """`--dry-run` validates the source but writes nothing."""
    src = tmp_path / "src"
    vol_mod.export_pack("sample-world", src, worlds_root=sample_pack_root)
    dest_root = tmp_path / "dest"
    dest_root.mkdir()
    rc = vol_mod.import_pack("sample-world", src,
                              worlds_root=dest_root, dry_run=True)
    assert rc is not None
    assert not (dest_root / "sample-world").exists()


def test_export_refuses_to_overwrite_existing_git_repo(sample_pack_root, tmp_path):
    """If the destination is already a non-empty git repo (the
    author probably has in-progress work), export is a no-op."""
    dest = tmp_path / "in-progress"
    dest.mkdir()
    subprocess_run = __import__("subprocess").run
    subprocess_run(["git", "-C", str(dest), "init", "-b", "main"],
                   capture_output=True, text=True, check=True)
    (dest / "WIP.md").write_text("in progress", encoding="utf-8")
    subprocess_run(["git", "-C", str(dest), "add", "-A"], check=True)
    # Inline identity: CI runner images have no global git config.
    subprocess_run(["git", "-C", str(dest), "-c", "user.name=test",
                    "-c", "user.email=test@example.test", "commit",
                    "-m", "wip"],
                   capture_output=True, text=True, check=True)

    # The export should not clobber the existing repo.
    result = vol_mod.export_pack("sample-world", dest,
                                 worlds_root=sample_pack_root)
    assert result == dest
    # The WIP file is still there; the export didn't write anything.
    assert (dest / "WIP.md").exists()


def test_export_no_git_skips_init(sample_pack_root, tmp_path):
    """`--no-git` writes the file tree without initing a repo or
    making an initial commit. Useful for one-off exports where
    the author is going to `git init` themselves or not use
    git at all."""
    dest = tmp_path / "no-git"
    vol_mod.export_pack("sample-world", dest,
                         worlds_root=sample_pack_root, init_git=False)
    assert (dest / "acts" / "act-1" / "town" / "contract.json").exists()
    assert not (dest / ".git").exists()


def test_pack_layout_detects_acts_vs_flat(tmp_path):
    """The layout detector reads the on-disk shape correctly."""
    # Acts: has acts/ subdir.
    acts = tmp_path / "acts-pack"
    (acts / "acts").mkdir(parents=True)
    (acts / "world.json").write_text("{}", encoding="utf-8")
    assert vol_mod._pack_layout(acts) == "acts"
    # Flat: no acts/ subdir.
    flat = tmp_path / "flat-pack"
    flat.mkdir()
    (flat / "world.json").write_text("{}", encoding="utf-8")
    assert vol_mod._pack_layout(flat) == "flat"
