# Big generated dungeon maps — research brief

Scope: a deterministic seeded JS generator for VEFR (`src/vefr/delve.py` is Python + JS twin, no behaviour change — that constraint shapes every pick below). All verified facts are from the URLs cited; inferences are flagged **[inf]**.

A short read of the engine context first, because the constraints matter:

- **Verified:** `src/vefr/delve.py` ships a generator `generate_floor(seed, width=30, height=20, rooms=8)` (rectangular rooms, L-corridors, solid border, stairs ≥ 10 tiles apart), `generate_floor_v2` (shared-PRNG twin), one shared `prng()` (xmur3 → mulberry32, integer maths so the JS twin matches), and a parity harness (`tests/test_floor_v2_parity.py`). Validator limits are `width, height in 20..64`, `rooms in 3..16`, `floors in 1..8` (`design/random-floors.md:48`). Phase 2 of `design/random-floors.md` and phase 2 of `design/gates-and-guardians.md` are still proposed. `design/random-floors.md:41-42` says the generator must guarantee the ending is reachable on every seed.
- **Inferred** **[inf]:** the existing 30×20–64-ish envelope is too small for the Diablo/DCSS vibe Rylee described. The hard ceiling is whatever JS generates in ~100 ms and renders fast in a canvas, not the validator limits.

I'll keep the answer concise, with tables where they help. Citations are inline.

---

## 1. Large-map generation techniques

| Algorithm | Best-known use | Why it works | Failure modes | Fit for VEFR |
|---|---|---|---|---|
| **BSP** | "Basic BSP Dungeon" (RogueBasin) — classic rectangles, easy to bail | "An all-seeing dungeon architect"; clean axis-aligned rooms, deterministic partitions, easy to bound the output | Visible tree structure ("boxing"), bad for natural caves, corridors are long | Cheap to implement as a second lane; matches `norns delve` style |
| **Cellular automata (CA)** | Cave smoothing; 4-5 rule and prune | Long-tail; small change in seed → cave-like topology | Open caverns often disconnect; needs a flood-fill sweep; bad for *rooms* | Already a known shape (RogueBasin index); adds a "cave" lanes the cottage cellar doesn't have |
| **Drunkard's walk** | Cave carving; Spelunky's tunnels are a variant | Cheap, fast; great for irregular caves | Almost always disconnected; low repeatability without a fix-up pass | Cheap and fast — fits the 100 ms budget |
| **Room-and-corridor** | What we have in `delve.py` (`src/vefr/delve.py:150-179`); Common; RogueBasin | Simple, fast, readable. Each room is a node | Boring at scale (the long thin corridor problem); few landmarks | We have it. Keep it; add a lanes slot for stamped rooms |
| **Wave Function Collapse (WFC)** | mxgmn/WaveFunctionCollapse; Caves of Qud uses it for biomes and architecture (Bucklew, GDC talk) | Constraint-satisfies tile adjacencies; good when you have a small hand-authored tile set and want infinite valid maps | Contradiction on bad constraints → broad kill; non-deterministic unless you seed and order carefully (see Deterministic WFC thread) | Overkill for a 2D tiled dungeon in JS; better as an *indoor filler* once a layout exists |
| **Wang / herringbone tiles** | Noita (Stucky/Collo90) | Wisest pattern for organic tile boundaries; the editor is a tile-based biomes | Needs a fixed tile dictionary per biome; less good for hand-crafted landmarks | Useful for the *interior texture* of a section, not the room graph |
| **Dormans / mission graphs** | Unexplored (Dormans), graph grammars | A high-order abstract graph (rooms, keys, locks) is constrained separately from geometry → guarantees story and endings; gameplay is yours to design | Overkill for 1-D-path dungeons; design surface is bigger | **Use only the lock/key subgraph** (§3 below), not the full grammar |
| **Brogue** ("room accretion") | Walker, talk at Roguelike Celebration 2018 | Rooms are placed by accretion around an existing structure; multiple room shapes (overlapping rectangles, CA blobs, circles, cross) | Hard to bound shape, easy to leak into disconnects | Different vibe from Cottage; take the **room-shape menu** idea (4 shapes) |
| **DCSS vaults + Lootfill** | crawl/crawl; "randomly generated maps, known as vaults" | Hand-made tiles authored, then placed into generated space; Lootfill pre-fills layouts to ensure loot density | Lootfill pass is what most engines skip | Use the *vault + Lootfill pattern* (anchors + fill) |
| **Diablo 2 DS1/DT1 presets** | Diablo 2 / d2-ds1-edit; Diablo Wiki | The level grid is built from a finite set of small DS1 "preset" rooms with edge-matching tiles; the engine stitches presets along matching borders | The hidden file `ld1.ds1` exists; "diablo II's lost maps" are exactly 9 presets | The **closest analogue** for hand-painted stamps + stitching |
| **Tiny Keep** | gamedeveloper.com; gist samjaninf | Rectangular rooms around a centre cell, no overlap; corridors by A* | Small rooms only; one algorithm | Not a fit |
| **Castle of the Winds** | Reddit thread1s838tf | Spine path + rooms off the spine | Tree feel; no loops | Use the **spine** idea for the section map (§5) |

Sources:
- BSP: https://www.roguebasin.com/index.php/Basic_BSP_Dungeon_generation
- CA: https://blog.jrheard.com/procedural-dungeon-generation-cellular-automata ; https://rogueliketutorials.com/tutorials/tcod/2019/part-3/
- Drunkard: https://blog.jrheard.com/procedural-dungeon-generation-cellular-automata- Room-and-corridor ("Rooms and Mazes"): https://journal.stuffwithstuff.com/2014/12/21/rooms-and-mazes/
- Brogue: http://anderoonies.github.io/2020/03/17/brogue-generation.html ; https://brogue.fandom.com/wiki/Level_Generation
- WFC: https://github.com/mxgmn/WaveFunctionCollapse ; https://gdcvault.com/play/1026263/ ; https://gamedev.stackexchange.com/questions/188719/deterministic-procedural-wave-function-collapse
- Noita/Wang: https://nothings.org/gamedev/herringbone/herringbone_tiles.html ; https://noitagame.com/
- Dormans: https://www.gamedeveloper.com/design/unexplored-s-secret-cyclic-dungeon-generation- ; https://www.boristhebrave.com/2021/04/02/graph-rewriting/
- DCSS: https://github.com/crawl/crawl ; https://crawl.develz.org/wordpress/behind-the-scenes-on-retrofitting-dcss-seeding
- Diablo 2 presets: https://www.boristhebrave.com/2019/07/14/dungeon-generation-in-diablo-1/ ; https://diablo-archive.fandom.com/wiki/Area_Size_(Diablo_II) ; https://github.com/bethington/d2-ds1-edit
- Tiny Keep: https://www.gamedeveloper.com/programming/procedural-dungeon-generation-algorithm ; https://gist.github.com/samjaninf/bc927ed97485c0057b8ed696961f17fe
- Castle of the Winds: https://www.reddit.com/r/CastleOfTheWinds/comments/1s838tf/dungeon_generation_method/ ; https://www.roguebasin.com/index.php/Castle_of_the_Winds
- Survey: https://www.sbgames.org/sbgames2019/files/papers/ComputacaoFull/198359.pdf
- Cogmind: https://www.gridsagegames.com/blog/2014/06/procedural-map-generation/ ; https://www.gridsagegames.com/blog/2019/03/roguelike-level-design-addendum-procedural-layouts/
- Caves of Qud WFC: https://www.youtube.com/watch?v=AdCgi9E90jw ; https://aidanpage.medium.com/generating-anything-and-everything-in-caves-of-qud-d6336e9afda0

**[inf]:** for VEFR the highest-value combinations are *room-and-corridor (we already have it) + authored stamp placement (Diablo 2 / DCSS)* with an *optional WFC filler inside rooms*. Brogue's room accretion is the next-most interesting if we ever want caves. BSP is the boring default of every other roguelike; skip it.

---

## 2. Hand-painted prefab / vault / stamp systems

| System | What the unit is | How it integrates | Source |
|---|---|---|---|
| **Diablo 2 presets (DS1)** | A small fixed-size grid of tiles (`.ds1`); tiles come from a tileset (`.dt1`). The level is `lvl-presets` stitched along edges. | Presets declare "edge types" so the engine can match border tiles when joining two presets. Nine presets in D2 per area | https://diablo-archive.fandom.com/wiki/Area_Size_(Diablo_II) ; https://www.boristhebrave.com/2019/07/14/dungeon-generation-in-diablo-1/ |
| **DCSS vaults (.des)** | A hand-made rectangular tile-grid map with `SUBST`/`TILE` macros for substitution; Lua entry header controls min/max depth, weights, weights per branch | The level builder picks a vault that fits (size, tags), then places other vaults touching along `:`-marked edges; one or more is forced to contain the upstairs, downstairs, and any keys to `targetX` | https://github.com/crawl/crawl ; http://crawl.chaosforge.org/The_Vaults |
| **Brogue "blueprints" / reward rooms** | Templates that compose into a room; "the algorithm's central conceit is to start with a structure (a single room), then continuously generate rooms and slap it onto the structure" | Rooms have doorways with explicit facing; the placer only places a room whose doorway faces existing dungeon space and whose interior doesn't overlap | http://anderoonies.github.io/2020/03/17/brogue-generation.html ; https://brogue.fandom.com/wiki/Level_Generation |
| **Spelunky room templates** | Each "level" is a 4×4 grid of 16 "rooms"; each room is 10 wide × 8 tall, with 8 entrances | First a path from entrance to exit is laid, then room templates are instantiated along the path; remaining slots fill from a pool of "off-path" rooms | http://tinysubversions.com/2009/09/spelunkys-procedural-space/index.html ; https://spelunky.fandom.com/wiki/Level_Generation/2 ; https://www.pcmag.com/news/how-spelunky-made-procedural-generation-fun |
| **Noita biomes (Wang + pixel scenes)** | Biomes are random-pseudorandom with tiles | Tiles are edited per biome; pixel scenes are pre-baked pixel regions in larger maps | https://noita.fandom.com/wiki/World_generation ; https://noita.wiki.gg/wiki/Documentation:_Biome |
| **Sigil of Kings prefabs** | Hand-made prefabs; "placement algorithm demonstrated to work on a number of simplistic layouts (rectangular room, rectangular cave)" | A prefab has named anchor points; the placer fits prefabs to anchors the generator just placed | https://byte-arcane.github.io/sigil-of-kings-website/2023/02/16/procedural-prefab-generation-part-2/ |
| **Dungeon of the Endless rooms** | Modular rooms from a set; doors, stairs | 2D grid, modular tiles, room exit/entry anchors | (industry reference; no single URL — used to anchor the door/anchor idea below) |

Common pattern across all of these:
- **Stamps are anchored** at a small set of named points (entrance/exit door, sometimes a *target* — a quest item, a key).
- **Doors/edges are typed**, so the placer only joins stamps whose edge types match.
- **Stamps are constrained by depth** ("min depth: 5", "weight per branch").
- **The downstairs, the upstairs, and any keys-to-locks are *placed* in named vault anchors** so the level is solvable; everything else is filler.

For VEFR, the cleanest model is **DCSS .des minus Lua**: a small stamp JSON with a `tiles` row grid, `at` anchors (one of them named `down`, one `up`, one `guardian`), and a `depth` band. Anchor on the *grid glyph* not the *coordinate*, so a stamp can be flipped/rotated.

---

## 3. Connectivity, reachability, "winnable" progression

**Verified best practice**: solve the *mission graph* (which room holds which key) before you solve the *level layout*. The layout is a constraint, not the source of truth.

- **Dormans** *(Unexplored / cyclic dungeon generation)*: a graph grammar generates a *mission graph* (cycles, lock/key pairs, optional branches). The level geometry is then stitched to that graph. The graph itself is the solver's input; you can read "is there a key for X?" off it.
  - https://www.gamedeveloper.com/design/unexplored-s-secret-cyclic-dungeon-generation-
  - https://www.boristhebrave.com/2021/02/27/lock-and-key-dungeons/
  - https://www.boristhebrave.com/2021/04/10/dungeon-generation-in-unexplored/
- **Brogue**: `reward room`s are *locked* with an iron door; the matching `key holder` is on the same floor (altar in secret room, altar in a known area, statue in a maze, item on the floor). "Levels in Brogue often have a treasure room protected by a key somewhere else on the same level."
  - https://brogue.fandom.com/wiki/Reward_room ; https://brogue.fandom.com/wiki/Key_Holder ; https://brogue.fandom.com/wiki/Altar
- **DCSS**: vault layout guarantees the downstairs/upstairs and key placement. Vaults declare tags (`place: Traps`, `miniboss`) and the level builder meets those *obligations*.
- **Generic lock-and-key** (cxong, shaggydev): "Start with an open area; randomly place rooms around the place; randomly lock some rooms, and place keys in the rooms."
  - https://cxong.github.io/2021/02/bsp-lock-and-key ; https://shaggydev.com/2021/12/17/lock-key-dungeon-generation/
- **Measurable fun** (RogueBasin, "Creating Measurably 'Fun' Maps"): measure how much of a floor the player is *forced* to explore, place rewards/keys to raise it. Direct quality bar.

For VEFR the win is to keep what `design/gates-and-guardians.md` already specifies (every floor has a Keybearer; the key is `requires` on the next stair) but *add a build-time reachability sweep* over a fixed seed list that asserts the Keybearer and the key are both on a reachable tile. **No generator may starve the floor that carries the key.** This rule is already in `design/random-floors.md:42` ("the generator must still guarantee the ending is reachable on every seed").

**[inf]:** for *quality* (dull-but-solvable vs fun-but-solvable) the cheapest big lever is points-of-interest density, not more graph machinery.

---

## 4. Scale — how big is "big"?

A spectrum of real sizes, verified:

| Game | "Big" map | Source |
|---|---|---|
| **Diablo 1** | Fixed 40×40 tile grid per level | https://www.boristhebrave.com/2019/07/14/dungeon-generation-in-diablo-1/ |
| **Diablo 2** | DS1 grids are typically dozens of tiles per side; presets are smaller. Maps "are larger and more complicated" on Nightmare and Hell (player reports) | https://diablo-archive.fandom.com/wiki/Area_Size_(Diablo_II) ; https://www.reddit.com/r/diablo2/comments/1ny4dd7/ |
| **DCSS** | Standard ASCII view fits 80×24 (one screen); full levels larger; Lair/Slime/Pit are big | https://www.reddit.com/r/dcss/comments/rdhhhp/transcending_80x24_smaller_map_grids/ |
| **Brogue** | "Cross rooms: shorter dimension 3–12 wide, 2–5 high; corridors 5–15 wide / 2–10 tall" — per-room budget. Levels are ~25–80 rooms | https://brogue.fandom.com/wiki/Level_Generation |
| **Cogmind** | "The largest main maps in Cogmind are giant 200×200 squares" | https://www.gridsagegames.com/blog/2019/03/roguelike-level-design-addendum-procedural-layouts/ |
| **Caves of Qud** | World map is 240 zones wide × 75 zones tall; each zone is 80×25 tiles | https://kernelmethod.org/notes/qud_worldmap/ |
| **Dwarf Fortress** | "Max size world map is 256×256 squares, each regional square is 16×16, each square on the regional map is 48×48 squares" | https://www.reddit.com/r/dwarffortress/comments/na2fz/ ; https://dwarffortresswiki.org/index.php/DF2014:Tile |
| **Minecraft chunk** | 16×16 portion of a world | https://minecraft.fandom.com/wiki/Chunk |
| **Castle of the Winds** | "Creates the first room near the center; creates a 'spine' path left and right OR top and bottom" | https://www.reddit.com/r/CastleOfTheWinds/comments/1s838tf/dungeon_generation_method/ |

Memory budgets for VEFR (browser, canvas) **[inf]:**
- One floor at 80×80 × 4 bytes = 25.6 KB raw; at 200×200 ×4 bytes = 160 KB. Even 10× the size fits in modern localStorage with no trouble.
- The hard limit is *what renders fast*. Drawing40 000 tiles every frame is fine; drawing 40 000 tiles with per-frame compositing isn't.

Two patterns to choose between:

- **Fixed big floor** (Cogmind, DCSS, Diablo): generate one 200×200-ish grid per floor. Simpler save (the floor is the unit), simpler fog of war (one bit per tile), simpler stamp placement. Memory is higher than a small floor.
- **Chunked / streamed** (Minecraft): a map is 16×16 chunks. Chunks are loaded/unloaded based on player position. Used when the world is effectively infinite. The save is per-chunk, blocks themselves are derived from seed+coords; saves store only what changed.
  - https://minecraft.fandom.com/wiki/Chunk ; https://floreauluca.github.io/blogposts/chunk-generation

For VEFR: **fixed big floor (one floor per generation)**, because we already say "dungeon of generated floors cut into sections of 8–11 floors" (`design/random-floors.md` + brief). The current `generate_floor` takes `width, height` and the validator already accepts up to 64 — push it to ~120×120 max for section floors **[inf]**, and keep40×40 for ordinary floors. Save stores the `(run seed, floor number)` and only the *deltas* (broken walls, opened chests, picked-up items). This is the path Cogmind/DCSS/Diablo 2 took.

Fog of war: classic pattern is one bit per tile ("explored") plus one bit per tile in the visible radius ("visible"). Both are per-floor, so the save grows with floors-explored, not with map size.

Sources:
- Diablo 2 / DS1: https://diablo-archive.fandom.com/wiki/Area_Size_(Diablo_II) ; https://www.reddit.com/r/diablo2/comments/1ny4dd7/comparison_of_maps_size_in_3_difficulties/
- Cogmind 200×200: https://www.gridsagegames.com/blog/2019/03/roguelike-level-design-addendum-procedural-layouts/
- Caves of Qud 240×75 zones of 80×25: https://kernelmethod.org/notes/qud_worldmap/
- Dwarf Fortress 256×256: https://www.reddit.com/r/dwarffortress/comments/na2fz/how_big_are_the_maps_exactly/
- Minecraft chunk: https://minecraft.fandom.com/wiki/Chunk
- Fog of war: https://www.reddit.com/r/roguelikedev/comments/1lh7la8/simple_vs_complex_fog_of_war/ ; https://www.gridsagegames.com/blog/2013/11/fog-war/

---

## 5. Pacing and fun at scale

Why big empty maps are boring (the rule): *landmarks > size*. Real example: "Cogmind's largest main maps are giant 200×200 squares with great freedom in terms of mobility and player options" — and they still pack landmarks (POIs, Garrison Access, key NPCs).

Concrete patterns that work in our brief's games:

- **Jaquaying the dungeon** — multiple entrances, loops, secrets. Verified pattern.
  - https://bumblingthroughdungeons.com/jaquaying-a-dungeon/
  - https://pathikablog.com/2025/04/26/how-jennell-jaquays-evolved-dungeon-design-part-1-pre-jacquays-dungeons/
- **Stardew Valley mines** — elevator every 5 floors; per-5-floor `multiplier` on ore; *infested floors* (slime, no rocks, clear all to ladder); *monster floors*; *special floors* (Prismatic Slime); *skull cavern* (endless).
  - https://stardewvalleywiki.com/The_Mines
  - https://stardewvalleywiki.com/Skull_Cavern
  - https://www.bisecthosting.com/blog/stardew-valley-mine-guide-floors-enemies-loot
  - Verified: "Each time you go down 5 levels the elevator dings. You can then use the elevator to go to floors you have been to but only in multiples of 5."
- **Stardew Skull Cavern**: endless; "the deepest floor you can reach in the skull cavern is… 2,147,483,647" (int32 max). "Just can't do deeper, no ladder, shaft."
  - https://www.reddit.com/r/StardewValley/comments/k1emzk/skull_cavern_depth_and_its_horrifying_implications/
- **Auto-map** (DCSS, Brogue, Cogmind) — minimap, magic mapping scrolls. "Autoexplore and item identification are discussed as player-facing systems (Crawl, Brogue), and autoexplore is also an accessibility feature."
- **Shortcuts** between disconnected parts of the same floor (stairs that unlock a previously locked door) — adds Jacquays loops.

For VEFR, the highest-value patterns are:
- **Sections of 8–11 floors** (already in brief): each section is one "tileset + family" — act 1 is the cellar, act 2 is the catacombs, etc. Section boundaries are visual landmarks (a different palette, a different mob family, a different minimap colour).
- **Elevator every 5 floors inside a section** (Stardew pattern): once you reach floor 5 you can teleport back. Cuts exploration cost without breaking the floor count.
- **Special floors** (Stardew pattern): one in every ~7 floors is a *variant floor* — infested (mobs only, clear to ladder), treasure (locked room with the floor's best loot), or hub (a small POI the floor's quest refers to).
- **Landmarks per floor**: every section floor has at least one named point of interest the journal can record ("the Warden's Hall"). This is the Fog of War auto-map payoff.

Sources (in addition to above):
- https://www.reddit.com/r/StardewValley/comments/1eo0u7y/how_do_the_mine_levels_work/
- https://www.reddit.com/r/StardewValley/comments/k1emzk/skull_cavern_depth_and_its_horrifying_implications/

---

## 6. Elites and groups

- **Diablo 2 Champion / Unique / SuperUnique packs:**
  - *Champion packs* "come in packs of 3 to 4 monsters" with one affix (Normal) or two (Nightmare/Hell). Cannot be `Minions`, `Horde`, `Missile Dampening` in some slots.
    - https://www.diablohub.com/guides/monster-traits-description/
    - https://diablo2.diablowiki.net/Monster_modifier
  - *Unique groups* = "1 boss monster and a pack of 3–6 Minions of the same monster type"; "The Unique boss has elite affixes in addition to a" set of base mods.
    - https://maxroll.gg/d2/resources/elite-monster - *Super Unique* = single named monster (e.g. the four Keywardens). The Diablo III Keywarden model is what `design/gates-and-guardians.md:36` already references for the **Keybearer** role.
    - https://diablo.fandom.com/wiki/Unique_Monsters
  - Pack spawn rules: D2 has fixed seeds for which *preset rooms* contain packs (e.g. "8 areas where a champion pack always spawns"), plus a density budget per area.
    - https://forums.d2jsp.org/topic.php?t=93056943&f=87
- **Path of Exile rare packs** — rares have 2–4 affixes; "Pack size scales with number of rares"; a rare's minions get a shared mod.
  - https://www.poewiki.net/wiki/Monster_modifiers
  - https://poe2db.tw/us/Pack
- **Diablo 3/4 elites** — same idea, affixes applied to base type + minions.

For VEFR (which is a 2D tile dungeon with one Elite already designed):
- **Mob group = one leader + 3–4 minions**, same species, leader gets 1 affix at a fixed tier per floor depth. Minions get the *same* tier but no extra affixes.
- **Pack placement** is by seeded roll against a per-floor "budget": N packs per floor (N rises with depth), placed only on reachable floor tiles away from stairs; never random in *any* sense except *which* roll was chosen. **[inf]**
- **Champion density**: Cap at 1 elite group per ~8 room-equivalent tiles so the floor is not entirely champions (the classic DCSS small-crypt complaint).
- **Spawn budget = floor area / k for some k**, with k shrinking per depth (more packs deeper).
- **Linking**: leader's aggro radius includes its minions (avoids the "minions standing around" problem).
- **SuperUniques** (= our **Keybearers**) are *placed* (not rolled), in the farthest room off the path to the stair (the rule already in `design/gates-and-guardians.md:32`).

---

## 7. Endless scaling and loot

- **Stardew Valley Skull Cavern**: the canonical "endless scaling" reference for a *cozy* tone. Monster HP and damage scale with depth; ore tier is fixed per floor; treasure rooms appear at depth milestones; "the deepest floor… 2,147,483,647" (int32 ceiling, not infinite but effectively so).
  - https://stardewvalleywiki.com/Skull_Cavern
  - https://www.reddit.com/r/StardewValley/comments/k1emzk/skull_cavern_depth_and_its_horrifying_implications/
- **Diablo 2 Nightmare/Hell**: "monsters' levels are identical with the area level unless they're considered boss monsters". Affixes stack up (boss Uniques get more in NM, fewer in HH but heavier resist). Confirmed: "Monsters are more difficult in Act V and Hell Difficulties than Nightmare Difficulty by improving the monsters stats (hit points, defense) and by boosting their" resists.
  - https://classic.battle.net/diablo2exp/basics/difficulty.shtml
  - https://diablo-archive.fandom.com/wiki/Area_Level_(Diablo_II)
  - https://diablo2.diablowiki.net/Difficulty
- **Hades Heat system** — the *modifiers*, not the stat numbers, are what escalate. Players add heat to *choose* harder mods (e.g. tighter timers, more enemies). Endless keeps the player ahead of stat creep by *choice*, not by numbers.
  - https://www.resetera.com/threads/im-starting-to-feel-that-stat-based-meta-progression-is-starting-to-ruin-roguelites-generally-speaking.1509337/page-2
- **Rogue Legacy** — class/upgrade RNG + per-run lineage. Loot differs.
- **Vampire Survivors Endless**: "Endless Mode disables the spawning of Reapers upon reaching the stage's time limit. Instead, reaching the final minute of a stage causes the enemy waves to" continue scaling. Endless is unlocked after collecting enough relics (the Seventh Trumpet from Eudaimonia Machine).
  - https://vampire-survivors.fandom.com/wiki/Stages
  - https://rogueranker.com/how-to-unlock-endless-mode-vampire-survivors/

**Two failure modes we must avoid** **[inf]**:
- **Power creep** (every floor gives +5% damage): by depth 200 the numbers are unrecognisable. Vampire Survivors plateaus for the second reason.
- **Flat grind** (loot tier 5 at depth 5, tier 5 at depth 500): no reason to keep going.

For VEFR, the **section model** is the key:
- *Sections* are 8–11 floors of one tileset + one family. The endless mode is *sections* that compose, not single floors that go to int32 max.
- *Inside a section*: gentle depth curve; Keybearer a touch stronger than the prior floor.
- *Crossing a section*: tileset and family change; loot tier bumps up by one; the visual language resets (player feels "I'm in a new place").
- *Endless*: a section-sampler, not a depth counter. Each new section is a fresh8–11 floors with a chosen tileset/family/tier; the tier rises every N sections; the Keybearer is the *section lord*; the floor *key* is replaced by a section-*seal* that opens the next section. Same Rylee-decision shape as `design/gates-and-guardians.md:24`.

This is exactly the D2 model (Act I → II → III → IV → V; Nightmare/Hell re-runs the acts with different `area level`).

---

## 8. Determinism and testing

The baseline we already have:
- **xmur3 → mulberry32** in `prng()` (`src/vefr/delve.py:72-99`); integer maths only, `Math.imul`-equivalent; a JS twin is provable identical row for row by `tests/test_floor_v2_parity.py` (referenced in `design/random-floors.md:22`).
- Run seed is `localStorage['vefr-run-<world>']` (`design/random-floors.md:39`); a floor derives from `(run seed, floor number)`.

To make scaling up safe (the brief asks for ~100 ms per floor and "much bigger maps than 30×30 tiles"):

- **Seeded PRNG per floor**: a sub-seed `sub = derive(run, floor_number)` keeps the per-floor stream reproducible and *independent* across floors, so a fix to floor 3's generator does not silently change floor 7.
- **Versioning the generator**: every generated floor records `{gen_version}` in the save; an older save keeps the older rules or asks for a New descent. This is `design/random-floors.md:55`.
- **Property-based sweep**: generate N seeds (200/size per `design/random-floors.md:49`), assert each floor:
  1. is single-component (BFS from `up` reaches every free tile),
  2. `down` is reachable from `up`,
  3. every placed NPC is on a reachable tile,
  4. every Keybearer is reachable,
5. every required item (the key) is reachable.
  Reference: fast-check-style property testing. https://fast-check.dev/docs/introduction/what-is-property-based-testing/
- **Golden-file tests**: lock the rows of a handful of canonical seeds at build time; any diff = test fail. This is the existing parity harness pattern; generalise it to the new v3.
- **Performance budget**: a `tests/test_floor_perf.py` that asserts `generate_floor_v3(seed, 100, 100, 12) < 100 ms` on CI. The brief sets the budget.
- **Stability across versions**: keep the seed algorithm and the row order stable for old seeds. New seeds get new rules; old seeds reproduce old floors.

The **BorisTheBrave/Unexplored** write-ups repeatedly stress that cyclic/mission-graph generation is *easier to keep stable* across versions because the algorithm is a transformation, not a one-pass. https://www.boristhebrave.com/2021/04/02/graph-rewriting/

---

## What to steal (10 ranked decisions)

Ranked by *smallest change to VEFR*, *biggest fun payoff*. Each entry: what we do, why it fits, and the source it came from. **[inf]** marks things I'd build that aren't strictly attested.

| # | Decision | What it is | Why | Source |
|---|---|---|---|---|
| **1** | **Stamps as the highest-value addition.** | Add a new pack-side "stamp" or "vault" record: a small tile grid with named anchor points (`up`, `down`, `guardian`, `key-cache`). A stamp is placed at a generator-decided anchor by seeded placement; its anchor points become transitions/NPC placements. | Solves the "hand-painted rooms placed into generated floors" line of the brief directly. Tiles + edges + named anchors are the same three things DS1 presets, DCSS .des vaults, and Spelunky rooms have in common. We don't need WFC for this. | https://github.com/crawl/crawl ; https://diablo-archive.fandom.com/wiki/Area_Size_(Diablo_II) ; https://noitagame.com/ |
| **2** | **Sections, then endless** *(not single-floor endless)* | A section is 8–11 floors, one tileset, one family; sections compose the act; endless mode is a section-sampler with rising tier every N sections. | This is the Stardew-cozy answer to "endless" (Skull Cavern is *conceptually* endless but practically capped) and the Diablo2 Nightmare/Hell answer to "harder" (re-run with a higher `area level`, not infinitely deeper floors). Avoids int32 traps and stat-creep. | https://stardewvalleywiki.com/Skull_Cavern ; https://classic.battle.net/diablo2exp/basics/difficulty.shtml |
| **3** | **Brogue-style reward-room placement with named anchor** *(the "key holder" rule)* | A floor may carry an authored "reward" or "key-holder" stamp; the placer puts it at a chosen reachable anchor (e.g. "farthest room off the path to the stair"). The matching lock is on the next floor's stair. | Already in `design/gates-and-guardians.md:32`. It's a *single rule*: pick a room, place a stamp there, set the next stair's `requires`. Codifying this from a proven pattern (Brogue Key Holder / Keywarden) makes it a known-good design. | https://brogue.fandom.com/wiki/Key_Holder ; https://brogue.fandom.com/wiki/Reward_room |
| **4** | **Stardew-style "special floors" every ~7** | A section's floor pattern is something like 1-1-2-3-1-2-1-1 with 1=normal, 2=variant, 3=infested / hub. | Verifies the brief's "elites + linked mob groups on every floor, hand-painted stamps, etc." but keeps the variety predictable so a player can plan their run. Verified pattern from one of the brief's named influences. | https://stardewvalleywiki.com/The_Mines ; https://www.bisecthosting.com/blog/stardew-valley-mine-guide-floors-enemies-loot |
| **5** | **Stardew-style elevator every 5 floors inside a section** | Once a floor-5 staircase is taken, an elevator (one-way, downward) is unlocked to floor 5; same at 15, 25, etc. | Cuts exploration cost inside a section without breaking the floor count. Rylee already uses elevators in her stated vibe. | https://www.reddit.com/r/StardewValley/comments/1eo0u7y/ |
| **6** | **Diablo 2 elite group = leader + 3–6 minions, one affix** | A floor carries N elite groups (N scales with depth); each group is "leader + minions, same species, leader has 1 affix (depth-tier), minions share the affix"; group is placed by seeded roll on a reachable tile. | Verifies the brief's "linked mob groups". Standard Diablo pattern, smallest possible, easiest to test. | https://maxroll.gg/d2/resources/elite-monster ; https://diablo2.diablowiki.net/Monster_modifier |
| **7** | **Jaquays: one loop per section** *(unlocked shortcut inside a section)* | The first time a player opens a stamp-locked shortcut door in a section, a `localStorage` flag unlocks the shortcut; the journal records the shortcut. | Adds loops ("Jacquaying the dungeon") cheaply — a section floor can re-use tiles already drawn. Rylee's named aesthetic (Stardew) has always-on loops; this is the loop lever. | https://bumblingthroughdungeons.com/jaquaying-a-dungeon/ |
| **8** | **Caves-of-Qud-style POI density** *(name every room)* | The placer assigns one POI name per floor from a per-section table (e.g. `Mossy Crossroads`, `The Warden's Hall`); the POI name appears on the auto-map and in the journal. | Big map + named POIs = landmarks. Auto-map is the cleanest single feature for "fun at scale" — the journal already exists. | https://www.gridsagegames.com/blog/2019/03/roguelike-level-design-addendum-procedural-layouts/ |
| **9** | **Hades-style *modifiers* (Heat), not numbers, for endless scaling** | The endless-mode sections layer 1–2 named modifiers per section (e.g. "Tighter Fog", "Keybearer Swarms", "Locked Halls"); modifiers are *added* by the section sampler, not by depth. | Verified: Hades's heat is *modifiers* the player chooses, not stat-creep. VEFR's endless should match. | https://www.resetera.com/threads/im-starting-to-feel-that-stat-based-meta-progression-is-starting-to-ruin-roguelites-generally-speaking.1509337/page-2 |
| **10** | **Connectivity sweep over 200 seeds + golden-file locks + 100 ms budget** | Extend the existing parity harness (referenced from `design/random-floors.md:22` and `design/random-floors.md:49`) with: (a) a per-floor reachability property; (b) a golden-file lock per canonical seed; (c) a perf budget test (`< 100 ms` for the largest size). | The brief demands it; existing test infra (`tests/test_floor_v2_parity.py`, `tests/test_locked_stairs.py`) gives the pattern. Property-based sweep is the standard way to prove "no seed breaks the ending". | https://fast-check.dev/docs/introduction/what-is-property-based-testing/ ; `design/random-floors.md:22-49` |

---

### One-line summary for the order table

1. **Stamps** (§2/§3, by far the biggest single lever for "hand-painted" + "big maps").
2. **Sections, then endless** (§5/§7, prevents the int32-stat-creep trap).
3. **Keybearer-as-placed-stamp** (§3, already in `design/gates-and-guardians.md`).
4. **Special floors + elevator** (§5, Stardew pattern).
5. **Elite group = leader + 3–6 minions** (§6, Diablo 2 pattern).
6. **One loop per section** (§5, Jacquays pattern).
7. **Named POIs + auto-map** (§5, Cogmind/Caves-of-Qud pattern).
8. **Hades heat, not numbers, for difficulty** (§7).
9. **Reachability sweep + golden files + 100 ms perf budget** (§8).
10. **Section-as-tileset-and-family** (cross-cutting; the section model from §7 is the bones under all of the above).

Skip: BSP (visible-tree artefact, no payoff for our brief), full WFC (overkill, hard to bound in JS), full Dormans grammar (the *mission graph* is enough — take that part, not the whole grammar).
