# Close the loop: put a character in the game, and play it right there

Status: **approved to build** by Rylee on 2026-10-01 ("Yes and approved to build" for new public routes and "close the loop" as the first slice).
The note comes first so each route's shape is written down. Source: Opus's product-direction answer and the named-edits notes (`design/named-edits.md`).

## The break this fixes

In the studio, only two things write to the game folder: making a world and building the map. A character you keep in the Folks room goes to the **vault**
(`web/js/rooms/characters.js`, `API.vaultKeep`) and never reaches the game you play. There is also no way to play inside the studio; the Desk only downloads a file.
(Opus traced this by reading; the foreman must confirm it by running a keep, a weave and a look at the baked speakers before changing anything.)

## 1. The edit: `place_character`

**What it does.** Turns a kept face into a real speaker in the game: one entry in the act's `world.json` `speakers` (`name`, `at`, `near`, `voice_file`, `seeds` for each phase), plus a voice file
`acts/<act>/<region>/voices/<id>.md`. It follows the same rules as `builder/map/build`: validate first, refuse to overwrite without `force`, back up, write through the shared writer (`maplab.write_pack`),
clear the world cache, no model call.

**Route:** `POST /api/builder/character/place`

```json
{"name": "<world>", "id": "stern", "display_name": "Stern", "role": "guard", "near": "the gate",
 "seeds": {"dusk": "Halt. ...oh, it's you.", "dawn": "Morning."},
 "voice": "You are Stern, a big burly guard who is secretly very soft...",
 "at": [3, 4], "region": "town", "preview": true, "force": false}
```

- `preview: true` writes nothing and returns what would change: the new speaker entry, the new voice file text, the tile, and `ok` or the plain-sentence problems.
- `id`: lowercase letters, digits and hyphens only (`^[a-z][a-z0-9-]{0,31}$`), never an existing speaker without `force`; the voice file path is built from it and checked to stay inside the pack (the same real-path guard as the tile code).
- `at`: if omitted, the engine picks a reachable free tile by the existing rule (`chat._pick_tile`: reachable from the hero start, not on anyone's spot, not on flood ground). If given it must be walkable, reachable and free, or 422 with a plain sentence.
- `seeds`: one short line per phase the world defines; missing phases get the first seed. Lines are capped to what the speech box shows.
- On success: `{"written": true, "files": [...], "backup": "...", "preview": {...}}`. 404 for an unknown world, 409 for an existing id without `force`, 422 for anything the validator refuses (plain sentences, one per problem).
- Deterministic and local. The model never writes here; a face is only *proposed* by `face/roll`.

**In the Folks room:** the **Keep** button on a suggested character calls `preview`, shows the preview card (a picture of them on the map plus their first line), and **Put in the game** calls the real write.
The vault keeps working as the "I like this person" shelf; placing is a separate, explicit step.

## 2. The "play it here" pane

**What it does.** On the Desk, a **Play it here** button weaves the current game and shows it in the page, inside a pane, so a player sees their change alive in seconds without downloading anything.

**Route:** `GET /api/builder/weave/play/{name}`: the same strict filename lookup as the download route (no path is ever built from the request), but served inline
(`Content-Disposition: inline`) with a `Content-Security-Policy: sandbox allow-scripts allow-same-origin` header so the woven page cannot reach the studio's own pages' scripts through a navigation.
The pane is an `<iframe>` with `sandbox="allow-scripts allow-same-origin"`, a title, and a visible **Open in a new tab** link.

**Open risk (UNVERIFIED, the foreman must test).** The woven player saves its bag, floor and fog in `localStorage`. A fully sandboxed iframe (no `allow-same-origin`) has no localStorage,
so the player may break there. With `allow-same-origin` the woven page runs on the studio's origin and could read the studio's storage; that is acceptable for a player's *own* active game
but **not** for an imported pack from a stranger. The foreman must:
1. test whether the player works without `localStorage` (try/catch around every access);
2. if it does, use the strict sandbox; if it does not, use `allow-same-origin` only for a world the player made in this studio, and refuse the pane for an imported pack with a plain sentence.

**Time budget.** Measure and report seconds from "keep" to "playing" (weave took 0.02 s on a small pack on the dev VM; the browser load was not timed).

## 3. The edit log and undo

- **Studio data folder:** `data/edits.jsonl`, one JSON line per kept edit: `{"ts", "who": "player"|"crew", "edit": "place_character", "world", "files": [...], "backup": "<path>"}`. Private; no contract change.
- **Game folder:** a short readable summary the studio keeps up to date, `EDITS.md` (one line per kept edit: date, plain sentence, e.g. "2026-10-01: put Stern the guard at the gate"). This is a pack-contract addition (additive); a pack without it is unchanged.
- **Undo the last edit:** `POST /api/builder/edits/undo` restores the backup taken before the last edit, removes the log line and the summary line, and says what it undid in a plain sentence. One level only in the first slice.
- Every route above appends to both places; `map/build` is wired in too, so the log covers the map from day one.

## 4. The first-playable walk and stickers

Two new events for the sticker engine and the walk rail: `play_here` (the pane was opened) and `character_placed`. Walk: **paint, check, play here, put a person in, play again**.
Steps tick only on the real event (the walk rail's own rule). At least one new sticker picture, made in a batched call and chosen by Rylee.

## 5. What this does not do

No chat that writes without a preview, no rules, no equipment, no new surfaces beyond characters, and no deploy. The edit log's other consumers (training records, the dev journal)
are later.

## Tests the build must carry

1. **Writer:** preview writes nothing; a real place writes exactly the speaker entry and the voice file; the pack still validates; a second place of the same id returns 409 without `force`.
2. **Safety:** ids with `..`, slashes, uppercase or spaces are refused before the disk is touched; a voice path that would leave the pack is refused (regression like `test_act_id_and_region_names_cannot_leave_the_pack`).
3. **Placement:** an unreachable, solid or occupied tile gets a 422 sentence; with no `at`, the chosen tile is reachable and free.
4. **Loop test:** keep a face, place it, weave, and the speaker is in the baked data on a walkable tile; talking to them at that tile uses the new seed line.
5. **Play pane:** browser test: press the button and the title card renders inside the pane; the `axe-core` gate passes; the localStorage experiment is a test, not an opinion.
6. **Log and undo:** place, undo, and the game folder matches the backup byte for byte; the log and `EDITS.md` agree.
7. **Compatibility:** the sample world bakes byte-for-byte as before; a pack with no `EDITS.md` loads unchanged.

## Build order (one foreman at a time)

| # | Task | Tag |
| --- | --- | --- |
| 1 | `place_character` writer and route with preview, safety and tests | offloadable |
| 2 | Folks room: preview card and **Put in the game** | offloadable |
| 3 | `weave/play` route, the Desk pane, the localStorage test, the timing measurement | offloadable, then **keep** (review the sandbox decision) |
| 4 | Edit log, `EDITS.md` summary, undo, and wiring `map/build` | offloadable |
| 5 | Events, walk and sticker | offloadable; the sticker picture is **keep** (Rylee picks) |
