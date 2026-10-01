# Proposal: art a pack can bring (moving characters, its own tiles, tile variants)

Status: **approved by Rylee on 2026-10-01 with the recommendations below** (4 directions, 4-frame walks, 3 variants per surface, a gentle hop). Pack-contract changes are ask-first; this is the ask and its answer. Build order: C, then A (in parallel where the code allows), then B.
Why now: Cottage is making all its own art in its own style. Three things stop the engine from
showing it: the hero is one painted picture that slides from tile to tile and never faces the way
she walks; **ground tiles are read only from the engine's own `web/art/tiles/`** (`_tiles_for_legend`
in `src/vefr/cli.py`), so a pack cannot bring a floor of its own; and one tile per surface repeats in
an obvious grid.

## Swappable by design

Every piece is replaceable without touching the others, so the same engine can serve very different
games (a painted storybook, a 32 px pixel game, a flat-colour puzzle):

- **Sizes are pack data.** A region's contract already carries `tile` (`maplab.py` defaults it to 32);
  character size follows the sprite. Nothing here hardcodes 96 or 128.
- **Tile sets, sprite sheets and their variants come from the pack**, never from engine code; the
  engine's own `web/art/tiles/` stays the fallback so old packs are unchanged.
- **The art tool is not the engine's business.** A game picks its generator and records it in the
  credits line; the engine only reads the finished files.
- **A style belongs to one game.** Another game gets its own kit; the engine never learns a look.


## What exists today (read in `web/packaged.html` and `src/vefr/world.py`)

- Every file under a region's `sprites/` is a named sprite by convention (`_discover_sprites`:
  `{stem: path}`). The woven player bakes them as `VEFR_SPRITES` (name to image).
- `drawSprite(key, tx, ty)` draws that one picture at 1.5 tiles tall, feet on the tile's bottom.
  It does not know a direction, a frame, or a step.
- A character with no sprite keeps the drawn figure, so everything here must keep that fallback.

## Two phases

### Phase A: the engine makes one drawing feel alive (no contract change)

Engine-only, so it can ship without this proposal being approved:

- **Face the way she walks.** Left/right mirrors the single drawing; up/down keep it.
- **A short hop per step:** a small vertical bob, a slight lean into the direction, a squash on
  landing, over about 110 ms. One tile per press, and a held key repeats at that cadence.
- **Reduced motion:** `prefers-reduced-motion` turns the hop, lean and squash off; facing stays.
- Applies to every character that has a sprite (hero, people, monsters).

### Phase B: real walk cycles (the contract change)

An optional **sprite sheet** next to the picture, so old packs load unchanged:

```
sprites/hero.png            # unchanged: the single drawing, still the fallback
sprites/hero-sheet.png      # the frames
sprites/hero.sheet.json     # describes the sheet
```

```json
{
  "image": "hero-sheet.png",
  "frame": [128, 128],
  "fps": 8,
  "directions": {
    "down":  {"idle": [0],  "walk": [1, 2, 3, 4]},
    "left":  {"idle": [5],  "walk": [6, 7, 8, 9]},
    "right": {"idle": [10], "walk": [11, 12, 13, 14]},
    "up":    {"idle": [15], "walk": [16, 17, 18, 19]}
  }
}
```

- Frames number left to right, top to bottom. Any direction may be missing: a missing `left`
  or `right` is the other side mirrored; a missing `up` falls back to `down`.
- Loader: `_discover_sprites` skips `*.sheet.json`, and attaches the parsed sheet to the sprite it
  names. The woven player bakes `VEFR_SPRITE_SHEETS` (empty for every existing pack, so a pack
  without sheets bakes exactly as before).
- Player: a character with a sheet draws frame `idle` when standing and cycles `walk` as it moves
  (one step advances the cycle). No sheet: Phase A applies.
- Same size rule as now: frames are drawn 1.5 tiles tall, feet on the tile's bottom.

## Phase C: a pack brings its own tiles, with variants (the other contract change)

**Today** (read in `src/vefr/cli.py` `_tiles_for_legend`): a legend symbol resolves to
`web/art/tiles/<name>.webp` from the engine, by an explicit `"tile": "<name>"` or by a fallback
(stone-wall, rug, grass, path). A pack has no way to supply its own picture, and one symbol means one
picture, so a floor repeats in a visible grid.

**Proposed, both optional so old packs bake exactly as before:**

1. **Pack tiles.** A region may carry `tiles/<name>.webp` (or `.png`) next to `sprites/`, found by the
   same convention as sprites. A legend `"tile": "<name>"` looks in the region's `tiles/` first, then in
   the engine's `web/art/tiles/`. A pack tile with the same name overrides the studio's.
2. **Variants.** `tiles/<name>.2.webp`, `tiles/<name>.3.webp`, ... are variants of `<name>`
   (the unnumbered file is variant 1). The weaver bakes the list for that symbol.
3. **Choice is deterministic, not random:** the player picks variant `hash(x, y) mod count`, so the same
   map always looks the same, saves and screenshots agree, and tests can assert it. A symbol with
   one picture behaves exactly as today.
4. **Size:** tiles are baked as webp at 2 times the on-screen size (192 px for a 96 px tile) to keep the
   single-file build small; a processing script in the pack repo (not the engine) produces them.

Validation: a `"tile"` that names nothing in the region's `tiles/` or the engine's set is a
validation error naming the symbol (today it silently falls back to a colour).

Tests: loader finds pack tiles and variants and orders them; the weave bakes the list only when
variants exist; the player's choice is deterministic for a fixed map; an unchanged pack's baked output
is byte-identical before and after (the compatibility test).

Demo: the sample world gets two generated flat-colour variants of one floor, from a fixture script.

## Order of work

1. **Phase C first** (pack tiles and variants): without it the new floors cannot appear in a build.
2. **Phase A** (the hero feels alive, no contract change) in parallel, since it is engine-only.
3. **Phase B** (sprite sheets) once the walk-cycle art exists.

## Validation of sprite sheets (`norns validate`)

The sheet is shape-checked like everything else the validator owns: `image` exists, `frame` divides
the image size exactly, every listed frame index is in range, direction names are a subset of
`down/up/left/right`, `fps` is 1 to 24, a `walk` list has at least two frames. A bad sheet is a
validation error naming the file, never a silent fallback.

## Demo and tests

- **Sample world demo:** a tiny sheet drawn by a test fixture script (flat coloured blocks), so the
  public repo ships no art with an unclear origin and the feature is provable without any game.
- **Unit:** loader skips the sidecar and attaches the sheet; validator accepts and rejects the cases above.
- **Node-vm harness** (`tests/fixtures/dom_harness.mjs`): frame choice by direction and step.
- **Browser** (`tests/browser/`, like `test_monster_walking.py`): the hero's frame changes when she
  walks, and does not under reduced motion.
- Old packs: the existing suite passing unchanged is the compatibility test.

## Docs

A short section in `docs/guides/` for a stranger ("give a character a walk"), and a line in the
journey guide's lessons log.

## Choices (decided 2026-10-01: all recommendations accepted)

1. **Directions to draw first:** all four, or left/right (mirrored) plus down? Four is the best result and
   the most art; the sheet format supports either.
2. **Frames per walk:** 4 (the sheet above) or 6 (smoother, more art).
3. **Hop feel:** a gentle hop (about 6 percent of a tile) or none (frames only).
4. **Variants per surface:** 3 (recommended: breaks repetition, small bake) or more.

## Not in this proposal

Attack, hurt and idle-breathing animations; per-item animation; animated tiles; the art itself (Cottage, in its own repo).
