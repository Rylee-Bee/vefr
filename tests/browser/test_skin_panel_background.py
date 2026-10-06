"""A skinned panel shows the skin's own face, not a sheet of the pack's accent.

Measured on the woven player (vefr PR 302): the skin's corner studs rewrite the player's own
`.carved::before` / `#config::before` into four corner pictures, spread over the whole panel. They set
the picture longhands and leave `background-color` alone - and the player's own rule for those
pseudo-elements (web/player/parts/020-style.css) paints a 6 px dot with the `background` SHORTHAND,
which leaves the background-colour set to the pack's accent. A panel-sized pseudo-element with an
accent background paints a full sheet of accent over the panel.

Measured at the centre pixel of the open menu: parchment 230,199,146 before PR 302, teal 63,126,132
after. It reproduces with a plain skin that carries neither fonts nor a backdrop, and forcing the
panel's own background to another colour changed nothing, which pinned it to the pseudo-element.

The contract:
  - a skinned panel's `::before` and `::after` have a transparent background-COLOR: the studs are
    pictures at the four corners and nothing else;
  - the corner pictures stay (they are the part the skin shipped);
  - the panel's middle is the panel's own face: nothing sits over the middle of it.

Uses the same skin fixture the engine's own skin tests use (tests/fixtures/make_skin_pack.py, the
`build_parts` skin carrying every part the contract names, `corner` among them) and weaves it the
same way, so the page under test is the one the rest of the skin suite already describes.
"""

import sys
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_skin_pack as mk  # noqa: E402

# The pack's own accent, as a colour the browser hands back. The player's rule paints the
# pseudo-element's background with it, so this is exactly what floods the panel when the skin
# leaves the background-COLOR alone. `transparent` is never equal to it, in either spelling.
TRANSPARENT = ("rgba(0, 0, 0, 0)", "transparent")

# The accent the pack's own world declares, when it declares one; read from the page rather than
# hardcoded, because --accent follows prefers-color-scheme and this test does not set a scheme.
ACCENT = """() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()"""

# What a pseudo-element of a real element is, read off that element. The pseudo-element has to be
# named as getComputedStyle's second argument: a selector cannot match one.
BEFORE = """([sel, pseudo]) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const cs = getComputedStyle(el, pseudo);
  return {bgColor: cs.backgroundColor, bgImage: cs.backgroundImage,
          bgSize: cs.backgroundSize, opacity: cs.opacity, pointerEvents: cs.pointerEvents};
}"""

# The middle of the panel: its own rect, its own computed face, and whatever is on top of its
# centre. A pseudo-element is never an elementFromPoint answer, so the hit element is the panel or
# something inside it unless a real overlay element has been laid over it.
CENTRE = """(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  if (r.width < 40 || r.height < 40) return {tooSmall: true, w: r.width, h: r.height};
  const x = Math.round(r.left + r.width / 2), y = Math.round(r.top + r.height / 2);
  const hit = document.elementFromPoint(x, y);
  const cs = getComputedStyle(el);
  return {x: x, y: y, w: r.width, h: r.height,
          face: cs.backgroundColor, image: cs.backgroundImage,
          hit: hit ? (hit.id || hit.tagName.toLowerCase()) : null,
          hitInside: !!hit && (hit === el || el.contains(hit))};
}"""


@pytest.fixture(scope="module")
def woven(tmp_path_factory):
    """The sample world wearing the skin that carries every part the contract names, corner included."""
    d = tmp_path_factory.mktemp("skin-panel")
    html = d / "parts.html"
    html.write_text(cli.weave_html(mk.build_parts(d)), encoding="utf-8")
    return html


@pytest.fixture(scope="module")
def skinned_page(browser, woven):
    """The woven game, entered as a player enters it, with the menu open on its carved panel."""
    ctx = browser.new_context(viewport={"width": 1100, "height": 1400})
    page = ctx.new_page()
    try:
        page.goto(woven.as_uri())
        page.click("#ts-enter")
        if page.is_visible("#config"):     # first run asks before it plays
            page.click("#cfg-save")
        page.wait_for_function("window.VEFR_COMBAT", timeout=15000)
        page.click("#menu-open")
        page.wait_for_selector("#menu .carved", state="visible")
        yield page
    finally:
        ctx.close()


def test_the_skin_and_its_corner_studs_are_on_the_page(skinned_page):
    """The negative half first: if the sheet never landed the assertions below pass for the wrong
    reason. A skin carrying `corner` must have painted all four studs."""
    style = skinned_page.evaluate(
        "() => { const s = document.getElementById('vefr-skin-css');"
        "return s ? s.textContent : ''; }")
    assert mk.picture_uri("corner.png") in style, "the corner picture is not in the skin's sheet"
    for stud in ("::before", "::after"):
        assert f".carved{stud}" in style, f"the skin draws no {stud} rule for a carved panel"
    assert "has-skin" in (skinned_page.evaluate("() => document.body.className")
                          + skinned_page.evaluate("() => document.documentElement.className"))


def test_the_corner_studs_keep_a_transparent_background(skinned_page):
    """The four studs are four corner pictures and nothing else. The player's own rule paints those
    pseudo-elements with the `background` shorthand, so the accent stays in the background-COLOR
    unless the skin's rule clears it - and a panel-sized pseudo-element with an accent background
    is a sheet of accent over the whole panel."""
    accent = skinned_page.evaluate(ACCENT)
    assert accent, "the page has no --accent for the player's own studs to have used"
    for panel in ("#menu .carved", "#menu-panel"):
        for pseudo in ("::before", "::after"):
            got = skinned_page.evaluate(BEFORE, [panel, pseudo])
            assert got is not None, f"no {panel}{pseudo} on the page"
            assert got["bgColor"] in TRANSPARENT, (
                f"{panel}{pseudo} paints a sheet of {got['bgColor']} over the panel: "
                f"the pack's accent is {accent}")


def test_the_corner_pictures_are_still_there(skinned_page):
    """Clearing the background-COLOR must not clear the picture: the longhand is the fix, and the
    four corner studs still have to be drawn at the four corners."""
    for panel in ("#menu .carved", "#menu-panel"):
        for pseudo in ("::before", "::after"):
            got = skinned_page.evaluate(BEFORE, [panel, pseudo])
            assert got, f"no {panel}{pseudo} on the page"
            assert got["bgImage"].startswith("url("), (
                f"{panel}{pseudo} lost its corner pictures: {got['bgImage']!r}")


def test_nothing_sits_over_the_middle_of_a_skinned_panel(skinned_page):
    """The panel's middle is the panel's own face. If the bug ever comes back by a different route
    - an overlay element rather than the pseudo-element - something on top of the centre is what
    gives it away."""
    for panel in ("#menu .carved", "#menu-panel"):
        got = skinned_page.evaluate(CENTRE, panel)
        assert got and not got.get("tooSmall"), f"{panel} is not on screen: {got}"
        assert got["hitInside"], (
            f"something is laid over the middle of {panel}: {got['hit']} is on top at "
            f"({got['x']}, {got['y']})")