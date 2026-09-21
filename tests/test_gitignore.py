"""Tripwire: only sample-world and lore packs may be tracked under worlds/.

If someone adds a new shipped pack, this test tells them to add it to
.gitignore negation rules. If someone accidentally stages a private
pack, this test catches it before merge."""

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHIPPED = {"sample-world", "lore"}


def _tracked_worlds() -> set[str]:
    """Return the set of top-level pack names tracked under worlds/."""
    result = subprocess.run(
        ["git", "ls-files", "worlds/"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    packs = set()
    for line in result.stdout.splitlines():
        parts = Path(line).parts
        if len(parts) >= 2 and parts[0] == "worlds":
            packs.add(parts[1])
    return packs


def test_only_shipped_worlds_are_tracked():
    """Every tracked path under worlds/ must belong to a shipped pack."""
    tracked = _tracked_worlds()
    untracked_packs = tracked - _SHIPPED
    assert not untracked_packs, (
        f"non-shipped world packs tracked in git: {untracked_packs}. "
        "Add negation rules to .gitignore or remove them from staging."
    )


def test_shipped_worlds_are_present():
    """sample-world and lore must exist (the engine needs them)."""
    worlds = _REPO_ROOT / "worlds"
    for name in _SHIPPED:
        assert (worlds / name).is_dir(), f"shipped pack worlds/{name}/ is missing"
