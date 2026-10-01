"""Start over, in a real browser.

Confirming clears every ``vefr-`` save on the site and returns to the
title screen; Cancel changes nothing and the game keeps running. The
woven file is served over http so localStorage behaves the way it does
for a player. Skips without chromium, like the rest of tests/browser.
"""

import argparse
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

# Planted saves: three the game itself would write, and one that belongs
# to another app on the same origin and must survive.
PLANT = """() => {
  localStorage.setItem('vefr-hp-testworld', '1');
  localStorage.setItem('vefr-slain-testworld', '["a-rat"]');
  localStorage.setItem('vefr-packaged-combat', '[]');
  localStorage.setItem('keep-me', 'safe');
}"""


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def woven(tmp_path_factory):
    home = tmp_path_factory.mktemp("start-over-home")
    rc = cli.cmd_build_web(argparse.Namespace(
        pack=str(SAMPLE), out=str(home / "sample.html"), pool=0,
        with_bundle=False, from_live=None))
    assert rc == 0
    port = _free_port()
    log = open(home / "server.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port),
         "--bind", "127.0.0.1", "--directory", str(home)],
        stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/sample.html"
    for _ in range(120):
        try:
            urllib.request.urlopen(url, timeout=2)
            break
        except Exception:  # noqa: BLE001 - not up yet
            time.sleep(0.25)
    else:
        proc.terminate()
        pytest.fail(f"the woven file never came up; see {home / 'server.log'}")
    yield url
    proc.terminate()
    proc.wait(timeout=10)


def open_woven(page, url):
    page.goto(url)
    page.get_by_role("button", name="Begin").click()
    page.wait_for_function("window.VEFR_COMBAT && window.VEFR_COMBAT.region")


def open_startover(page):
    """Open the pause menu, then the Start over confirmation panel."""
    page.keyboard.press("Escape")
    page.locator('[data-panel="startover"]').click()
    page.locator("#startover-body").wait_for(state="visible")


def keys(page):
    return page.evaluate("() => Object.keys(localStorage)")


def test_opening_start_over_focuses_cancel_not_the_destructive_button(page, woven):
    open_woven(page, woven)
    open_startover(page)
    assert page.evaluate(
        "() => document.activeElement && document.activeElement.id"
    ) == "startover-cancel"


def test_confirm_clears_vefr_saves_and_returns_to_the_title(page, woven):
    open_woven(page, woven)
    page.evaluate(PLANT)
    open_startover(page)
    page.locator("#startover-confirm").click()
    # Confirming reloads the page: the title screen is back.
    page.locator("#ts-enter").wait_for(state="visible", timeout=10000)
    after = keys(page)
    assert not [k for k in after if k.startswith("vefr-")], after
    assert "keep-me" in after


def test_cancel_changes_nothing_and_the_game_keeps_running(page, woven):
    open_woven(page, woven)
    page.evaluate(PLANT)
    open_startover(page)
    page.locator("#startover-cancel").click()
    after = keys(page)
    assert "vefr-hp-testworld" in after
    assert "vefr-slain-testworld" in after
    assert "vefr-packaged-combat" in after
    assert "keep-me" in after
    assert page.evaluate("!!window.VEFR_COMBAT")
    assert not page.locator("#startover-body").is_visible()