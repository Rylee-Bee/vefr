# What the Cottage release taught VEFR (discovery record)

Written 2026-10-04 after Cottage of the Breeze Release 1 (the overnight run of 2026-10-03/04). **Method:** the run was read as evidence (commits, PRs, the mission record, the playthrough bot's workarounds, the review notes) and every candidate below comes from something that actually happened during the build, not from a wishlist. Nothing here is built. Each finding names what it overlaps, and whether it is new.

**Context that must not be lost:** Release 1 was deliberately scoped to a complete, polished Act 1. Acts 2 and 3 remain part of the larger three-act direction; stopping after Act 1 was Rylee's decision, and the release is not evidence that VEFR cannot support later acts. Act advance and status effects stay useful next capabilities *because* the future acts need them.

**Legend.** Novelty: NEW (not represented), DEEPENED (an existing idea gained material new evidence or scope), KNOWN (tracked; evidence only). Class: engine, authoring, QA, player. Priority: now / next / later.

## The findings, ranked

### 1. Story status the pack can state: draft or approved. NEW · authoring + QA · now
- **Evidence.** Cottage's rule is that Rylee writes the canon. To honour it, every story line written overnight (the King's-room note, the Keeper and Regular lines, tutorial lines, the About book, sticker names, gear names, Keybearer descriptions) was flagged **by hand** in `NOTES.md` and again in the morning report, assembled from memory. Cottage issue #76 ("make draft, playable, canon and release-ready story status explicit") sat open while it happened. The engine cannot tell an agent draft from an approved line, so a draft could ship looking identical to canon.
- **Missing ability.** Ask the pack: which player-visible words are draft, and which Rylee approved?
- **Why VEFR.** Any creator working with an agent, or a team, needs "what has a human signed off on" before a release. It is a safety property of an AI-assisted engine.
- **Smallest shape.** An optional `status: draft | approved` on books (front matter), speakers/voice files, rules that `say`, album stickers and item names, defaulting to `approved` so nothing changes; `vefr check --release` lists every draft with its file, exits non-zero when asked to require none, and the credits/About book can show a count. No UI change for players.
- **Existing overlap.** None in VEFR. Cottage #76 is the game-side symptom. `docs/guides/storyteller-packs.md` says VEFR is authoritative for canon *state*, which is a different thing (what is true in the world, not who approved the words).
- **Priority.** now: small, protects the owner's core rule, and the next agent pass would otherwise repeat the manual flagging.

### 2. Scenarios: start the game in any state. NEW (with filed evidence) · authoring + QA · now
- **Evidence.** To see the King's room I had to play 1,651 keypresses with the bot. `player.wake` did not move the start, so `vefr look` could only photograph the town (VEFR #260, filed that night). The bot also had to *earn* every state it wanted to test (levels, keys, gear). Screenshots of floors 4 to 6, the King fight and the end card all came from full runs.
- **Missing ability.** Name a game state ("level 8, bell key, on floor 5 at 12,9, album half full") and open the game in it.
- **Why VEFR.** Every creator needs to look at, test and demo a deep room without replaying the game; every harness needs it.
- **Smallest shape.** A `scenarios/<name>.json` beside the pack (region, position, level, bag, equipped, flags, album) written in the same keys the saves already use, plus `vefr look --scenario NAME` / `--at REGION X,Y`, the same file accepted by `vefr probe`, the bot and tests. The validator checks it against the pack.
- **Overlap.** #260 is the narrow form (a start position). Saves and the `saves` block already define the keys; `docs/guides/brain-socket.md` mentions "scenarios" only for auditioning model brains. This generalises #260.
- **Priority.** now: it removes the biggest repeated cost of the night and unlocks findings 3, 7 and 8.

### 3. QA that measures what players see: stage containment, many sizes, every panel. NEW · QA · now
- **Evidence.** I measured Cottage at seven window sizes and found zero overflow. Rylee's actual complaint was different: the HUD icons and buttons float out onto the page background beside the map, and the game does not read as one object. The check measured the *viewport*, not whether the interface lives *inside the play stage*. Separately, VEFR's CI axe gate audits only the play surface of the sample world; Cottage had to invent `tests/playthrough/axe_panels.py` to cover seven menu panels and the end card (0 violations) and `fit.py` for sizes.
- **Missing ability.** "Is every piece of interface inside the game's own stage, at phone, laptop and wide sizes, and are all panels and cards accessible?"
- **Why VEFR.** The woven player is shared by every game; a fit or panel regression would hit all of them. The gate should be part of the engine, not rebuilt per game.
- **Smallest shape.** `vefr look --sizes 360x640,390x844,844x390,1280x720,1920x1080 --report` that screenshots each, lists any interactive element outside the stage rectangle, and runs axe over the play screen, each menu panel and any open card; fold the panel walk into `scripts/a11y_check.py` and CI.
- **Overlap.** The axe gate (`dev-guards.yml`, `scripts/a11y_check.py`), `vefr look`, and `docs/guides/accessibility-contract.md` exist; none walks panels, sizes or containment. The native-UI direction (Cottage `docs/plans/native-ui/PLAN.md`) makes containment the main acceptance test.
- **Priority.** now: it is the check that would have caught the thing Rylee saw.

### 4. "Can everything be had?" Completeness beyond keys. DEEPENED · QA · now
- **Evidence.** `vefr check` now follows locks (#253) and caught nothing wrong, but the same class of risk was everywhere else: gear is obtainable only because one chosen enemy instance carries a drop (the copper ladle is dropped by `floor-5-loud-1`; retargeting a Blueprint instance silently removes it); album stickers name enemy instance ids (`met-barrel-mimic` -> `floor-5-loud-1`), so a Blueprint edit can leave a sticker that can never be earned; books can sit where no one can reach.
- **Missing ability.** Report anything the player is promised but can never get.
- **Why VEFR.** The softlock check already pays for itself; completionist features (album, equipment) create more promises than keys.
- **Smallest shape.** Extend the existing reachability fixpoint in `src/vefr/locks.py` into "obtainability": every non-key item, every book, every sticker's `when`, and every enemy must be reachable/earnable; report unreachable ones in plain sentences. Same fixpoint, wider inventory.
- **Overlap.** #253 (keys), #254 (album), design/album.md "Checks the build must carry". Not a new system; a widening.
- **Priority.** now: the module and tests exist; this is the cheapest high-trust extension.

### 5. The feature catalog must know what a pack uses. DEEPENED · authoring · next
- **Evidence.** `vefr features --pack cottage-of-the-breeze` (run 2026-10-04) says `sound`, `walk-sheets`, `album`, `rule-saves` and `gates` are "unknown / not detectable from a pack" although Cottage uses all five and the foremen set their `detect` to `none`. The catalog still lists `album` as partial and `equipment` as partial after both are playable end to end; `complete-act` is not a catalog feature at all. Meanwhile Cottage's CI had to be re-pinned to a VEFR commit by hand four times so the validator would know the new keys.
- **Missing ability.** Ask a pack which engine features it needs, and ask an engine whether it has them.
- **Why VEFR.** Packs live in other repos pinned to an engine revision; "this pack needs album + sound + walk sheets" is exactly the compatibility fact a creator needs.
- **Smallest shape.** Give each feature a real `detect` rule (the pack key it adds), make `vefr features --pack` honest, and add `vefr check --engine REV|PATH` (or a `requires` list derived from detection) so CI can say "this engine lacks `album`" instead of a generic unknown-key error. Retire the manual pin chase.
- **Overlap.** `docs/features.json` and `vefr features --check` exist (drift only against docs, not against what detection covers).
- **Priority.** next: correctness fixes to the catalog are tiny and done in the cleanup; the capability needs a short design.

### 6. A pack art-import verb, and credits hygiene. NEW · authoring · next
- **Evidence.** Every picture went through the same manual chain: pick from a contact sheet, `process_sprites.py` with the right flags (`--clear-holes` for keys, bells, ladles), register in `player.sprites`, register the item, copy a credits line, test. Walk sheets needed a bespoke assembly script (16 cells into a 5x4 sheet plus `hero.sheet.json`). A wrong tile form (`deep-wall.grid2x2`) rendered as flat blocks and was found only by looking at a screenshot. Codex credits files embed the whole prompt *and the generator's temp paths* (`/tmp/claude-.../refs/king.png`), which I had to trim by hand in `CREDITS-release1.md`; in a public pack that leaks local paths.
- **Missing ability.** "Take this picture, make it the sprite/tile/sheet/icon for X, register it, credit it, check it."
- **Why VEFR.** Every pack author does the same dance; the tools live in Cottage's `art/tools/`, not in VEFR.
- **Smallest shape.** `vefr art import SRC --as sprite|tile|sheet|item-icon --key NAME [--size 128] [--clear-holes]` that cuts, sizes, writes into the pack, adds the registration, and writes a *clean* credit line (tool, date, source file name; never absolute paths); a validator rule that refuses absolute local paths in credits and a tile whose form renders flat.
- **Overlap.** `tools/art/import_art.py` (the engine's own art), Cottage `art/tools/*.py` (pack-side, unshared). `docs/guides/making-art.md` documents the manual route.
- **Priority.** next: highest-volume repeated work, but not blocking.

### 7. A route through the pack, and one stable play-state API. NEW · QA · next
- **Evidence.** The playthrough bot (700+ lines) re-derived what VEFR already computes in `locks.py`: the region graph, which transition needs which key, where each key drops. It read the game through an assortment of ad hoc snapshots (`VEFR_COMBAT`, `VEFR_REGIONS`, `VEFR_ALBUM`, `VEFR_SOUND`, `VEFR_HERO_FRAME`, `VEFR_ACT_COMPLETE`, `VEFR_WHY`) and found the Bag's Use button by pressing Tab up to 25 times. It also had to learn to grind a floor before a boss, which no pack data tells it.
- **Missing ability.** Ask the pack for its critical path ("start, region steps, keys in order, guardians, ending") and drive/inspect the live game through one documented state object.
- **Why VEFR.** A generic "can this game be finished by a keyboard player" test would serve every pack and replace per-game bots.
- **Smallest shape.** `vefr route --pack P --json` (from the lock fixpoint: ordered goals with regions, positions, keys, enemy ids) and a documented `window.VEFR_STATE` facade over the existing snapshots; a generic runner that follows `route` and checks the same things Cottage's bot checks.
- **Overlap.** `vefr probe`/`look` (single events/screenshots); finding 2 supplies states; `locks.py` supplies the graph.
- **Priority.** next: depends on 2; high leverage for Act 2.

### 8. A balance report from pack data. NEW · QA · next
- **Evidence.** The King was 40 hp / 4 atk and a level-8 hero could not beat him; only the bot discovered it (2026-10-04, retuned to 36 / 3). NOTES calls every number a "first guess to tune by playing". XP, levels and enemy numbers are all in the pack, but nothing computes "at level N with this gear, how many hits to win and how much health is lost".
- **Missing ability.** Predict whether a fight is winnable and how hard each floor is, before playing.
- **Why VEFR.** Balance is the first thing a creator guesses and the last they can verify; deterministic combat makes it calculable.
- **Smallest shape.** `vefr balance --pack P`: per floor the expected level on arrival (from XP of everything cleared), hits-to-kill and damage taken against each enemy and guardian, flagging fights a hero of the expected level loses.
- **Overlap.** None (combat is deterministic: designs `growth.md`, `equipment.md` define the numbers).
- **Priority.** next: cheap, pure, and Act 2 will need it.

### 9. Authored and generated content in one file. DEEPENED · authoring · next
- **Evidence.** Floor 6's `map.md` is `vefr delve` output that I hand-edited to place the sealed door; a rerun of `delve` overwrites it (recorded only in `NOTES.md` and CURRENT). Region `contract.json` mixes hand-authored fields (pois, legend, tiles) with Blueprint-generated `enemies`; I edited both with ad hoc scripts in the same hour, and the generator's "stale" check protects only `enemies`.
- **Missing ability.** Keep a human edit to a generated thing from being silently lost or silently drifting.
- **Why VEFR.** Random floors phase 2 will generate more floors; every creator will want to place a door or a chest on top of generated output.
- **Smallest shape.** A pack-side overlay (`floor-6.overlay.json`: set tile, add poi, add transition) applied after delve/normalize, validated by `check`; the same stale/lock model Blueprint already uses.
- **Overlap.** Blueprint (ADR 0008) already refuses stale generated lists; `design/random-floors.md` says the last room "is placed by the generator". This adds the human-edit lane.
- **Priority.** next: Act 2 floors will be generated, so the lane is needed before they are.

### 10. Ask VEFR the development questions. NEW · authoring · later
- **Evidence.** I wrote one-off scripts for questions VEFR could answer: who drops this item, what opens this door, where is the farthest room that is *not* on the mandatory path to the stairs (done twice, for guardian placement, with a BFS and an articulation test I wrote by hand), which sprites are unused (a deleted `chest-open.png`, two alternate sets), which enemies carry which family.
- **Missing ability.** `vefr where item bell-key`, `vefr explain door floor-6:11,1`, `vefr map query --farthest-off-path`.
- **Why VEFR.** The answers are already inside `locks.py` and the loaders; a creator or agent should not have to rebuild them.
- **Smallest shape.** A small `vefr where|explain|map` read-only family built on the same loaders; plain sentences.
- **Overlap.** `vefr why` (rules), `vefr find`, `vefr doctor`. None answers pack-structure questions.
- **Priority.** later: pleasant, not blocking; findings 2, 4 and 7 deliver much of the substance.

## Evidence only (KNOWN, not new discoveries)
- **`web/packaged.html` is too large and collides.** Two foremen (sound and walk sheets) both appended to `docs/features.json`, and the second patch failed to apply; both added big blocks to the same player file. Tracked: `docs/plans/player-split/PLAN.md` (#261). Extra evidence: a per-feature catalog file (or generated catalog) would remove the `features.json` merge hotspot.
- **Raw region ids in hints; stairs labelled "down" going up.** #259 (filed) and #255 (fixed). Common cause: engine wording derived from structure, not from pack-supplied names. Evidence for #259, not a new idea.
- **Playthrough-found balance and layout defects** feed findings 3 and 8.

## Considered and not promoted
- **Save compatibility across content changes.** The one piece of evidence ("existing saves repopulate floors") is accepted behaviour; revisit when a game has real players with saves.
- **Hearing/seeing cues without playing.** The bot confirms all nine cues fire; auditioning them is a nicety.
- **Foreman/worker workflow friction** (diff transfer by ssh, stray `PLAN.md`, "quiet = stalled?" false alarms, a classifier that blocks merges until the owner says so in chat) belongs to the estate's `offload`/`mission` tooling, not VEFR. Lessons are in `.project/DECISIONS.md` (2026-10-04).

## How these class together (what VEFR is becoming)
Engine capability: the five that Release 1 already added (end card, lock check, album, sound, walk sheets). Authoring and developer experience: findings 1, 5, 6, 9, 10. Validation and QA: 2, 3, 4, 7, 8. Player capability: none of the ten; the player-facing items (portraits, effects, native HUD) are the Cottage native-UI plan, not discoveries from the run.
