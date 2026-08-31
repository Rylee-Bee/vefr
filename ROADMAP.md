# vefr - Roadmap

> The three Norns weave fate at the well beneath the world tree -
> not one fixed fate, whichever one is given them. This is the
> ladder from a tool built for one story, playable - to a tool
> anyone can point at their own.

## Landed

- [x] **the engine's identity locked in** (2026-08-31, this session):
      Norse-coded + Hero's Journey as story structure + lore packs as
      data. The journey/rune anchors are in `src/vefr/journey.py`
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
- [x] **the canon**: the archive, Private Canon, the hero, the bell, the
      church, the dictionary, the laughing room, the labyrinth, the
      monsters, Bog & Bell style, the Gold Rule
- [x] **the founding myth**: the Keeper's empty throne, the Weaver's
      scorn, the Untongued - the Conserved Word vs the Fen Verse
- [x] **v1.0 - first tiles**: MAP.md became a walkable grid; the hero
      leaves the bookshop; the tower's sightlines became geometry you
      can feel
- [x] **v2.0 - the bones and the flesh**: engine/world split. All
      canon moved into worlds/private-canon/ (logbok, ledger, map,
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
      ferries messages up and down Yggdrasil - skipa, test, weave
      (the file packager), and ferry (deploy / carry to NAS / fetch
      from Gitea). `norns` are the weavers - chat, validate,
      build-map, verify. `maplab.py` is the one geometry validator
      shared by both CLIs and the tests.
- [x] **the full rename, 2026-08-31**: this repo and package are
      `vefr` now (were `old-name`, briefly `old-name`, then `norn`) - the
      umbrella under which `ratatoskr` (formerly `raven`) and `norns`
      (formerly `old-name`) both live as commands. Env vars
      (`VEFR_HOME`, `VEFR_WORLD`, `VEFR_MODEL`, `VEFR_VAULT`,
      `VEFR_KEEP_ALIVE`), and every hardcoded story reference in the
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
      the vault, `VEFR_JOURNAL` to move it. `main.py`'s existing
      routes log after each generation, so the record is a byproduct
      of play, not a chore. `export.py` weaves the pack's title +
      logbok.md + the journal + the vault into one markdown document
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
      item the hero carries are the same list. `/api/world` is fetched
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
      Wall time on the live `vefr` went from ~27.6s per rumor/bell
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
      backend from `VEFR_LLAMACPP_URL` (preferred) or `OLLAMA_URL`
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

- [x] **the always-array world loader + the visible engine**
      (2026-08-31). `load_world()` now returns a single canonical
      shape: top-level keys (title, phases, surface, logbok,
      ledger, voices, bonds, acts) and `acts` is ALWAYS a list.
      Two on-disk shapes are supported. Flat: worlds/<name>/
      world.json + voices/ + map.md (legacy packs still work).
      Acts: worlds/<name>/world.json (pack-level contract) +
      acts/<id>/world.json (act contract) + acts/<id>/<region>/
      (map.md, voices/, sprites/). The loader walks the tree
      and discovers voices/sprites by convention. maplab.load_pack
      and maplab.write_pack round-trip both shapes; chat.py
      writes a new pack in whichever shape the scaffold uses.
      `current_act(world)` and `current_town(world)` are the
      accessors; every consumer reads through them. The canary
      pack `sample-world/` is migrated to the acts shape. The
      `surface` field is now in the always-array payload so the
      web UI can branch on it in a follow-on PR. Every loader
      step is recorded to `data/weave.jsonl` (the weave log) and
      surfaced at `/api/weave`. The Builder tab gets a "What the
      engine sees" panel that shows the resolved world and
      packages a markdown handoff bundle for an AI-buddy
      debugging session - see `docs/guides/handoff.md` for the
      format. 159 tests pass; the canary pack validates
      identically before and after the migration.

- [x] **the kilo init** (2026-08-31): `AGENTS.md` (the repo's
      operating rules - bones/flesh contract, the boundaries table,
      the gate command, the known drift) and `.kilo/kilo.jsonc`
      (project config: instructions = AGENTS.md only, uv/pytest/git
      allow-list, `data/**` + `uv.lock` edit-deny) are now tracked.
      Rylee's profile + shared agent rules load from the global
      kilo config, so this repo's instructions list stays one entry.

- [x] **the handoff guide caught up** (2026-08-31):
      `docs/guides/session-handoff.md` refreshed to the kilo-init
      HEAD + the 171-test gate; all three "honest gaps" closed out
      with evidence (real pool weave landed, mem0 live again,
      `tests/test_web_packaged.py`); the next-move table repointed
      at the surface-UI continuation.

## Next

- [ ] **the engine is a game too** (2026-08-31): the umbrella. Every
      part of the story and the engine - replaceable, modifiable,
      fork-able from a dev menu, each enhanced by the local AI chat:
      a structured template call scoped to the screen/resource
      you're on, plus a chat box that answers little questions as
      you go. The aspects (lore packs, act structure, graphics
      resources, maps) callable and visible in the UI and over the
      API. The container stays bones-ro / story-rw (the volumes
      work); the story packs and exports as a real formatted ebook
      with your own unique playthrough; the journal is always there
      to revert and fork from - git-like history, honesty contract
      applied to the game itself. And the export can go all the
      way: a fully formed git repo, bones and world together, so
      playing the game teaches the development process. Most of the
      machinery exists (volumes ro/rw, pack contract, journal
      rewind/fork, deterministic export, `ferry scaffold`); the
      gaps are presentation - the dev menu, per-screen enhance
      calls, the chat box, ebook formatting, a bones+world
      scaffold. The shape of it: the homelab repo's two months -
      git, PRs, an honesty contract, deploys - but fun, with
      training wheels, a cool UI, and a story. The surface UI,
      `norns chat` v2, and the pack contract work below all serve
      this.
- [ ] **surface UI for `surface: "combat"` packs**: the data shape
      now carries the surface (the always-array loader exposes it
      on every /api/world response) but the web UI + packaged
      file don't yet *render* the surface. The HP bar, the
      encounter prompt, the "attack" button that records as a
      journal entry - none of those are wired yet. The
      `<body data-surface="...">` CSS hook is in place from the
      loader work; this is a HUD-only PR now.
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
- [ ] **research: offline/no-server generation fallback for shared
      packaged games**. Today's `ratatoskr weave` output still needs
      a live OpenAI-compatible endpoint (VEFR_LLAMACPP_URL or
      OLLAMA_URL) to generate anything - a friend you send a .html
      file to needs their own model server. Siri/Apple Intelligence
      and Android's Gemini Nano are dead ends for a browser-based
      packaged file (native-app-only APIs, no web page access);
      Chrome's experimental on-device AI API is Chrome-only and
      origin-trial-gated. The real candidate is purpose-built, not
      a general LLM: a small, narrow generator (a tiny fine-tuned
      model, a retrieval+recombination system over the pack's own
      voice files, or a template/Markov approach) that only needs
      to do what this engine actually asks for - short,
      schema-constrained JSON (one rumor, one line, one letter) -
      not general-purpose writing. Weaker prose than gpt-oss-20b,
      but zero-setup for whoever you hand the file to.
      hand the file to.

      The most promising shape found so far: split by platform, not
      by trying to build one fallback model that works everywhere.
      Desktop/world-building keeps the live local LLM (full power,
      you're actively authoring). Mobile/handed-to-a-friend play
      uses a pool PRE-generated by that same LLM during authoring,
      not hand-written templates - the rune cast's shape is finite
      (24 runes x N phases x N speakers), so a `ratatoskr weave`
      step could ask the live model for several real generations
      per rune/phase/speaker combination and bake that pool into
      the packaged file. Mobile play then pulls from the pool for
      whichever rune/phase/speaker actually lands, reusing the rune
      cast's own no-duplicate-within-a-draw rule so it doesn't feel
      like picking from a fixed list even though nothing is calling
      a model live. Explicitly NOT a static phrase bank / mad-libs
      table by hand - every line in the pool is real model output
      in the pack's own voice, just precomputed instead of live.

      The investigation, closed (2026-08-31) with concrete numbers
      for the build:

      | Question | Answer |
      |---|---|
      | What are the combinations, really? | whispers: 4 phases; voices: 4 phases x N speakers (~7 = 28); stefna: 1 slot; forge: 1 slot. ~34 combos, not 24 runes x anything - the cast shapes *which* pool entry is drawn, not how many exist |
      | Samples per combination | 5. Enough that the no-duplicate rule has room across a long sitting; 10 doubles packaging time for a difference play can't feel |
      | Packaging cost | ~175 generations at 1-2s on the 6900XT llama.cpp = 3-6 minutes of authoring, once, at weave time |
      | Pool size | ~175 entries x ~400B = ~70KB (10 samples: ~140KB) - inline it |
      | Embed vs sidecar | Inline into the packaged HTML. The single file is the unit of sharing; a sidecar would break "send it as one attachment" |
      | Spent-pool behavior | Track used (speaker, line) pairs in localStorage; when a combo's pool is spent, fall back to unused lines from the same phase, then say so plainly: the pool is spent, the world waits for its author to re-weave |

      Build shape: `ratatoskr weave --pool` runs the pre-generation
      pass during packaging and inlines `window.VEFR_POOL = {combo:
      [lines...]}` next to the other VEFR_* globals. The packaged
      page already has a no-endpoint path to hang it on; play falls
      back to the pool whenever no live endpoint is configured or a
      call fails.

      LANDED (2026-08-31): `ratatoskr weave --pool N` is live, the
      packaged page draws from the pool with per-combo spending
      tracked in localStorage, the first real-model weave ran
      end-to-end in the container against the warm 6900XT
      (sample-world, 1 sample per combo, 10 lines, 24KB file), and
      the pool-draw runtime itself is machine-tested
      (tests/test_web_packaged.py executes the shipped poolDraw code
      in a node vm: no repeats, cross-combo fallthrough, honest
      null when spent). The deeper research item above - purpose-
      built small generators for a world with NO pool at all -
      stays open; the pool covers the common case (author has a
      model, the friend does not).

## The always-layer

- the loop: whisper -> keep what's true -> the ledger -> the voice
  compounds
- the backups: Gitea, the durable clone, the NAS bundle
- private until it isn't: one checkbox, whenever - or never. Both
  are complete endings.
