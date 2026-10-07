"""A skinned menu shows its words: every tab labelled, the panel full, both widths.

Measured on a woven game wearing a soft-wood skin (tests/fixtures/make_skin_pack.py's
`build_wood`, the shape the private Cottage pack wears): a skin's panel PICTURE supplies
the face every skinned surface is painted with - the player samples the picture's own
middle into `--vefr-skin-ground` and lays every panel, tab and HUD box on it - and the
skin supplies the words in `ink.on_panel`. Nothing between the two checked that they can
be read together. Dark wood plus dark ink is 1.14:1, so every label, the whole content
panel and every HUD value box went blank while the text stayed in the DOM, visible, and
fully opaque: `textContent` was "Journal", `visibility: visible`, `opacity: 1`,
`font-size: 15.2px`. That is why the eight existing Cottage checks and axe-core passed -
none of them looks at whether a label can be seen, only at whether it exists.

So this check reads what a person would actually see, at both widths the screenshots were
taken at (390x844 and 1440x900): the words are there, the box is there, and the words are
readable on the box they sit on. WCAG AA for body text is 4.5:1, the floor
tests/test_teal_contrast.py already uses for this project's 10-13px labels.

Uses the same fixture the engine's own skin tests use and weaves it the same way, so the
page under test is one the rest of the skin suite already describes.
"""

import sys
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_skin_pack as mk  # noqa: E402

sys.path.insert(0, str(ROOT / "tests"))
from test_teal_contrast import contrast  # noqa: E402  (the WCAG maths, used as it is)

# WCAG 2.1: 4.5 for body text. The tab labels are ~15px, so they are body text.
BODY_FLOOR = 4.5

# The two widths the report's screenshots were taken at: the phone and the desktop.
WIDTHS = {"phone": (390, 844), "desktop": (1440, 900)}

# What a person can see on one piece of text: its words, and the face behind them.
# Everything here is read off the live page with getComputedStyle, not off the sheet.
SEEN = """(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  return {text: el.textContent.trim(), visible: cs.visibility === 'visible'
            && cs.opacity !== '0' && cs.display !== 'none',
          size: cs.fontSize, color: cs.color, face: cs.backgroundColor,
          w: Math.round(r.width), h: Math.round(r.height)};
}"""

TABS = """() => Array.from(document.querySelectorAll('#menu .pm button')).map((b) => {
  const cs = getComputedStyle(b);
  const r = b.getBoundingClientRect();
  return {text: b.textContent.trim(), visible: cs.visibility === 'visible'
            && cs.opacity !== '0' && cs.display !== 'none',
          onScreen: b.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}),
          hiddenBy: b.closest("[hidden]") ? (b.closest("[hidden]").id || b.closest("[hidden]").className) : null,
          size: cs.fontSize, color: cs.color, face: cs.backgroundColor,
          w: Math.round(r.width), h: Math.round(r.height)};
})"""


CORE_TABS = {"Journal", "Books", "Where next?", "Why did that happen?",
             "Bag", "How to play", "Display", "Start over"}


def _hex(colour: str) -> str:
    """`rgb(r, g, b)` as the `#RRGGBB` the WCAG maths takes."""
    n = [round(float(v)) for v in colour[colour.index("(") + 1:colour.index(")")].split(",")[:3]]
    return "#{:02X}{:02X}{:02X}".format(*n)


def _readable(seen: dict, what: str) -> float:
    """The contrast of one piece of text on the face behind it, with the reading."""
    assert seen, f"{what} is not on the page at all"
    assert seen["text"], f"{what} has no words in it"
    assert seen["visible"], f"{what} is in the DOM but not visible: {seen}"
    assert seen["w"] > 0 and seen["h"] > 0, f"{what} is laid out at no size: {seen}"
    got = contrast(_hex(seen["color"]), _hex(seen["face"]))
    assert got >= BODY_FLOOR, (
        f"{what} is unreadable: {seen['color']} on {seen['face']} is {got}:1, "
        f"under the {BODY_FLOOR}:1 floor - the words are there but nobody can see them")
    return got


@pytest.fixture(scope="module")
def woven(tmp_path_factory):
    """The sample world wearing a soft-wood skin that carries every part the contract names."""
    d = tmp_path_factory.mktemp("menu-labels")
    html = d / "wood.html"
    html.write_text(cli.weave_html(mk.build_wood(d)), encoding="utf-8")
    return html


@pytest.fixture(params=sorted(WIDTHS), ids=sorted(WIDTHS))
def skinned_menu(request, browser, woven):
    """The woven game, entered as a player enters it, with the menu open, at one width."""
    w, h = WIDTHS[request.param]
    ctx = browser.new_context(viewport={"width": w, "height": h})
    page = ctx.new_page()
    try:
        page.goto(woven.as_uri())
        page.click("#ts-enter")
        if page.is_visible("#config"):     # first run asks before it plays
            page.click("#cfg-save")
        page.wait_for_function("window.VEFR_COMBAT", timeout=15000)
        page.click("#menu-open")
        page.wait_for_selector("#menu .carved", state="visible")
        # The panel face is sampled from the picture when it decodes, so let that
        # decode land before reading: the sample rides on this same picture. Waiting
        # for the sampled property instead would be wrong - a skin whose picture
        # cannot carry the words never sets it, which is the fix working.
        page.evaluate("""async (arg) => {
          if (!arg) return null;
          const im = new Image(); im.src = arg;
          if (im.decode) await im.decode().catch(() => {});
          return true;
        }""", page.evaluate(
            "() => { const p = window.VEFR_SKIN && window.VEFR_SKIN.parts"
            " && window.VEFR_SKIN.parts.panel; return p ? p.file : null; }"))
        page.wait_for_timeout(200)
        yield page
    finally:
        ctx.close()


def test_every_menu_tab_has_readable_words_on_it(skinned_menu):
    """The reported symptom: every tab button showing no label at all.

    Only the tabs actually on screen are measured. A tab inside a hidden
    section has no size because nobody can see it, and asking for 4.5:1 on
    a box of zero pixels fails for a reason that has nothing to do with the
    ink. The hidden ones are checked separately, below, so that skipping
    them cannot quietly become skipping the check.
    """
    tabs = skinned_menu.evaluate(TABS)
    assert tabs, "the open menu has no tabs"
    on_screen = [s for s in tabs if s["onScreen"]]
    off_screen = [s for s in tabs if not s["onScreen"]]
    assert on_screen, "the open menu shows no tabs at all"
    assert CORE_TABS <= {s["text"] for s in on_screen}, (
        "the core tabs are not all on screen: "
        + str(sorted(CORE_TABS - {s["text"] for s in on_screen})))
    for seen in on_screen:
        _readable(seen, f"the {seen['text'] or 'blank'} tab")
    for seen in off_screen:
        assert seen["hiddenBy"] is not None, (
            "the tab " + seen["text"] + " is off screen but is not inside a [hidden] section: " + str(seen))


def test_the_menu_content_panel_has_words_on_it(skinned_menu):
    """The other half of the report: the right-hand panel completely empty."""
    _readable(skinned_menu.evaluate(SEEN, "#menu-panel"), "the menu content panel")


def test_the_hud_value_boxes_still_show_their_numbers(skinned_menu):
    """The report named the HUD boxes too. They are `.glass` panels, so they stand or
    fall with the same face - this is the check that the fix reached all of them and
    not just the menu."""
    _readable(skinned_menu.evaluate(SEEN, "#hud-hp"), "the health value box")