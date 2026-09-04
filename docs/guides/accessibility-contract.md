# VEFR Accessibility Contract

**Every story deserves every audience.**

We build the bones so anyone can play. Then we make it look incredible.

Accessibility is not a feature of the VEFR platform. It is the architecture —
the skeleton that every game inherits before a single brand color is chosen.
Visual identity is the skin: the colors, textures, type personality, and
decorative weirdness that make each game feel like *itself*.

This document is the platform contract. Every game built on VEFR — Burrito
Journalism, MUNR, whatever you build next — gets these structural guarantees
for free. Your job is to make it yours without breaking them.

---

## Who This Is For

These are not edge cases. These are your players.

| Audience | What the platform guarantees |
|---|---|
| **Low vision & blind** | High contrast tiers, screen reader semantics, luminance-only hierarchy. Information never conveyed by color alone. |
| **Motor & mobility** | 44px minimum targets on every interactive element. Keyboard-first navigation. No precision requirements. |
| **Neurological & cognitive** | Motion OFF by default. Reduced visual complexity. Short reading load. Migraine-safe palettes. No strobing or flashing. |
| **Situational & environmental** | Works on small screens. Works in bright sunlight (high contrast). Works without sound (captions + visual pairing). |

---

## The Seven Rules

Non-negotiable. Every game, every screen, every interactive element.

### 1. Targets ≥ 44px

Every button, tab, toggle, link, and input has a minimum hit target of
44×44px. Compact density mode makes things *look* tighter — it never shrinks
what your finger or keyboard can reach.

```css
button, [role="button"], .tab, .toggle, select, input { min-height: 44px; min-width: 44px; }
```

### 2. Luminance Carries Rank

Your hierarchy is built from light and dark, not color. Hue adds
personality — it never carries meaning. A player with any form of color
vision reads the same hierarchy you designed.

### 3. Motion OFF by Default

`prefs.motion` defaults to `'off'`. Nothing moves until the player says so.
Subtle mode (≤200ms, color/opacity only) is the first opt-in. Full motion is
never required for gameplay.

The OS `prefers-reduced-motion: reduce` is the final word — it overrides
everything, always.

### 4. Text ≥ 14px

Player-facing text never drops below 14px. Body default is 16px. Debug text
can go to 12px. The type scale responds to player preferences from `xs`
through `2xl`.

### 5. Focus Rings Always Visible

Keyboard navigation gets a clear, luminance-based focus ring on every
interactive element. 2px solid, 2px offset. Uses `--ink` by default so it
works regardless of your game's palette or the player's color vision.
Players can switch to accent-colored rings if they prefer.

```css
:focus-visible { outline: 2px solid var(--ring); outline-offset: 2px; }
```

### 6. Sound = Visual

Every audio event has a visual counterpart. Captions are ON by default.
The game is fully playable on mute. If a player turns off their speakers,
they miss atmosphere — never information.

### 7. Plain Language First

Labels, instructions, and feedback in clear English. Flavor language — Norse
terms in the engine, journalism jargon in Burrito, whatever vocabulary your
game invents — is decoration. It's never the only path to understanding.

---

## The Preference Engine (`prefs.js`)

Every player controls their own experience. You build the settings panel;
the engine handles the plumbing.

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
   space-delimited token string (e.g.
   `text=m spacing=m font=atkinson contrast=m ...`).
3. CSS selectors key off this attribute (`html[data-prefs~="..."]`)
   — no JS needed in the stylesheet.
4. Call `VEFR_PREFS.set({ contrast: 'high' })` to persist,
   `VEFR_PREFS.preview({ contrast: 'high' })` for live preview
   without saving.

---

## The Contrast Ladder

Three tiers. Your game defines its own colors using the same CSS custom
property names. The engine applies the tier; your tokens decide what it
looks like.

### Required Tokens

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
  /* Maximum contrast: pure black/white, thicker borders, heavier weight */
}
```

### What Each Tier Means

| Tier | Purpose | Guidance |
|---|---|---|
| **Standard** | Comfortable for most. Warm, low-glare, readable. | ≥ WCAG AA (4.5:1 text, 3:1 UI) |
| **High** | Sharper edges, brighter text, stronger borders. For low vision and bright environments. | ≥ WCAG AAA (7:1 text) |
| **Ultra** | Maximum separation. Pure black, pure white, nothing hides. | Maximum achievable ratios |

### VEFR Engine Defaults

| Token | Standard | High | Ultra |
|---|---|---|---|
| `--bg` | `#131311` | `#0D0D0B` | `#000000` |
| `--card` | `#1D1B17` | `#161412` | `#000000` |
| `--card-edge` | `#3A352C` | `#5A5347` | `#FFFFFF` |
| `--ink` | `#E8E5DF` | `#F5F3EC` | `#FFFFFF` |
| `--ink-dim` | `#A39E92` | `#C2BDB0` | `#E8E8E8` |
| `--accent` | `#C9AD6B` | `#E1C282` | `#FFD56B` |

### Burrito Journalism

| Token | Standard | High | Ultra |
|---|---|---|---|
| `--bg` | `#1B1F22` | `#0D0D0B` | `#000000` |
| `--card` | `#252A2E` | `#161412` | `#000000` |
| `--card-edge` | `#3D4247` | `#5A5347` | `#FFFFFF` |
| `--ink` | `#EDE6D9` | `#F5F3EC` | `#FFFFFF` |
| `--ink-dim` | `#A8A29E` | `#C2BDB0` | `#E8E8E8` |
| `--accent` | `#D97706` | `#FFB833` | `#FFD56B` |

---

## Colorblind-Safe Palette

The `cb-safe` palette shifts hue-dependent distinctions to
luminance-equivalent alternatives. Your game adds its own overrides for
any game-specific hue use:

```css
html[data-prefs~="palette=cb-safe"] {
  /* Shift any color that relies on hue alone for meaning */
}
```

The engine handles phase colors (awed/feared) and bond colors. You handle
yours (e.g. Burrito's stamina bar and NPC indicators).

---

## Building a Settings Panel

The engine provides the preference contract. Your game builds its own
settings panel with its own personality. The panel must:

1. **Show every preference key** — don't hide options. Let the player
   decide what they need.
2. **Use `VEFR_PREFS.preview(patch)` on change** — live preview without
   saving.
3. **Use `VEFR_PREFS.set(patch)` on commit** — persist and notify.
4. **Respect 44px targets** — every control in the panel itself must meet
   the same rules it configures.
5. **Default to the inclusive floor** — the panel opens showing the current
   saved state, not the "normal" state.

---

## Getting Started — Checklist for New Games

The foundation comes first. Your identity follows.

### Layer 1 — The Skeleton (inherited from VEFR)

- [ ] All interactive elements have `min-height: 44px; min-width: 44px`
- [ ] Motion defaults to `off` — verify nothing animates at default prefs
- [ ] Focus rings visible on every interactive element via `:focus-visible`
- [ ] Body font is Atkinson Hyperlegible Next with fallback stack
- [ ] All `data-prefs` CSS selectors from the engine are supported
- [ ] No player-facing text below 14px
- [ ] Captions and visual pairing on by default

### Layer 2 — The Skin (owned by you)

- [ ] Define `--bg`, `--card`, `--card-edge`, `--ink`, `--ink-dim`,
      `--accent` in all three contrast tiers
- [ ] Define `cb-safe` palette overrides for any hue-dependent tokens
- [ ] Verify contrast ratios: standard ≥ AA, high ≥ AAA, ultra ≥ max
- [ ] Build a settings panel calling `VEFR_PREFS.set/preview`
- [ ] Make it look incredible — your identity references the foundation
      tokens, never overrides target sizes, motion defaults, or reading
      structure

---

*vefr — a rumor engine for playable worlds. build something worth telling.*

---

## References

- Engine CSS: `web/index.html` (`:root` tokens and accessibility rules)
- Preferences: `web/prefs.js` (contract, defaults, CSS integration)
- Agent rules: `AGENTS.md` (boundary table, "Always" row)
- Burrito tokens: `burgeswe/burrito-journalism/web/design-tokens.css`
- Figma source: file `J0iRc8JElLGrJkvCz6L6fk`, foundation node `16:4`
