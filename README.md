# Old Name

> *old-name* - memory, and longing. The raven that flies out every day
> and comes home.
>
> **It gives the hellos that never happened.**

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
  style.py           prompts from pack voices + bible + ledger
  generator.py       rumor cards (speaker, whisper, is_true)
  forge.py           items; bonds come from the pack
  bell.py            sealed voices (the goodbye)
  npc.py             whisper NPCs; seeds keep the world alive
  main.py            FastAPI surface incl. GET /api/world

worlds/<name>/       a world pack (private - this is someone's story)
  world.json         phases, tones, voices, bonds, speakers, the town
  bible.md           the world bible - canon + style contract
  ledger.md          collected whispers - voice anchors, hand-curated
  map.md             the story's geometry, source of truth
  voices/*.md        sealed voices (rules only; knowing stays sealed)

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

1. Copy `worlds/private-canon/` to `worlds/yours/` - or start from the
   keys in `world.json` alone.
2. Write your `bible.md` (canon + the rules the engine must obey)
   and `ledger.md` (seed whispers; the cadence compounds).
3. Define phases and their tones, your bonds, your speakers, your
   town grid and palette.
4. `MUNR_WORLD=yours`. The engine does the rest.

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
- Engine license: MIT (see LICENSE). World packs are the author's
  story and are not licensed for redistribution.

## Development

```sh
uv sync --group test
uv run --group test pytest -q
```
