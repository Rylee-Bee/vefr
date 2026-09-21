# Contributing to vefr

Thank you for wanting to help build vefr — a rumor engine for playable worlds.

**Play-Nice promise:** Every contribution honors the [Play-Nice Contracts](https://github.com/Rylee-Bee/play-nice-contracts): truth and evidence before generating content, explicit state, asking instead of guessing, and accessibility floors. If your change touches a player-facing surface, read the accessibility matrix first.

## Quick start (for humans)

```sh
git clone https://github.com/Rylee-Bee/vefr.git
cd vefr
uv sync --group test
uv run --group test pytest -q       # should pass (412+ tests)
uv run uvicorn vefr.main:app --app-dir src --port 8820
# open http://127.0.0.1:8820
```

## Quick start (for agents)

1. Read `AGENTS.md` — it has every rule this repo enforces.
2. Read `.project/CURRENT.md` — what's true right now.
3. Run the gate: `uv run --group test ruff check src tests && uv run --group test pytest -q`
4. The 2 pre-existing failures (`test_face_roll_is_honest_without_a_model`, `test_map_propose_is_honest_without_a_model`) are model-dependent — they fail when no LLM is reachable. Ignore them.

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
uv run --group test ruff check src tests    # lint
uv run --group test pytest -q               # tests (412+ pass, 2 pre-existing fail)
uv run norns validate --pack worlds/sample-world  # pack integrity
```

## Accessibility matrix (every UI change must answer)

- **Targets:** ≥44px minimum tap/click target
- **Colour:** rank by luminance, never hue alone; no colour-only meaning
- **Motion:** off by default; `prefers-reduced-motion` respected
- **Keyboard:** every interactive element reachable and operable
- **Screen reader:** semantic HTML, ARIA labels, live regions for dynamic content
- **Reading load:** short, plain English; Norse as flavour, not requirement

## What never goes in

- Story content from a private pack (worlds under `worlds/` are gitignored unless shipped)
- Names of any specific game in engine code, prompts, API titles, or docs
- Runtime state (data/sessions/, vault JSON, journal JSON)
- Model calls in deterministic surfaces (export.py, weave.py, maplab.py, journal.py)

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

- **Issues:** Bug reports and feature requests welcome
- **Discussions:** For questions about building your own world
- **Security:** See `SECURITY.md` — never paste secrets in issues
