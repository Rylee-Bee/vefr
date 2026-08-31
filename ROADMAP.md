# norn - Roadmap

> The three Norns weave fate at the well beneath the world tree -
> not one fixed fate, whichever one is given them. This is the
> ladder from a tool built for one story, playable - to a tool
> anyone can point at their own.

## Landed

- [x] **v0.1 - the skeleton**: FastAPI + ollama structured output,
      parchment UI, quadlet deploy on bazzite
- [x] **v0.2 - the ledger**: collected whispers become the engine's
      voice anchors (Rylee curates; the cadence compounds)
- [x] **v0.3 - the forge & the vault**: items with three bonds -
      assigned (church-blue), attuned (gold, rare on purpose), cold
      (grey). Offer your hand. Kept items persist on bazzite.
- [x] **v0.4 - the bell**: the bog at night, one ring per visit, the
      mother's chore-note in her voice - headed "For you."
- [x] **the canon**: the archive, Private Canon, the wanderer, the bell, the
      church, the dictionary, the laughing room, the labyrinth, the
      monsters, Bog & Bell style, the Gold Rule
- [x] **the founding myth**: the Keeper's empty throne, the Weaver's
      scorn, the Untongued - the Conserved Word vs the Fen Verse
- [x] **v1.0 - first tiles**: MAP.md became a walkable grid; the wanderer
      leaves the bookshop; the tower's sightlines became geometry you
      can feel
- [x] **v2.0 - the bones and the flesh**: engine/world split. All
      canon moved into worlds/private-canon/ (bible, ledger, map,
      voices, world.json); the engine reads everything through the
      pack loader. The town renderer is world-driven (/api/world).
      MIT on the bones; the flesh stays private. Someday: hand
      someone the bones, they grow their own story.
- [x] **the hearth**: the old soldier and the housekeeper come to Private Canon -
      the soldier's house in the church's own shadow, one standing
      gold window, a sanctuary threshold the watch never crosses,
      plain speech and corn-bread. The the sea-folk join the canon: the
      Weaver's people, the name-keepers, seen once at the water's
      edge. And one law from the sealed layer: the game never holds
      her under.

- [x] **v1.2 - items in the world**: the vault became the game's
      inventory (carried item in the HUD); attunement on screen
      (gold ring, gold only when the world is kind); the reed
      crossing's water level became a choice (high in feared); the
      the sea-figure sighting at the water's edge (awed, gold, once).
      And the town grew 30x20 -> 40x28: the moot hall (Old the roll-keeper
      keeps the roll), Katla's tavern (rumors are born there),
      Sigga's store (her ledger is not the parish ledger) - all
      with doors, verified reachable by flood-fill.
- [x] **the storytelling layer named**: style.py is saga.py -
      for the goddess who keeps stories at Sokkvabekk. Bragi
      composes the prompts; Idunn keeps the ledger that renews
      the voice.
- [x] **the rpg-js question**: answered 2026-08-30 - the custom
      renderer stays canonical. RPG-JS stays admired (MIT, a fine
      tool), and the door remains open through the pack contract:
      any future render target reads the same /api/world.
- [x] **`raven`/`old-name` - the lab-style wrapper**: two entry points,
      raven and smith - universal tooling, story-agnostic.
      `raven tidyup/deploy/backup/test`, `old-name validate/build/verify`.
      `maplab.py` is the one geometry validator shared by both CLIs
      and the tests.
- [x] **the full rename, 2026-08-31**: this repo and package are
      `norn` now (were `old-name`, briefly `old-name`) - the umbrella under
      which `raven` and `old-name` both still live as commands. Env vars
      (`NORN_HOME`, `NORN_WORLD`, `NORN_MODEL`, `NORN_VAULT`,
      `NORN_KEEP_ALIVE`), and every hardcoded story reference in the
      engine (the API title, the health check's service name, the
      shared rumor system prompt, `world_name()`'s private-canon
      special-case) are gone. "Old Name" is free to mean only the game.
      The story itself (`worlds/private-canon/`, `STYLE.md`) moved to
      its own private repo, `the private story repo`, verified
      byte-identical before the move; the engine repo's history was
      then rewritten (`git filter-repo`) so no trace of it remains in
      any commit.
- [x] **the bones boot alone**: `worlds/sample-world/` (Emberfield) -
      a demonstration pack with zero story content, proven by
      physically removing the author's own pack and running the suite
      green. The engine works with any pack, or none beyond the
      sample.
- [x] **license split**: engine MIT (`src/`, `web/`, `tests/`,
      `deploy/`, `Containerfile`, `worlds/sample-world/`);
      `worlds/private-canon/` is the author's own story and game - all
      rights reserved, see `worlds/private-canon/LICENSE`.
- [x] **`old-name chat`**: the conversational world-builder. Interviews
      canon, theme colors, phases, bonds, and one speaker's voice
      against the local ollama, starting from `worlds/sample-world/`
      so geometry can't break. The interview's flow is deterministic
      Python; the model only ever fills in prose or a hex color
      inside a schema it can't escape - `maplab.validate()` runs
      after every write. Fixed alongside it: every schema-constrained
      call in the engine (`generator`, `forge`, `bell`, `npc`, `chat`)
      now sends `"think": false` - the thinking model was dumping its
      chain-of-thought into the one string field a JSON schema left
      it, which would have shown up as narration inside rumors, item
      names, and the bell's letter.

- [x] **the session journal + story export** (2026-08-31): the
      vault was the only thing that persisted; now `journal.py` keeps
      a timestamped record of every rumor heard, line spoken, item
      kept, and the bell's letter - same atomic tmp+replace write as
      the vault, `NORN_JOURNAL` to move it. `main.py`'s existing
      routes log after each generation, so the record is a byproduct
      of play, not a chore. `export.py` weaves the pack's title +
      bible.md + the journal + the vault into one markdown document
      by deterministic templating (never a model call: it must work
      with ollama cold and must match what actually happened). New
      routes `GET /api/journal`, `POST /api/journal/clear`,
      `GET /api/export`; a Journal tab in `web/` reads the timeline
      back and downloads the story as a `.md`. A model-polish pass
      over the export stays available as a v2.

## Next

- [ ] **v1.3 - the labyrinth (act II's door)**: the memory rooms in
      order - the heels, the sentence, the dictionary, the letter -
      one wall down per accepted thing, the empty room, the
      chore-note as map. It feels like the ending. It is not.
- [ ] **v1.4 - the water (act III)**: the grave in the reeds; the
      bell rings once, warm-tuned; the the sea-figure surfaces (gold); the
      town says the name; the golden light's words arrive. The last
      screen is gold. (The reed crossing's water-level choice and the
      water's-edge sighting already landed in v1.2.)
- [ ] **shared story state**: the town's phase rail and the rumors
      rail become one state, carried across views
- [ ] **`old-name chat` v2**: let the interview grow the map itself
      (currently frozen at the scaffold's proven-valid layout),
      and add more than one speaker

## The always-layer

- the loop: whisper -> keep what's true -> the ledger -> the voice
  compounds
- the backups: Gitea, the durable clone, the NAS bundle
- private until it isn't: one checkbox, whenever - or never. Both
  are complete endings.
