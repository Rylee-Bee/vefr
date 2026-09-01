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
      The helper is monkeypatched instead
      of the wire layer, so backend swaps stay test-clean. Two btrfs-
      on-Fedora-Atomic gotchas hit along the way (documented in
      `~/llama-server/run-gptoss.sh`): podman bind sources MUST go
      through `/var/home/rylee` not `/home/rylee` (the `/home`
      symlink to `/var/home` confuses rootless-podman statfs on the
      btrfs subvol); `HSA_OVERRIDE_GFX_VERSION=10.3.0` is required
      for the 6900XT (RDNA2/gfx1030) since llama.cpp's compiled
      runtime only recognizes gfx900/1030/1100/1200. The bazzite
      quadlet was updated in place.

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
      format. The canary pack validates
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
- [x] **the LAN left the source** (2026-08-31): `VEFR_GITEA_URL`,
      `VEFR_LIVE_URL`, `VEFR_DEFAULT_DEPLOY_HOST`, and
      `VEFR_DEFAULT_BACKUP_LOCATION` (host:/path) replace the
      hardcoded Gitea IP, the live-stack IP, and the SSH host
      aliases - the engine source now carries neutral localhost
      defaults and takes its identity from the environment. The
      scaffold README derives its engine link from the checkout's
      own `origin` at runtime. Runtime data, not repo data.

- [x] **the reading row** (2026-08-31, this session): the
      Reading & sound panel, opened from a 44px trigger in the
      title bar, slides up as a bottom-sheet on mobile and a
      centered dialog on desktop. Three columns named for the
      three Norns: **Urd** (recalled settings, reset, share-link),
      **Verdandi** (live controls - text size, line spacing,
      font, contrast, colorblind-safe palette, motion, focus
      ring, density), **Skuld** (live preview of how the page
      reads right now). English labels lead; Norse names ride
      visibly as a secondary line. The full contract:
      `window.VEFR_PREFS.{get,set,preview,reset,on,shareLink,
      applyFromUrl}`; persistence is localStorage under
      `vefr-prefs`; cross-device sync is a base64-encoded URL
      (`?prefs=...`) you copy via the **Deila** button. The
      stylesheet keys off a single `<html data-prefs="...">`
      attribute set on every set/preview, so adding a new
      preference is one CSS rule and one `[data-pref-key]`
      select. The always-layer's reading row is part of the
      gate. Self-hosted Atkinson Hyperlegible Next + OpenDyslexic
      woff2 tracked under `web/fonts/` (SIL OFL); until the
      binaries are downloaded the @font-face rules 404 silently
      and the body falls through to its system serif. See
      `docs/guides/identity-terms-glossary.md` for the terms
      the panel uses.
- [x] **companion resources surveyed** (2026-08-31): a full
      CC0/MIT tool survey (engines, renderers, map authoring,
      narrative tools, art editors, audio, dev workflow) kept as a
      local research note - gitignored, since the repo may publish
      one day. Durable decisions: Kenney CC0 art ships as pack
      data once the renderer grows sprite support; Tiled (then
      LDtk) importers parked after the surface-UI work; rot.js
      algorithms get borrowed for mapgen when `norns chat` v2
      opens; frameworks skip (the custom renderer stays
      canonical); the ebook export stays a stdlib writer; idea
      credits for incompatible-but-borrowed sources live in
      README's Attribution section.

- [x] **the bones stop talking** (2026-08-31, this session):
      A1+A2+A3+A4 - the strip. Every user-visible string in the
      engine that named a specific pack's voice, place, or
      speaker (the mill / the bell / the tower / the bookshop /
      the bog / the ferryman / the roll-keeper / the wanderer / the sea-figure) is gone or
      replaced with engine-neutral prose. The engine paints
      nothing where a pack would speak - tabs show empty
      status until `/api/world` returns, the whisper button
      says `listening...` / `whispered` / `nothing came back`
      instead of `the mill turns / the mill is warm / the
      mill is silent`, the Skuld preview shows em-dashes
      where the pack's phase + speaker would live. Comment
      drift (`the wanderer` in `state.js` / `town.js`,
      `Old Name` in `world.py`, `private-canon` in `volumes.py` /
      `cli.py` / `main.py`) replaced with engine-neutral
      identifiers; the one load-bearing `private-canon` rename
      in `norns build-map`'s scaffold helper gets an
      explanatory comment so the history isn't lost. The
      `norns chat` builder's system prompt no longer names
      example NPCs from the author's canon. README's
      "bones and the flesh" section now carries a worked
      example: develop on vefr, write the game in
      `the private story repo`, ferry fetch to play. The bones
      stay empty until a pack mounts.

- [x] **the dev board** (2026-08-31, this session): the Dev zone's
      github-projects-style board - the pack's four generators
      (whispers / voices / forge / bell) as draggable cards in a
      file-tree chrome. Cards are drawn from the loaded pack
      (/api/world, shared fetch - one request per page); a column
      the pack cannot fill is seeded from a deterministic
      engine-neutral pool (Norse-coded names, no canon strings -
      the strip holds here too), so the board is never empty and
      never storyful. A fresh seed per browser persists in
      localStorage (`vefr-board-seed`), so a run is reproducible
      but never identical to the pack. Dragging a card between
      columns re-homes it and persists (`vefr-board-cards`), with
      an honest "moved" timestamp; a fresh boot loads the store
      instead of regenerating. The right rail (hidden until a card
      is selected) shows the column's real endpoint, request and
      response shapes, a "try it" button that calls the endpoint
      like the game's own buttons do (and says plainly when the
      engine does not answer), and a draft box reserved for
      `norns chat` wiring. The board boots lazily on its own tab
      - the Play path never asks for it - and `web/board.js` is
      machine-tested two ways: the vm contract harness
      (tests/fixtures/board_harness.mjs) and the full-DOM
      harness's tab tour, which now proves the board adds no
      second /api/world fetch. Packaged play files are untouched
      (the board is a served-UI Dev feature). Editing cards
      belongs to `norns chat`, not a textarea - navigation-only
      chrome on purpose.

- [x] **the shadcn layer** (2026-08-31, this session): the UI
      adopts shadcn/ui's design language as a token vocabulary +
      component anatomy - CSS custom properties only. No React, no
      Tailwind, no build step: the packaged single-file stays
      self-contained. The shadcn names (--background, --foreground,
      --card, --border, --ring, --primary, --radius...) are DERIVED
      tokens referencing the engine's own luminance-first palette,
      so the reading row's contrast/palette overrides flow through
      the entire new vocabulary unchanged - the focus ring became a
      token (--ring), replacing two long per-selector pref lists
      with one rule pair. Buttons, cards, and inputs collapsed from
      ~8 near-duplicate blocks each into one :is() anatomy (outline
      default, solid primary variant, 44px minimums, motion off);
      radii follow shadcn's scale (one base, sm/md/lg/xl derived).
      The board stylesheet rides the same tokens. The town canvas
      renderer stays custom (the rpg-js decision stands - this
      layer dresses the document UI, not the game canvas).

- [x] **the drag layer** (2026-08-31, this session): the board's
      pointer drag moved to vendored SortableJS 1.15.7 (MIT, 45KB,
      classic script, provenance in web/vendor/README.md) - native
      HTML5 DnD has no touch support, so the board was desktop-only
      before. Drops now keep their dropped position (the store syncs
      to the DOM order instead of re-rendering), the ghost/chosen
      states use the token vocabulary, and native DnD remains as the
      honest fallback when the vendor file is absent (the test
      sandbox, a packaged file without it). Keyboard users re-home
      cards without a pointer at all: the rail carries one button
      per column (current column disabled), every move announces
      through an aria-live status line. @dnd-kit/dom was evaluated
      first and rejected on evidence: v0.5.0 ships ESM-only (verified
      against the jsDelivr entrypoint), which would force an import
      map or bundler onto a no-build repo. Two real bugs caught by
      the vm harness on the way in: syncColumns originally resolved
      cards only from the target column's store array (a card
      dragged in from another column would have been silently
      dropped) and the move() rewrite had lost its render() call.

- [x] **the draft wires to the smith** (2026-08-31, this session):
      the board rail's draft box is live - it was shipped inert with
      an IOU and now keeps its promise. One thread per card, held by
      the page (the /api/builder/chat endpoint is stateless; the
      last 6 turns replay for context). Every turn carries the
      card's context - name, kind, column, current text - so the
      smith knows what the author is pointing at; the wire format
      keeps the composed message while the rail's log renders the
      short draft. The thread dies with the page: drafts are
      conversation, not lore (nothing is persisted to the pack).
      Offline, the turn comes back out of the thread and the rail
      says so plainly - the draft stays yours. The vm harness drives
      the full contract: context in the composed message, both turns
      logged, textarea cleared, honest failure leaving the thread
      empty.

- [x] **one shell, every zone** (2026-08-31, this session): the
      layout instability Rylee flagged - the page swapped between a
      narrow reading column (Play/World) and a wide workbench (Dev),
      and the World zone was a third unrelated body of bare lists -
      is gone. The shell is one width everywhere (min(80rem,
      100% - 2rem)); reading surfaces cap their own line length
      (46rem) because the short-line reading win belongs to the
      text column, not the page. The World pane now wears the same
      skeleton as the board: Characters / Relics as two columns of
      selectable cards (role=button, Enter/Space, aria-pressed,
      luminance ring) with the full record in a shared right rail.
      The pane vocabulary (board-container / board-column /
      board-cards / board-rail) is the app's shared skeleton;
      Play keeps its inline cards for now - they already show their
      whole content, and hiding it behind a selection would add
      reading load, not remove it.

- [x] **the reachable UI** (2026-08-31): header earns its title,
      9 flat tabs become 3 static zones (Play / World / Dev) with
      plain-English labels leading and Norse secondary, 44px+ targets,
      luminance-only active states, prefers-reduced-motion honored,
      keyboard focus-visible tokens, and the reading row (text size,
      line spacing, contrast, fonts) built on VEFR_PREFS.

- [x] **ratatoskr weave --pool** (2026-08-31): pre-generation pass
      during packaging inlines `window.VEFR_POOL` for offline play
      with per-combo spending tracked in localStorage and fallback to
      honest silence when spent.

- [x] **surface UI for `surface: "combat"` packs** (2026-08-31,
      `06eed41`): the web UI renders the surface. `web/index.html`
      gains the HP bar (`.hud-hp`, combat surface only), the
      phase-dependent encounter prompt (hidden in the whispers
      phase), the combat verb row posting to `/api/combat/action`
      with the response landing in the journal, and the
      `<body data-surface="...">` attribute set from the
      `/api/world` payload at load. HP is synthesized per-phase by
      `combat.hp_for_pack()`, so packs need no hp data of their
      own; plain/investigation surfaces hide the whole costume
      via CSS. Verified live on bazzite (2026-09-01): `/api/world`
      serves `surface: combat` + `hp: {current: 4, max: 4,
      per_phase: {dusk: 3, dawn: 4}}`. The half still open:
      `web/packaged.html`, the weave artifact, has none of it
      (Next keeps that scoped item).

- [x] **audit 2026-09-01** (2026-09-01): 10 PR sequence resolving
      live scaffold NameError, pack contract verification (stefna_voice,
      voices dual convention, strike prompt), final story prose and
      pronoun stripping, AST shape-based neutrality guard, vefr renaming
      sweep across web globals/events, and test harness execution for
      the reading row controller.

- [x] **dev overlay & aspect inspector + engine maintenance bundle** (2026-09-01, this session):
      In-game development overlay & aspect inspector drawer with
      accessible 44px trigger, dark-mode styling, and keyboard shortcuts
      (` and F12), wired to `GET /api/builder/aspects`. Surfaces loaded pack
      aspects, active act structure, region metadata, speaker seed matrices,
      living rune cast, and recent trace events. Full DOM harness coverage
      and FastAPI route verification. Plus mechanical cleanup bundle:
      deduplicated journey attachment in `world.py` (L2), extracted shared
      `UndoBuffer` helper in `sessions.py` preserving living tree touch
      semantics across vault and journal (L3), populated speaker source on
      `NpcLine` (L4), resilient FastAPI title & static mount handling (M5),
      and robust `app_home()` fallback guards for unbundled installs (M6).

- [x] **contextual AI enhance** (2026-09-01, this session):
      Scoped structured generation calls tailored to the active screen
      and resource in authoring and dev views. Implemented `src/vefr/enhance.py`
      with strict JSON schemas for map/POI descriptions, speaker voice prompts &
      dialogue rules, and relic forge flavor/curses. Wired into FastAPI at
      `POST /api/builder/enhance/{map,voice,item}` and integrated into the
      Builder tab with accessible triggers and status reporting. Tested with
      dedicated test suite (`tests/test_enhance.py`).

- [x] **`ferry deploy` hardened as the single ship button** (2026-09-01,
      this session). `ratatoskr ferry deploy` now owns the bazzite
      deploy path end-to-end: pre-flight gate (`pytest -q` +
      `norns validate --pack sample-world`, `--skip-tests` to bypass),
      rsync the checkout, skip `podman build` when the remote image's
      `vefr.engine_sha` label already matches the local HEAD
      (`--rebuild` to force), `systemctl --user restart vefr`,
      ensure the `vefr-{template,worlds}` named volumes exist,
      post-deploy `/api/health` + `maplab verify` (`--no-health` to
      bypass). `--init` writes `deploy.toml.example` + the README
      path; the wrapper refuses to run with the silent `bazzite`
      default and points operators at `--init` (a fresh clone
      without a host should explode loudly, not `ssh` a hostname
      that resolves to nothing). `Containerfile` stamps
      `ENGINE_SHA=$(git rev-parse HEAD)` as a label so the
      no-op-skip works; `VEFR_DEPLOY_IMAGE` env override. New guide
      `docs/guides/deploy.md`; cross-link in `GETTING_STARTED.md`.
      Legacy `docs/guides/deploy-rsync-dance.md` kept for old
      bind-mount hosts. Tested in `tests/test_deploy.py` (4 new
      tests, full suite 200 passed).

- [x] **deploy-day fixes, atomic with the first wrapper deploy**
      (2026-09-01, `a11e532`). Two bugs the first ferry deploy
      exposed: `norns validate --pack sample-world` accepted only
      real paths and raised `FileNotFoundError` on a bare name, so
      the pre-flight gate could never pass - `maplab.cmd_validate`
      now resolves bare names through `pack_root()` the way
      `handbok`/`doctor`/`export` already did (3 tests in
      `tests/test_validate_pack_path.py`). And the post-deploy
      health probe hit `127.0.0.1` on the dev box (its `bazzite`
      SSH alias resolves to the wrong host) and gave up after one
      fixed 2-second sleep - it now probes through an SSH
      port-forward with a 20-attempt x 1.5s retry loop.

- [x] **dev zone polish: board, draft thread, inspector filter**
      (2026-09-01, PR #32, `526e06c`). Board drags within a column
      now announce `reordered in <col>.` in the board-status
      aria-live region (cross-column moves already did; intra-column
      was silent), and cards get a grabbing cursor while held. The
      draft-to-the-smith thread renders as labeled paragraphs
      (`board-chat-user` / `board-chat-smith`, luminance carries the
      role) instead of one flat text blob, auto-scrolls to the
      newest turn, gains a Clear thread button, and says under the
      log that the last 6 turns replay - the 7-turn harness run
      proves the cap. The aspect inspector gains a section filter
      (`dev-drawer-filter` + aria-live match count) that re-renders
      from the stored `/api/builder/aspects` payload - no refetch
      per keystroke; an empty query restores all six sections, and a
      no-match query says `no sections match.` plainly. Two real
      bugs the harnesses caught before any human did: the smith
      paragraph was classed `board-chat-assistant` (the CSS and the
      claim say smith), and the filter read `.html` off a string.
      Live on bazzite after deploy (`526e06c`): served index.html
      carries the new ids, served board.css carries the grabbing
      cursor. Discovered and fixed along the way: the dev-box
      `bazzite` SSH alias is now correct (user `rylee` @
      `192.168.2.76`), so `VEFR_DEPLOY_HOST=bazzite` is the right
      value - a bare IP literal drops the user and rsync fails.

## Next
- [ ] **interactive chat helper**: inline conversational assistant in
      the builder UI answering world-building questions and adjusting pack data.
      Acceptance: persistent 6-turn chat in Builder tab successfully calls
      `/api/builder/chat` with pack context.
      (Existing machinery: `chat.py`, `/api/builder/chat`).
- [ ] **formatted ebook export**: single-document narrative exporter
      formatting playthroughs with chapter headings, character wiki, and
      collected relics. Acceptance: `/api/export` generates clean e-reader
      compatible EPUB/Markdown artifact with full metadata.
      (Existing machinery: `export.py`, deterministic preface templating).
- [ ] **engine + world full git scaffold**: standalone repository exporter
      packaging engine bones and author pack into an independent git project.
      Acceptance: `ratatoskr ferry scaffold --full` creates functional standalone
      repo with passing offline test suite.
      (Existing machinery: `cmd_scaffold`, pack contract loader).
- [ ] **surface UI in the packaged file**: the web UI half landed
      (`06eed41`, see Landed) but `web/packaged.html` - the
      single-file weave artifact - still has no surface costume
      (zero matches for hud-hp / data-surface / encounter-prompt /
      verb-row). The weave template needs the same HP bar,
      encounter prompt, and verb-row treatment before offline
      packaged play shows the combat surface.
- [ ] **Tiled map importer** (parked after the surface-UI work):
      `norns import-tiled map.json --pack X` reads Tiled's JSON
      export - visual map authoring, the storyteller-critical gap -
      and writes `map.md` + contract points through
      `maplab.build_map` + `maplab.validate()`. Thin and optional;
      text authoring stays canonical, no Tiled dependency. Tiled
      1.10's JS scripting API could later host a one-click "export
      as vefr pack" from inside the editor. See
      `docs/guides/companion-resources.md`.
- [ ] **`norns chat` v2**: let the interview grow the map itself
      (currently frozen at the scaffold's proven-valid layout),
      and add more than one speaker
- [ ] **more lore packs**: worlds/lore/<new-flavor>/ directories.
      Adding one is data-only (mkdir + four markdown files); the
      engine discovers it. Future flavors: homeric, east-asian-
      folklore, jewish-diaspora, contemporary-urban. Each one is
      a literary mood-board for fiction, licensed CC BY-SA 4.0.
- [ ] **research: offline/no-server generation fallback for shared
      packaged games**. Purpose-built small generators for a world
      with no precomputed pool. The pool covers the common case
      (author has a model, friend does not).

- [ ] **the marketplace**: a community place to share, search, and
      rate engine add-ons - world packs, lore packs, sprites, map
      recipes, and model settings ("local LLM packs": someone's
      perfect llama.cpp + gpt-oss configuration for their exact
      hardware, shareable as data). The distribution path already
      exists (`ferry fetch --pull`, the Builder tab's import by
      owner/name), so v1 is an index over plain git repos, not new
      infrastructure - ratings live with the community, and
      discovery may grow a `norns market` command. The always-
      layer's "private until it isn't" made social.
- [ ] **accessible controls and audio-pairing**: the keybinds remap
      (GAG Basic, localStorage config) and audio-pairing hooks for
      visual event pairing when sound effects land.

## The always-layer

- the loop: whisper -> keep what's true -> the ledger -> the voice
  compounds
- the backups: Gitea, the durable clone, the NAS bundle
- inclusive-forward: every screen answers for different needs -
  reading load, target size, contrast over color, motion off by
  default, and when sound arrives, every sound paired with a
  visual event. It is part of the gate, not a follow-up.
- private until it isn't: one checkbox, whenever - or never. Both
  are complete endings.
