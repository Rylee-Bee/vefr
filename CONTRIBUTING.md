# Contributing to vefr

Thank you for wanting to help build vefr — a story engine for
playable worlds.

**Quick start:** clone, install, test, run:

```sh
git clone https://github.com/Rylee-Bee/vefr.git
cd vefr
uv sync --group test
uv run --group test pytest -q       # should pass — count varies; check no new failures
uv run uvicorn vefr.main:app --app-dir src --port 8820
# open http://127.0.0.1:8820
```

From here, pick what you want to do:

| Want to... | Read this |
|---|---|
| Fix a bug | Reproduce → fix → test gate → PR |
| Add a feature | `ROADMAP.md` → find the Next item → discuss in an issue first |
| Build a world | [`GETTING_STARTED.md` §3](GETTING_STARTED.md#3-make-your-own-world) |
| Change the UI | `web/` — follow the [accessibility matrix](#accessibility-matrix) below |
| Change the pack contract | `src/vefr/world.py` docstring — **ask first** |

## Play-Nice Contracts

This project adopts [Play-Nice Contracts](https://github.com/Rylee-Bee/play-nice-contracts)
as its shared cooperation constitution: truth and evidence before
generating content, explicit state, asking instead of guessing,
and accessibility floors. If your change touches a player-facing
surface, read the accessibility matrix first.

## Quick start (for agents)

1. Read `AGENTS.md` — it has every rule this repo enforces.
2. Read `AGENT_POLICY.md` — the decision kernel and definition of done.
3. Read `.project/CURRENT.md` — what's true right now.
4. Run the gate (must match CI exactly):
   ```sh
   uv sync --group test
   uv run --group test ruff check src tests scripts
   uv run --group test pytest -q \
     --ignore=tests/test_npc_action.py \
     --ignore=tests/test_storyteller_benchmark.py
   python3 scripts/check_public_surface.py
   ```
5. Known pre-existing failures (do not treat as regressions):
   - `test_npc_action.py` + `test_storyteller_benchmark.py` — WIP Storyteller files, excluded from CI via `--ignore` (tracked in rylee/vefr#50).
   - `test_face_roll_is_honest_without_a_model`, `test_map_propose_is_honest_without_a_model` — model-dependent; fail when no LLM endpoint is reachable.

## What to work on

| Want to... | Read this |
|---|---|
| Fix a bug | `GETTING_STARTED.md` → reproduce → fix → test gate → PR |
| Add a feature | `ROADMAP.md` → find the Next item → discuss in an issue first |
| Build a world | `GETTING_STARTED.md` §4 ("Make your own world") |
| Change the pack contract | `src/vefr/world.py` docstring — **ask first** |
| Add a new API route | `src/vefr/main.py` — **ask first** |
| Change the UI | `web/` — follow the accessibility matrix below |
| Run the engine in a container | `docs/guides/bundled-brain.md` |

## Branch model

```
main ← PR ← feat/*
```

- One PR per concern. Keep them small.
- PR targets `main`. No direct pushes (branch protection enforced).
- Rebase before requesting review if your branch is behind.

## Test gate (every PR must pass)

```sh
uv run --group test ruff check src tests scripts    # lint (scripts/ too — CI checks it)
uv run --group test pytest -q \
  --ignore=tests/test_npc_action.py \
  --ignore=tests/test_storyteller_benchmark.py      # tests (WIP files excluded, matches CI)
uv run norns validate --pack worlds/sample-world    # pack integrity
python3 scripts/check_public_surface.py            # no private IPs, hostnames, or creds
```

## Accessibility matrix (every UI change must answer)

- **Targets:** ≥44px minimum tap/click target
- **Colour:** rank by luminance, never hue alone; no colour-only meaning
- **Motion:** off by default; `prefers-reduced-motion` respected
- **Keyboard:** every interactive element reachable and operable
- **Screen reader:** semantic HTML, ARIA labels, live regions for dynamic content
- **Reading load:** short, plain English; Norse as flavour, not requirement

## Engine neutrality

The engine must stay story-agnostic — it works with any world pack,
including ones that don't exist yet. To keep that:

- No story content from private packs in tracked files
  (worlds under `worlds/` are gitignored unless shipped)
- No game-specific names in engine code, prompts, or API titles
- No runtime state (sessions, vault, journal)
- No model calls in deterministic surfaces
  (`export.py`, `weave.py`, `maplab.py`, `journal.py`)

## Commit messages

Keep them short, imperative, prefixed:

```
fix: correct ollama URL in GETTING_STARTED
feat: add title screen to woven HTML export
docs: update README with bundled brain section
test: add gitignore tripwire for worlds tracking
```

For messages with quotes or newlines, use `git commit -F <file>`.

## Play-Nice Contracts

This project adopts [Play-Nice Contracts](https://github.com/Rylee-Bee/play-nice-contracts) as its shared cooperation constitution. Every design, engineering, documentation, and release decision must point to the Play-Nice Contract it preserves or changes. See `.project/contracts/adoption.yaml` for the pinned revision.

## Getting help

- **[Issues](https://github.com/Rylee-Bee/vefr/issues):** Bug reports
  and feature requests welcome
- **[Discussions](https://github.com/Rylee-Bee/vefr/discussions):**
  For questions about building your own world
- **Security:** See [`SECURITY.md`](SECURITY.md) — never paste
  secrets in issues
- **Stuck?** Check [`GETTING_STARTED.md`](GETTING_STARTED.md) and
  the [API docs](http://127.0.0.1:8820/docs) (when the engine is
  running)
