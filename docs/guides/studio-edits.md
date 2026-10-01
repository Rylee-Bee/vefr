# Making changes to your game in the studio (edits, play it here, undo)

You make a game by changing it a little at a time and seeing the change. This page explains the three things that make that safe and quick.
It is for people first and for AI assistants second: every sentence says what happens and what to do.

## An edit is one checked change that you keep

An **edit** is one change to your game's files: painting the map, or putting a person in the game. Every edit follows the same steps:

1. **Preview.** The studio shows what would change. Nothing is written yet.
2. **Check.** The game must still pass the one check (`vefr check`). If it does not, you get a plain sentence saying what to fix, and nothing changes.
3. **Keep.** Only when you say so, the studio backs up the old file, writes the change, and adds a line to the edit log.

A helper (the Keeper of Faces, or an AI assistant in chat) can *suggest* a change. It never writes. You keep it, change it, or bin it.

## Put a person in the game

In the **Folks** room, ask for a character. The Keeper of Faces suggests someone and a place for them to stand. Press **Put in the game** (it shows a preview first).
The studio adds the person to the act's speakers and writes their voice file.

- Their id is one lowercase word (letters, digits and dashes, up to 32 characters). The studio refuses anything else before it touches a file.
- Limits: the voice up to 4000 characters, the name and the "near" phrase up to 64, each first line up to 280.
- If the id already exists, you are asked before it is replaced. If the tile is solid, flooded, taken or unreachable, you get one sentence saying which.
- **Keep** on its own only saves a character to your vault shelf. **Put in the game** is what makes them real.

For scripts and assistants: `POST /api/builder/character/place` with `{"name", "id", "display_name", "near", "seeds", "voice", "region", "at", "preview", "force"}`.
`preview: true` writes nothing. It answers 422 with plain sentences, 409 if the id exists, 404 for an unknown game.

## Play it here

On the **Desk**, press **Play it here**. The studio weaves your game and shows it in a pane on the page. There is nothing to download. The pane is sandboxed, so the game cannot reach the studio.
**Open in a new tab** is there if you want a bigger view. If you change something, press it again to see the change.

## Undo the last edit

`POST /api/builder/edits/undo` with `{"name": "<game>"}` puts the last kept edit back from its backup, removes its line from the log, and answers in plain words what it undid.
It undoes one step. If there is nothing to undo, it says so (404); if the backup is missing or not made by this studio, it refuses (409).
**Undo last edit** is a button on the Desk, beside **Play it here**.
Press it and the studio calls `POST /api/builder/edits/undo` for the game you are playing.
The route's plain-sentence answer appears right there on the Desk, in the status line beside the button.

## Where the record lives

- **The studio keeps the full log** in its data folder (`data/edits.jsonl`): who made the edit (the player or a helper), when, which files, and where the backup is.
- **Your game folder keeps `EDITS.md`**: one readable line per kept edit ("put Stern at the gate"). It travels with your game when you share it. A game without the file works as before.

## For people changing the studio

The code is `src/vefr/edits.py` (the log and undo), `src/vefr/main.py` (the routes), and `web/js/rooms/characters.js`, `web/js/rooms/workshop.js` (the rooms).
Any path built from a request or from the log goes through `cli._inside` before any disk probe; there are tests that try `..`, slashes and absolute paths.
Design notes: `design/close-the-loop.md`, `design/named-edits.md`.
