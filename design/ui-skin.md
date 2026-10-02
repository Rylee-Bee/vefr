# UI skin: a swappable picture pack for the game's interface

Status: **loader built (2026-10-02)**. Rylee asked for "a UI pack" on 2026-10-01 and chose: parchment and carved wood; panels, buttons and tabs, bars and meters, dividers, banners and a cursor;
used as swappable CSS skin files. Build steps 4 and 5 are done; step 6, a second tiny skin, is not.

## What exists today

The woven player styles everything with CSS variables (`--glass`, `--glass-edge`, `--accent`, `--ink`, `--display`, `--read`, a light and a dark set in `web/packaged.html`) and flat panels
(`.glass`, `.gbtn`, `.gbtn--gold`). The studio already draws one panel from a picture: `web/studio.css` uses `border-image: url('/static/art/textures/carved-wood.webp') 30 round`.
So the technique is proven in this repo; the woven player just has no skin.

## The idea

A **skin** is a folder of pictures and one small file that says which picture is which part of the interface. The player bakes the skin into the woven file and applies it with CSS.
A game with no skin looks exactly as it does today. Another game swaps in its own skin by replacing the folder, with no engine change.

```
skins/parchment-and-wood/
  skin.json
  panel.webp  panel-small.webp  speech.webp  tooltip.webp
  button.webp  button-hover.webp  button-pressed.webp  button-disabled.webp
  tab.webp  tab-selected.webp  toggle-off.webp  toggle-on.webp
  bar-frame.webp  bar-fill.webp  gold-plate.webp  slot.webp  slot-hover.webp  slot-filled.webp  hotbar.webp
  divider.webp  banner.webp  corner.webp  cursor.webp  cursor-hand.webp
  parchment.webp   (a seamless texture; see below)
```

```json
{
  "name": "parchment-and-wood",
  "credit": "Rylee and Claude; Codex proofs, training: not cleared",
  "parts": {
    "panel":   {"file": "panel.webp",  "slice": 32, "fill": "parchment"},
    "button":  {"file": "button.webp", "slice": 20, "hover": "button-hover.webp", "pressed": "button-pressed.webp", "disabled": "button-disabled.webp"},
    "bar":     {"frame": "bar-frame.webp", "fill": "bar-fill.webp"},
    "cursor":  {"file": "cursor.webp", "hand": "cursor-hand.webp", "hotspot": [4, 4]}
  },
  "ink": {"on_panel": "#2B2118", "on_panel_dim": "#5A4A38"}
}
```

## How it is drawn

- **Panels, buttons, tabs** use CSS `border-image` with a slice width (nine-slice), so one small picture stretches to any size. The panel's inside is a CSS background (the seamless parchment) so text is always real HTML on a flat-enough ground.
- **Bars** are a frame picture with a clipped fill picture behind it, driven by the real number (health, light). The number is always also written as text.
- **Slots** (the five equipment slots and the bag grid) use `slot`, `slot-hover` and `slot-filled`.
- **The cursor** is a CSS `cursor: url(...)` with a hotspot, and a hand for things you can use. It never replaces the focus ring.
- The skin is baked into the woven file as data URIs (one file, offline). Each picture is small (a panel is about 96 px; the parchment is 288 px).

## Rules (this is where skins go wrong)

1. **Text is never inside a picture.** Every word is real text; pictures are only backgrounds, borders and icons.
2. **Contrast is checked, not hoped for.** `skin.json` declares the ink colours used on panels. A test measures the contrast of that ink against the panel's real average colour and fails below 4.5:1 for body text and 3:1 for large text.
3. **Focus stays visible.** A skin may add a decoration but can never remove the focus outline. Targets stay at least 44 px.
4. **Light, dark and high contrast.** The player's existing light and dark sets stay. A skin declares which it is made for; with `prefers-contrast: more` or `forced-colors`, the player falls back to the plain flat style.
5. **A bad skin is refused with a sentence.** The validator checks that every file named exists, is a webp or png, is small (a size cap per part), and that `slice` fits inside the picture.
6. **No skin means no change.** A pack with no `skin` field bakes byte-for-byte as before (the existing compatibility test).

## How the pictures are made (and the honest risk)

Codex draws sheets that are close to, but never exactly, a clean nine-slice. So the pipeline does not trust a generated border:
- A generated **panel sample** (a regular parchment panel with a carved wooden border, brass studs at the corners, an empty middle) is processed by a tool, `process_ui.py`:
  it takes the top-left corner and the top and left edge strips and **mirrors** them to guarantee a perfectly symmetric, uniform border, then fills the centre from the seamless parchment texture.
- Buttons come as four separate pictures of the same shape (normal, hover, pressed, disabled); `check_ui.py` verifies equal size, equal border width, and that the four states are visibly different.
- Textures (parchment, wood strip, brass stud) come as 3x3 grid pictures (the grid-tile trick) so they repeat without a pattern.
- **Risk (UNVERIFIED):** whether the mirrored corner of a Codex-drawn border looks right. The first panel is proof; if it does not, the fallback is to compose frames in code from the wood strip and stud.

## Build order (one foreman at a time)

| # | Task | Tag |
| --- | --- | --- |
| 1 | Approve this note | **keep** (Rylee) |
| 2 | Generate the source pictures (six batches; the orchestrator runs Codex) and show them | **keep** (Rylee picks) |
| 3 | `process_ui.py` (mirror-fix nine-slice, seamless parchment) and `check_ui.py` with synthetic-image tests | offloadable |
| 4 | The skin loader: `skin.json` validation, baking into the woven file, CSS custom properties, the compatibility test | offloadable, then **keep** (review) |
| 5 | Apply the skin to panels, buttons, bars and slots in the woven player; contrast test; browser and axe tests | offloadable, then **keep** |
| 6 | A second tiny skin (flat dark) to prove it swaps | offloadable |

## Open questions for Rylee

- Should the default engine look stay the flat glass style, with parchment-and-wood as Cottage's skin? (Recommended: yes, a skin belongs to a game.)
- Should the studio itself ever use a skin, or stay as it is? (Recommended: stay for now.)
