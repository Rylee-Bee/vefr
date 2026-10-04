#!/usr/bin/env python3
"""derive.py: make a skin's state variants from its base pictures.

  derive.tint(img, r, g, b, amount) -> Image
  derive.flip_knob(img)             -> Image
  derive.derive_one(src, out, recipe) -> Path

A skin draws each widget once and gets its other states for free: the hover
button is the button lightened, the pressed button is it darkened, a knob that
points the other way is the knob mirrored. This module is those two moves and
nothing else - there is no drawing here, no colour science, and no knobs.

`tint` blends every pixel toward (r, g, b) by `amount`: 0 is the picture
unchanged, 1 is the flat colour. Only the three colour channels move; alpha is
copied through, so a rounded corner stays rounded. The blend is computed on
integers from a 256-entry table per channel, so the same picture and the same
numbers give the same pixels every time - no dithering, no rounding that
wanders with the platform.

`flip_knob` mirrors left to right, for a toggle whose knob moves from one end
to the other.

`derive_one` is the door the kit uses: it reads `src`, applies the recipe
string the manifest names - `tint(r,g,b,amount)` or `flip-knob` - and writes
`out`, returning that path. An unknown or malformed recipe is one plain
`ValueError` sentence, never a traceback.

Output is byte-identical for the same input, recipe and destination suffix: PNG
by default, lossless WebP when the destination ends in `.webp`. Nothing
lossy, no timestamp, no seed, so re-running a skin build over an unchanged
picture leaves an unchanged file. Needs Pillow:
  uv run --with pillow python -c "import sys; sys.path.insert(0, 'tools/art'); import derive"
"""
import re
from pathlib import Path

from PIL import Image, ImageOps

# The recipe the manifest writes after "derive:".
FLIP_KNOB = "flip-knob"

# tint(r,g,b,amount). The amount is a plain decimal - no exponent, no sign -
# so the string a human reads in a manifest is the string parsed here.
_TINT = re.compile(r"^tint\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d*\.?\d+)\s*\)$")

# The modes we tint as they are; the alpha band is carried through untouched.
_RGB = ("RGB", "RGBA")

# A mode that carries transparency is widened to RGBA rather than flattened.
_TRANSPARENT = ("LA", "PA")


def _blend(value, target, amount):
    """One channel blended toward `target`, as an integer 0-255.

    `amount` is 0 to 1. Rounding half to even is Python's round() and is the
    same on every platform, which is what keeps the output byte-stable.
    """
    return max(0, min(255, round(value + (target - value) * amount)))


def _tintable(img):
    """`img` in a mode this module can tint, converted once if it must be."""
    if img.mode in _RGB:
        return img
    if img.mode in _TRANSPARENT or "transparency" in img.info:
        return img.convert("RGBA")
    return img.convert("RGB")


def tint(img, r, g, b, amount):
    """Blend every pixel of `img` toward (r, g, b) by `amount`.

    0 leaves the picture as it is, 1 is the flat colour. Alpha is copied
    through unchanged. The result has the input's size, and the input's mode
    for RGB and RGBA; any other mode is converted once to RGB or RGBA first.
    """
    img = _tintable(img)
    if not 0 <= amount <= 1:
        raise ValueError(f"a tint amount of {amount} is outside 0 to 1.")
    tables = [[_blend(v, c, amount) for v in range(256)] for c in (r, g, b)]
    bands = list(img.split())
    for index, table in enumerate(tables):
        bands[index] = bands[index].point(table)
    return Image.merge(img.mode, bands)


def flip_knob(img):
    """Mirror `img` left to right, keeping its size and its mode."""
    return ImageOps.mirror(img)


def parse_recipe(recipe):
    """The recipe as (kind, arguments), or one plain sentence as a ValueError.

    kind is FLIP_KNOB, or "tint" with (r, g, b, amount). A recipe this module
    cannot honour is refused here, once, so every door into it refuses the same
    way.
    """
    if not isinstance(recipe, str):
        raise ValueError(f"a recipe must be a string, not {type(recipe).__name__}.")
    recipe = recipe.strip()
    if recipe == FLIP_KNOB:
        return FLIP_KNOB, ()
    match = _TINT.match(recipe)
    if match is None:
        raise ValueError(f"the recipe {recipe!r} is not tint(r,g,b,amount) or {FLIP_KNOB}.")
    red, green, blue = (int(part) for part in match.group(1, 2, 3))
    if any(channel > 255 for channel in (red, green, blue)):
        raise ValueError(f"the recipe {recipe!r} has a tint channel above 255.")
    amount = float(match.group(4))
    if not 0 <= amount <= 1:
        raise ValueError(f"the recipe {recipe!r} has a tint amount outside 0 to 1.")
    return "tint", (red, green, blue, amount)


def _save(img, out_path):
    """Write `img` to `out_path`, PNG unless the name asks for WebP."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".webp":
        img.save(out_path, format="WEBP", lossless=True, quality=100, method=4)
    else:
        img.save(out_path, format="PNG", optimize=False, compress_level=6)


def derive_one(src_path, out_path, recipe):
    """Derive `out_path` from `src_path` with `recipe`; return `out_path`.

    `recipe` is the string the manifest's make names, without the "derive:"
    in front of it. The output has the input's size. Writing the same input
    with the same recipe twice produces the same bytes.
    """
    kind, args = parse_recipe(recipe)
    out_path = Path(out_path)
    with Image.open(src_path) as opened:
        opened.load()
        base = opened.copy()
    if kind == FLIP_KNOB:
        out = flip_knob(base)
    else:
        out = tint(base, *args)
    _save(out, out_path)
    return out_path
