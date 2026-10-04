# 0010 - Things and places: one record per thing

Date: 2026-10-04

## Status

Proposed, approved to start by Rylee on 2026-10-04 (she picked "Things and places in Blueprint" among the tightening work). **Decided by Rylee on 2026-10-04 (after Opus's plan, `docs/plans/tighten-shapes/PLAN.md`):** doors, stairs and chests write their map glyphs **into `map.md`** (no weave-time overlay); **places come before things**; **placement sentences are built in this mission**, with the language kept as small as it can be (below). Slice B0 has frozen tests; the rest are built one at a time, each with its own tests first. The evidence is `docs/research/size-and-language-pass.md` (pass 3).

## Context

Adding one monster, one piece of gear, one door or one region touches 8, 6, 6 and 8 places today (a sprite file, `player.sprites`, `sprite_scale`, a family, an instance, a sticker, credits; a map glyph, a legend entry, a transition, a poi and its text; and so on). "Where" is written five ways. Blueprint (ADR 0008) already shows the cure for creatures: a short source, expanded into canonical committed files, with a lock and an exit ramp.

## Decision

Extend that one pattern, in small slices, never adding a parallel system:

- **B0, sprites by name.** A picture file `sprites/<key>.*` is the sprite named `<key>`; a key is baked when `player.sprites` lists it or when something references it (an item, an enemy, a speaker, `hero`). Unused files are not baked. No Blueprint needed; `tests/test_sprites_by_name.py`.
- **B2, places (first, format 3).** See below. Format `1` is enemies, format `3` is places, and format `2` is reserved for things (B1) and does not exist yet. A `"blueprint": 3` file is complete on its own and never waits for format 2. A format-1 pack stays unchanged byte for byte.
- **B1, things (after places).** `blueprint.json` gains `things`: gear and items as one record each (name, slot, mods, value, `from` = the carrier instance). Expansion writes the `items` entry and the carrier's `drops`; the sprite is found by name. Owned keys follow ADR 0008's stale rule.
- **B2, places.** Per region, `places`: doors, stairs, chests, signs as `{kind, at, to, needs, text}`. Expansion writes the legend entry, the transition, the poi and its text **and the glyph into `map.md`** (`map.md` is a generated surface at those tiles; the lock records their hashes).
- **B3, placement sentences.** `at` may be a short sentence instead of coordinates, resolved once by `vefr normalize` and then locked, so a regenerated floor keeps its guardian and its door. The whole language is six words, ANDed, each reading as English left to right:
  `far:ANCHOR` (the farthest from it), `near:ANCHOR`, `off:A>B` (not on any shortest route from A to B), `dead-end`, `room:N`, `x,y` (a coordinate, the only form that exists today).
  Example, a guardian: `"at": "far:up off:up>down"` = the farthest tile from the arrival stair that is not on the way to the stair down. Anchors are the names a place or poi already has (`up`, `down`, a door id, `start`). Ties break by a hash of `(seed, record id)` and never by one shared random stream, so adding a record cannot move another. The resolved coordinate is written next to the sentence in the canonical output, so the result is readable and diffable.
- **B4, stickers from the cast.** `album` entries may say `meet each family` and `find each thing`.

## Rules (inherited from ADR 0008, restated as checks)

Short source in, canonical files out, committed and read-only; `vefr check` rejects stale output; the lock records the source hash and normalizer version; deleting the source is the exit ramp and leaves a working pack; a pack without the new sections is unchanged byte for byte; every sentence an author sees is plain and names the record.

## Consequences

A monster takes 2 edits (art and a family), gear 2, a door 1, a region 3. The risk is a second source of truth; the stale rule and the exit ramp are the mitigation, and each slice must show the Cottage trial passing the same threshold Blueprint did (every record equal, the woven player identical).
