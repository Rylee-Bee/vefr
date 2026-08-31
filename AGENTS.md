# AGENTS.md

vefr - a rumor engine for playable worlds (MIT). This file is loaded
by `.kilo/kilo.jsonc` `instructions:`. Rylee's personal profile
(voice, accessibility, shared agent rules) comes from the global
kilo config - do not add personal files to this repo.

| Want to...                        | Open this                                            |
| --------------------------------- | ---------------------------------------------------- |
| Run the engine / build a world    | `GETTING_STARTED.md`                                 |
| Understand the bones/flesh split  | `README.md`                                          |
| See what's landed / what's next   | `ROADMAP.md` (the ledger - update it when you land)  |
| Change what a world pack can hold | `src/vefr/world.py` docstring - the contract         |
| Validate a pack                   | `uv run norns validate --pack worlds/<name>`         |

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

- The game. The author's story (Old Name, `worlds/private-canon/`) lives in
  the private `the private story repo` repo and is gitignored here. Engine
  history was filter-repo'd on 2026-08-31 to remove every trace; the
  engine must never re-learn any specific game's name.
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
uv run --group test pytest -q      # 171 passed, 2 skipped (2026-08-31)

# One-command session-start check (git, tree, tests, pack, live)
uv run --group test norns doctor   # set VEFR_LIVE_URL to check a stack

# CLI references (canonical, always in sync with code)
uv run ratatoskr --help            # ops: skipa, test, weave, ferry
uv run norns --help                # craft: chat, validate, build-map, verify

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
| Always    | `maplab.validate()` (via `norns validate`) after any world-pack write. The tool always checks; never trust a hand edit.                                   |
| Always    | Keep deterministic surfaces deterministic: no model calls in `export.py`, `weave.py`, `maplab.py`, `journal.py`. The runes are the only stochastic surface. |
| Always    | One ROADMAP.md entry per landed change (Landed list, dated). Keep README/GETTING_STARTED in sync when commands or contracts change.                      |
| Ask first | Changing the pack contract: `world.py` REQUIRED keys, `VALID_SURFACES`, the loader's canonical shape, or the acts/flat on-disk layouts.                  |
| Ask first | Adding a tracked world pack beyond `sample-world`, or a new public API route in `main.py`.                                                             |
| Ask first | Any git history rewrite. (The 2026-08-31 filter-repo was a one-time, backed-up, verified operation - not a template.)                                    |
| Never     | Commit story content from `the private story repo` (`worlds/private-canon/` is gitignored - keep it that way), or name any specific game in engine code, prompts, API titles, or tests. |
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
- **Rename history:** this package was `old-name`, briefly `old-name`, then
  `norn`, now `vefr` (2026-08-31). Env vars are `VEFR_*`. If you meet
  an old name in a comment, it's drift - fix it.
- **Known drift:** 76 runtime-state files under `data/` plus
  `worlds/poolworld/world-tree.md` are still tracked despite matching
  gitignore rules (they predate the rules). Removing them is its own
  PR (`git rm -r --cached`), not a drive-by.

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
| `ROADMAP.md`                   | Landed/Next ledger - the project's memory       |
| `GETTING_STARTED.md`           | Install + first-world walkthrough               |
| `src/vefr/world.py` (docstring)| The pack contract, canonical form               |
| `docs/guides/handoff.md`       | The AI-buddy debugging bundle format            |
| `docs/guides/volumes.md`       | The 3-volume container layout                   |
