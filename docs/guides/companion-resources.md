# Companion resources - what we borrow, what we skip

A digest of MIT-licensed libraries, CC0 asset packs, and mapping
tools evaluated against this engine's real constraints (2026-08-31).
Companion data, not dependencies: borrow algorithms, keep the
learnable hand-rolled versions in `web/`, and let the pack contract
carry the art.

## The rules this digest follows

| Rule | Where it comes from                                  |
| ---- | ---------------------------------------------------- |
| No framework in `web/`; plain object + patch + subscribers | AGENTS.md style |
| Shipped JS executes under a node vm in tests | AGENTS.md style |
| The custom renderer stays canonical; alternate render targets read `/api/world` | ROADMAP, the rpg-js answer (2026-08-30) |
| Packaged game = one file, everything inlined | ROADMAP, the pool decision |
| CC0 art may ship in-repo; MIT code gets attribution; lore packs stay CC BY-SA text | the license split |

## Libraries

| Resource        | License | Verdict                     | Why                                                                                             |
| --------------- | ------- | --------------------------- | ----------------------------------------------------------------------------------------------- |
| PixiJS          | MIT     | Skip dep                    | WebGL framework built for thousands of moving sprites; the town is a 40x28 canvas. Breaks no-framework + node-vm + single-file constraints |
| Excalibur.js    | MIT     | Skip                        | Full TypeScript engine - the same category RPG-JS already ruled on: custom renderer stays canonical |
| LittleJS        | MIT     | Skip dep, note as reference | Closest size-fit, but swapping the tested canvas renderer buys nothing visible today; a future alternate render target behind `/api/world` can revisit |
| Rot.js          | MIT     | Borrow algorithms           | Map-gen for `norns chat` v2 (geometry frozen at the scaffold today) + the labyrinth; FOV could deepen watch-radius. Seeded, then every map gates through `maplab.validate()` - generate, then prove walkable |
| Javascript-astar | MIT    | Borrow when combat needs it | 40x28 grid A* is ~60 lines; hand-roll with the node-vm test treatment; vendor only if it grows   |
| bitECS          | MIT     | Skip                        | vefr's state is the pack + journal - narrative, not hundreds of frame entities                   |
| Pixi-Tilemap    | MIT     | Skip                        | Pixi-dependent                                                                                   |
| Howler.js       | MIT     | Real need, decide later     | No audio today - the bell should ring. Single-file weave makes audio assets heavy; raw WebAudio synth fits the 1-bit aesthetic and keeps the file honest |

## Map authoring - the missing piece

Today a storyteller edits `map.md` char grids by hand or writes
run-length segment files for `norns build-map --segments`
(`maplab.build_map`). `norns chat` leaves geometry untouched in v1.
No visual editor exists anywhere in the toolchain - that is
coder-adjacent, against the north-star rule that a storyteller
never needs to learn to code.

| Resource             | License        | Verdict                        | Why                                                                                       |
| -------------------- | -------------- | ------------------------------ | ----------------------------------------------------------------------------------------- |
| Tiled Map Editor (github.com/mapeditor/tiled) | GPL-2.0+ app, BSD/Apache components | Adopt as authoring tool + small importer | The open standard for visual tile-map authoring: 12.9k stars, actively maintained, JSON export, and a JS scripting API - a small vefr export script could write pack-native files from inside Tiled. Authors paint tiles; object layers hold named points (`"tower": [5,1]`); the export gates through `maplab.validate()`. No GPL code enters vefr - we only parse the documented output format |
| Rot.js mapgen + FOV  | MIT            | Borrow algorithms (see above)  | Generation, not authoring - complements Tiled, never replaces validation                  |
| In-engine visual editor | -           | North-star item                | The dev menu grows its own paint-the-map surface; the Tiled importer bridges until then    |

## Asset packs

| Pack               | License | Verdict      | Notes                                                                                       |
| ------------------ | ------- | ------------ | ------------------------------------------------------------------------------------------- |
| Kenney 1-Bit Pack  | CC0 1.0 | Adopt - best fit | Monochrome = luminance-based, exactly the accessibility rule (rank by lightness, never hue); CC0 can ship inside the MIT engine repo; the scaffold README already tells authors to replace default art - Kenney is the neutral default |
| Kenney RPG Base    | CC0 1.0 | Adopt as alt | Colored terrain tiles fine; status/rank must stay luminance-encoded; `W.tile` is pack-driven (`web/town.js:41`, default 32) so tile px adapts without code change |
| Kenney RPG Audio + Interface Sounds | CC0 1.0 | Adopt when audio lands | Confirmed CC0; the default source for the bell's ring and UI sounds if real files beat the WebAudio synth |

### Found in research (2026-08-31)

| Pack                    | License | Verdict                                                              |
| ----------------------- | ------- | -------------------------------------------------------------------- |
| Foozle "Lucifer" Exterior | CC0   | 32x32 - exact `W.tile` match; .ase sources included; strongest alt to Kenney for outdoor regions |
| Foozle "Lucifer" Desert   | CC0   | Same family; biome variety for act regions                           |
| Mythic Dungeon (VerzatileDev) | CC0 | 16/32/48/64 sizes; walls, water, chests - ready for the labyrinth  |

"Name your own price" is not CC0. The Mixel 32x32 pack is free
for commercial use but forbids modification - it fails the
make-it-unique rule. Paid packs (Wardmarch, Emberfen) carry
no-redistribution clauses: an author may use them inside their own
local pack, but they cannot ship in `worlds/sample-world/` or the
repo.

Sprites drop into a pack's `sprites/` directory - the acts loader
discovers them by convention. Art is pack data, not code.

## Sequencing

1. Renderer sprite support: a `drawImage` path in `web/town.js`
   (pack-provided images, CC0 defaults, hand-drawn overrides).
   Today the renderer draws colored rects and arcs; `sprites/`
   exists in the contract but nothing draws it yet.
2. Kenney art drops into `sample-world/` as pack data - zero code,
   pure content.
3. Tiled JSON importer (`norns` craft command) gated by
   `maplab.validate()`.
4. Rot.js mapgen when `norns chat` v2 opens up geometry.
5. Audio decision when the bell deserves its ring: WebAudio synth
   before asset files; Kenney's CC0 audio packs are the fallback
   source when real files arrive.

## Licensing quick-rules

- CC0: may ship in-repo, no attribution required (credit anyway
  where a page allows).
- MIT code: vendoring allowed with the license notice intact;
  prefer borrowed algorithms re-typed in the engine's own voice
  with attribution comments - more learnable, less surface.
- GPL (Tiled): use the tool, parse the output; never vendor the
  code.
- CC BY-SA: lore packs only (text mood-boards).
- Anything shipping in `worlds/sample-world/` must survive the
  standalone-playable rule: complete, no private content.

## Sources

- PixiJS: pixijs.com
- Excalibur: excaliburjs.com
- LittleJS: killedbyapixel.github.io/LittleJS
- Rot.js: ondras.github.io/rot.js
- Javascript-astar: bgrins.github.io/javascript-astar
- bitECS: github.com/fritzy/ecs-js (bitECS)
- Howler.js: howlerjs.com
- Tiled: mapeditor.org (repo: github.com/mapeditor/tiled)
- Kenney 1-Bit: kenney-assets.itch.io/1-bit-pack
- Kenney RPG Base: kenney.nl/assets/rpg-base
- Kenney RPG Audio: kenney.nl/assets/rpg-audio
- Kenney Interface Sounds: kenney.nl/assets/interface-sounds
- Foozle Lucifer Exterior: foozlecc.itch.io/lucifer-exterior-tileset
- Foozle Lucifer Desert: foozlecc.itch.io/lucifer-desert-tileset
- Mythic Dungeon: verzatiledev.itch.io/mythic-dungeon
