# norn - Roadmap

> The three Norns weave fate at the well beneath the world tree -
> not one fixed fate, whichever one is given them. This is the
> ladder from a tool built for one story, playable - to a tool
> anyone can point at their own.

## Landed

- [x] **the engine's identity locked in** (2026-08-31, this session):
      Norse-coded + Hero's Journey as story structure + lore packs as
      data. The journey/rune anchors are in `src/norn/journey.py`
      (whispers->Fehu, doubts->Thurisaz, feared->Kenaz, awed->Sowilo).
      Three lore packs ship: `worlds/lore/norse/` (wandering poets),
      `worlds/lore/historical-event/` (what the record couldn't hold),
      `worlds/lore/norse-runes/` (the rune-cast flavor with all 24
      Elder Futhark rune poems). Every lore pack is CC BY-SA 4.0 +
      per-pack LICENSE.md with sources. The engine reads the
      textures/names/questions; the author reads the prompt.md
      and copies it into any LLM.

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
- [x] **`ratatoskr`/`norns` - the world-tree tooling**: two CLI
      entry points, story-agnostic. `ratatoskr` is the squirrel who
      ferries messages up and down Yggdrasil - tidyup, test, weave
      (the file packager), and ferry (deploy / carry to NAS / fetch
      from Gitea). `norns` are the weavers - chat, validate,
      build-map, verify. `maplab.py` is the one geometry validator
      shared by both CLIs and the tests.
- [x] **the full rename, 2026-08-31**: this repo and package are
      `norn` now (were `old-name`, briefly `old-name`) - the umbrella under
      which `ratatoskr` (formerly `raven`) and `norns` (formerly
      `old-name`) both live as commands. Env vars
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
- [x] **`norns chat`**: the conversational world-builder. Interviews
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

- [x] **shared story state** (2026-08-31): the two phase rails were
      two variables. `web/state.js` is now the one client-side state
      (`window.OLD-STATE-GLOBAL` - a plain object, a patch function, a list of
      subscribers; no framework), and both script scopes - the town
      renderer and the tabs - read and write it. Set the world's tone
      in Rumors and the town's rail, watch radius, water level and
      canvas follow; set it in Town and the rumors rail follows.
      Keeping an item reaches the town's HUD and its gold ring without
      a tab click, because the vault list the Vault tab draws and the
      item the wanderer carries are the same list. `/api/world` is fetched
      once for the page instead of once per view. Two smaller things
      fell out of it: the rumors rail was hardcoded to the author's own
      four phase names (a story leak in engine HTML - any other pack's
      rumors silently fell back to its first phase), so it is built
      from the pack like the town's always was; and the Vault tab now
      loads the kept list when you open it rather than only after a
      forge. Validated by executing `state.js`, `town.js` and
      index.html's inline script under a stubbed DOM in node -
      including strict mode, to catch the undeclared-variable class of
      runtime bug that no syntax checker sees.

- [x] **inference backend: ollama -> llama.cpp on the 6900XT** (2026-08-31).
      Wall time on the live `norn` went from ~27.6s per rumor/bell
      to ~2-5s end-to-end (curl + SSH overhead included). Root cause
      of the old slowness: the ollama container on bazzite was the
      correct `ollama/ollama:rocm` image, but `podman inspect ollama`
      showed `Devices=[]` - no `/dev/kfd` or `/dev/dri` passed
      through, so a dense 27B Qwen was running on CPU the whole time.
      Switched to llama.cpp's OpenAI-compatible
      `/v1/chat/completions` endpoint with `gpt-oss-20b-UD-Q4_K_XL`
      (Apache-2.0, MoE 3.6B active). All five generation modules
      (`generator`, `forge`, `bell`, `npc`, `chat`) now go through
      one helper, `generator._completion(payload)`, which decides
      backend from `NORN_LLAMACPP_URL` (preferred) or `OLLAMA_URL`
      (fallback). JSON constraint is now `response_format.json_schema`
      with `strict: true`; reasoning control is
      `chat_template_kwargs.reasoning_effort=low` (gpt-oss has no
      `off` - low/medium/high only, llama.cpp maintainers confirmed).
      51/51 tests still pass - the helper is monkeypatched instead
      of the wire layer, so backend swaps stay test-clean. Two btrfs-
      on-Fedora-Atomic gotchas hit along the way (documented in
      `~/llama-server/run-gptoss.sh`): podman bind sources MUST go
      through `/var/home/rylee` not `/home/rylee` (the `/home`
      symlink to `/var/home` confuses rootless-podman statfs on the
      btrfs subvol); `HSA_OVERRIDE_GFX_VERSION=10.3.0` is required
      for the 6900XT (RDNA2/gfx1030) since llama.cpp's compiled
      runtime only recognizes gfx900/1030/1100/1200. The bazzite
      quadlet `~/.config/containers/systemd/old-name.container` was
      updated in place (note: `deploy/old-name.container` in the repo
      is a stale doc - the live game has never run on homelab-vm,
      only on bazzite; flagged separately).

## Next

- [ ] **surface UI for `surface: "combat"` packs**: the engine now
      declares the surface in world.json but the web UI + packaged
      file don't yet *render* the surface. The HP bar, the encounter
      prompt, the "attack" button that records as a journal entry -
      none of those are wired yet. This is the work that lets the
      engine's Norse-coded default feel like an RPG without ever
      gating the player on it. Packs that declare `surface: "plain"`
      (the sample world) just skip the RPG panel.
- [ ] **v1.3 - the labyrinth (act II's door)**: the memory rooms in
      order - the heels, the sentence, the dictionary, the letter -
      one wall down per accepted thing, the empty room, the
      chore-note as map. It feels like the ending. It is not.
- [ ] **v1.4 - the water (act III)**: the grave in the reeds; the
      bell rings once, warm-tuned; the the sea-figure surfaces (gold); the
      town says the name; the golden light's words arrive. The last
      screen is gold. (The reed crossing's water-level choice and the
      water's-edge sighting already landed in v1.2.)
- [ ] **`norns chat` v2**: let the interview grow the map itself
      (currently frozen at the scaffold's proven-valid layout),
      and add more than one speaker
- [ ] **more lore packs**: worlds/lore/<new-flavor>/ directories.
      Adding one is data-only (mkdir + four markdown files); the
      engine discovers it. Future flavors: homeric, east-asian-
      folklore, jewish-diaspora, contemporary-urban. Each one is
      a literary mood-board for fiction, licensed CC BY-SA 4.0.

## The always-layer

- the loop: whisper -> keep what's true -> the ledger -> the voice
  compounds
- the backups: Gitea, the durable clone, the NAS bundle
- private until it isn't: one checkbox, whenever - or never. Both
  are complete endings.
