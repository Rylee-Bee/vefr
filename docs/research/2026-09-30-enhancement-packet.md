# vefr enhancement packet

> A survey of open-source projects, toolsets, engines, and ideas that could
> grow vefr. Compiled 2026-09-30 from GitHub topic sweeps (sorted by stars)
> and open-web research. Every repo below was checked against the live GitHub
> API on 2026-09-30 for **stars, license, last push, archived**; where GitHub
> could not classify a license that is marked **verify**.
>
> Nothing here is a commitment. It is a shelf to pick from.

## How to read an entry

Each entry is: **what it gives** - **the vefr seam it touches** - **license / health**.
Licence note: vefr is **MPL-2.0** and ships as one public repo. A **GPL/AGPL**
tool is fine used *outside* the process (a CLI, an editor, an action); porting
its *algorithm* is fine; linking it *into* vefr is not. Entries are marked
when that distinction matters.

Effort is a three-point guess: **S** (an afternoon), **M** (a slice),
**L** (its own ruleset/roadmap item).

---

## 0. The constraints that shape every pick

These come from vefr's own rules, and they are why some obvious projects are
absent or caveated.

- **The dependency list stays short**: fastapi, uvicorn, httpx, pydantic.
  Anything new is a real ask.
- **Deterministic surfaces take no model calls**: `export`, `weave`, `maplab`,
  `journal`, `delve`. Generative flavour must be able to run *without* a model.
- **`web/` has no framework.** The woven player is one file, offline, no build.
- **Accessibility is a gate, not a follow-up** (≥44px, luminance, motion off,
  keyboard + SR).
- **A pack is markdown + JSON.** New capabilities must be additive and optional.
- **Local-first, CPU.** No cloud account, no subscription.
- **The engine never learns a game's name.**

---

## 1. The shortlist - twelve things worth folding in

Ranked by leverage, not by size. This is the "if you read nothing else" list.

| # | Project | Gives vefr | Seam | Licence | Effort |
|---|---|---|---|---|---|
| 1 | **GBNF / Outlines / lm-format-enforcer** | Guaranteed-valid JSON from *any* local model, not just those that respect `response_format` | `src/vefr/generator.py`, `forge.py`, the "strict json_schema" rule | GBNF is part of llama.cpp (MIT); Outlines Apache-2.0; lmfe MIT | M |
| 2 | **sqlite-vec** | A real embedded vector index for the Lorekeeper, replacing the hand-rolled `vectors.jsonl` scan | `src/vefr/lore.py`, `data/lore/index/` | Apache-2.0, active | S-M |
| 3 | **Tracery** | Grammar-driven rumour/whisper/flavour text with **no model** - deterministic, seedable | a new pure function beside `delve.py`; the "rumor" surface | Apache-2.0 | S |
| 4 | **Ink + inkjs** | A real branching-dialogue format, with a JS runtime that runs inside the single-file player | speaker `seeds` -> conversation; `web/packaged.html` | MIT (both) | M-L |
| 5 | **guidepup** | Automated screen-reader testing, so the a11y gate tests what it claims | `dev-guards.yml`, `scripts/a11y_check.py` | MIT | S-M |
| 6 | **vulture + deptry** | Mechanical dead-code and unused-dependency detection - the exact class the recent audit found by hand | the gate (`ruff` step) | MIT (both) | S |
| 7 | **lychee** | Link-check every markdown file in CI; catch doc rot before a reader does | `ci.yml` | Apache-2.0 | S |
| 8 | **Hypothesis** | Property tests: "same seed => same floor", "fog never reveals through a wall", "every floor is reachable" | `tests/test_delve.py`, fog, `maplab` | MPL-2.0 | S-M |
| 9 | **rot.js** | FOV, A*/Dijkstra, turn scheduling, noise - all BSD, all tiny, all browser-native | `web/packaged.html` (the renderer refactor), `delve.py` ideas | BSD-3-Clause | M |
| 10 | **ZzFX** | A ~1KB synth that turns event hooks into sound - the pairing half of "audio pairing" | the player's event loop; the roadmap's audio item | MIT | S |
| 11 | **Renovate** | Dependency updates that actually understand the repo (dependabot missed npm entirely) | replaces/extends `.github/dependabot.yml` | AGPL-3.0 (**CI-only**) | S |
| 12 | **Vale** | A prose linter that can enforce vefr's house voice (one idea per line, short prose) | `docs/`, `web/library/` | MIT | S |

---

## 2. By area

### 2.1 Roguelike core: FOV, pathfinding, turns, AI

- **libtcod** / **python-tcod** (BSD-3 / BSD-2; 1.2k / 480 stars) - the classic
  roguelike toolkit: true-colour console, FOV, pathfinding, noise. `python-tcod`
  is installable and would give the engine battle-tested FOV and weighted
  pathfinding. *Seam:* `delve.py` generation, monster AI. Dep cost: one.
- **rot.js** (BSD-3; 2.7k) - the same toolkit in JavaScript, dependency-free,
  designed to drop into a single web page. *Seam:* the woven player.
- **bracket-lib / RLTK** (MIT; 1.7k) - Rust roguelike toolkit. Read for
  architecture, not to adopt.
- **Read, don't link:** **BrogueCE** (AGPL-3.0), **NetHack**, **DCSS**
  (`crawl/crawl`), **Angband**, **Cataclysm-DDA** (CC-BY-SA). These are the
  genre's design canon.
- **Ideas with no code, all high-value** (RogueBasin, CC BY-SA):
  - *The Incredible Power of Dijkstra Maps* - the single best article for
    cheap, eerie monster AI, autoexplore, auto-travel, hazard avoidance.
  - *Creating Measurably "Fun" Maps* - measure how much of a floor the player
    is *forced* to explore, then place rewards/keys to raise it. A direct
    quality bar for `delve`.
  - *The Dungeon-Building Algorithm*, *Delving a Connected Cavern*,
    *Grid Based Dungeon Generator* - three more generation shapes.
  - **Autoexplore** and **item identification** are discussed as player-facing
    systems (Crawl, Brogue), and autoexplore is also an accessibility feature.

### 2.2 Procedural generation

- **mxgmn/WaveFunctionCollapse** (25.4k; **verify licence**) and
  **mxgmn/MarkovJunior** (MIT; 8.3k) - example-driven tilemap and pattern
  generation. WFC is the standard way to make tile regions feel hand-authored.
- **BorisTheBrave/DeBroglie** (MIT; 526) - a well-engineered WFC with
  backtracking and non-local constraints. C#, but the clearest reference.
- **Azgaar/Fantasy-Map-Generator** (6.0k; **verify licence**) - whole-world
  maps: continents, states, cultures, routes. *Seam:* a future overworld pack.
- **redblobgames/mapgen4** (Apache-2.0; 888) - Amit Patel's terrain generator,
  with the best explanations anywhere of noise, rivers, and hex grids.
- **AsPJT/DungeonTemplateLibrary** (BSL-1.0) - many small generators in one
  place (`DungeonTemplateLibrary`); a menu of techniques.
- **terrain-forge** (Rust) and **shepherd-procedural-dungeons** (.NET) - both
  notably **deterministic by seed** and built around room-graph topology, which
  is exactly the model `delve` already uses.

### 2.3 Narrative, dialogue, storylets

- **inkle/ink** (MIT; 5.0k) + **y-lohse/inkjs** (MIT; 652) - a prose-first
  narrative language with an official JS runtime. Ink handles the things vefr's
  speaker seeds cannot: variables, once-only choices, conditional text, gathers,
  revisits. `inkjs` runs in the browser, so the woven player could host it.
  *Seam:* replace/extend `speakers[].seeds` with an optional `conversation.ink`.
- **YarnSpinnerTool/YarnSpinner** (MIT; 2.9k) - node-graph dialogue with
  **storylets and saliency** built in. Even if not adopted, its model is worth
  copying: a storylet is a piece of story the *system* chooses, ranked by how
  specific its conditions are, least-recently-seen first.
- **Emily Short's storylet writing** - the design theory behind the above.
- **klembot/twinejs** (GPL-3.0; separate tool) - the authoring environment most
  writers already know.
- **le-doux/bitsy** (MIT; archived) - tiny worlds as data; a possible
  "one-screen pack" format.
- **mhgolkar/Arrow** (MIT; 1.3k) - a visual narrative design tool.
- **Inform 7** (Artistic-2.0), **Dialog** (Dialog-IF), **PunyInform** (MIT) -
  mature IF languages; reference for parser/IPv.
- **galaxykate/tracery** (Apache-2.0; 2.2k) - see shortlist. The most
  vefr-shaped narrative tool here: no model, just grammar.

### 2.4 Generative agents and NPC memory

This is the area most likely to change what vefr *is*, so read it carefully.

- **joonspk-research/generative_agents** (Apache-2.0; 22.2k) - the Stanford
  paper's code. The architecture that matters: a **memory stream** (every
  experience in natural language), **retrieval** by recency x importance x
  relevance, and **reflection** (periodic higher-level summaries that feed back).
  vefr's journal/vault is a simpler version of exactly this.
- **a16z-infra/ai-town** (MIT; 10.6k) - a deployable town of agents; TS/JS, maps
  to the studio's stack. Shows the memory search and conversation loop cleanly.
- **google-deepmind/concordia** (Apache-2.0; 1.8k) - a library for generative
  social simulation; the most rigorous of the three.
- **valentown**, **NPCAgent**, **mkturkcan/generative-agents** - small,
  single-process reimplementations with **deterministic fallbacks** when the
  model is absent. That fallback discipline is very vefr.
- **Memory products** (all active): **mem0** (Apache-2.0; 66k), **graphiti**
  (Apache-2.0; 31k), **cognee** (Apache-2.0; 31k), **letta** (Apache-2.0; 25k).
  Useful mainly as vocabulary for what a "resident memory" could grow into.

### 2.5 LLM tooling: constrained output, evaluation, tracing

- **Constrained decoding** (the highest-value LLM item):
  **dottxt-ai/outlines** (Apache-2.0; 15.9k), **guidance-ai/guidance**
  (MIT; 21.8k), **noamgat/lm-format-enforcer** (MIT; 2.0k), and llama.cpp's own
  **GBNF** grammars. These make a small model produce a valid object *by
  construction*. vefr's "strict json_schema" rule currently depends on the
  model cooperating; these remove that dependence.
- **mangiucugna/json_repair** (MIT; 5.1k) - last-resort repair of malformed
  model JSON. Cheap insurance.
- **guardrails-ai/guardrails** (Apache-2.0; 7.5k) - validate/repair outputs
  against a schema with retries.
- **BerriAI/litellm** (59.9k; **verify licence**) - one API in front of every
  provider. Could let a pack author point vefr at anything without new code.
- **Evaluation:** **UKGovernmentBEIS/inspect_ai** (MIT; 2.9k) and
  **promptfoo/promptfoo** (MIT; 25.6k) - real harnesses for the Small Model
  Olympics. **vibrantlabsai/ragas** (Apache-2.0; 15.9k) for the Lorekeeper.
- **Observability:** **langfuse/langfuse** (35.2k; **verify licence**) and
  **Arize-ai/phoenix** (11.7k; **verify licence**) - trace every model call.
  vefr already logs JSONL; these add query and comparison.
- **Prompt optimisation:** **stanfordnlp/dspy** (MIT; 38.4k).
- **Local serving:** **llama.cpp** (MIT; 130k) already in use;
  **ollama** (MIT; 182k), **mozilla-ai/llamafile** (26.1k; **verify licence**)
  for one-file distribution. **whisper.cpp** (MIT; 54k) for speech-in.
  **TTS:** **rhasspy/piper** (MIT; **archived**) and **hexgrad/kokoro**
  (Apache-2.0; 9.1k) for a local read-aloud voice - a direct accessibility win.

### 2.6 Memory, storage, retrieval

- **asg017/sqlite-vec** (Apache-2.0; 8.2k) - vectors inside SQLite. vefr
  already has SQLite (`content.db`) and a JSONL vector file; this is the
  obvious consolidation.
- **unum-cloud/USearch** (Apache-2.0; 4.3k) - single-header vector search.
- **lancedb** (Apache-2.0; 11.6k), **chroma** (Apache-2.0; 29.4k) - heavier.
- **qdrant/fastembed** (Apache-2.0; 3.2k) - small local embeddings; a lighter
  path than shipping bge-m3 for every case.
- **simonw/sqlite-utils** (Apache-2.0; 2.2k) and **simonw/datasette**
  (Apache-2.0; 11.5k) - browse/inspect/maintain `content.db`, and publish it as
  a world browser.
- **Graph memory:** **kuzudb/kuzu** (MIT; archived) or its active successor
  **GrafeoDB/grafeo** (Apache-2.0; 793) - embedded graph for bonds/lore.
  **microsoft/graphrag** (MIT; 36.2k) for the retrieval pattern.

### 2.7 Game AI

- **splintered-reality/py_trees** (**verify licence**; 641) - behaviour trees
  with a visual debugger; a natural fit for residents and monsters.
- **pytransitions/transitions** (MIT; 6.6k) - a clean FSM for quest/scene state.
- **Dijkstra maps / utility AI** (RogueBasin, Brogue) - see 2.1; cheaper than
  both and more in keeping with the engine.
- **facebookresearch/nle** and **minihack** (Apache-2.0; **both archived**) -
  RL/eval environments on NetHack. A model for how to *score* the bench beyond
  a blind A/B.

### 2.8 Art, tiles, palettes, fonts

- **Editors:** **mapeditor/tiled** (GPL-2.0; separate tool; 12.9k) and
  **deepnight/ldtk** (MIT; 4.3k) - the two de-facto tilemap editors. An importer
  would let artists author maps outside the run-length rows.
- **Loaders:** **bitcraft/PyTMX** (LGPL-3.0; 419), `pytiled_parser`
  (**location moved - verify**).
- **Pixel editors:** **Orama-Interactive/Pixelorama** (MIT; 10.4k),
  **LibreSprite** (GPL-2.0; 8.5k). **Aseprite** is source-available with a
  licence that restricts redistribution - check before depending on it.
- **Assets:** **Kenney** (kenney.nl, CC0), **Liberated Pixel Cup** (CC-BY-SA /
  GPL), **Lospec** palettes (lospec.com) - all pack-friendly.
- **Fonts:** **fonttools** (MIT; 5.3k) and **Munter/subfont** (MIT; 1.6k) -
  subset the two shipped fonts, which would shrink every woven file.
  **Atkinson Hyperlegible** is already used; **Lexend** and **OpenDyslexic** are
  the other readability-first faces.
- **Colour:** **color-js/color.js** (MIT; 2.3k) and **Myndex/apca-w3**
  (**verify**) - perceptual contrast beyond WCAG 2's ratio.
- **Optimisation:** **GoogleChromeLabs/squoosh** (Apache-2.0; 26k) - shrink
  pack art and player images.

### 2.9 Accessibility

This is vefr's differentiator; the ecosystem here is unusually strong.

- **dequelabs/axe-core** (MPL-2.0; 7.6k) - already vendored.
- **guidepup/guidepup** (MIT; 567) - automate NVDA/VoiceOver in tests. See
  shortlist.
- **GoogleChrome/lighthouse-ci** (Apache-2.0; 7.1k) - perf/a11y budgets in CI.
- **pa11y/pa11y** (LGPL-3.0; separate tool), **IBMa/equal-access**.
- **DCSS "Accessible Crawl" wiki** - the single best list of concrete features
  that make a tile roguelike playable by screen reader: autoexplore, autofight,
  a full monster/item list (`Ctrl-X`), textual position feedback, and
  "single-column menus" toggles. Several map directly onto vefr.
- **tapestry-mud/tapestry** (AGPL-3.0; new) - a modular MUD whose accessibility
  is architectural: every printed reaction is *also* sent over a structured
  channel, so any content pack is readable by default. That is the strongest
  idea here for vefr's player.
- **Battle Weary** (7DRL) - a written-after-action account of why `aria-live`
  is fragile for games and what to do instead (turn-based "conversation",
  a "sentinel page" of conventions, always-available recap keys).
- **fastfinge/sral-mudlet**, **destructatron/gtkmud** - screen-reader plumbing
  for text games (SRAL, GMCP, sound protocols).
- **References:** WCAG 2.2, the Game Accessibility Guidelines, AbleGamers APX.

### 2.10 Repo quality, CI, supply chain

- **Dead code / deps:** **jendrikseipp/vulture** (MIT; 4.8k),
  **osprey-oss/deptry** (MIT; 1.5k). See shortlist.
- **Dependency freshness:** **renovatebot/renovate** (AGPL-3.0; CI-only; 22.6k).
- **Security:** **pypa/pip-audit** (Apache-2.0; 1.4k),
  **google/osv-scanner** (Apache-2.0; 11.1k), **semgrep**, **bandit**;
  **aquasecurity/trivy** / **anchore/grype** for the published image;
  **anchore/syft** for an SBOM.
- **Provenance:** **sigstore/cosign**, SLSA, **ossf/scorecard** - the image
  publish currently sets `provenance: false`.
- **Types:** **astral-sh/ty** (MIT; 19.8k), the fast Astral type checker. vefr
  has no type gate; this is the natural one.
- **Testing:** **Hypothesis** (MPL-2.0; 9.0k), **syrupy** (MIT; 890),
  **boxed/mutmut**.
- **Release/docs plumbing:** release-please, towncrier, git-cliff,
  **pre-commit** (MIT; 15.6k), **casey/just** (CC0; 36.1k) - the latter would
  let the gate become one command without a Makefile.
- **Prose/docs:** **vale-cli/vale** (MIT; 6.2k), **get-alex/alex** (MIT; 5.1k;
  quiet since 2024), **lycheeverse/lychee** (Apache-2.0; 4.0k).

### 2.11 Docs, distribution, packaging

- **mdBook** (MPL-2.0; 22.2k) or **mkdocs-material** (MIT; 27.5k) - publish the
  studio Library as a real site (and validate it in CI).
- **tauri-apps/tauri** (Apache-2.0; 111k) - wrap the woven player as a desktop
  app without Electron's weight.
- **itchio/butler** (MIT; 990) - publish builds to itch.io from a script.
- **pygame-web/pygbag** (MIT; 519) - ship a Python build to the browser, if the
  engine ever needs to run client-side.
- A **PWA manifest + service worker** would make the woven file installable and
  offline-first with no new dependency.

### 2.12 Web, CSS, animation, audio (player + studio)

- **argyleink/open-props** (MIT; 5.5k) - framework-free design tokens;
  a good fit for the token files vefr already keeps.
- **motiondivision/motion** (MIT; 33.8k) - small, declarative animation.
- **pixijs/pixijs** (MIT; 48.2k) - if the canvas renderer ever needs to scale.
- **Tonejs/Tone.js** (MIT; 14.7k) and **goldfire/howler.js** (MIT; 25.4k) -
  audio; **ZzFX** (MIT; 793) for the tiny version (shortlist).
- **jamiebuilds/tinykeys** (MIT; 4.1k) - keybinds, which pairs with the
  roadmap's keybind remap.
- **jakearchibald/idb** (ISC; 7.4k) - a better IndexedDB than localStorage for
  saves; leave localStorage for settings only.

### 2.13 Design references (no code, high value)

- **RogueBasin** (CC BY-SA) - the whole genre's wiki; several articles named
  above.
- **Red Blob Games** (Amit Patel) - pathfinding, hex grids, map generation,
  explained interactively.
- **munificent/game-programming-patterns** - free online; component, state,
  event queue, spatial patterns.
- **Procedural Content Generation in Games** (Shaker, Togelius, Nelson) - the
  free textbook.
- **Emily Short** on storylets and narrative systems.
- **r/roguelikedev** and its annual "Complete Roguelike Tutorial" (Python +
  libtcod), plus the RogueBasin design canon in 2.1.

---

## 3. New tooling we already have that could fold in

The estate has grown tools of its own since vefr started. Some belong in the
engine's day-to-day.

| Tool | Where | How it could fold into vefr |
|---|---|---|
| **offload** (`route`, `agent`, `ask`) | estate `~/.agents` | A cost-aware path for heavy work. Could become a `norns` mode that routes drafting to a cheap model, or power the bench's batch runs. |
| **gallery** + `lab_gallery.py` | `studio/` | Already publishes woven builds. Could become `ratatoskr publish` (build + version + shots in one verb), codifying the "every demo is a new URL" habit. |
| **studio web app** (`scripts/studio.py`) | this repo | Its throwaway-data mode is already the safe way to test; it could host the map/lore editors the pack needs. |
| **bench/cli.py** | this repo | A full third CLI that is unregistered and undocumented in `--help`. Fold into `ratatoskr`/`norns` or document it. |
| **memory-graph / homelab-memory** | estate MCP | A shared memory service; the pattern to copy for resident memory, not to link. |
| **lab / lab lore** | estate | Session context, not engine. Useful for recording what the engine learns. |
| **A shared renderer** | (needed, not built) | The studio player and the woven player have drifted apart. One renderer shared by both is itself the largest internal "enhancement" available - and the place 2.1/2.12 land. |

---

## 4. Licence caution list

Read before adopting. "Verify" means GitHub could not classify it on 2026-09-30.

- **GPL / AGPL - separate tool or algorithm-port only** (never linked into
  MPL-2.0 vefr): BrogueCE (AGPL-3.0), Twine (GPL-3.0), LibreSprite (GPL-2.0),
  Tiled (GPL-2.0), pa11y (LGPL-3.0), PyTMX (LGPL-3.0), Renovate (AGPL-3.0,
  fine as CI), Cataclysm-DDA (CC-BY-SA), tapestry (AGPL-3.0).
- **Verify licence / source:** WaveFunctionCollapse, Azgaar Fantasy Map
  Generator, litellm, langfuse, Phoenix, py_trees, APCA, llamafile, Tiled,
  pytiled_parser (moved).
- **Archived but usable (pin and be ready to fork):** bitsy, piper, kuzu, NLE,
  MiniHack, alex (quiet since 2024).
- **Source-available, not open:** Aseprite - confirm before depending on it.

---

## 5. Suggested sequencing

**Wave 1 - trust, speed, and the gate** (low risk, compounding)
1. Constrained decoding: GBNF grammars and/or Outlines/lm-format-enforcer.
2. `sqlite-vec` for the Lorekeeper; `fastembed` as a lighter embedding option.
3. `vulture` + `deptry` + `lychee` + `guidepup` into the gate.
4. `Hypothesis` properties for `delve`/fog reachability and determinism.
5. `Renovate` (or expanded dependabot) so versions stop drifting.

**Wave 2 - the game gets richer** (player-facing)
6. Tracery-driven deterministic flavour (rumours, weather, names) - no model.
7. Ink + inkjs conversations for speakers, opt-in per pack.
8. rot.js FOV/pathfinding + Dijkstra-map AI + **autoexplore** (a mechanic *and*
   an accessibility feature).
9. ZzFX/Tone audio pairing; subset fonts with fonttools/subfont.
10. WFC (DeBroglie/MarkovJunior ideas) for floor and region variety.

**Wave 3 - the engine grows a memory and a body**
11. Resident memory in the generative-agent shape (memory stream + reflection +
    three-factor retrieval), with deterministic fallbacks.
12. Graph memory (Grafeo/kuzu patterns) for bonds and lore.
13. mdBook/mkdocs Library; Tauri or a PWA for the player.
14. Authoring: Tiled/LDtk import in `build-map`; Datasette over `content.db`.
15. Distribution: a pack registry (Tapestry's model), `ratatoskr publish`.

---

## 6. Evidence

- GitHub topic sweeps, sorted by stars, 2026-09-30: `roguelike`,
  `procedural-generation`, `interactive-fiction`, `dialogue-systems`,
  `generative-agents`, `llm+structured-output`, `worldbuilding`, `llm-evaluation`,
  `pathfinding`, `text-adventure`, `pixel-art`, `text-to-speech`,
  `speech-recognition`, `knowledge-graph`, `vector-search`, `wave-function-collapse`,
  `roguelike+javascript`, `accessibility+testing`.
- Per-repo metadata from the GitHub REST API on 2026-09-30 (stars, licence,
  last push, archived).
- RogueBasin articles (Dijkstra maps; Dijkstra Maps Visualized; Creating
  Measurably "Fun" Maps; The Dungeon-Building Algorithm; Delving a Connected
  Cavern; Grid Based Dungeon Generator; Data structures for the map).
- DCSS "Accessible Crawl" wiki; Tapestry MUD; Battle Weary dev writing.
- Web research on Ink-vs-Yarn, storylets and saliency, and generative-agent
  memory architectures.
