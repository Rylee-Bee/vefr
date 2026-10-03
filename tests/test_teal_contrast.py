"""Teal as text has a contrast floor; teal as a fill does not (#218).

`--teal` is the brand/AI-presence colour and is used for dots, borders and fills, where
WCAG has nothing to say. Small *text* is a different job: a 10-13px label needs 4.5:1
against its surface, and the brand step only reached 4.36 on a card. So the text uses
go through `--teal-text` (and `--teal-text-hi` on hover), which is one step up the
same ramp.

This test is the guard, so the failure cannot come back quietly:

1. every theme's `--color-teal-text` clears 4.5:1 against the surface it is drawn on,
   including the composited badge background, which is the worst case;
2. no stylesheet sets `color:` from the fill token `--teal` - text must go through
   `--teal-text`, because the fill token has no contrast floor.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "web" / "vefr-theme.css"
CSS = sorted((ROOT / "web").rglob("*.css"))

# WCAG 2.1: 4.5 for body text, 3.0 for large text. These labels are 10-13px, so
# they are body text and the floor is 4.5.
BODY_FLOOR = 4.5


def _srgb(channel: float) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _srgb(r) + 0.7152 * _srgb(g) + 0.0722 * _srgb(b)


def contrast(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def blend(fg: str, bg: str, alpha: float) -> str:
    """The effective background of a translucent fill over an opaque one."""
    f, b = fg.lstrip("#"), bg.lstrip("#")
    out = []
    for i in (0, 2, 4):
        fv, bv = int(f[i:i + 2], 16), int(b[i:i + 2], 16)
        out.append(round(alpha * fv + (1 - alpha) * bv))
    return "#{:02X}{:02X}{:02X}".format(*out)


THEME_CSS = THEME.read_text(encoding="utf-8")
RAMP = {name: value for name, value in
        re.findall(r"--color-teal-(300|400|500):\s*(#[0-9A-Fa-f]{6})", THEME_CSS)}


def _block(selector: str) -> str:
    """The declarations inside the first block whose header contains `selector`."""
    at = THEME_CSS.find(selector)
    assert at != -1, f"{selector} is not in {THEME.name}"
    return THEME_CSS[at:THEME_CSS.find("}", at)]


def _token(block: str, name: str) -> str:
    m = re.search(rf"{name}:\s*var\(--color-teal-(\d+)\)", block)
    assert m, f"{name} must come from the teal ramp, not a literal"
    return RAMP[m.group(1)]


# Each theme, and the surface its teal text is actually drawn on.
THEMES = {
    "warm (default)": (':root,\nhtml[data-theme="warm"]', "charcoal-800"),
    "bright": ('html[data-theme="bright"]', "charcoal-800"),
    "max-contrast": ('html[data-theme="max-contrast"]', "charcoal-900"),
}
# The 10px world-card badge sits on a 15%-teal wash over a card: the worst case.
BADGE_WASH = "rgba(91, 138, 114, 0.15)"


def _surface(colour_name: str) -> str:
    for name, value in re.findall(
            r"--color-(charcoal-\d+|parchment-\d+):\s*(#[0-9A-Fa-f]{6})", THEME_CSS):
        if name == colour_name:
            return value
    raise AssertionError(f"{colour_name} is not in the palette")


def test_the_teal_ramp_is_parsed():
    assert set(RAMP) == {"300", "400", "500"}, RAMP


@pytest.mark.parametrize("theme", sorted(THEMES))
def test_teal_text_clears_the_body_floor_on_its_surface(theme):
    selector, surface_name = THEMES[theme]
    block = _block(selector)
    text = _token(block, "--color-teal-text")
    card = _surface(surface_name)
    got = contrast(text, card)
    assert got >= BODY_FLOOR, (
        f"{theme}: teal text {text} on {card} is {got:.2f}:1, "
        f"under the {BODY_FLOOR} floor for 10-13px text")


@pytest.mark.parametrize("theme", sorted(THEMES))
def test_the_hover_step_is_never_dimmer_than_the_rest(theme):
    selector, _ = THEMES[theme]
    block = _block(selector)
    rest, hover = (_token(block, "--color-teal-text"),
                   _token(block, "--color-teal-text-hi"))
    assert luminance(hover) >= luminance(rest), (
        f"{theme}: hover {hover} is dimmer than the resting colour {rest}")


def test_the_10px_badge_wash_clears_the_floor_too():
    # The badge is the smallest teal text in the app and it is drawn on a
    # translucent teal wash, which lifts the effective background.
    block = _block('html[data-theme="warm"]')
    text = _token(block, "--color-teal-text")
    card = _surface("charcoal-800")
    assert BADGE_WASH in (ROOT / "web" / "screens" / "worlds.css").read_text(
        encoding="utf-8"), "the badge wash moved; update this test"
    wash = blend(RAMP["500"], card, 0.15)
    got = contrast(text, wash)
    assert got >= BODY_FLOOR, (
        f"teal text {text} on the composited badge wash {wash} is {got:.2f}:1, "
        f"under the {BODY_FLOOR} floor")


def test_no_stylesheet_sets_text_colour_from_the_fill_token():
    """`color: var(--teal)` is the bug this issue was. The fill token has no
    contrast floor, so a small label must never take its colour from it."""
    offenders = []
    for path in CSS:
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"(?<![-\w])color:\s*var\((--teal[^)]*)\)", text):
            token = m.group(1).strip()
            if token in ("--teal-text", "--teal-text-hi"):
                continue
            line = text[:m.start()].count("\n") + 1
            offenders.append(f"{path.relative_to(ROOT)}:{line} color: var({token})")
    assert not offenders, (
        "teal text must use --teal-text (it has a 4.5:1 floor); "
        "--teal is a fill colour:\n  " + "\n  ".join(offenders))


def test_the_hover_token_that_was_never_defined_is_gone():
    """`--teal-light` was used once and defined nowhere, so that hover silently
    fell back to the inherited colour. Nothing may reference it again."""
    hits = [f"{p.relative_to(ROOT)}" for p in CSS
            if "--teal-light" in p.read_text(encoding="utf-8")]
    assert not hits, f"--teal-light is referenced but never defined: {hits}"
