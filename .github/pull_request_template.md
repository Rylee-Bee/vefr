name: Pull request

## What this PR does

<!-- one or two sentences -->

## Linked issue

<!-- "fixes #N" or "n/a" -->

## Type of change

- [ ] bug fix
- [ ] new feature
- [ ] refactor / cleanup
- [ ] docs
- [ ] CI / infrastructure

## How I tested it

- [ ] `uv sync --group test && uv run --group test ruff check src tests scripts`
- [ ] `uv run --group test pytest -q`
- [ ] `uv run --group test norns validate --pack worlds/<pack>`
- [ ] `python3 scripts/check_public_surface.py` (clean)

## Checklist

- [ ] I did not touch any protected Storyteller WIP file
      (`src/vefr/{cli,generator,storyteller_test}.py`,
      `docs/guides/storyteller-packs.md`, `deploy/vefr.container`,
      and the 20 untracked files in
      `tests/fixtures/storyteller/` + `storyteller_packs/` +
      `src/vefr/{npc_action,npc_action_scenarios,storyteller_benchmark}.py`).
- [ ] I did not name any specific game in engine code, prompts,
      API titles, tests, or docs (per AGENTS.md "Never" rule).
- [ ] If I added a new env var, I updated `example.env` and
      `docs/guides/install.md`.
- [ ] If I changed the pack contract, I asked first and updated
      `src/vefr/world.py` docstring.

## Notes for the reviewer

<!-- anything that surprised you, anything you'd want a second pair
     of eyes on -->
