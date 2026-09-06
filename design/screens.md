# VEFR Screen Inventory

Canonical source: [Figma file](https://www.figma.com/design/kRwOoUtrZsbmB4NfQzxXNR/) → **VEFR – UI Screens** page

---

## Desktop Screens (1440px wide)

### Core Application Flow (1440×1024)

| # | Frame | Description |
|---|---|---|
| 1 | `vefr-workshop-story` | Story workshop — narrative editor with AI collaboration panel |
| 2 | `vefr-world-selection` | World browser — grid of playable worlds with metadata |
| 3 | `vefr-map-editor` | Spatial map editor with toolbar and layer controls |
| 4 | `vefr-characters` | Character sheet browser with detail panel |
| 5 | `vefr-items-loot` | Item/loot catalog with filtering and detail view |
| 6 | `vefr-asset-browser-v2` | Asset library with tags, search, and preview |
| 7 | `vefr-journal-expanded` | Session journal / event log with expandable entries |
| 8 | `vefr-settings` | Preference engine (accessibility themes, controls) |
| 9 | `vefr-ai-context` | AI context inspector — shows what the AI "knows" |
| 10 | `vefr-states` | UI state demonstrations (loading, empty, error, success) |
| 11 | `vefr-responsive` | Responsive breakpoint demo (900px) |
| 12 | `vefr-play-test` | Play-test mode — live preview of the running world (1440×900) |

### Concept & Exploration Screens

| Frame | Size | Description |
|---|---|---|
| `vefr-workshop-home` | 1440×900 | Dashboard — project overview, recent sessions |
| `vefr-world-builder` | 1440×900 | World-building canvas (earlier concept) |
| `vefr-ai-builder-chat` | 1440×900 | AI chat interface for world-building |
| `vefr-asset-browser` | 1440×900 | Asset browser v1 (earlier concept) |
| `vefr-play-preview` | 1440×900 | Play preview (earlier concept) |
| `vefr-story-structure` | 1440×1100 | Story structure / arc planner |

### Foundation & Reference

| Frame | Size | Description |
|---|---|---|
| `accessible-first-foundation` | 1440×2952 | Accessibility-first design system foundation doc |
| `vefr-roadmap` | 1440×2736 | Product roadmap / contract document |
| `vefr-ai-chat-interface` | 1440×900 | AI chat UI reference |
| `vefr-workshop-concept` | 1440×1024 | Workshop concept exploration |

---

## Tablet Screens (768×1024)

| # | Frame | Description |
|---|---|---|
| 1 | `vefr-workshop-tablet` | Workshop story (responsive) |
| 2 | `vefr-map-tablet` | Map editor (responsive) |
| 3 | `vefr-assets-tablet` | Asset browser (responsive) |
| 4 | `vefr-journal-tablet` | Journal (responsive) |
| 5 | `vefr-characters-tablet` | Characters (responsive) |
| 6 | `vefr-items-tablet` | Items & loot (responsive) |
| 7 | `vefr-settings-tablet` | Settings (responsive) |
| 8 | `vefr-playtest-tablet` | Play test (responsive) |
| 9 | `vefr-worlds-tablet` | World selection (responsive) |
| 10 | `vefr-ai-context-tablet` | AI context (responsive) |

---

## Mobile Screens (390×844)

| # | Frame | Description |
|---|---|---|
| 1 | `vefr-workshop-mobile` | Workshop story (responsive) |
| 2 | `vefr-map-mobile` | Map editor (responsive) |
| 3 | `vefr-assets-mobile` | Asset browser (responsive) |
| 4 | `vefr-journal-mobile` | Journal (responsive) |
| 5 | `vefr-characters-mobile` | Characters (responsive) |
| 6 | `vefr-items-mobile` | Items & loot (responsive) |
| 7 | `vefr-settings-mobile` | Settings (responsive) |
| 8 | `vefr-playtest-mobile` | Play test (responsive) |
| 9 | `vefr-worlds-mobile` | World selection (responsive) |
| 10 | `vefr-ai-context-mobile` | AI context (responsive) |

---

## Coverage Summary

| Breakpoint | Screens | Status |
|---|---|---|
| Desktop (1440px) | 12 core + 10 concept/reference | ✅ Complete |
| Tablet (768px) | 10 responsive | ✅ Complete |
| Mobile (390px) | 10 responsive | ✅ Complete |

**Total: 42 frames** across all breakpoints and explorations.

---

## Component Library

All reusable components live on the **Components & Tokens** page:

| Component | Variants |
|---|---|
| `Button` | Primary, Secondary, Danger, Ghost |
| `NavItem` | Default, Selected, Hover, Focus |
| `StatusIndicator` | Online, Warning, Unavailable, Working |
| `MessageRow` | User, AI |
| `ModeTab` | Active, Inactive |

---

## Earlier Design Explorations (on LRW Reference page)

The first page contains 22 earlier explorations from the initial design phase, including:
- Chat states (default, code response)
- Agent states (working, input needed)
- First launch / empty states
- Projects, Models, Memory, Files, Settings screens
- System error state
- Mobile chat
- Design system reference sheet
- Workshop dashboard, active delegation, handoff note
- Verification (known-good), quiet operation
- LRW identity system
- Mobile workshop variants

These are preserved for reference but superseded by the VEFR – UI Screens page.
