# Figma → VEFR Integration Map

How the Figma design system (this directory + the canonical Figma file)
is wired into the running engine, and where each kind of change lives.

Status: integrated on `feat/figma-theme-integration`, 2026-09-06.
Verification evidence for every claim lives in the PR description and
the ROADMAP entry for that date.

---

## Where the design lives

| Layer | File | What it holds |
|---|---|---|
| Tokens + themes | `web/vefr-theme.css` | Every Figma primitive, the three `[data-theme]` semantic themes, spacing/radius/sizing scales, component tokens, and the legacy var aliases |
| Reference mockups | `design/mockups/*.png` | The 36 exported Figma frames (desktop/tablet/mobile), copied verbatim from the design export |
| Design spec | `design/README.md`, `tokens.md`, `screens.md`, `HANDOFF.md` | The condensed Figma documentation (landed from GitHub before this integration) |
| Canonical source | [Figma file](https://www.figma.com/design/kRwOoUtrZsbmB4NfQzxXNR/) | When CSS and Figma disagree, Figma wins; update `vefr-theme.css` and this doc together |

## How the themes reach the DOM

```
prefs.js (localStorage 'vefr-prefs')
  contrast: 'm' | 'high' | 'ultra'
      |  THEME_BY_CONTRAST
      v
<html data-theme="warm" | "bright" | "max-contrast">
      v
vefr-theme.css [data-theme=...] blocks
      v  (semantic tokens)
legacy aliases: --bg --card --card-edge --ink --ink-dim --accent --church --danger --ring
      v
every pre-existing rule in index.html / board.css (unchanged names)
```

One user-facing control (the contrast select in Reading & sound)
drives both vocabularies. The Figma theme names and the pref values
map 1:1:

| Pref value | Figma theme | `data-theme` |
|---|---|---|
| `m` | Warm & Easy (standard) | `warm` |
| `high` | Bright & Clear (high contrast) | `bright` |
| `ultra` | Nothing Hides (ultra outlines) | `max-contrast` |

The legacy per-pref palette overrides were removed — their values had
drifted (the old `contrast=high` card color was accidentally
transparent, `#18161200`); the theme blocks are the single home now.

## Component mapping (Figma → CSS)

| Figma component | Implementation |
|---|---|
| Button Primary | `.btn-primary` (teal/500 fill — the mockups' Keep Idea / Play Test / Continue Building) |
| Button Secondary/Ghost | the outline anatomy (`:is(...)` rule in index.html) — the default for every button |
| Button Danger | `.btn-danger` (HANDOFF's `#6B3A3A` dim red fill) |
| Brand CTA (gold) | `.btn-gold` (gold/500 fill, dark ink) |
| NavItem | `.zone-btn` in the top bar (Play / Build / Weave) |
| ModeTab | `.tabs button` and `.zone-btn` pill restyle (radius 20px, active = card fill + edge border) |
| StatusIndicator | `.status-chip` (+ `.is-working` / `.is-warning` / `.is-down`); the top-bar engine chip is fed by the real `/api/world` round-trip |
| MessageRow | the existing whisper/NPC cards (`.card`), restyled via tokens |
| Panels/cards | `.card`, `.play-panel`, `board-*` — all token-driven |
| Empty/loading/error states | `.empty` (dashed card), `.error` (red-edged card), `#status.is-busy` (ai-state color), per the `vefr-states` frame |

Typography: Inter (`--font-ui`, self-hosted variable woff2) for UI
chrome — buttons, selects, tabs, chips, top bar. Display headings
(panel titles, prefs title) use the serif stack (`--font-display`),
matching the mockups' bookish headers. Body/reading text stays on the
prefs-driven reading font (Atkinson default — the inclusive-forward
floor is a product contract, not a style choice). Mono labels
(`--font-mono`) for the gold section markers (`URD`, `TODAY'S CAST`,
builder section heads).

## Decisions worth remembering

1. **Alias, don't rewrite.** The engine's historical var names
   (`--bg`, `--card`, ...) are kept as aliases pointing at the Figma
   semantic tokens. Every rule written before the redesign themes
   itself; there is no second palette to maintain.
2. **Teal primary, not the HANDOFF's plum.** `design/HANDOFF.md`
   specifies `#6B4A52` for the primary fill, but every rendered
   mockup shows a teal fill for primary actions. The mockups are the
   final intent; `--fill-primary` is teal/500. Documented here so the
   discrepancy doesn't get "fixed" backwards.
3. **Panel workspace, not full-bleed play.** The `vefr-play-test`
   mockup shows the renderer full-bleed with floating chrome. The
   shipped product keeps the composed/free-dock panel workspace (the
   2026-09 free-dock build) — the renderer itself is untouched and
   sits inside the themed frame.
4. **Pack neutrality holds.** The top-bar breadcrumbs take world and
   act titles from `/api/world` at runtime; no screen name is
   hardcoded. The mockups' world name belongs to the author's private
   pack and never enters engine code.
5. **Packaged file stays standalone.** `web/packaged.html` cannot
   link `/static`, so its palette is spelled out inline — values kept
   in step with `vefr-theme.css` (charcoal/parchment/gold, 4/6/8/12
   radii). Its `prefers-color-scheme: light` block is kept: it
   predates the dark-only decision and serves e-reader playback.
6. **`vefr-foundation.css` is the shared skeleton contract**, not an
   import — index.html carries its own inline copy of the same
   guarantees. Left as-is.

## Verification performed (2026-09-06)

- `uv run --group test ruff check src tests` — clean.
- `uv run --group test pytest -q` — 307 passed; the 9 failures are
  pre-existing on the base commit (the `MUNR` doc leak in
  `test_pack_neutrality`, and `test_npc_action.py` WIP that isn't
  part of this branch). Evidence and baseline run in the PR.
- Headless Chromium (kilo-browser) against the dev server:
  1440px play/build/weave zones, prefs dialog,
  tablet-width 900px, all three contrast themes, whisper round-trip —
  zero console errors, zero failed requests, zero 4xx/5xx.
- Static-asset checks: `/static/vefr-theme.css`,
  `/static/fonts/Inter-Variable.woff2` served 200.

## When you touch the design next

1. Change the Figma file.
2. Update `web/vefr-theme.css` tokens (and `web/packaged.html` values
   if a primitive changed).
3. Re-export changed frames into `design/mockups/`.
4. Update `design/tokens.md` if a token was added or renamed.
5. Run the gate: `uv run --group test ruff check src tests && uv run
   --group test pytest -q`.
