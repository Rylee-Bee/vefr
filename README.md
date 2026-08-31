# Old Name

> *old-name* - memory, and longing. The raven that flies out every day
> and comes home.
>
> **It gives the hellos that never happened.**

**Naming note (2026-08-31):** this repo is still called `old-name` (its
original name); the engine's own commands are `raven` and `old-name`
and never reference this project's name, on purpose - so "Old Name"
stays free to be a game's title, not the toolkit's. The author's own
game, built on `worlds/private-canon`, is called Old Name.

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
src/old-name/            the engine (MIT)
  paths.py           where things live (OLD-NAME-HOME, MUNR_WORLD)
  world.py           the pack loader - the only seam
  saga.py            the storytelling layer - Saga keeps the stories:
                     Bragi composes (prompts, voices), Idunn keeps
                     (the ledger that renews the voice)
  generator.py       rumor cards (speaker, whisper, is_true)
  forge.py           items; bonds come from the pack
  bell.py            sealed voices (the goodbye)
  npc.py             whisper NPCs; seeds keep the world alive
  main.py            FastAPI surface incl. GET /api/world
  cli.py             two entry points, raven and smith:
                       raven - memory: tidyup, deploy, backup, test
                       old-name - craft: validate, build, verify worlds
  maplab.py          old-name's toolkit - the one validator shared by
                     tests and both clis

worlds/<name>/       a world pack - a story
  world.json         phases, tones, voices, bonds, speakers, the town
  bible.md           the world bible - canon + style contract
  ledger.md          collected whispers - voice anchors, hand-curated
  map.md             the story's geometry, source of truth
  voices/*.md        sealed voices (rules only; knowing stays sealed)

worlds/sample-world/ Emberfield - the teaching example (MIT, ships
                     with the engine so it's shareable end to end)
worlds/private-canon/   the author's own story (all rights reserved -
                     see worlds/private-canon/LICENSE)

web/                 parchment UI + canvas town (world-driven)
tests/               pytest - pack contract, schemas, fallbacks
```

One env var selects the world: `MUNR_WORLD=private-canon`. Point it at
your own pack and the same engine serves your story.

## Quickstart (container)

```sh
podman build -t localhost/old-name:latest .
mkdir -p ~/old-name-data
podman run -d --name old-name -p 8820:8820 \
  -v ~/old-name-data:/app/data \
  -e OLLAMA_URL=http://127.0.0.1:11434 \
  localhost/old-name:latest
curl -s http://127.0.0.1:8820/api/health
```

Model default: `MUNR_MODEL=qwen3.8-27b:ctx32k` (any ollama model
works; structured output via JSON schema).

## Make your own world

**By hand:**

1. Copy `worlds/private-canon/` to `worlds/yours/` - or start from the
   keys in `world.json` alone.
2. Write your `bible.md` (canon + the rules the engine must obey)
   and `ledger.md` (seed whispers; the cadence compounds).
3. Define phases and their tones, your bonds, your speakers, your
   town grid and palette.
4. `MUNR_WORLD=yours`. The engine does the rest.

**By conversation** (`old-name chat --name yours`): an interview, run
against your own local ollama, drafts the canon, the theme colors,
your phases, bonds, and one speaker's voice - starting from
`worlds/sample-world/` (a known-valid scaffold) so the geometry can
never break. The interview's flow is plain Python, never the model's
call; the model only ever fills in prose or a hex color inside a
schema it can't escape. Every write ends in `maplab.validate()` - you
never have to trust your own edits, the tool always checks. The map
itself stays the scaffold's in v1; grow it after with
`old-name build --segments`.

## More docs

- **New here?** `GETTING_STARTED.md` - install, run, build your own
  world, no story content required.
- **CLI reference:** `raven --help` / `old-name --help` - the full
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
  example). `worlds/private-canon/` is the author's own story and game:
  all rights reserved, no license granted - see
  `worlds/private-canon/LICENSE`.

## Development

```sh
uv sync --group test
uv run --group test pytest -q
```
