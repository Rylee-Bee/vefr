# norn

> The three Norns weave fate at the well beneath the world tree -
> not one fixed fate, whichever one is given them.
>
> **It gives the hellos that never happened.**

Two entry points, `raven` and `old-name`, live under this one umbrella -
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

web/                 parchment UI + canvas town (world-driven)
tests/               pytest - pack contract, schemas, fallbacks
```

No world pack ships tracked in this repo except the sample - the
author's own game keeps its pack in a separate private repo and
drops it into `worlds/<name>/` locally. One env var selects the
world: `NORN_WORLD=your-world`. Point it at your own pack and the
same engine serves your story.

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

## Make your own world

**By hand:**

1. Copy `worlds/sample-world/` to `worlds/yours/` - or start from the
   keys in `world.json` alone.
2. Write your `bible.md` (canon + the rules the engine must obey)
   and `ledger.md` (seed whispers; the cadence compounds).
3. Define phases and their tones, your bonds, your speakers, your
   town grid and palette.
4. `NORN_WORLD=yours`. The engine does the rest.

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
  example). Any other world pack dropped into `worlds/<name>/` locally
  is that pack's own author's property - the engine grants no license
  to story content, and carries none in this repo.

## Development

```sh
uv sync --group test
uv run --group test pytest -q
```
