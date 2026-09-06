# VEFR — Developer Handoff

> Implementation reference for translating the Figma designs into code.
>
> **Figma source:** [Open in Figma →](https://www.figma.com/design/kRwOoUtrZsbmB4NfQzxXNR/)  
> **Token reference:** [tokens.md](./tokens.md)  
> **Screen inventory:** [screens.md](./screens.md)

---

## Table of Contents

1. [Tech Stack Assumptions](#tech-stack-assumptions)
2. [Layout Shell](#layout-shell)
3. [Responsive Strategy](#responsive-strategy)
4. [Token → CSS Mapping](#token--css-mapping)
5. [Accessibility Themes](#accessibility-themes)
6. [Typography](#typography)
7. [Component Specs](#component-specs)
8. [Iconography](#iconography)
9. [Interaction States](#interaction-states)
10. [Known Gaps & Future Work](#known-gaps--future-work)

---

## Tech Stack Assumptions

The designs are stack-agnostic, but here's what they're optimized for:

- **CSS custom properties** for all tokens (no preprocessor required)
- **Flexbox** for all layouts (the Figma auto-layout maps 1:1)
- **CSS Grid** optional for the 3-panel desktop workspace
- **`prefers-color-scheme`** is not used — VEFR is dark-only with 3 contrast modes controlled by a user setting
- **`rem`-based** sizing recommended (designs use pixel values; divide by 16 for rem)

---

## Layout Shell

Every screen shares the same shell. Only the workspace panels change between screens.

### Desktop (≥1024px)

```
┌─────────────────────────────────────────┐
│  top-bar (72px h, horizontal flex)      │
│  [logo] [breadcrumbs]    [engine-ctrls] │
├─────────┬───────────────────┬───────────┤
│  loom   │   thread-panel    │  journal  │
│  panel  │   (main content)  │  panel    │
│  280px  │   flex: 1         │  300px    │
│         │                   │           │
│  fixed  │   scrollable      │  fixed    │
│  width  │                   │  width    │
└─────────┴───────────────────┴───────────┘
```

**Top bar:**
- Height: `72px`
- Background: `var(--color-card)` → `#1D1B17`
- Padding: `12px 24px`
- Horizontal flex, vertically centered
- Bottom border: `1px solid var(--color-card-edge)`

**Workspace:**
- Horizontal flex, no gap
- Full remaining height: `calc(100vh - 72px)`
- 3 panels side by side

**Loom panel (left sidebar):**
- Fixed width: `280px`
- Background: `var(--color-card)` → `#1D1B17`
- Vertical flex, `20px` gap
- Padding: `16px`
- Right border: `1px solid var(--color-card-edge)`
- Contains: map section, NPC section, lore section

**Thread panel (center):**
- `flex: 1` (takes remaining space, ~860px at 1440)
- Background: `var(--color-bg)` → `#131311`
- Vertical flex, `16px` gap
- Contains: thread navigation (`40px`), scrollable discussion area, composer box (`56px`)

**Journal panel (right sidebar):**
- Fixed width: `300px`
- Background: `var(--color-card)` → `#1D1B17`
- Vertical flex, `16px` gap
- Left border: `1px solid var(--color-card-edge)`

---

## Responsive Strategy

Three breakpoints, progressively simplified:

| Breakpoint | Width | Layout Changes |
|---|---|---|
| **Desktop** | ≥1024px | 3-panel layout, full top bar |
| **Tablet** | 768–1023px | Single-panel workspace + floating action buttons for loom/journal + tab navigation strip |
| **Mobile** | <768px | Single-panel + bottom nav bar + horizontal scrolling tabs |

### Tablet (768px)

```
┌──────────────────────────┐
│  top-bar (72px)          │
├──────────────────────────┤
│  tabs-navigation (58px)  │
├──────────────────────────┤
│                          │
│  studio-workspace        │
│  (single panel, flex: 1) │
│                          │
├──────────────────────────┤
│  [FAB: loom] [FAB: jrnl] │  ← floating, bottom-right
└──────────────────────────┘
```

- Side panels collapse into floating action buttons (44×44px, `var(--size-target-min)`)
- Tab strip replaces breadcrumbs for screen navigation
- Content area is single-panel, full width

### Mobile (390px)

```
┌──────────────────────────┐
│  top-bar (52px, compact) │
├──────────────────────────┤
│  tabs-scroll (43px)      │  ← horizontal scroll
├──────────────────────────┤
│                          │
│  thread-panel-mobile     │
│  (flex: 1)               │
│                          │
├──────────────────────────┤
│  bottom-nav-bar (64px)   │
└──────────────────────────┘
```

- Top bar shrinks to `52px`
- Tab strip is horizontally scrollable
- Bottom navigation bar (`64px`) for primary navigation
- All side panels become full-screen overlays triggered from bottom nav

---

## Token → CSS Mapping

Map Figma variable names directly to CSS custom properties:

```css
:root {
  /* Primitives */
  --color-charcoal-900: #131311;
  --color-charcoal-800: #1D1B17;
  --color-charcoal-700: #2A2E33;
  --color-charcoal-600: #3A352C;
  --color-charcoal-500: #5A5347;
  --color-parchment-dim: #A39E92;
  --color-parchment-muted: #C2BDB0;
  --color-parchment-100: #E8E5DF;
  --color-parchment-200: #F5F3EC;
  --color-parchment-300: #FFFFFF;
  --color-gold-500: #C9AD6B;
  --color-gold-400: #E1C282;
  --color-gold-300: #FFD56B;
  --color-teal-500: #5B8A72;
  --color-teal-400: #6EA88A;
  --color-teal-300: #8EC4A6;
  --color-red-500: #B8543F;
  --color-red-400: #D4644C;
  --color-blue-500: #6C8AA8;
  --color-green-500: #5FB85F;

  /* Spacing */
  --space-2xs: 2px;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;
  --space-xl: 24px;
  --space-2xl: 32px;
  --space-3xl: 48px;

  /* Radius */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 12px;

  /* Sizing */
  --size-target-min: 44px;
  --size-icon-sm: 16px;
  --size-icon-md: 20px;
  --size-icon-lg: 24px;
}
```

### Theme: Warm & Easy (default)

```css
[data-theme="warm"], :root {
  --color-bg: var(--color-charcoal-900);
  --color-card: var(--color-charcoal-800);
  --color-card-edge: var(--color-charcoal-600);
  --color-ink: var(--color-parchment-100);
  --color-ink-dim: var(--color-parchment-dim);
  --color-accent: var(--color-gold-500);
  --color-church: var(--color-charcoal-700);
  --color-danger: var(--color-red-500);
  --color-teal: var(--color-teal-500);
  --color-success: var(--color-green-500);
  --color-ai-state: var(--color-teal-500);
  --color-focus-ring: var(--color-parchment-100);
}
```

### Theme: Bright & Clear

```css
[data-theme="bright"] {
  --color-card-edge: var(--color-charcoal-500);
  --color-ink: var(--color-parchment-200);
  --color-ink-dim: var(--color-parchment-muted);
  --color-accent: var(--color-gold-400);
  --color-danger: var(--color-red-400);
  --color-teal: var(--color-teal-400);
  --color-ai-state: var(--color-teal-400);
  --color-focus-ring: var(--color-parchment-200);
}
```

### Theme: Nothing Hides

```css
[data-theme="max-contrast"] {
  --color-card: var(--color-charcoal-900);
  --color-card-edge: var(--color-parchment-300);
  --color-ink: var(--color-parchment-300);
  --color-ink-dim: var(--color-parchment-100);
  --color-accent: var(--color-gold-300);
  --color-church: var(--color-charcoal-900);
  --color-danger: var(--color-red-400);
  --color-teal: var(--color-teal-300);
  --color-ai-state: var(--color-teal-300);
  --color-focus-ring: var(--color-parchment-300);
}
```

---

## Accessibility Themes

The three themes are **user-selectable** in the Settings screen (not system-driven).

| Theme | Target | Visual Effect |
|---|---|---|
| **Warm & Easy** | WCAG AA, comfortable extended use | Soft parchment text, muted borders, warm gold |
| **Bright & Clear** | WCAG AA+, bright rooms | Brighter text and accents, visible borders |
| **Nothing Hides** | WCAG AAA target | White text, white borders, bright gold, maximum contrast |

**Implementation:** Use a `data-theme` attribute on `<html>` or `<body>`. Store preference in `localStorage`. The Settings screen shows all three themes with live preview.

**Focus rings:** All interactive elements use `outline: 2px solid var(--color-focus-ring)` with a `2px` offset. The ring color shifts per theme to maintain visibility.

**Minimum touch targets:** All interactive elements are at least `44×44px` (`var(--size-target-min)`) per WCAG 2.5.8.

---

## Typography

One font family throughout: **Inter**.

| Use | Weight | Size | Color |
|---|---|---|---|
| Button labels | Semi Bold (600) | 15px | `var(--color-ink)` |
| Nav items | Medium (500) | 14px | `var(--color-ink-dim)` (default), `var(--color-ink)` (selected) |
| Status badges | Semi Bold (600) | 12px | Contextual status color |
| Tab labels | Medium (500) | 14px | `var(--color-ink-dim)` (inactive), `var(--color-ink)` (active) |
| Body text | Regular (400) | 14–15px | `var(--color-ink)` |
| Secondary text | Regular (400) | 13px | `var(--color-ink-dim)` |
| Captions / meta | Regular (400) | 11–12px | `var(--color-ink-dim)` |

**Line height:** ~1.4–1.5 for body text, ~1.2 for headings and labels.

**Font loading:** Use `font-display: swap`. Inter is available from Google Fonts or can be self-hosted from the `/web/fonts/` directory already in this repo.

---

## Component Specs

### Button

```css
.btn {
  height: 44px;
  padding: 12px 24px;
  border-radius: var(--radius-lg);  /* 8px */
  font: 600 15px/1 'Inter', sans-serif;
  cursor: pointer;
  transition: background 120ms ease, border-color 120ms ease;
}
```

| Variant | Background | Border | Text Color |
|---|---|---|---|
| **Primary** | `#6B4A52` (interactive/primary-fill) | none | `var(--color-ink)` |
| **Secondary** | `var(--color-card)` | `1px solid var(--color-card-edge)` | `var(--color-ink-dim)` |
| **Danger** | `#6B3A3A` (interactive/danger-fill) | none | `var(--color-ink)` |
| **Ghost** | transparent | `1px solid var(--color-card-edge)` | `var(--color-ink-dim)` |

### NavItem

```css
.nav-item {
  height: 40px;
  padding: 10px 16px;
  border-radius: var(--radius-lg);  /* 8px */
  font: 500 14px/1 'Inter', sans-serif;
  gap: 12px;  /* between icon and label */
  display: flex;
  align-items: center;
}
```

| State | Background | Border | Text Color |
|---|---|---|---|
| **Default** | transparent | none | `var(--color-ink-dim)` |
| **Hover** | `var(--color-card)` | none | `var(--color-ink-dim)` |
| **Selected** | `rgba(128, 121, 142, 0.15)` | `1px solid #80798E` | `var(--color-ink)` |
| **Focus** | transparent | `2px solid var(--color-focus-ring)` | `var(--color-ink-dim)` |

The selected state uses the lavender/purple accent (`#80798E`) at 15% opacity for the background — this is the AI/agent color, used because the selected nav item typically represents the active agent context.

### StatusIndicator

```css
.status {
  padding: 4px 8px;
  border-radius: var(--radius-md);  /* 6px */
  font: 600 12px/1 'Inter', sans-serif;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
```

| Status | Text/Icon Color | Background |
|---|---|---|
| **Online** | `#6F8A6A` (status/online) | `rgba(111, 138, 106, 0.12)` |
| **Warning** | `#C9A06A` (status/warning) | `rgba(201, 160, 106, 0.12)` |
| **Unavailable** | `#C9A06A` (status/warning) | `rgba(201, 160, 106, 0.12)` |
| **Working** | `#80798E` (status/agent-working) | `rgba(128, 121, 142, 0.12)` |

Pattern: Each status uses its color at `12%` opacity for the background chip.

### ModeTab

```css
.mode-tab {
  padding: 6px 20px;
  border-radius: 20px;  /* pill shape */
  font: 500 14px/1 'Inter', sans-serif;
}
```

| State | Background | Border | Text Color |
|---|---|---|---|
| **Active** | `var(--color-card)` | `1px solid var(--color-card-edge)` | `var(--color-ink)` |
| **Inactive** | transparent | none | `var(--color-ink-dim)` |

### MessageRow

```css
.message-row {
  padding: 16px 0;
  display: flex;
  gap: 16px;
}
```

- User messages and AI messages share the same layout structure
- Differentiated by avatar/icon and subtle background treatment
- AI messages may include code blocks, structured data, and action buttons

---

## Iconography

The designs use simple geometric icons at three sizes:

| Size token | Pixel size | Use |
|---|---|---|
| `icon-sm` | 16px | Inline with text, status indicators |
| `icon-md` | 20px | Nav items, buttons with icons |
| `icon-lg` | 24px | Prominent actions, empty states |

**Style:** Outlined/stroked, 1.5–2px stroke weight, rounded caps and joins. Monochrome — colored via `currentColor` or the semantic text color.

**Brand mark (leaf):** A stylized gold leaf at `icon-sm` (16px) in headers, `icon-md` (20px) in logos. Rendered in `var(--color-accent)`.

---

## Interaction States

General patterns used across all interactive elements:

| State | Treatment |
|---|---|
| **Default** | Base appearance |
| **Hover** | Background lightens one step (e.g., transparent → `var(--color-card)`) |
| **Focus** | `2px solid var(--color-focus-ring)` outline, `2px` offset |
| **Active/Pressed** | Background darkens slightly from hover |
| **Selected** | Distinct fill + border (component-specific) |
| **Disabled** | 40% opacity, `pointer-events: none` |

**Transitions:** `120ms ease` on background, border-color, and color. No transitions on layout properties.

**Scroll areas:** The thread/discussion panel is the only scroll area in the desktop layout. Use `overflow-y: auto` with a thin scrollbar styled to match `var(--color-card-edge)`.

---

## Known Gaps & Future Work

These items are designed but may need refinement during implementation:

| Area | Status | Notes |
|---|---|---|
| **Logo / brand mark** | ✅ Finalized | Simple gold leaf. No further iteration needed. |
| **Component variants** | ⚠️ Partial | Button, NavItem, StatusIndicator, MessageRow, ModeTab are fully spec'd. Additional components (dropdowns, modals, tooltips, form inputs) will be extracted as screens are built. |
| **Empty / loading / error states** | ⚠️ Designed | `vefr-states` frame has examples. May need refinement during implementation. |
| **Motion / animation** | 🔲 Not designed | Use `120ms ease` for micro-interactions. Page transitions TBD. |
| **Dark mode only** | ✅ Intentional | VEFR is dark-first. No light theme planned. The 3 contrast modes serve accessibility. |
| **Story export flow** | 🔲 Placeholder | Export UI exists in journal panel but flow needs detailed design. |
| **Real-time collaboration** | 🔲 Not designed | Cursor presence, live indicators TBD if multiplayer is added. |
| **Onboarding / first-run** | ⚠️ Partial | `vefr-workshop-home` serves as landing. Guided onboarding flow TBD. |

---

## Quick Reference

```
Font:           Inter (400, 500, 600)
Background:     #131311
Card:           #1D1B17
Border:         #3A352C
Text:           #E8E5DF
Text secondary: #A39E92
Accent gold:    #C9AD6B
AI teal:        #5B8A72
Danger:         #B8543F
Radius:         4 / 6 / 8 / 12
Spacing:        2 / 4 / 8 / 12 / 16 / 24 / 32 / 48
Min target:     44px
Top bar:        72px (desktop) / 52px (mobile)
Sidebar:        280px (left) / 300px (right)
Breakpoints:    <768 mobile / 768–1023 tablet / ≥1024 desktop
```
