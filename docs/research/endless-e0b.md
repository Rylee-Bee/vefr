# E0b: what the player can already do (read, not run)

Read 2026-10-04 on `main` after #271. Answers the UNKNOWNs in `docs/plans/endless-dungeon/PLAN.md` §3.

| Question | Answer | Where |
|---|---|---|
| Can a `requires` lock test a flag? | **Yes.** A transition opens when the named item is in the bag *or* the named flag is `true` in rules state. A missing state leaves a flag lock shut. The key is never consumed. | `web/player/parts/480-town-input-and-turns.js` `lockOpen` (~L628-641) |
| Can the player load a region not baked at weave time? | **Probably, by inserting into plain objects before `enterRegion`.** `regions = window.VEFR_REGIONS` and `transitions = window.VEFR_TRANSITIONS` are ordinary mutable objects; `enterRegion(name, at)` only needs `regions[name]`; `regionTown(name)` builds the town from `r.map/legend/pois/...`. Enemies come from a second table, `enemiesByRegion[regionName]` (`410-the-living-hazards.js` L32-54). Chests, books and POIs likely have their own per-region tables (UNKNOWN: list them in E1). | `400-setup-town-open.js` L10-45; `480` `enterRegion` ~L366 |
| Fog storage format? | `localStorage` key `vefr-fog-<world>-<region>`, a JSON **array of `"x,y"` strings** (all explored tiles). About 6-8 bytes per tile, so a fully explored 96x64 floor is ~35-45 KB. No cap. | `450-fog-of-war.js` L21-35 |
| Floor loot storage? | `vefr-floor-<world>`: one list of `{region, at, item}` for the whole world. Slain enemies are a separate list keyed `id#sig`. | `430-loot-on-the-floor.js` L1-30; `410` `loadSlain` |
| Extra move for a monster ("quick")? | UNKNOWN. Not read; E7 checks the AI loop. | |

Consequences for the plan
- E1 should replace the fog array with a bitset *before* big floors ship, and key per-floor state by the identity triple, not a region name that never repeats.
- Generated regions need a name scheme (`<section>-<cycle>-<k>`); `journalVisit` and the saves already key by region name, so names must be stable across reloads.
- Slain ids must be derived from the seed (spawn ids `m7`), or the `id#sig` list cannot match after regeneration.
