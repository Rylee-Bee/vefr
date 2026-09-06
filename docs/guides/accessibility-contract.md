# VEFR Accessibility Contract

**Every story deserves every audience.**

Weave your world tree. An AI sits beside you — not above you — figuring
it out together. Make a story, learn something about stories, and maybe
about yourself. Then share it with anyone, anywhere.

---

## What VEFR Is

VEFR is an engine *and* a game. The building is the playing — when you're
in the map editor placing tiles, tuning the forge, peeking at how the
world's AI pipeline makes decisions, that's the game. The Norse naming runs
deep because it's woven into the mythology that matters.

Three things ship on this platform:

- **VEFR itself** — the workshop. A creative tool that's also a game. You
  weave worlds alongside an AI collaborator, and the weaving teaches you
  about story structure, AI engineering, and yourself. Three panels define
  the workspace: *The Loom* (world builder — map tiles, NPCs, lore, all
  transparent), *The Thread* (AI chat — pair-programming conversation with
  keep/try-again/discard), and *The Journal* (history — git-like but human,
  with rewind, fork, bookmark, and export-as-e-book). The palette is
  restrained — warm grays, soft cream, calm teal accent. A place you'd
  spend hours in without fatigue. Super useful, lots to find.
- **Burrito Journalism** — the engine demo. You sell breakfast burritos
  from a truck. You're good at it. You roll into a new town, people try
  your food, you get popular, you get trusted — then they start asking for
  help. Eventually you're delivering newspapers AND burritos. "The Daily
  Hash(browns)." Different locations, different game styles (Diablo-like
  dungeon, food truck sim, journalism beat), one voice, one story. Also
  there are mutant water polo players who steal a printing press because
  they think it's neat. It's weird. It's an apocalypse. It's fun. Super fun.
- **VEFR** — a personal RPG rooted in Norse myth. Crafted. Starts as a
  Castle of the Winds homage — monochrome, constrained, the UI looks like
  every RPG you've ever played. But nothing is what it seems. The HP bar
  is actually the journey phase (whispers → doubts → feared → awed). The
  inventory items have bonds, not types — "given" (it fits badly), "cold"
  (a tool that doesn't care), "found" (rare — made for waiting hands).
  The quest log is actually starred whispers — moments you chose to
  remember. The decorative runes in the corner are a live cast (what was,
  what is, what asks). As you play, as the AI learns your story, the world
  itself transforms from monochrome tradition into a colorful, living
  place that's uniquely yours. The UI blooms alongside the world — because
  the transformation IS the game. You start thinking you're the hero out
  to save the world from monsters, but the world thinks YOU are the
  monster. The real journey is learning there is good, and the old shell
  and skeleton isn't true. Crafted, old RPG that slowly gives way to a
  colorful, livid, living world.

All three share the same accessible foundation. All three feel completely
different. That's the point.

---

## Tone

The platform has a voice. Here's how it sounds.

### The AI is your pair programmer

The LLM that helps you build your game isn't a tool you command — it's a
collaborator you think alongside. The conversation is casual, back-and-
forth, two people figuring something out together.

**What this means for UI language:**

| Instead of | Write |
|---|---|
| `GENERATE WORLD` | `let's build this` |
| `EXECUTE` | `try it` |
| `REVERT TO CHECKPOINT` | `go back to when...` |
| `COMMIT` | `bookmark this moment` |
| `INSPECT PIPELINE STATE` | `see how this works` |
| `CONFIGURE PARAMETERS` | `set this up` |
| `ERROR: INVALID INPUT` | `that didn't work — want to try something else?` |

Buttons are invitations, not commands. The journal is a notebook, not
version control. The inspector is curiosity, not debugging.

### Every UI element is transparent

Each panel, knob, and setting has a way to see what it calls and what it
does under the hood. This isn't hidden developer tooling — it's part of
the game. You're learning AI engineering by building a world, and the
platform lets you peek at the wiring whenever you're curious.

### The journal is git for your story

The journal system uses git-like mechanics — rewind, fork, bookmark — but
the language stays human. You're not managing branches and commits. You're
exploring paths your story could take, bookmarking moments you want to
remember, and forking timelines to see what happens if.

---

## The Story Lifecycle

A story on VEFR doesn't end when you stop playing. It transforms.

1. **Play it.** You and the AI weave a story together — making choices,
   building the world, watching it grow.
2. **Export it.** When the story is done, export it as an accessible
   e-book. This is the Bilbo moment — closing the notebook, happy it
   happened, a little sad it's over. *"There and back again."* The e-book
   inherits the platform's accessibility: readable by anyone, on any
   device, with the same contrast/font/motion preferences baked in.
3. **Re-import it.** The exported story can be re-imported into the engine
   as a lore pack — the world you built becomes the foundation for someone
   else's story, or your own sequel. The circle closes.

Every story becomes the soil for the next.

---

## The Core Loop

Everything hangs off five beats:

**weave → play → understand → remember → grow**

Make something → play with it → understand it → remember it → grow it.

---

## Values

Before the rules, the why.

VEFR is a platform designed for anyone to tell a story. That means
the person playing — or building — could be anyone. Any background, any
identity, any body, any brain, any life situation. We don't know who's on
the other side of the screen, and we don't need to. The platform works for
them regardless.

**What this means in practice:**

- **Language is neutral and warm.** No gendered defaults. No assumptions
  about who the player is, what they look like, who they love, or what
  they've been through. When we address the player, we say "you" — and
  that "you" means whoever shows up.
- **Defaults are the inclusive floor.** The out-of-box experience isn't
  "normal mode" with accessibility bolted on. It *is* the accessible
  experience. Players opt *up* into more motion, more density, more
  complexity — never the reverse.
- **Fun is not optional.** If building with the engine doesn't feel like
  play, something is wrong. If playing a game on the engine doesn't make
  you want to keep going, something is wrong. Accessibility and joy are
  the same design goal — not competing priorities.
- **No one has to explain themselves.** The settings panel doesn't ask
  *why* you want high contrast or motion off. It just lets you set it.
  Preferences are personal — the platform respects them without
  requiring justification.

---

## Who This Is Really For

Not edge cases. Not special accommodations. Your players — and your
builders.

| Who shows up | What the platform does for them |
|---|---|
| **Someone who can't see the screen clearly** | Three contrast tiers. Luminance-only hierarchy. Screen reader structure. Nothing relies on color alone. |
| **Someone who navigates differently** | 44px targets everywhere. Full keyboard traversal. No precision requirements. Works with whatever input device they have. |
| **Someone whose brain works differently** | Motion off by default. No strobing. Short reading load. Migraine-safe palettes. Collapsed complexity with optional depth. |
| **Someone playing on the bus, in the sun, on mute** | Works on small screens. Readable in bright light. Fully playable without sound — captions and visual cues cover everything. |
| **Someone who just wants to play** | It works. Right away. Without configuration. The defaults are already good. |
| **Someone who just wants to build** | The creative tools feel like play. The AI is right there beside you. You learn by doing, not by reading docs. |

---

## The Seven Rules

Non-negotiable. Every game, every screen, every interactive element —
including the engine's own builder UI and the AI chat.

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
never required for gameplay or building.

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

Labels, instructions, and feedback in clear, warm language. Flavor text —
Norse terms in the engine, journalism jargon in Burrito, whatever vocabulary
your game invents — adds character. It's never the only path to
understanding.

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

Your choices stick — they persist across sessions, travel via shareable
URL, and always respect OS accessibility settings. Set it once, it follows
you.

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

### What Each Tier Looks Like

| Tier | Feels like | Guidance |
|---|---|---|
| **Standard** | Warm & easy. Comfortable, low-glare, readable. | ≥ WCAG AA (4.5:1 text, 3:1 UI) |
| **High** | Bright & clear. Sharper edges, stronger borders. | ≥ WCAG AAA (7:1 text) |
| **Ultra** | Nothing hides. Pure black, pure white, maximum separation. | Maximum achievable ratios |

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
6. **No justification required** — the panel doesn't ask *why* someone
   wants high contrast or motion off. It just lets them set it.

---

## Getting Started — Checklist for New Games

The foundation comes first. Your identity follows.

### Layer 1 — The Skeleton (inherited from VEFR)

Import `vefr-foundation.css` — it provides all of these out of the box:

- [ ] All interactive elements have `min-height: 44px; min-width: 44px`
- [ ] Motion defaults to `off` — verify nothing animates at default prefs
- [ ] Focus rings visible on every interactive element via `:focus-visible`
- [ ] Body font is Atkinson Hyperlegible Next with fallback stack
- [ ] All `data-prefs` CSS selectors from the engine are supported
- [ ] No player-facing text below 14px
- [ ] Captions and visual pairing on by default
- [ ] Language is neutral, warm, and assumes nothing about the player
- [ ] AI chat follows pair-programming tone — invitations, not commands

### Layer 2 — The Skin (owned by you)

- [ ] Define `--bg`, `--card`, `--card-edge`, `--ink`, `--ink-dim`,
      `--accent` in all three contrast tiers
- [ ] Define `cb-safe` palette overrides for any hue-dependent tokens
- [ ] Verify contrast ratios: standard ≥ AA, high ≥ AAA, ultra ≥ max
- [ ] Build a settings panel calling `VEFR_PREFS.set/preview`
- [ ] Make it feel like play — your identity references the foundation
      tokens, never overrides target sizes, motion defaults, or reading
      structure
- [ ] Audit all player-facing text for inclusive language — no gendered
      defaults, no assumptions about identity or ability
- [ ] Every panel has a "see how this works" path for the curious

---

*vefr — weave your world tree. every story becomes the soil for the next.*

*made with care for whoever you are, and the story only you can tell.*

---

## References

- Foundation CSS: `web/vefr-foundation.css` (shared accessible skeleton)
- Preferences: `web/prefs.js` (contract, defaults, CSS integration)
- Agent rules: `AGENTS.md` (boundary table, "Always" row)
- Burrito tokens: `burgeswe/burrito-journalism/web/design-tokens.css`
  (skin only — imports vefr-foundation.css)
- Figma source: file `J0iRc8JElLGrJkvCz6L6fk`
  - Foundation: node `16:4`
  - Burrito gameplay: node `8:4`
  - Burrito UI kit: node `8:401`
  - AI chat concept: node `20:261`
  - Roadmap: node `20:4`
  - VEFR workshop concept: node `23:4`
  - VEFR workshop concept: node `25:244`
