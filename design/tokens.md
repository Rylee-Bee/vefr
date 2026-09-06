# VEFR Design Tokens

Canonical source: [Figma file](https://www.figma.com/design/kRwOoUtrZsbmB4NfQzxXNR/)

---

## Color Primitives (`VEFR Primitives` collection)

The brand ramp. These are raw values — use semantic tokens in production.

### Charcoal (backgrounds, surfaces)

| Token | Hex | RGB |
|---|---|---|
| `color/charcoal/900` | `#131311` | `19, 19, 17` |
| `color/charcoal/800` | `#1D1B17` | `29, 27, 23` |
| `color/charcoal/700` | `#2A2E33` | `42, 46, 51` |
| `color/charcoal/600` | `#3A352C` | `58, 53, 44` |
| `color/charcoal/500` | `#5A5347` | `90, 83, 71` |

### Parchment (text, foreground)

| Token | Hex | RGB |
|---|---|---|
| `color/parchment/dim` | `#A39E92` | `163, 158, 146` |
| `color/parchment/muted` | `#C2BDB0` | `194, 189, 176` |
| `color/parchment/100` | `#E8E5DF` | `232, 229, 223` |
| `color/parchment/200` | `#F5F3EC` | `245, 243, 236` |
| `color/parchment/300` | `#FFFFFF` | `255, 255, 255` |

### Gold (accent, brand)

| Token | Hex | RGB |
|---|---|---|
| `color/gold/500` | `#C9AD6B` | `201, 173, 107` |
| `color/gold/400` | `#E1C282` | `225, 194, 130` |
| `color/gold/300` | `#FFD56B` | `255, 213, 107` |

### Teal (AI, success-adjacent)

| Token | Hex | RGB |
|---|---|---|
| `color/teal/500` | `#5B8A72` | `91, 138, 114` |
| `color/teal/400` | `#6EA88A` | `110, 168, 138` |
| `color/teal/300` | `#8EC4A6` | `142, 196, 166` |

### Status Colors

| Token | Hex | RGB |
|---|---|---|
| `color/red/500` | `#B8543F` | `184, 84, 63` |
| `color/red/400` | `#D4644C` | `212, 100, 76` |
| `color/blue/500` | `#6C8AA8` | `108, 138, 168` |
| `color/blue/400` | `#8BA8C4` | `139, 168, 196` |
| `color/yellow/500` | `#C9A92E` | `201, 169, 46` |
| `color/green/500` | `#5FB85F` | `95, 184, 95` |

---

## Semantic Tokens (`VEFR Semantic` collection)

Three accessibility modes. Each maps to a primitive above.

| Token | Role | Warm & Easy | Bright & Clear | Nothing Hides |
|---|---|---|---|---|
| `color/bg` | Page background | charcoal/900 | charcoal/900 | charcoal/900 |
| `color/card` | Card/panel bg | charcoal/800 | charcoal/800 | charcoal/900 |
| `color/card-edge` | Card border | charcoal/600 | charcoal/500 | parchment/300 |
| `color/ink` | Primary text | parchment/100 | parchment/200 | parchment/300 |
| `color/ink-dim` | Secondary text | parchment/dim | parchment/muted | parchment/100 |
| `color/accent` | Gold accent | gold/500 | gold/400 | gold/300 |
| `color/church` | Recessed bg | charcoal/700 | charcoal/700 | charcoal/900 |
| `color/danger` | Destructive | red/500 | red/400 | red/400 |
| `color/teal` | AI / nature | teal/500 | teal/400 | teal/300 |
| `color/success` | Success state | green/500 | green/500 | green/500 |
| `color/ai-state` | AI working | teal/500 | teal/400 | teal/300 |
| `color/focus-ring` | Focus outline | parchment/100 | parchment/200 | parchment/300 |

### Accessibility Theme Intent

- **Warm & Easy** (default) — Soft parchment-on-charcoal. Comfortable for extended sessions. WCAG AA.
- **Bright & Clear** — Bumped contrast. For bright rooms or mild vision issues. WCAG AA+.
- **Nothing Hides** — Maximum contrast: white text, white borders, bright accents. WCAG AAA target.

---

## Spacing & Sizing (`VEFR Spacing` collection)

### Spacing Scale

| Token | Value | Use |
|---|---|---|
| `spacing/2xs` | 2px | Hairline gaps |
| `spacing/xs` | 4px | Tight internal padding |
| `spacing/sm` | 8px | Standard internal padding |
| `spacing/md` | 12px | Component padding |
| `spacing/lg` | 16px | Section padding |
| `spacing/xl` | 24px | Card/panel padding |
| `spacing/2xl` | 32px | Major section gaps |
| `spacing/3xl` | 48px | Page-level spacing |

### Border Radius

| Token | Value | Use |
|---|---|---|
| `radius/sm` | 4px | Small elements, tags |
| `radius/md` | 6px | Buttons, inputs |
| `radius/lg` | 8px | Cards, panels |
| `radius/xl` | 12px | Modals, hero cards |

### Sizing

| Token | Value | Use |
|---|---|---|
| `size/target-min` | 44px | Minimum touch/click target (WCAG 2.5.8) |
| `size/icon-sm` | 16px | Inline icons |
| `size/icon-md` | 20px | Standard icons |
| `size/icon-lg` | 24px | Prominent icons |

---

## Legacy Foundation Tokens

These were defined in an earlier design pass (`Colors`, `Spacing`, `Radius`, `Typography` collections) and are progressively being replaced by the VEFR-specific tokens above.

| Collection | Tokens | Notes |
|---|---|---|
| Colors | 21 tokens | Dark-theme foundation (deep-charcoal, surfaces, text, accents, interactive, status) |
| Spacing | 8 tokens | 2–48px scale |
| Radius | 4 tokens | 4–12px |
| Typography | 6 tokens | Font sizes (11–20px) |
