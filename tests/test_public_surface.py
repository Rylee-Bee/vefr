"""Public-surface guard tests.

These tests pin the guard's behavior: it catches the leak classes
the public-release audit found, and its allowlist does not silently
let real leaks through.

Run directly:

    python scripts/check_public_surface.py

Or as a pytest module:

    pytest tests/test_public_surface.py -q
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD = REPO_ROOT / "scripts" / "check_public_surface.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location("check_public_surface", GUARD)
    assert spec and spec.loader, "guard module spec"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- the guard itself runs clean on the tracked tree ----


def test_guard_runs_clean_on_current_tree():
    """The current public tree must scan clean. If this fails, the
    sanitization commit missed a leak."""
    res = subprocess.run(
        [sys.executable, str(GUARD)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert res.returncode == 0, (
        "public-surface guard reported leaks:\n"
        f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )


# ---- pattern categories ----


@pytest.mark.parametrize("category,pattern", [
    ("real-lan-192-168-2", r"192.168.2.42"),
    ("homelab-hostname", r"gitea.hulganfamily.duckdns.org"),
    ("homelab-machine", r"ssh bazzite"),
    ("private-path", r"/var/home/rylee/projects/vefr"),
    ("private-ssh-user", r"ssh rylee@host"),
    ("private-gitea-owner", r"http://gitea.example/rylee/sample-pack"),
    ("private-email", r"rylee@hulgan.home"),
    ("private-key-header", r"-----BEGIN RSA PRIVATE KEY-----"),
    ("github-token", r"ghp_abc123def456ghi789jkl012mno345pqr678"),
    ("openai-key", r"sk-abcdefghijklmnopqrstuvwxyz0123456789"),
    ("aws-access-key", r"AKIAIOSFODNN7EXAMPLE"),
    ("slack-token", r"xoxb-1234567890-abcdefghij"),
])
def test_pattern_catches_documented_leak(category, pattern, tmp_path):
    """Every pattern must catch its representative leak on a tiny
    synthetic tracked file. The test creates a temp file inside a
    temp git repo so `git ls-files` returns it; the guard is then
    pointed at that repo by chdir."""
    mod = _load_guard()
    # Build a one-file git repo containing the leak pattern.
    work = tmp_path / "guard_probe"
    work.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=work, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.email", "probe@local"], cwd=work,
                   check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "probe"], cwd=work,
                   check=True, capture_output=True)
    (work / "leak.txt").write_text(pattern + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "leak.txt"], cwd=work, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "probe"],
                   cwd=work, check=True, capture_output=True)
    # Run the guard against the temp repo.
    hits = mod.scan_file("leak.txt", work)
    matched = [h for h in hits if h[0] == category]
    assert matched, (
        f"pattern {category!r} ({pattern!r}) failed to match; "
        f"got hits={hits!r}"
    )


def test_allowlist_lets_example_domains_through(tmp_path):
    """The guard must not flag RFC 5737 example IPs or .example.test."""
    mod = _load_guard()
    work = tmp_path / "guard_probe"
    work.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=work, check=True,
                   capture_output=True)
    (work / "clean.txt").write_text(
        "Try http://192.0.2.10:8081 or http://198.51.100.10:3000.\n"
        "Or https://gitea.example.test/owner/repo.\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "clean.txt"], cwd=work, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "probe"],
                   cwd=work, check=True, capture_output=True)
    hits = mod.scan_file("clean.txt", work)
    assert hits == [], (
        f"guard flagged a clean example as a leak: {hits!r}"
    )


def test_skip_path_prefixes_skip_data_artifacts_git(tmp_path):
    mod = _load_guard()
    work = tmp_path / "guard_probe"
    work.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=work, check=True,
                   capture_output=True)
    (work / "data").mkdir()
    (work / "data" / "leak.jsonl").write_text("192.168.2.42\n", encoding="utf-8")
    subprocess.run(["git", "add", "data/leak.jsonl"], cwd=work, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "probe"],
                   cwd=work, check=True, capture_output=True)
    assert mod.should_skip("data/leak.jsonl") is True


def test_skip_storyteller_wip_paths():
    mod = _load_guard()
    assert mod.should_skip("tests/fixtures/storyteller/rosa-after-close.json")
    assert mod.should_skip("storyteller_packs/qwen3-0.6b/manifest.json")
    assert mod.should_skip("src/vefr/npc_action.py")


def test_scan_empty_repo_returns_no_hits(tmp_path):
    mod = _load_guard()
    work = tmp_path / "empty"
    work.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=work, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.email", "e@l"], cwd=work,
                   check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "e"], cwd=work,
                   check=True, capture_output=True)
    (work / "readme.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "readme.md"], cwd=work, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "init"], cwd=work,
                   check=True, capture_output=True)
    assert mod.scan_file("readme.md", work) == []
