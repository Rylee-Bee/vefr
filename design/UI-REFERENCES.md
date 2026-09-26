# UI References — where this look comes from

The workshop's look is **not** a skin. It is a set of *techniques*
borrowed from games that got the material right, re-carved into
vefr's own tokens. Nothing here is vendored — no assets, no CSS
files, no fonts, no code are copied into this repo. Only ideas are
home-ported, then rebuilt from vefr-theme.css tokens and vefr's
vanilla-JS bones.

Rule that keeps this honest:

- **Port techniques, never skins.** A technique is *"chunky carved
  borders read as graspable"*. A skin is *"use their exact sprite
  sheets"*. This repo only ever borrows the first kind.
- Every source below is checked for license before a technique is
  ported. When in doubt, the technique stays generic.
- The engine never names a game. If a reference's name appears in
  this file, that is provenance for the *builder*, not content for
  the engine — it must never leak into prompts, UI copy, or tests.

## RPGUI — zlib license

- Source: <https://github.com/RonenNess/RPGUI> (zlib — free to use,
  modify, distribute, even commercially, provided the notice stays).
- What we port: the **material grammar** — bevelled/bevel-plus
  borders, inset surfaces, and progress treatments that read as
  carved wood and worked metal rather than flat rectangles. In vefr
  these become border-radius pairs (asymmetric, hand-made feel),
  inset `box-shadow` highlights, and the gold/brass token treatments.
- What we do not port: the asset sheets, the kit's own class names,
  its layout system.

## A Dark Room — MPL-2.0

- Source: <https://github.com/doublespeakgames/adarkroom> (MPL-2.0 —
  file-level copyleft; we borrow philosophy, no files).
- What we port: the **no-chrome, in-world voice**. The conviction
  that a text game's interface should be a place ("the fire is
  dying", not "⚠ HP LOW") — status as narration, hierarchy expressed
  by what's *said*, not by layout chrome. vefr's mood-note, lantern
  (the storyteller's reachability, in words), and resident greetings
  are this idea in our own iron and wood.
- What we do not port: its code, its prose, its setting.

## Twine / SugarCube themes — license varies per theme

- Source: <https://twinery.org> / <https://www.motoslave.net/sugarcube/2/>
- What we port: the **story-game text discipline** — long-form text
  as the primary interface, semantic affordances that read as part
  of the story, whitespace as rhythm. The idea that a "button" can
  be a carved word.
- Legal caution: each Twine/SugarCube theme has its own license.
  **Check the theme's license before porting anything from a
  specific theme.** Generic ideas (asymmetric corners, ink-on-
  parchment contrast) are fair game; specific theme code or assets
  are not. No specific theme code is currently used.

## Game UI Database — taste reference only

- Source: <https://www.gameuidatabase.com>
- What we use it for: **taste calibration** — studying how beloved
  games make inventory, dialogue, and map screens feel like places.
  Screenshots are references for *feel*, not sources of assets.
- Nothing from this site is ever copied; it is a museum, not a
  quarry.

## How a technique becomes vefr

1. A reference shows a *material truth* (carved = graspable; warm
   contrast = readable; slight rotation = human hand).
2. The truth is written as an accessibility test, not a style:
   every interactive target ≥44px, luminance over hue, plain English
   first, motion off by default.
3. The visual is rebuilt from vefr-theme.css tokens only, in
   studio.css, with the a11y floor (vefr-foundation.css) untouched.
4. If the technique can't survive step 2, it doesn't ship.

The household's faces, the room scenes, and the keepsake Hall are
vefr's own identity — informed by these references, never wearing
them.