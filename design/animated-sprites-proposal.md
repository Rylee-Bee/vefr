# Proposal: characters that move (animated sprites)

Status: **proposed, no code written.** Pack-contract changes are ask-first; this is the ask.
Why now: the hero is one painted picture that slides from tile to tile. It never faces the way
she walks and does not feel part of the world.

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

## Validation (`norns validate`)

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

## Open choices for Rylee

1. **Directions to draw first:** all four, or left/right (mirrored) plus down? Four is the best result and
   the most art; the sheet format supports either.
2. **Frames per walk:** 4 (the sheet above) or 6 (smoother, more art).
3. **Hop feel:** a gentle hop (about 6 percent of a tile) or none (frames only).

## Not in this proposal

Attack, hurt and idle-breathing animations; per-item animation; the art itself (Cottage, in its own repo).
