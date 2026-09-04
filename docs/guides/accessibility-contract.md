# VEFR Accessibility Contract — Inclusive-Forward Design

This document formalizes the accessibility rules declared in
`AGENTS.md` into a reference that any game built on VEFR can use
as its implementation checklist. The rules are not aspirational —
they are enforced in the engine's CSS (`web/index.html`), the
preference system (`web/prefs.js`), and the agent boundary table.

## The Matrix

Every UI change must answer these:

| Rule | Implementation | Enforced by |
|---|---|---|
| **Touch targets ≥ 44×44px** | `min-height: 44px; min-width: 44px` on every interactive element. Compact density reduces padding, never hit-target geometry. | CSS anatomy rules |
| **Luminance over hue** | Luminance carries rank; hue is a tint at most. Information never conveyed by color alone. | Design review |
| **Motion OFF by default** | `prefs.motion` defaults to `'off'`. Subtle (≤200ms, color/opacity only) and full are opt-in. `@media (prefers-reduced-motion: reduce)` overrides saved prefs. | `prefs.js` + CSS |
| **Focus ring = luminance** | `--ring: var(--ink)` by default (soft white outline). Accent ring is opt-in via `prefs.focus = 'accent'`. | CSS `--ring` token |
| **Font: Atkinson Hyperlegible Next** | Default body font. OpenDyslexic, system serif, and system sans available via prefs. Self-hosted woff2 under `web/fonts/`. | `prefs.js` + CSS |
| **Plain English first** | UI labels, instructions, and error messages in plain English. Norse/flavor terms as secondary decoration only. | Design review |
| **Reading load short** | Panels collapse by default. No text walls. Details/summary for optional depth. | Design review |
| **Sound paired with visual** | Every audio event has a corresponding visual indicator. Default: `prefs.sound.pairWithVisual = true`. | `prefs.js` |
| **Captions on by default** | `prefs.sound.captions = true` by default. | `prefs.js` |
| **Minimum text size: 14px** | Player-facing text never below 14px (0.875rem). Developer/debug text may go to 12px. | Design tokens |

## The Preference System (`prefs.js`)

The engine ships a complete preference system that games inherit.
Games own their **panel UI** (the visual settings screen); the
engine owns the **preference contract** (the keys, defaults, and
CSS selectors).

### Keys and Defaults

```js
{
  textSize: 'm',           // xs | s | m | l | xl | 2xl
  spacing:  'm',           // tight | m | loose
  font:     'atkinson',    // system | atkinson | opendyslexic | serif
  contrast: 'm',           // m | high | ultra
  palette:  'standard',    // standard | cb-safe
  motion:   'off',         // off | subtle | full
  focus:    'luminance',   // luminance | accent
  density:  'comfortable', // comfortable | compact
  sound: {
    effects: 0.7,
    speech: 0.8,
    ambience: 0.5,
    pairWithVisual: true,
    captions: true
  }
}
```

### How It Works

1. `prefs.js` loads saved preferences from `localStorage` (key:
   `vefr-prefs`), merging with defaults so new keys land safely.
2. It writes a `data-prefs` attribute to `<html>` as a
   semicolon-delimited token string (e.g.
   `text=m;space=m;font=atkinson;contrast=m;...`).
3. CSS selectors key off this attribute (`html[data-prefs~="..."]`)
   to apply each setting — no JS state-reading required in the
   stylesheet.
4. Games call `VEFR_PREFS.set({ contrast: 'high' })` to persist,
   `VEFR_PREFS.preview({ contrast: 'high' })` for live preview
   without persisting.

## The Three Contrast Tiers

Games must define their own color values for each tier using the
same CSS custom property names. The prefs engine applies the tier;
the game's tokens decide what it looks like.

### Token Structure (required)

```css
:root {
  --bg:        /* canvas background */;
  --card:      /* panel surfaces */;
  --card-edge: /* borders, dividers */;
  --ink:       /* primary text */;
  --ink-dim:   /* secondary text */;
  --accent:    /* primary accent color */;
}

html[data-prefs~="contrast=high"] {
  /* Higher contrast values — same token names */
}

html[data-prefs~="contrast=ultra"] {
  /* Maximum contrast: often pure black/white */
  /* border-width: 2px, font-weight: 550 */
}
```

### VEFR Engine Defaults (sample-world)

| Token | Standard | High | Ultra |
|---|---|---|---|
| `--bg` | `#131311` | `#0D0D0B` | `#000000` |
| `--card` | `#1D1B17` | `#161412` | `#000000` |
| `--card-edge` | `#3A352C` | `#5A5347` | `#FFFFFF` |
| `--ink` | `#E8E5DF` | `#F5F3EC` | `#FFFFFF` |
| `--ink-dim` | `#A39E92` | `#C2BDB0` | `#E8E8E8` |
| `--accent` | `#C9AD6B` | `#E1C282` | `#FFD56B` |

### Burrito Journalism Example

| Token | Standard | High | Ultra |
|---|---|---|---|
| `--bg` | `#1B1F22` | `#0D0D0B` | `#000000` |
| `--card` | `#252A2E` | `#161412` | `#000000` |
| `--card-edge` | `#3D4247` | `#5A5347` | `#FFFFFF` |
| `--ink` | `#EDE6D9` | `#F5F3EC` | `#FFFFFF` |
| `--ink-dim` | `#A8A29E` | `#C2BDB0` | `#E8E8E8` |
| `--accent` | `#D97706` | `#FFB833` | `#FFD56B` |

## Colorblind-Safe Palette

The `cb-safe` palette variant shifts hue-dependent distinctions to
luminance-equivalent alternatives for common forms of CVD. Games
define their own `cb-safe` overrides:

```css
html[data-prefs~="palette=cb-safe"] {
  /* Shift any color that relies on hue alone for meaning */
}
```

The engine's own cb-safe rules handle phase colors (awed/feared)
and bond colors. Games add their own for game-specific hue use.

## Building a Settings Panel

The engine provides the preference contract. Each game builds its
own settings panel with its own visual identity. The panel must:

1. **Show every preference key** — don't hide options, let the
   player decide what they need.
2. **Use `VEFR_PREFS.preview(patch)` on drag/change** — live
   preview without persisting.
3. **Use `VEFR_PREFS.set(patch)` on commit** — persist and notify.
4. **Respect 44px targets** — every control in the panel itself
   must meet the same accessibility rules it configures.
5. **Default to the inclusive floor** — the panel opens showing
   the current saved state, not the "normal" state.

## Checklist for New Games

When building a new game on VEFR:

- [ ] Define `--bg`, `--card`, `--card-edge`, `--ink`, `--ink-dim`,
      `--accent` in three contrast tiers
- [ ] Define `cb-safe` palette overrides
- [ ] Set `min-height: 44px; min-width: 44px` on all interactive
      elements
- [ ] Use `font-family: 'Atkinson Hyperlegible Next', Georgia, serif`
      as the body default
- [ ] Support all `data-prefs` CSS selectors from the engine
- [ ] Build a settings panel calling `VEFR_PREFS.set/preview`
- [ ] Verify no text below 14px in player-facing UI
- [ ] Verify contrast ratios: standard ≥ AA (4.5:1), high ≥ AAA
      (7:1), ultra ≥ AAA with max legibility
- [ ] Test with `motion=off` — nothing should animate
- [ ] Ship with `motion: 'off'` as the default

## References

- Engine CSS: `web/index.html` (the `:root` and reading-row rules)
- Preferences: `web/prefs.js` (the contract and defaults)
- Agent rules: `AGENTS.md` (the boundary table, "Always" row)
- Burrito tokens: `burgeswe/burrito-journalism/web/design-tokens.css`
- Figma source: file `J0iRc8JElLGrJkvCz6L6fk`
