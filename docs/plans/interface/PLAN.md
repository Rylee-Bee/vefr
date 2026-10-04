# The in-world interface (VEFR side; direction from Rylee, 2026-10-04)

Direction and rules: Cottage `docs/plans/native-ui/PLAN.md`. Her words: everything running inside the game should be in a themed UI for that game, only real controls outside it, no literal device frame, native to the world; chosen look: **parchment and soft wood** with the **Ledger** type (Crimson Pro). This file is the engine work, kept neutral (no Cottage names); a game opts in through its skin.

## Why the HUD spills (measured 2026-10-04)
`.stage` is the whole window (`height: 100dvh`), the canvas fills it, and a map smaller than the window is centred inside with the page's dark ground around it. The HUD (`.hud--tl`, `.hud--tr`), the message panels and the action buttons are positioned against the window corners, so on a small map they sit on the dark page beside the drawn map, not on the map. My seven-size overflow check found nothing because it measured the window, not the map. (finding 3 of `docs/research/cottage-release-1-learnings.md`)

## Slices (each tests-first, foreman-built in the new `web/player/parts/`, reviewed by hand)
1. **Stage rect and HUD frame.** After every resize the camera publishes `window.VEFR_STAGE = {x, y, w, h}` (the drawn map clipped to the window) and sets CSS variables on `#stage`; a new `.hud-frame` element placed exactly on that rectangle holds the HUD, messages and controls. Parts: `440-the-camera.js` (publish), `030-shell.html` (wrap), `020-style.css` (position by the variables). Acceptance: `tests/browser/test_stage_containment.py` (written, failing) at seven sizes.
2. **A themed backdrop.** The ground outside the map inside the window takes the skin's table (wood) instead of flat black; `skin.json` gains an optional `backdrop` part (a seamless picture). No skin means today's dark ground.
3. **Bundled type, chosen by the skin.** `skin.json` may name `fonts: {display, body}` from the families the engine bundles (Cinzel, Atkinson Hyperlegible Next, and a new addition, Crimson Pro, SIL OFL). Contrast checks as for any skin.
4. **Apply the skin parts the player ignores.** `slot`, `tab`, `toggle`, `tooltip`, `speech`, `divider`, `banner`, `corner`, `gold-plate`: the pictures exist; only `panel`, `button`, `bar` and `cursor` are drawn today (`440-the-skin.js`).
5. **HUD icons and a speech box that belongs.** Small inline-SVG icons (heart, star, coin, door, bag) in `currentColor` beside the words; a portrait slot in the speech box when a speaker has one.
6. **A second skin.** The soft-wood variant (rounder pictures, quieter shadows) proves the contract and is what Cottage opts into.

## Rules that never bend
All words real text; 4.5:1 contrast (checked, not hoped); 44 px targets (the picture can be smaller than its hit area); a visible focus ring; reduced motion respected; `prefers-contrast: more` and forced colours return the plain flat style; a pack with no skin plays exactly as before (the weave digest for packs without a skin stays identical).
