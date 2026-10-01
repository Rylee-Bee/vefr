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
