# Named edits: one way to change a game, many ways in

Status: **proposed**. Source: Opus's product-direction answer (2026-10-01) and the "pretend chat editor" experiment below.
Nothing here changes the pack contract yet; where a step would, it says so and waits for Rylee.

## The idea in one paragraph

A game is a folder of plain files. Today only two things in the studio write to that folder: making a world, and building the map.
A **named edit** is one small, checked change to those files ("paint these squares", "place this character", "write this line").
Chat, drag-and-drop, visual tools, the command line and AI assistants all call the same edits. Chat only *proposes* an edit as a
preview card (Keep / Change / No). Nothing is written until the player keeps it. The files stay the single source of truth.

## Rules every edit follows

1. **Pure and checked.** An edit takes the game folder and returns a changed game folder. The result must pass `norns validate`
   (the one check) or nothing is written.
2. **One writer.** Writes go through the shared writer the map already uses (`maplab.write_pack`), so the CLI and the studio produce
   identical bytes. `builder/map/build` is the pattern: validate, refuse to overwrite without force, back up, write.
3. **Preview first.** Every edit can return a preview (the changed files as a diff or a picture) without writing.
4. **Plain errors.** A refused edit says in one plain sentence what to change. No stack traces, no raw URLs.
5. **JSON in and out**, so a person, a script and an AI assistant can all call it. The same edit is a command (`vefr edit <name> --json`).
6. **A log line per kept edit** (who, when, which edit, which files). That gives undo, a real dev journal and, only where a tool's terms are
   cleared, honest training examples. *Where the log lives is a pack-contract question: Rylee decides.*
7. **Ask when vague.** If a sentence has two readings ("make it bigger"), the proposal is one small question, not a guess.
8. **The crew never decides for the player.** A draft is labelled a draft; the player keeps, edits or bins it.

## The experiment (2026-10-01): a pretend chat editor

**Question.** Does a small, fixed set of named edits cover what people actually say about their game, and is seeing the change in the
running game the reward?

**Method.** Claude wrote 20 plain sentences about Cottage of the Breeze, the way a curious beginner might say them. Each was mapped by
hand to one of six edits: paint tiles, place a character, write a line, add a book, set style words, set title or start tile.
The two paint sentences were applied to a throwaway copy of the pack, checked with `norns validate`, woven, and screenshotted before and after.

**Result.** 13 of 20 fit the six edits cleanly (65%). Three more were near misses (a window needs a picture that doesn't exist; a shy dragon
needs the monster system; undo needs the log), so 16 of 20 (80%) with small additions. The two applied edits validated and played.
The weave took 0.02 s for this pack on the dev VM; the browser load was not timed.

| What did not fit | Needs |
| --- | --- |
| "A secret door behind the hearth"; "add a second floor" | a door or stairs edit, and a new-room edit |
| "Opening the chest gives me a key" | a chest-with-drops edit |
| "A little bell sound when the cat moves" | a sound edit (no sound surface exists) |

**What it taught.**
- "Bigger" was ambiguous: the first attempt widened the room to the right only. A proposal must ask which way.
- Seeing the hero stand in the wider room was the moment that worked. The preview should be a picture, not a list.
- **Caveats.** The author of the sentences knew the edits, so the 65% is probably flattering. A fair test uses sentences written by someone who doesn't. Only map edits were applied; the other fits are by reading, not by running.

## The second run (2026-10-01): Rylee's own twenty sentences

**Method.** Rylee wrote one sentence for each of 20 scenario cards (`design/named-edits-sentences.md`), in her own words. Claude then mapped
each to the named edits by reading, with three outcomes: *fits now* (the six edits above), *fits with a planned edit* (an edit in the "build first" or
"build next" lists), or *needs something else*. Nothing was applied this time: the new people, props and ground pictures are being drawn (round 8 art),
so the apply-and-show step waits for them.

| Card | Sentence (shortened) | Result |
| --- | --- | --- |
| A1 | a game about exploring for my grandson | **Fits now**: `set_identity` (the brief) |
| A2 | a cat that runs a bakery at night | **Fits now**: identity, `place_character`, phase text |
| A3 | a game on the back of an ancient nightmare | **Fits now**: identity and tone |
| A4 | a cute, warm library scene | Planned: `add_region` plus style words |
| B1 | a kind old grandma, a warm hug and a slice of pie | **Fits now**: `place_character`, `write_line` |
| B2 | a big burly guard, an uber softie, a pet frog | **Fits now**: two characters and lines |
| B3 | a wizened old woman the locals ignore | **Fits now**: `place_character`, `write_line` |
| B4 | "Sounds too robot. How do I make it talk normal?" | **Fits now after a question**: `write_line`; propose three rewrites |
| C1 | "Can we maybe spruce it up a little?" | **Needs a question first** ("what would you add?"), then paint or props |
| C2 | "It's just so boring!" | **Needs a question first** (the fight? the room?), then enemy or rules edits |
| C3 | the grass is too same-y | **Fits now**: `set_tile_grid` (a grid picture) |
| C4 | "something that tells me where to go" | **Needs something else**: a hint or guide mechanic |
| D1 | a little hidden escape on the map | Planned: `add_transition` |
| D2 | a sneaky surprise chest that's a bad guy | **Needs something else**: a chest that turns into a monster |
| D3 | an ominous fog when its name is spoken | **Needs something else**: weather that reacts to an event |
| D4 | "Can the cat notice me?" | **Needs something else**: a reaction when the hero comes near |
| E1 | "Can we have a system for little treasures?" | **Needs something else**: a collection mechanic, not an edit |
| E2 | the mighty spooncalibur | Planned: `add_item` with a slot (see `design/equipment.md`) |
| E3 | a split map, pieces found as the story goes on | Planned: `add_item` x N, **plus** something that joins the pieces |
| E4 | a key to open the secret panel for the door in the lab | Planned: `add_item` and `add_transition`, **plus** a lock |

**Result.** 8 of 20 fit the edits that exist in the plan (40%). With the planned edits it is 13 of 20 (65%). Two sentences need a clarifying question first.
**Seven of 20 (35%) are not content at all: they describe behaviour** ("when its name is spoken", "the cat notices me", "a chest that is a bad guy", "pieces you find",
"tells me where to go"). Content edits cannot express those.

**What it taught.**
1. **There is a second kind of edit: "when this happens, do that".** Four of the seven behaviour sentences are triggers (name spoken, hero near, chest opened, piece found).
   A small, safe trigger surface (an event, a condition, a response from a short fixed list) is the biggest gap. This is a new pack-contract surface, so it is Rylee's call.
2. **People say what they want, not how.** Most sentences are short and feeling-led ("boring", "same-y", "spruce it up"). The right answer is a small question or three picture options, not a guess.
3. **Requests arrive as questions** ("Can the cat notice me?", "How do I make it talk normal?"). A chat editor must treat a question as a request, and answer in plain words.
4. **The first sentences are about the game, not the map.** Five of the first six sentences are the brief ("a game about...", "a cat that runs a bakery"). `set_identity` and the interview
   matter more at minute one than painting does.
5. The 40% (not 65%) reflects honest author-blindness: Claude's sentences in the first run fit more often because Claude knew the edits.

**What it did not test.** No edit was applied, so "does it feel like mine?" is untested. A third run applies the "fits now" sentences once the round 8 art (people, props, ground) exists.

## The surfaces an edit can reach

"Today" says what exists in the studio API (`src/vefr/main.py`) or the CLI. Edits marked **new** need a new route and a decision from Rylee
(new public routes are ask-first). Edits marked **proposes** already have a proposal route that never writes.

| Surface | Where it lives | Today | Named edit (proposed) |
| --- | --- | --- | --- |
| World identity | `world.json`: `name`, `title`, `description`, `creed` | create world only (`POST /api/builder/worlds`) | `set_identity` (new) |
| Phases and mood | `world.json` `phases`; per-act `tone` | none | `set_phase_text`, `set_tone` (new) |
| Rules of the act | per-act `ruleset`, `floor` (costume/story/stakes), `verbs` | none | `set_law` (new) |
| Map squares | region `map.md` | `map/propose`, `map/check`, `map/build` | `paint_tiles` (exists as map/build), `resize_region` (new) |
| Tile meanings | region `contract.json` `legend` | inside map/build | `set_legend` (new) |
| Named places | `pois`, `poi_text` | none | `set_place_text` (new) |
| Start point | `hero_start` | none | `set_start` (new) |
| Weather, fog, light | `watch`, `water_by_phase`, `flood_tiles`, `fog` | none | `set_region_weather`, `set_fog` (new) |
| Doors and stairs | act `transitions` | none | `add_transition` (new) |
| New rooms | `acts/<id>/<region>/` | none | `add_region` (new) |
| Characters | `voices/*.md` plus speaker position and region | `face/roll` proposes; keep goes to the vault only | `place_character` (new; closes the vault gap) |
| What they say | `voices/*.md`, per-phase seeds | `enhance/voice` proposes | `write_line` (new) |
| Bonds between people | `bonds`, `bond_draw` | none | `set_bond` (new) |
| Traders | speaker `shop` | none | `set_shop` (new) |
| Monsters | region `enemies`, `drops` | `combat/action` plays, nothing authors | `place_enemy` (new) |
| Items | `world.json` `items` catalog | `enhance/item` proposes | `add_item` (new) |
| Books and chests | `library/*.md` (a chest is a book with `drops`) | `GET /api/library` reads | `add_book`, `place_chest` (new) |
| Character art | `sprites/` | none | `set_sprite` (new) |
| Ground art | `tiles/` (variants and grids) | none | `set_tile_picture`, `set_tile_grid` (new) |
| Style words | `grammars`, `forge_texture`, `stefna_voice` | none | `set_style_words` (new) |
| Ruleset content | cooking `pantry`/`orders`, desk `headlines`, delve settings | `verify` checks | `set_ruleset_content` (new) |
| Narrator and brain role | studio settings, storyteller pack | `spark/*`, `teach/mode` | `set_narrator` (studio setting, not a game file) |
| Stickers and journal | `achievements`, play journal | read and event routes exist | none (read-only for players) |
| Share it | woven single file | `builder/weave`, `weave/file/{name}` | none (not an edit; the "play it here" pane reuses it) |
| Undo and history | the edit log | `vault/undo`, `journal/undo` (other things) | `undo_last`, `show_history` (new) |

**Three groups, so the build stays small.**
- *Build first* (closes the loop): `place_character`, `write_line`, `add_transition`, `undo_last`, and the play-here pane.
- *Build next*: `set_identity`, `set_start`, `set_place_text`, `add_item`, `place_chest`, `place_enemy`, `set_style_words`.
- *Later or never yet*: sound, a free-form canvas, node scripting, the marketplace.

## What this does not decide

The edit log's location (pack contract), the exact route names, whether a kept edit may ever be applied without a preview,
and which model proposes edits for chat. The small-model evidence says chat must stay preview-only for now
(`bench/interface/results/summary.json`: qwen2.5-1.5b scored 48.3% safe on the interface translator).

## Next

Rylee writes (or picks) scenario-based sentences using the scenario cards in `design/named-edits-scenarios.md`; the next run applies
the ones that fit and records which do not, with a person who did not write the edits as the judge of "does this feel like mine".
