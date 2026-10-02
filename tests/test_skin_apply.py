"""Skin loader, K2 (design/ui-skin.md "How it is drawn" and the Rules): the player paints the skin.

The REAL woven player is driven in jsdom (tests/fixtures/skin_apply_harness.mjs). A skinned game
gets one `<style id="vefr-skin-css">` built from the baked skin; a game with no skin gets nothing
and looks exactly as it did.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
import make_skin_pack as mk  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("skin-apply")
    skinned, plain = home / "skinned.html", home / "plain.html"
    skinned.write_text(cli.weave_html(mk.build(home)), encoding="utf-8")
    plain.write_text(cli.weave_html(ROOT / "worlds" / "sample-world"), encoding="utf-8")
    run = subprocess.run(["node", str(ROOT / "tests/fixtures/skin_apply_harness.mjs"),
                          str(skinned), str(plain)], capture_output=True, text=True, timeout=240)
    assert run.returncode == 0, run.stderr + run.stdout
    return json.loads(run.stdout)


def test_a_skinned_game_gets_one_style_element(ran):
    s = ran["skinned"]
    assert s["hasStyle"] is True
    assert "has-skin" in (s["bodyClass"] + " " + s["htmlClass"])


def test_the_css_paints_panels_buttons_bars_and_the_cursor_from_the_pictures(ran):
    css = ran["skinned"]["css"]
    assert "border-image" in css and "url(data:image/png;base64," in css
    assert ".glass" in css and ".gbtn" in css                       # the player's panel and button
    assert "cursor:" in css.replace(" :", ":")                      # the skin's cursor part


def test_a_skin_never_removes_focus_or_shrinks_targets(ran):
    css = ran["skinned"]["css"]
    assert "outline: none" not in css and "outline:none" not in css
    assert "min-height: 44px" in css or "min-height:44px" in css


def test_high_contrast_and_forced_colors_fall_back_to_the_plain_style(ran):
    css = ran["skinned"]["css"]
    assert "prefers-contrast" in css and "forced-colors" in css


def test_text_is_never_inside_a_picture(ran):
    assert ran["skinned"]["imgsWithText"] == 0
    assert "content: url(" not in ran["skinned"]["css"]            # no picture used as text


def test_no_skin_means_no_change(ran):
    p = ran["plain"]
    assert p["hasStyle"] is False and p["css"] == ""
    assert "has-skin" not in (p["bodyClass"] + " " + p["htmlClass"])
