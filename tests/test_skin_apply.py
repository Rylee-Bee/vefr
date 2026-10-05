"""Skin loader, K2 (design/ui-skin.md "How it is drawn" and the Rules): the player paints the skin.

The REAL woven player is driven in jsdom (tests/fixtures/skin_apply_harness.mjs). A skinned game
gets one `<style id="vefr-skin-css">` built from the baked skin; a game with no skin gets nothing
and looks exactly as it did.
"""

import copy
import json
import re
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
    dressed, contrast = home / "dressed.html", home / "contrast.html"
    skinned.write_text(cli.weave_html(mk.build(home, name="skin-plain")), encoding="utf-8")
    plain.write_text(cli.weave_html(ROOT / "worlds" / "sample-world"), encoding="utf-8")
    dressed.write_text(cli.weave_html(mk.build(home, skin=_dressed_skin(), files=_dressed_files(),
                                              name="skin-dressed")), encoding="utf-8")
    contrast.write_text(dressed.read_text(encoding="utf-8"), encoding="utf-8")
    run = subprocess.run(["node", str(ROOT / "tests/fixtures/skin_apply_harness.mjs"),
                          str(skinned), str(plain), str(dressed), str(contrast)],
                         capture_output=True, text=True, timeout=240)
    assert run.returncode == 0, run.stderr + run.stdout
    return json.loads(run.stdout)


def _dressed_skin():
    """The same test skin plus the two optional parts of the in-world
    interface: a backdrop (the ground outside the map) and a font choice."""
    skin = copy.deepcopy(mk.SKIN)
    skin["backdrop"] = "table.png"
    skin["fonts"] = {"display": "Cinzel", "body": "Crimson Pro"}
    return skin


def _dressed_files():
    return dict(mk.FILES, **{"table.png": (128, 128)})


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


# ---- the backdrop (docs/plans/interface/PLAN.md, slice 2) ----


def test_the_ground_outside_the_map_takes_the_skins_table(ran):
    """A skin with a backdrop paints it on the ground the map does not cover:
    the picture arrives as a data URI, and the map is redrawn when it decodes."""
    d = ran["dressed"]
    assert d["backdropUrl"].startswith("data:image/png;base64,")
    assert d["withPicture"]["ready"] is True
    assert d["withPicture"]["drawn"] > 0        # tiles of the table on the ground
    assert d["withPicture"]["bands"], "nothing was painted"
    # A picture that arrives after the first frame repaints the map by itself.
    assert d["hasRedraw"] is True


def test_the_ground_is_painted_only_where_the_map_is_not(ran):
    """The bands are the window minus the map's own rectangle, clipped to the
    window: ground on all four sides of a small map, and none at all when the
    map fills the window."""
    bands = ran["dressed"]["bands"]
    assert len(bands["smallMap"]) == 4
    assert bands["fullWindow"] == []
    map_x, map_y, map_w, map_h = 250, 180, 300, 240     # 800x600 window, map centred
    for x, y, w, h in bands["smallMap"]:
        overlap_x = max(0, min(x + w, map_x + map_w) - max(x, map_x))
        overlap_y = max(0, min(y + h, map_y + map_h) - max(y, map_y))
        assert overlap_x == 0 or overlap_y == 0, (x, y, w, h)


def test_the_backdrop_paints_only_when_the_picture_is_there(ran):
    """No picture, no painting: the bands are the flat ground exactly as before."""
    assert ran["dressed"]["withoutPicture"]["drawn"] == 0
    assert ran["dressed"]["withoutPicture"]["ready"] is False
    assert ran["dressed"]["bands"]["noPicture"] == []
    # A skin with no backdrop never even asks for one.
    assert ran["skinned"]["backdropUrl"] is None
    assert ran["skinned"]["withoutPicture"]["drawn"] == 0


def test_a_game_with_no_skin_keeps_todays_dark_ground(ran):
    """Even with a picture on the table, a pack with no skin paints the flat
    ground: the backdrop is a skin's, and only a skin's."""
    p = ran["plain"]
    assert p["backdropUrl"] is None
    assert p["withPicture"]["drawn"] == 0
    assert p["withPicture"]["ready"] is False
    assert p["hasStyle"] is False


def test_the_ground_is_never_asked_about_picture_only(ran):
    """A backdrop is a picture; every word in the game is still real text."""
    css = ran["dressed"]["css"]
    assert "content: url(" not in css
    assert ran["dressed"]["imgsWithText"] == 0


# ---- the type a skin chooses (docs/plans/interface/PLAN.md, slice 3) ----


def test_the_display_and_body_families_come_from_the_skin(ran):
    css = ran["dressed"]["css"]
    assert "--display: 'Cinzel', Georgia" in css
    assert "--read: 'Crimson Pro', Georgia" in css


def test_a_family_the_engine_does_not_bundle_is_never_asked_for(ran):
    """The player draws the three bundled families and nothing else, so a hand
    edited skin cannot name a typeface that would 404 into a fallback."""
    parts = (ROOT / "web" / "player" / "parts" / "540-the-skin.js").read_text(encoding="utf-8")
    stacks = re.search(r"var SKIN_FONT_STACKS = \{(.*?)\};", parts, re.S).group(1)
    assert set(re.findall(r"'([^']+)':", stacks)) == {"Cinzel", "Atkinson Hyperlegible Next", "Crimson Pro"}
    assert "--read:" not in ran["skinned"]["css"]    # a skin with no fonts keeps the player's own


def test_contrast_more_keeps_the_flat_ground_and_the_plain_type(ran):
    """`prefers-contrast: more` returns the plain flat style: no backdrop, and
    the skin's fonts inside the same media guard as the rest of the sheet."""
    c = ran["contrast"]
    assert c["backdropUrl"] is None
    assert c["withoutPicture"]["drawn"] == 0
    assert c["hasStyle"] is True and "prefers-contrast" in c["css"] and "forced-colors" in c["css"]
