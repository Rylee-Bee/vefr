# VEFR — UI/UX Design System

> *A story opens, and a world grows out of it.*

## Implementation

The code-side home of this design system is **`web/vefr-theme.css`**
(tokens, the three contrast themes, legacy aliases) plus
**[INTEGRATION.md](./INTEGRATION.md)** — the map from Figma components
to CSS, the decisions made while integrating, and the re-verification
checklist. Reference mockups for every screen live in
`design/mockups/`.

## Figma Source (canonical)

**[Open in Figma →](https://www.figma.com/design/kRwOoUtrZsbmB4NfQzxXNR/)**

The Figma file is the single source of truth for all VEFR visual design.
Everything below is a reference snapshot — when in doubt, check the file.

---

## Design Principles

| Principle | What it means in practice |
|---|---|
| **Dark-first, warm undertones** | Charcoal backgrounds with parchment text and gold accents — feels like a well-worn grimoire, not a generic dark theme |
| **Readable before clever** | Every element must be legible at a glance. Atmosphere comes from restraint, not ornament |
| **Three accessibility themes** | "Warm & Easy" (default), "Bright & Clear" (high contrast), "Nothing Hides" (maximum contrast) — all WCAG AA+ |
| **Responsive, not adaptive** | The same design language works from 390px mobile to 1440px desktop |
| **Narrative engine, not fantasy game** | Norse-literary warmth, technical precision. Not medieval fantasy branding |

---

## Brand Mark

The VEFR mark is a simple **gold leaf** (🍃) — a single stylized leaf in `color/gold/500` (`#C9AD6B`).
Used at 16–20px in the UI chrome; may be rendered larger for splash/marketing.

The mark is intentionally minimal. The product name "VEFR" does the heavy lifting.

---

## Palette

See **[tokens.md](./tokens.md)** for the full token reference.

### Primitives (brand ramp)

| Swatch | Token | Hex |
|---|---|---|
| ⬛ | `charcoal/900` | `#131311` |
| ⬛ | `charcoal/800` | `#1D1B17` |
| ⬛ | `charcoal/700` | `#2A2E33` |
| ⬛ | `charcoal/600` | `#3A352C` |
| ⬛ | `charcoal/500` | `#5A5347` |
| 🟫 | `parchment/dim` | `#A39E92` |
| 🟫 | `parchment/muted` | `#C2BDB0` |
| ⬜ | `parchment/100` | `#E8E5DF` |
| ⬜ | `parchment/200` | `#F5F3EC` |
| ⬜ | `parchment/300` | `#FFFFFF` |
| 🟡 | `gold/500` | `#C9AD6B` |
| 🟡 | `gold/400` | `#E1C282` |
| 🟡 | `gold/300` | `#FFD56B` |
| 🟢 | `teal/500` | `#5B8A72` |
| 🔴 | `red/500` | `#B8543F` |
| 🔵 | `blue/500` | `#6C8AA8` |

### Semantic Themes

Three modes map the same semantic tokens to different primitive values:

| Semantic Token | Warm & Easy (default) | Bright & Clear | Nothing Hides |
|---|---|---|---|
| `bg` | charcoal/900 | charcoal/900 | charcoal/900 |
| `card` | charcoal/800 | charcoal/800 | charcoal/900 |
| `card-edge` | charcoal/600 | charcoal/500 | parchment/300 |
| `ink` | parchment/100 | parchment/200 | parchment/300 |
| `ink-dim` | parchment/dim | parchment/muted | parchment/100 |
| `accent` | gold/500 | gold/400 | gold/300 |
| `danger` | red/500 | red/400 | red/400 |
| `teal` / `ai-state` | teal/500 | teal/400 | teal/300 |
| `focus-ring` | parchment/100 | parchment/200 | parchment/300 |

---

## Components

All components live on the **Components & Tokens** page in Figma.

| Component | Variants | Notes |
|---|---|---|
| **Button** | Primary, Secondary, Danger, Ghost | Standard action button |
| **NavItem** | Default, Selected, Hover, Focus | Sidebar navigation items |
| **StatusIndicator** | Online, Warning, Unavailable, Working | Colored dot + label |
| **MessageRow** | User, AI | Chat message container |
| **ModeTab** | Active, Inactive | Tab bar items |

---

## Screen Inventory

See **[screens.md](./screens.md)** for the full inventory.

### Desktop (1440px)

12 core screens covering the full VEFR workflow:
Workshop Story → World Selection → Map Editor → Characters → Items & Loot → Asset Browser → Journal → Play Test → Settings → AI Context → States → Responsive demo

### Tablet (768px)

10 responsive layouts:
Workshop → Map → Assets → Journal → Characters → Items → Settings → Play Test → Worlds → AI Context

### Mobile (390px)

10 responsive layouts (same screen set as tablet)

### Concept & Foundation Screens

6 additional explorations:
Workshop Home, World Builder, AI Builder Chat, Asset Browser (v1), Play Preview, Story Structure

Plus foundation references: Accessible-First Foundation system, Roadmap, AI Chat Interface, Workshop Concept

---

## Spacing & Sizing

| Token | Value |
|---|---|
| `spacing/2xs` | 2px |
| `spacing/xs` | 4px |
| `spacing/sm` | 8px |
| `spacing/md` | 12px |
| `spacing/lg` | 16px |
| `spacing/xl` | 24px |
| `spacing/2xl` | 32px |
| `spacing/3xl` | 48px |
| `radius/sm` | 4px |
| `radius/md` | 6px |
| `radius/lg` | 8px |
| `radius/xl` | 12px |
| `size/target-min` | 44px |
| `size/icon-sm` | 16px |
| `size/icon-md` | 20px |
| `size/icon-lg` | 24px |
