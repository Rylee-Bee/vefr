# norn

> The three Norns weave fate at the well beneath the world tree -
> not one fixed fate, whichever one is given them.
>
> **It gives the hellos that never happened.**

Two entry points, `ratatoskr` and `norns`, live under this one umbrella -
universal tooling that never references any specific game's name, so
any story can be woven here. "Old Name" is Old Norse for memory and
longing; it's also the title of the author's own game,
`the private story repo`, which is built on this engine but lives in its
own private repo and ships nothing here.

A rumor engine for playable worlds. The engine holds the rules:
phases, whispers, the forge, the vault, a walkable town under a
watchful tower. A **world pack** holds the story. The two only
touch through one contract, so anyone can take the bones and grow
their own flesh.

It is an honesty contract rendered as a game: the world's claims
live in the pack, the engine's rules are tested, and every name
spoken must be true.

## The bones and the flesh

```
src/norn/           the engine (MIT)
  paths.py           where things live (NORN_HOME, NORN_WORLD)
  world.py           the pack loader - the only seam
  saga.py            the storytelling layer - Saga keeps the stories:
                     Bragi composes (prompts, voices), Idunn keeps
                     (the ledger that renews the voice)
  generator.py       rumor cards (speaker, whisper, is_true)
  forge.py           items; bonds come from the pack
  bell.py            sealed voices (the goodbye)
  npc.py             whisper NPCs; seeds keep the world alive
  journal.py         the session journal - what happened, on disk
                     (NORN_JOURNAL)
  export.py          canon + journal + vault -> one markdown story,
                     deterministic templating, no model needed
  main.py            FastAPI surface incl. GET /api/world,
                     GET /api/journal, GET /api/export
  cli.py             two entry points, ratatoskr (the squirrel) and norns (the weavers):
                       ratatoskr - memory: tidyup, test, weave, ferry (deploy, carry, fetch)
                       norns - craft: chat, validate, build-map, verify
  maplab.py          norns's toolkit - the one validator shared by
                     tests and both clis

worlds/<name>/       a world pack - a story
  world.json         phases, tones, voices, bonds, speakers, the town
  bible.md           the world bible - canon + style contract
  ledger.md          collected whispers - voice anchors, hand-curated
  map.md             the story's geometry, source of truth
  voices/*.md        sealed voices (rules only; knowing stays sealed)

worlds/sample-world/ Emberfield - the teaching example (MIT, ships
                     with the engine so it's shareable end to end)

web/                 parchment UI + canvas town (world-driven)
tests/               pytest - pack contract, schemas, fallbacks
```

No world pack ships tracked in this repo except the sample - the
author's own game keeps its pack in a separate private repo and
drops it into `worlds/<name>/` locally. One env var selects the
world: `NORN_WORLD=your-world`. Point it at your own pack and the
same engine serves your story.

## Design

The engine's identity is *part of the skeleton*, not a flavor toggle.

**The contract is airtight.** The engine never gates the player on
HP, attack, or roll results. The Old Name way — what Private Canon does,
what Emberfield does — has no failure state. The bell never rings
bad, items can't be lost, NPCs always have a line. HP bars are a
*costume*. Death is not on the table.

**The journey begins.** The engine's story structure is the
**Hero's Journey** told through the **Elder Futhark** runes — a
four-act shape anchored to four runes:

| Phase | Journey stage | Rune |
|---|---|---|
| `whispers` | the call to adventure | **Fehu** (wealth, the seed-fire) |
| `doubts` | the refusal / the threshold | **Thurisaz** (the thorn) |
| `feared` | the tests, allies, enemies | **Kenaz** (the torch) |
| `awed` | the revelation / the return | **Sowilo** (the sun) |

Packs can rename their phase keys; the engine maps them by
position. The runes don't predict either — they're the bones the
system prompts thread through every generation, so the LLM's
voice carries the journey shape without the journey being a gate.

**The tree is being woven.** The engine is **Yggdrasil**; the
ratatoskr ferries data between the roots (dev box, deploy host,
Gitea, NAS) and the crown (the player's play history); the
norns weave what happens at runtime. The world tree is also a
literal artifact — `ratatoskr weave` produces a `<name>.tree.md`,
the world's living document with one section per dev-UI tab.

**Only the runes leave room for chaos.** Every other surface is
deterministic — the engine's contract, the packs, the lore, the
tree. The runes are the one stochastic surface; the cast is
the one moment where what happens is *up to the world*. The
player reads what the chips say; the chips don't read the player.

### Lore packs

Three lore packs ship with the engine. Each is data — a directory
under `worlds/lore/<name>/` with four markdown files the engine
reads and a fifth the author copies by hand:

| File | Engine reads? | Author reads? |
|---|---|---|
| `textures.md` | yes | yes |
| `names.md` | yes | yes |
| `questions.md` | yes | yes |
| `prompt.md` | no | **yes** (copy-paste into any LLM) |
| `LICENSE.md` | no | yes (CC BY-SA 4.0 + attributions) |

The packs:

- **`norse`** — the wandering-poets flavor (skalds, verse in
  place of record, names with weight)
- **`historical-event`** — what the record couldn't hold (real
  events, role-not-name descriptors, the witness)
- **`norse-runes`** — the rune-cast flavor (twenty-four runes in
  three aettir, mapped to the Hero's Journey stages)

To use a pack, call `/api/builder/lore` with the pack name + seed
words, get back the wandering-poets shape (`textures`, `names`,
`questions`) — mood, not canon. Then `norns craft chat` carries
the mood into the world's interview questions.

To add your own pack: `mkdir worlds/lore/<your-flavor>` and write
the four files. The engine discovers it; no PR required.

### Surface

`world.json` may declare a `surface` field — `combat`,
`investigation`, or `plain`. The surface is the *grammar* the
player sees (HP bars, encounter prompts, investigation dice), not
the engine's actual behavior. Default surface is `combat` for
back-compat with existing packs. A pack that wants the engine's
"no HP, no dice, just the bell and the whispers" experience
declares `surface: "plain"` and the UI knows to skip the
RPG-looking panels.

## Quickstart (container)

```sh
podman build -t localhost/norn:latest .
mkdir -p ~/norn-data
podman run -d --name norn -p 8820:8820 \
  -v ~/norn-data:/app/data \
  -e NORN_LLAMACPP_URL=http://127.0.0.1:8081 \
  -e NORN_MODEL=gpt-oss-20b \
  localhost/norn:latest
curl -s http://127.0.0.1:8820/api/health
```

The engine prefers `NORN_LLAMACPP_URL` (llama.cpp's OpenAI-compatible
`/v1/chat/completions` endpoint) and falls back to `OLLAMA_URL`
(legacy ollama `/api/generate`). Set `OLLAMA_URL=""` to disable the
fallback entirely. Model default: `gpt-oss-20b` (works with any
llama.cpp model that supports the chat template; set `NORN_MODEL`
to change it; structured output via JSON schema with `strict: true`).

### Use your own pack

The bundled engine ships with `worlds/sample-world/` (Emberfield) so
it boots with something to play. To swap in your own world:

1. Copy `worlds/sample-world/` to `worlds/<your-name>/`.
2. Edit `world.json`, `bible.md`, `voices/*.md`, `map.md`. The
   contract lives in `world.json`'s `REQUIRED` keys (see
   `src/norn/world.py`); `norns validate --pack worlds/<your-name>`
   catches mistakes.
3. Mount it into the container and tell the engine which pack to load:

```sh
podman run -d --name norn -p 8820:8820 \
  -v ~/norn-data:/app/data \
  -v /path/to/your-pack:/app/worlds/your-name:Z \
  -e NORN_WORLD=your-name \
  -e NORN_LLAMACPP_URL=http://host.docker.internal:8081 \
  localhost/norn:latest
```

### Point it at a phone-as-backend

Anywhere the engine can reach an OpenAI-compatible HTTP endpoint,
the engine is happy. That includes:

- `Local LLM Server` on the iPhone (App Store, iOS 26+) - runs Apple's
  Foundation Models on-device, exposes OpenAI + Ollama APIs
- `Crucible LLM Server` or `Pirate LLM Server` - open-source, llama.cpp
  + Metal, sideloadable via AltStore
- A Mac running Ollama / LM Studio, exposed to your LAN

Set `NORN_LLAMACPP_URL=http://<phone-ip>:11434/v1` and the game runs
entirely off the laptop, the cloud, and any LAN host.

### Package a single HTML file (the bones)

```sh
ratatoskr weave
# -> dist/private-canon-2026-08-31.html  (one self-contained file)
```

The packaged file is the engine's `web/` UI with your world pack
inlined as JSON. Send it to someone - they open it in a browser
(on a phone, on a tablet, on a desktop), point it at any
OpenAI-compatible LLM URL, and play. No Python, no server, no
internet.

## Make your own world

**By hand:**

1. Copy `worlds/sample-world/` to `worlds/yours/` - or start from the
   keys in `world.json` alone.
2. Write your `bible.md` (canon + the rules the engine must obey)
   and `ledger.md` (seed whispers; the cadence compounds).
3. Define phases and their tones, your bonds, your speakers, your
   town grid and palette.
4. `NORN_WORLD=yours`. The engine does the rest.

**By conversation** (`norns chat --name yours`): an interview, run
against your own local ollama, drafts the canon, the theme colors,
your phases, bonds, and one speaker's voice - starting from
`worlds/sample-world/` (a known-valid scaffold) so the geometry can
never break. The interview's flow is plain Python, never the model's
call; the model only ever fills in prose or a hex color inside a
schema it can't escape. Every write ends in `maplab.validate()` - you
never have to trust your own edits, the tool always checks. The map
itself stays the scaffold's in v1; grow it after with
`norns build-map --segments`.

## More docs

- **New here?** `GETTING_STARTED.md` - install, run, build your own
  world, no story content required.
- **CLI reference:** `ratatoskr --help` / `norns --help` - the full
  command list, always in sync with the code.
- **API reference:** the running app serves interactive docs for
  free at `/docs` (e.g. `http://127.0.0.1:8820/docs`) - every route,
  every shape, try-it-out included. No separate file to keep in sync.
- **What's landed, what's next:** `ROADMAP.md`.

## The town

Walk with the pad, WASD, or arrows. `E` or tap talks to whoever is
near. The tower's watch is geometry - safe pockets exist, and the
world's tone narrows them as the phases turn. Gold appears only
when the world is kind.

## Attribution

- Dependencies: fastapi, uvicorn, httpx, pydantic (MIT/BSD-3) -
  declared in `pyproject.toml`; their notices ship in the wheels.
- Model: Qwen (Apache-2.0); outputs are shaped by this repo's
  prompts and reviewed by a human before they become canon.
- Code co-written with Kilo (AI) at the author's direction.
- Engine license: MIT (see LICENSE) - covers `src/`, `web/`, `tests/`,
  `deploy/`, `Containerfile`, and `worlds/sample-world/` (the teaching
  example). Any other world pack dropped into `worlds/<name>/` locally
  is that pack's own author's property - the engine grants no license
  to story content, and carries none in this repo.

## Development

```sh
uv sync --group test
uv run --group test pytest -q
```
