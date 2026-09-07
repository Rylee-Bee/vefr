# AGENTS.md

vefr - a rumor engine for playable worlds (MIT). This file is loaded
by `.kilo/kilo.jsonc` `instructions:`. Rylee's personal profile
(voice, accessibility, shared agent rules) comes from the global
kilo config - do not add personal files to this repo.

| Want to...                        | Open this                                            |
| --------------------------------- | ---------------------------------------------------- |
| Run the engine / build a world    | `GETTING_STARTED.md`                                 |
| Understand the bones/flesh split  | `README.md`                                          |
| Understand the brain/provider seam| `docs/guides/brain-socket.md`                        |
| Run the resident Spark service    | `docs/guides/spark.md`                               |
| See what's landed / what's next   | `ROADMAP.md` (the ledger - update it when you land)  |
| Change what a world pack can hold | `src/vefr/world.py` docstring - the contract         |
| Validate a pack                   | `uv run norns validate --pack worlds/<name>`         |

## Canonical checkout (2026-09-07)

There are **two checkouts** of this repo on the dev box:

- **`/mnt/c/Users/ryleeb/projects/vefr` — canonical.** Tracks
  `origin/main` (Gitea `rylee/vefr`, mirrored to GitHub
  `burgeswe/vefr`). Run tests, open PRs, and land work here.
- **`/mnt/c/Users/ryleeb/projects/kilo2/vefr` — Storyteller WIP lane.**
  Deliberately behind `origin/main` with uncommitted work
  (`src/vefr/npc_action*.py`, `storyteller_benchmark.py`, modified
  `cli.py`/`generator.py`/`storyteller_test.py`). **Do not "help" this
  checkout by committing, stashing, cleaning, or rebasing its WIP** —
  it is preserved lane state awaiting the story-team design
  (homelab issue rylee/vefr#50). If you must sync it, ask Rylee first.

A fresh agent: work in the `projects/vefr` checkout. If you find
yourself in the kilo2 one, `cd` out rather than committing there.

## What this repo is

- The **engine** only ("the bones"): FastAPI + any OpenAI-compatible
  LLM backend. MIT-licensed, shareable, may go public someday.
- Two CLI entry points: `ratatoskr` (ops: skipa, test, weave, ferry)
  and `norns` (craft: chat, validate, build-map, verify). Both share
  one geometry/contract validator: `src/vefr/maplab.py`.
- `worlds/sample-world/` (Emberfield) is the only tracked world pack -
  the playable demonstration pack that ships with the engine, complete
  on its own with no private content. Its content is scaffolding, not
  a requirement for other worlds. Kept in the acts shape.
- `worlds/lore/<flavor>/` packs are data-only literary mood-boards
  (CC BY-SA 4.0). Adding one is `mkdir` + four markdown files.

## What this repo isn't

- The game. The engine is the bones; the author's story is the
  flesh, kept in a separate private pack repo and dropped into
  `worlds/<name>/` locally when it's time to play. Any non-shipped
  pack under `worlds/` is author-canon and gitignored here. Engine
  history was filter-repo'd on 2026-08-31 to remove every trace of
  any specific game; the engine must never re-learn a game's name
  - whether from the author's pack or from any other pack. If a
  string in `web/`, `src/`, docs, tests, a system prompt, or a
  placeholder defaults to a name that isn't pack-supplied, that's
  a leak; replace it with an engine-neutral verb (or empty the
  slot until the pack loads).
- Multi-backend tied: llama.cpp (`VEFR_LLAMACPP_URL`) is preferred,
  Ollama (`OLLAMA_URL`) is fallback. Structured output only
  (`response_format.json_schema`, `strict: true`).

## Directory map

| Path                  | Purpose                                                        |
| --------------------- | -------------------------------------------------------------- |
| `src/vefr/` (25)      | The engine. `world.py` is the only seam between engine + story |
| `web/`                | Parchment UI + canvas town; `state.js` is the one client state |
| `worlds/sample-world/`| Playable demo pack, acts shape, validates green            |
| `worlds/lore/`        | Three lore packs (norse, historical-event, norse-runes)        |
| `tests/`              | pytest suite, incl. node-vm harnesses for shipped JS           |
| `docs/guides/`        | Operational guides (install, volumes, handoff, deploy)         |
| `deploy/`             | Quadlet template. Live game runs on bazzite, not homelab-vm    |
| `Containerfile`       | The one build. `compose.yml` gives a 3-command local run       |
| `data/`               | Runtime state. Never hand-edit; see Never table                |

## Commands

```bash
# The gate - run before claiming anything is done
uv sync --group test
uv run --group test ruff check src tests
# The pass/skip count is NOT recorded here - it drifted twice
# (200 vs 307 vs reality). Paste the pytest summary line from YOUR
# run with any done claim; the verified count per epoch lives in
# ROADMAP.md (the ledger), not in this file.
uv run --group test pytest -q

# One-command session-start check (git, tree, tests, pack, live)
uv run --group test norns doctor   # set VEFR_LIVE_URL to check a stack

# CLI references (canonical, always in sync with code)
uv run ratatoskr --help            # ops: skipa, test, weave, ferry
uv run norns --help                # craft: chat, validate, build-map, verify

# Session tidyup - the seven questions (this repo's own; do not use
# the homelab's scripts/tidyup.sh here)
uv run ratatoskr skipa

# Validate a world pack
uv run norns validate --pack worlds/<name>

# Run the engine locally
uv run uvicorn vefr.main:app --app-dir src --port 8820

# Package a single shareable HTML file (needs a live model)
uv run ratatoskr weave --pool 5
```

## Boundaries

| Severity  | Trigger                                                                                                                                                  |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Always    | `uv run --group test ruff check src tests && uv run --group test pytest -q` green before claiming done. Every claim about counts/results includes the exact command that produces the evidence.   |
| Always    | Inclusive-forward is the design identity: every UI change answers the accessibility matrix - targets ≥44px, luminance over hue, plain-English first (Norse as flavor), motion off by default, reading load short, and when sound arrives, every sound paired with a visual event. |
| Always    | `maplab.validate()` (via `norns validate`) after any world-pack write. The tool always checks; never trust a hand edit.                                   |
| Always    | Keep deterministic surfaces deterministic: no model calls in `export.py`, `weave.py`, `maplab.py`, `journal.py`. The runes are the only stochastic surface. |
| Always    | One ROADMAP.md entry per landed change (Landed list, dated). Keep README/GETTING_STARTED in sync when commands or contracts change.                      |
| Ask first | Changing the pack contract: `world.py` REQUIRED keys, `VALID_SURFACES`, the loader's canonical shape, or the acts/flat on-disk layouts.                  |
| Ask first | Adding a tracked world pack beyond `sample-world`, or a new public API route in `main.py`.                                                             |
| Ask first | Any git history rewrite. There have been two, both
             backed-up and verified: 2026-08-31 (removed the story
             pack's content) and 2026-09-01 (scrubbed the private
             pack, game, and canon names from every historical blob,
             message, and path - backups in
             `vefr-pre-scrub-2026-09-01.bundle` on the dev box root
             and bazzite `~/`). Neither is a template. |
| Never     | Commit story content from a private story-pack repo (any non-shipped pack under `worlds/` is gitignored - keep it that way), or name any specific game in engine code, prompts, API titles, tests, or docs. |
| Never     | Commit runtime state: `data/sessions/`, `data/vault-*.json`, `data/journal-*.json`, `data/weave.jsonl`, `worlds/*/world-tree.md`, `worlds/*/handbok.md` (all gitignored). |
| Never     | Hand-edit `uv.lock`. Add `"think": true` (or drop `strict: true`) on any schema-constrained generation call.                                             |
| Never     | Report done without the pytest gate output pasted. Proposed = committed, not merged; staged = on a branch only.                                          |

## Repo conventions

- **Branch model:** `main` <- PR <- `feat/*`. PRs via `tea` against
  `rylee/vefr`. No CI on this repo yet - the local pytest gate above
  is the whole gate, so run it.
- **Honesty contract:** this repo's own design ethos applies to its
  process too - every name spoken must be true, every claim has a
  verifiable command. Paste the command with the claim.
- **Rename history:** this package was renamed several times before
  it landed as `vefr` (2026-08-31). Env vars are `VEFR_*`. If you
  meet an old name in a comment, it's drift - fix it.
- **Known drift:** none. The 76 tracked runtime-state files under
  `data/` plus `worlds/poolworld/world-tree.md` were untracked
  2026-09-01 (`git rm -r --cached`, feat/dev-playability-five);
  the gitignore rules now hold alone.

## Style

- Python 3.11+, hatchling, `src/` layout. Deps: fastapi, uvicorn,
  httpx, pydantic - keep the list short.
- Markdown: one idea per line, prose lines kept short (see README).
- JS in `web/`: no framework; `state.js` is a plain object + patch
  function + subscribers. Shipped JS is tested by executing it under
  a node vm (see `tests/test_web_packaged.py`, `test_web_dom.py`) -
  new shipped behavior needs the same treatment.
- Engine voice: Norse-named, story-agnostic. Names from any specific
  game belong in that game's pack, never here.

## References

| Doc                            | What it is                                      |
| ------------------------------ | ----------------------------------------------- |
| `README.md`                    | Design philosophy: journey, runes, honesty      |
| `docs/guides/brain-socket.md` | Architecture: VEFR owns reality; brains plug in |
| `docs/guides/spark.md`        | Spark: the resident small brain, service + contract |
| `ROADMAP.md`                   | Landed/Next ledger - the project's memory       |
| `GETTING_STARTED.md`           | Install + first-world walkthrough               |
| `src/vefr/world.py` (docstring)| The pack contract, canonical form               |
| `docs/guides/handoff.md`       | The AI-buddy debugging bundle format            |
| `docs/guides/volumes.md`       | The 3-volume container layout                   |
