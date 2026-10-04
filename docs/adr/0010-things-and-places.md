# 0010 - Things and places: one record per thing

Date: 2026-10-04

## Status

Proposed, approved to start by Rylee on 2026-10-04 (she picked "Things and places in Blueprint" among the tightening work). Slice B0 has frozen tests; B1 to B4 are written here as the order and are built one at a time, each with its own tests first. The evidence is `docs/research/size-and-language-pass.md` (pass 3).

## Context

Adding one monster, one piece of gear, one door or one region touches 8, 6, 6 and 8 places today (a sprite file, `player.sprites`, `sprite_scale`, a family, an instance, a sticker, credits; a map glyph, a legend entry, a transition, a poi and its text; and so on). "Where" is written five ways. Blueprint (ADR 0008) already shows the cure for creatures: a short source, expanded into canonical committed files, with a lock and an exit ramp.

## Decision

Extend that one pattern, in small slices, never adding a parallel system:

- **B0, sprites by name.** A picture file `sprites/<key>.*` is the sprite named `<key>`; a key is baked when `player.sprites` lists it or when something references it (an item, an enemy, a speaker, `hero`). Unused files are not baked. No Blueprint needed; `tests/test_sprites_by_name.py`.
- **B1, things.** `blueprint.json` gains `things`: gear and items as one record each (name, slot, mods, value, `from` = the carrier instance). Expansion writes the `items` entry and the carrier's `drops`; the sprite is found by name. Owned keys follow ADR 0008's stale rule.
- **B2, places.** Per region, `places`: doors, stairs, chests, signs as `{kind, at, to, needs, text}`. Expansion writes the legend entry, the transition, the poi and its text; the map glyph is applied as an overlay rather than editing `map.md` text.
- **B3, placement sentences.** `at` may be a rule ("farthest room off the path to the stair") resolved once by `vefr normalize` with a seed and then locked, so a regenerated floor keeps its guardian and its door.
- **B4, stickers from the cast.** `album` entries may say `meet each family` and `find each thing`.

## Rules (inherited from ADR 0008, restated as checks)

Short source in, canonical files out, committed and read-only; `vefr check` rejects stale output; the lock records the source hash and normalizer version; deleting the source is the exit ramp and leaves a working pack; a pack without the new sections is unchanged byte for byte; every sentence an author sees is plain and names the record.

## Consequences

A monster takes 2 edits (art and a family), gear 2, a door 1, a region 3. The risk is a second source of truth; the stale rule and the exit ramp are the mitigation, and each slice must show the Cottage trial passing the same threshold Blueprint did (every record equal, the woven player identical).
