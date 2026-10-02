"""vefr publish / look / probe, and doctor's tooling rows (src/vefr/devtools.py).

The verbs are thin: `cmd_publish`, `cmd_look`, `cmd_probe` in vefr.cli hand
their args to vefr.devtools (the way cmd_find hands to vefr.find); the front
door contract is pinned in tests/test_cli_help.py. Hermetic: publish runs
against a fake gallery script; look/probe need Playwright + Chromium and skip
without them (VEFR_BROWSER_REQUIRED=1 makes a missing browser a failure).
"""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import vefr.cli as cli
from vefr import devtools

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "worlds" / "sample-world"
sys.path.insert(0, str(Path(__file__).parent / "fixtures"))


# ---------------------------------------------------------------- publish

@pytest.fixture
def fake_gallery(tmp_path, monkeypatch):
    out = tmp_path / "gal"
    out.mkdir()
    script = tmp_path / "fake-gallery"
    script.write_text(
        "#!/usr/bin/env bash\n"
        f'OUT="{out}"\n'
        'printf "%s\\n" "$@" > "$OUT/args"\n'
        'stat -c %a "$3" > "$OUT/mode"\n'
        'test -f "$3/index.html" && echo yes > "$OUT/idx"\n'
        'exit 0\n')
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("VEFR_GALLERY", str(script))
    return out


def _publish(**kw):
    base = dict(pack=str(SAMPLE), project=None, sha=None, live=False,
                dry_run=False)
    base.update(kw)
    return cli.cmd_publish(SimpleNamespace(**base))


def test_publish_weaves_into_a_readable_dir_and_calls_the_gallery(fake_gallery):
    assert _publish(sha="abc1234") == 0
    args = (fake_gallery / "args").read_text().split()
    assert args[:3] == ["build", "sample-world", args[2]]   # project = pack dir name
    assert args[args.index("--sha") + 1] == "abc1234"
    assert "--live" not in args
    assert (fake_gallery / "idx").read_text().strip() == "yes"
    assert (fake_gallery / "mode").read_text().strip() == "755"   # not mktemp's 700


def test_publish_flags(fake_gallery):
    assert _publish(project="my-game", sha="abc1234", live=True) == 0
    args = (fake_gallery / "args").read_text().split()
    assert args[1] == "my-game" and "--live" in args


def test_publish_sha_defaults_to_the_packs_git_head(fake_gallery, tmp_path):
    repo = tmp_path / "game"
    shutil_copy = __import__("shutil").copytree
    shutil_copy(SAMPLE, repo / "worlds" / "sample-world")
    run = lambda *a: subprocess.run(a, cwd=repo, check=True, capture_output=True)  # noqa: E731
    run("git", "init", "-q")
    run("git", "-c", "user.email=t@t", "-c", "user.name=t", "commit",
        "-q", "--allow-empty", "-m", "x")
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo,
                          capture_output=True, text=True).stdout.strip()
    assert _publish(pack=str(repo / "worlds" / "sample-world")) == 0
    args = (fake_gallery / "args").read_text().split()
    assert args[args.index("--sha") + 1] == head


def test_publish_dry_run_does_not_call_the_gallery(fake_gallery, capsys):
    assert _publish(sha="abc1234", dry_run=True) == 0
    assert not (fake_gallery / "args").exists()
    assert "build sample-world" in capsys.readouterr().out


def test_publish_without_a_gallery_says_so(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("VEFR_GALLERY", str(tmp_path / "nope"))
    assert _publish(sha="abc1234") == 2
    assert "gallery" in capsys.readouterr().err.lower()


# ---------------------------------------------------- look / probe (browser)

def _need_browser():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
    except Exception as e:      # noqa: BLE001
        if os.environ.get("VEFR_BROWSER_REQUIRED") == "1":
            pytest.fail(f"browser required but unavailable: {e}")
        pytest.skip(f"no Chromium for Playwright: {e}")


@pytest.fixture(scope="module")
def woven(tmp_path_factory):
    out = tmp_path_factory.mktemp("devtools") / "sample.html"
    out.write_text(cli.weave_html(SAMPLE), encoding="utf-8")
    return out


def test_look_writes_a_screenshot_and_lists_text_over_the_map(woven, tmp_path, capsys):
    _need_browser()
    png = tmp_path / "look.png"
    rc = cli.cmd_look(SimpleNamespace(
        html=str(woven), pack=None, out=str(png), steps="ArrowDown,ArrowRight",
        json=True))
    assert rc == 0
    assert png.stat().st_size > 1000
    report = json.loads(capsys.readouterr().out)
    assert report["screenshot"] == str(png)
    ids = {e["id"] for e in report["overlay_text"]}
    assert "status" in ids                  # the how-to-move line the player shows
    for e in report["overlay_text"]:
        assert set(e) >= {"id", "text", "y"}


def test_probe_fires_events_and_prints_the_why_records(tmp_path, capsys):
    _need_browser()
    import make_events_pack
    pack = make_events_pack.build(tmp_path)
    html = tmp_path / "events.html"
    html.write_text(cli.weave_html(pack), encoding="utf-8")
    rc = cli.cmd_probe(SimpleNamespace(
        html=str(html), pack=None,
        fire=["reads:what=the-fixture-note"], json=True))
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    ids = [w["id"] for w in report["why"]]
    assert "the-note-closed" in ids
    assert report["flags"].get("read-it") is True
    assert report["fired"][0]["event"] == "reads"


def test_probe_rejects_a_malformed_fire_spec(tmp_path, capsys):
    rc = cli.cmd_probe(SimpleNamespace(
        html=str(tmp_path / "x.html"), pack=None, fire=["nonsense"], json=True))
    assert rc == 2
    assert "event:key=value" in capsys.readouterr().err


# ------------------------------------------------------ doctor tooling rows

def test_tooling_checks_report_each_tool_with_a_fix_hint(tmp_path):
    (tmp_path / "root" / "node_modules" / "jsdom").mkdir(parents=True)
    home = tmp_path / "home"
    (home / ".cache" / "ms-playwright" / "chromium-1").mkdir(parents=True)
    (home / ".agents" / "bin").mkdir(parents=True)
    (home / ".agents" / "bin" / "gallery").write_text("#!/bin/sh\n")
    rows = devtools.tooling_checks(tmp_path / "root", which=lambda n: "/bin/" + n,
                                   home=home)
    by = {name: (status, detail) for name, status, detail in rows}
    assert set(by) >= {"node", "jsdom", "chromium", "gallery"}
    assert all(s == "ok" for s, _ in by.values()), by

    rows = devtools.tooling_checks(tmp_path / "empty", which=lambda n: None,
                                   home=tmp_path / "nohome")
    by = {name: (status, detail) for name, status, detail in rows}
    for name in ("node", "jsdom", "chromium", "gallery"):
        assert by[name][0] == "missing", name
        assert by[name][1], f"{name} needs a fix hint"
    assert "npm ci" in by["jsdom"][1]
    assert "playwright install" in by["chromium"][1]


def test_doctor_prints_the_tooling_rows_but_never_fails_on_them(monkeypatch, tmp_path, capsys):
    from test_doctor import _patch
    args = _patch(monkeypatch, tmp_path)
    monkeypatch.setattr(devtools, "tooling_checks", lambda root, **kw: [
        ("node", "ok", "v24"), ("jsdom", "missing", "npm ci"),
        ("chromium", "ok", "chromium-1"), ("gallery", "missing", "see skills/gallery")])
    rc = cli.cmd_doctor(args)
    out = capsys.readouterr().out
    assert rc == 0                                   # a missing dev tool is not a failure
    assert "4 ok, 0 failed, 1 skipped" in out        # the existing summary is unchanged
    assert "tooling" in out.lower()
    assert "jsdom" in out and "npm ci" in out


def test_the_command_guide_documents_the_new_verbs():
    guide = (ROOT / "docs" / "guides" / "vefr-command.md").read_text(encoding="utf-8")
    for verb in ("vefr publish", "vefr look", "vefr probe"):
        assert verb in guide, verb
    assert "tooling" in guide.lower()          # doctor's new rows are mentioned
