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


def test_the_ink_reaches_text_inside_panels_and_buttons_stay_readable(ran):
    """Measured on Cottage's real skin before this fix: the reader's body text was cream on
    parchment (1.4:1) and the health label gold on parchment (1.2:1), because only the panel
    itself took the ink. Text inside a skinned panel now takes the ink; buttons get light text."""
    css = ran["skinned"]["css"]
    assert "#2B2118 !important" in css                   # the test skin's on_panel ink
    assert ":not(button, button *, .cta, .cta *, .gbtn, .gbtn *, kbd)" in css
    assert "color: #F6F0E2 !important" in css            # light text on the wooden button face


def test_a_panel_middle_is_flat_not_a_tiled_patch(ran):
    """A 32 px patch tiled across a wide panel showed as stripes behind the text (seen on the
    real Cottage skin). Panels keep only the carved border from the picture."""
    css = ran["skinned"]["css"]
    panel_rule = css[css.index(".glass, #npc-box"):]
    panel_rule = panel_rule[:panel_rule.index("}")]
    assert "var(--vefr-skin-ground," in panel_rule
    assert " fill " not in panel_rule                    # no tiled middle
    assert "#menu .carved" in css and "#menu .pm button" in css


def test_skinned_buttons_have_a_dark_base_under_the_picture(ran):
    """axe saw the gold Whisper button's own gold background under the wood (3.2:1 with the
    light text). A dark base keeps the text readable even with the picture missing."""
    assert "background-color: #5F5043 !important" in ran["skinned"]["css"]
