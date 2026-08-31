# Companion resources - the survey

Every candidate tool considered for vefr, each with a link to its
own repo page. Companion data, not dependencies: borrow algorithms,
keep the learnable hand-rolled versions in `web/`, and let the
pack contract carry the art. Last full pass: 2026-08-31.

## The rules this digest follows

| Rule | Where it comes from                                  |
| ---- | ---------------------------------------------------- |
| No framework in `web/`; plain object + patch + subscribers | AGENTS.md style |
| Shipped JS executes under a node vm in tests | AGENTS.md style |
| The custom renderer stays canonical; alternate render targets read `/api/world` | ROADMAP, the rpg-js answer (2026-08-30) |
| Packaged game = one file, everything inlined | ROADMAP, the pool decision |
| CC0 art may ship in-repo; MIT code gets attribution; lore packs stay CC BY-SA text | the license split |
| Prefer the most open license: CC0 first, then MIT | Rylee, 2026-08-31 |

## Engines & renderers

The custom canvas renderer stays canonical (ROADMAP, 2026-08-30).
These are evaluated as alternates, not dependencies.

| Resource | License | Verdict | Why |
| -------- | ------- | ------- | --- |
| PixiJS - github.com/pixijs/pixijs | MIT | Skip dep | WebGL framework for thousands of moving sprites; the town is a 40x28 canvas. Breaks no-framework + node-vm + single-file |
| Excalibur - github.com/excaliburjs/Excalibur | MIT | Skip | Full TypeScript engine - same category as the RPG-JS ruling |
| Phaser - github.com/phaserjs/phaser | MIT | Skip | The mainstream 2D web engine; same framework rules apply. Admired, not adopted |
| LittleJS - github.com/killedbyapixel/LittleJS | MIT | Skip dep, note as reference | Closest size-fit; a future alternate render target behind `/api/world` can revisit |
| Godot - github.com/godotengine/godot | MIT | Context only | The flagship open engine; not browser-single-file. Its MIT choice is the precedent for vefr's own license |
| RPG-JS - github.com/rpgjs/rpgjs | MIT | Skip | Ruled on 2026-08-30: the custom renderer stays canonical |

## Libraries

| Resource | License | Verdict | Why |
| -------- | ------- | ------- | --- |
| Rot.js - github.com/ondras/rot.js | MIT | Borrow algorithms | Map-gen for `norns chat` v2 (geometry frozen at the scaffold today) + the labyrinth; FOV could deepen watch-radius. Seeded, then every map gates through `maplab.validate()` - generate, then prove walkable |
| Javascript-astar - github.com/bgrins/javascript-astar | MIT | Borrow when combat needs it | 40x28 grid A* is ~60 lines; hand-roll with the node-vm test treatment; vendor only if it grows |
| bitECS - github.com/NateTheGreatt/bitECS | MPL-2.0 | Skip | vefr's state is the pack + journal - narrative, not hundreds of frame entities. File-level copyleft besides |
| Pixi-Tilemap - github.com/pixijs-userland/tilemap | (license unverified in this pass) | Skip | Pixi-dependent (@pixi/tilemap) |
| Howler.js - github.com/goldfire/howler.js | MIT | Real need, decide later | No audio today - the bell should ring. Single-file weave makes audio assets heavy; raw WebAudio synth fits the 1-bit aesthetic and keeps the file honest |

## Map authoring

Today a storyteller edits `map.md` char grids by hand or writes
run-length segment files for `norns build-map --segments`
(`maplab.build_map`). `norns chat` leaves geometry untouched in v1.
No visual editor exists in the toolchain - that is coder-adjacent,
against the rule that a storyteller never needs to learn to code.

| Resource | License | Verdict | Why |
| -------- | ------- | ------- | --- |
| Tiled - github.com/mapeditor/tiled | GPL-2.0+ app, BSD/Apache components | Adopt as authoring tool + small importer | The open standard: 12.9k stars, actively maintained, JSON export, JS scripting API (a small vefr export script could write pack-native files from inside Tiled). Object layers hold named points (`"tower": [5,1]`); the export gates through `maplab.validate()`. No GPL code enters vefr |
| LDtk - github.com/deepnight/ldtk | MIT | Second importer target | 4.1k stars, MIT (verified), by the Dead Cells level director. Its "Super Simple Export" emits tiny JSON + PNGs per level - designed exactly for minimal ingestion; auto-rendering rules could skin maps automatically. Tiled first (bigger ecosystem, wangsets), LDtk importer second |
| In-engine visual editor | - | North-star item | The dev menu grows its own paint-the-map surface; Tiled bridges until then |

## Narrative tools

| Resource | License | Verdict | Why |
| -------- | ------- | ------- | --- |
| ink - github.com/inkle/ink | MIT | Keep on the shelf | inkle's branching-narrative language (80 Days, Heaven's Vault). vefr's story is LLM-generated inside schemas, so hand-authored branching is not the current model - but an optional `story.ink` in a pack could give authors deterministic branching scenes, and inkjs (github.com/y-lohse/inkjs, MIT) runs in the browser single-file. A someday pack-contract extension, not a today need |
| inkjs - github.com/y-lohse/inkjs | MIT | Shelf (with ink) | The browser runtime that would make ink work in `web/packaged.html` |
| Yarn Spinner - github.com/YarnSpinnerTool/YarnSpinner | MIT | Shelf | Unity-oriented; ink's ecosystem fits browser play better |

## Art editors

| Resource | License | Verdict | Why |
| -------- | ------- | ------- | --- |
| Pixelorama - github.com/Orama-Interactive/Pixelorama | MIT | Recommend to authors | 10.2k stars, free, runs on desktop AND in the browser - the no-cost art tool for authors replacing the CC0 defaults |
| Piskel - github.com/piskelapp/piskel | Apache-2.0 | Recommend as zero-install | Web-based, 12.7k stars; a storyteller edits sprites in a tab with nothing installed |
| Aseprite - github.com/aseprite/aseprite | EULA (paid, source-available) | The pro option | The industry standard; authors buy their own copy. Its `.ase` files are also what LDtk loads directly |

## Audio

| Resource | License | Verdict | Why |
| -------- | ------- | ------- | --- |
| Howler.js - github.com/goldfire/howler.js | MIT | Decide later (see Libraries) | Only when real audio files beat the synth approach |
| sfxr-style WebAudio synth (e.g. jsfxr) | unverified - check before borrowing | Prefer for the first bell | Generated retro SFX keeps the single file honest; the 1-bit aesthetic does the rest |
| Kenney RPG Audio + Interface Sounds | CC0 1.0 | Adopt when audio lands | The fallback source for real files |

## Asset packs

| Pack | License | Verdict | Notes |
| ---- | ------- | ------- | ----- |
| Kenney 1-Bit Pack - kenney-assets.itch.io/1-bit-pack | CC0 1.0 | Adopt - best fit | Monochrome = luminance-based, exactly the accessibility rule (rank by lightness, never hue); CC0 ships inside the MIT engine repo; the scaffold README already tells authors to replace default art - Kenney is the neutral default |
| Kenney RPG Base - kenney.nl/assets/rpg-base | CC0 1.0 | Adopt as alt | Colored terrain fine; status/rank stays luminance-encoded; `W.tile` is pack-driven (`web/town.js:41`, default 32) |
| Foozle "Lucifer" Exterior - foozlecc.itch.io/lucifer-exterior-tileset | CC0 | Strongest alt | 32x32 - exact `W.tile` match; .ase sources included |
| Foozle "Lucifer" Desert - foozlecc.itch.io/lucifer-desert-tileset | CC0 | Alt, biome variety | Same family |
| Mythic Dungeon - verzatiledev.itch.io/mythic-dungeon | CC0 | Ready for the labyrinth | 16/32/48/64 sizes; walls, water, chests |
| Mixel Top-Down RPG 32x32 - mixelslime.itch.io/free-top-down-rpg-32x32-tile-set | Free, NO modification | Skip | Free for commercial use but modifications forbidden - fails the make-it-unique rule |
| Wardmarch / Emberfen - najjar320.itch.io | Paid, no-redistribute | Skip for shipping | Authors may use them in their own local packs; they cannot ship in `worlds/sample-world/` or the repo |

Sprites drop into a pack's `sprites/` directory - the acts loader
discovers them by convention. Art is pack data, not code.

## Dev workflow

| Tool | License | Verdict | Why |
| ---- | ------- | ------- | --- |
| `norns doctor` (first-party) | - | Build it | One command session-start check: git state, pytest, current-pack validate, live-stack health if reachable. Replaces the manual checklist in `session-handoff.md` |
| ruff - github.com/astral-sh/ruff | MIT | Add to the gate | <1s lint pass; catches rename drift mechanically ("if you meet an old name in a comment, it's drift - fix it") |
| uv - github.com/astral-sh/uv | MIT/Apache | Already in use | The gate already runs through it |
| tea - gitea.com/gitea/tea | MIT | Already in use | PRs via CLI (Rule: tea, not raw curl) |
| quadlet - github.com/containers/quadlet | GPL (tool) | Already in use | Deploy-side only |
| pandoc - github.com/jgm/pandoc | GPL (tool) | Prefer hand-rolled EPUB | The ebook export should be a deterministic stdlib writer (zipfile + OPF + XHTML, ~150 lines, no dep) - fits the no-new-deps and deterministic-surfaces rules. Pandoc stays the manual fallback |
| Playwright - github.com/microsoft/playwright | Apache-2.0 | Skip for now | Visual regression is heavy; the node-vm DOM harness covers behavior. Revisit if visual drift keeps biting |

## Sequencing

1. Renderer sprite support: a `drawImage` path in `web/town.js`
   (pack-provided images, CC0 defaults, hand-drawn overrides).
   Today the renderer draws colored rects and arcs; `sprites/`
   exists in the contract but nothing draws it yet.
2. Kenney art drops into `sample-world/` as pack data - zero code,
   pure content.
3. Tiled JSON importer (`norns import-tiled`) - parked in ROADMAP
   Next after the surface-UI work; LDtk's Super Simple Export is
   the natural second format.
4. Rot.js mapgen when `norns chat` v2 opens up geometry.
5. Audio: sfxr-style WebAudio synth before asset files; Kenney's
   CC0 packs are the fallback source.
6. Quick wins available immediately: `norns doctor` and ruff in
   the gate.
7. The ebook export stays a stdlib hand-rolled writer - no pandoc
   dependency.

## Licensing quick-rules

Preference order: CC0 (public domain) first, MIT second - when two
assets are otherwise equal, pick the more open license. The engine
itself ships MIT (chosen deliberately over 0BSD/CC0: the
notice-preservation keeps Rylee's name on every fork); Rylee's
game and story stay their own property (the private
`the private story repo` repo).

- CC0: may ship in-repo, no attribution required (credit anyway
  where a page allows).
- MIT code: vendoring allowed with the license notice intact;
  prefer borrowed algorithms re-typed in the engine's own voice
  with attribution comments - more learnable, less surface.
- GPL (Tiled, quadlet): use the tool, parse the output; never
  vendor the code.
- EULA / paid assets (Aseprite, Wardmarch, Emberfen): author's
  own tool or local pack only; never ship in-repo.
- CC BY-SA: lore packs only (text mood-boards).
- Anything shipping in `worlds/sample-world/` must survive the
  standalone-playable rule: complete, no private content.

## Sources

- PixiJS: github.com/pixijs/pixijs
- Excalibur: github.com/excaliburjs/Excalibur
- Phaser: github.com/phaserjs/phaser
- LittleJS: github.com/killedbyapixel/LittleJS
- Godot: github.com/godotengine/godot
- RPG-JS: github.com/rpgjs/rpgjs
- Rot.js: github.com/ondras/rot.js
- Javascript-astar: github.com/bgrins/javascript-astar
- bitECS: github.com/NateTheGreatt/bitECS
- Pixi-Tilemap: github.com/pixijs-userland/tilemap
- Howler.js: github.com/goldfire/howler.js
- Tiled: github.com/mapeditor/tiled (mapeditor.org)
- LDtk: github.com/deepnight/ldtk (ldtk.io)
- ink: github.com/inkle/ink
- inkjs: github.com/y-lohse/inkjs
- Yarn Spinner: github.com/YarnSpinnerTool/YarnSpinner
- Pixelorama: github.com/Orama-Interactive/Pixelorama
- Piskel: github.com/piskelapp/piskel
- Aseprite: github.com/aseprite/aseprite
- ruff: github.com/astral-sh/ruff
- uv: github.com/astral-sh/uv
- tea: gitea.com/gitea/tea
- quadlet: github.com/containers/quadlet
- pandoc: github.com/jgm/pandoc
- Playwright: github.com/microsoft/playwright
- Kenney 1-Bit: kenney-assets.itch.io/1-bit-pack
- Kenney RPG Base: kenney.nl/assets/rpg-base
- Kenney RPG Audio: kenney.nl/assets/rpg-audio
- Kenney Interface Sounds: kenney.nl/assets/interface-sounds
- Foozle Lucifer Exterior: foozlecc.itch.io/lucifer-exterior-tileset
- Foozle Lucifer Desert: foozlecc.itch.io/lucifer-desert-tileset
- Mythic Dungeon: verzatiledev.itch.io/mythic-dungeon
