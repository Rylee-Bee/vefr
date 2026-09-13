# Contributing

VEFR is a small engine with a specific shape. The fastest way to
get a change in is to read this file end-to-end before opening the
PR.

## What the project is

- The **engine** ("the bones"). FastAPI + any OpenAI-compatible
  LLM. MPL-2.0-licensed, shareable. This is the only thing in this
  repository.
- **World packs** ("the flesh"). Data. Lives in
  `worlds/<name>/`. The shipped packs are `sample-world` (Emberfield,
  the playable demo) and three lore mood-boards under `worlds/lore/`.
- **The brain / provider** is not in this repository. You bring
  your own; the engine speaks `/v1/chat/completions`.

## What the project isn't

- Not a game. The engine renders whatever the world pack says.
- Not a hosted service. The engine runs on your machine and only
  talks to endpoints you configure.
- Not a multi-tenant system. There is no per-user database, no
  auth layer, no cloud fallback.

If a contribution would push the engine in any of those
directions, please open an issue first. The answer is often
"the world pack is the right place for that."

## Architectural principles

These are non-negotiable. If a change conflicts with them, the
change is wrong, not the principle.

1. **The world is authoritative; the brain is replaceable.** The
   engine owns geometry, validation, truth, memory, and the
   structured-output contract. The brain owns prose.
2. **Play Nice is the cooperation layer.** VEFR resolves
   behavioral authority to
   [Play-Nice Contracts](https://github.com/Rylee-Bee/play-nice-contracts)
   at the pinned revision in `.project/contracts/adoption.yaml`.
   Re-pin only with explicit discussion; the pin is load-bearing.
3. **Determinism beats cleverness.** No model calls in
   `export.py`, `weave.py`, `maplab.py`, `journal.py`. The runes
   are the only stochastic surface.
4. **Local-first, small-model-friendly.** The engine runs on CPU.
   A 0.8B model is a credible resident brain. Cloud-only
   features are a no.
5. **Truth is inspectable.** Persistent state lives on disk.
   Durable decisions go in `ROADMAP.md` and
   `.project/DECISIONS.md`. There is no hidden engine database.
6. **Accessibility is identity, not follow-up.** Every UI change
   answers the matrix: targets ≥44px, luminance over hue, plain
   English first, motion off by default, reading load short.

## The gate

Before opening a PR:

```sh
uv sync --group test
uv run --group test ruff check src tests scripts
uv run --group test pytest -q
uv run --group test norns validate --pack worlds/sample-world
python3 scripts/check_public_surface.py
```

Paste the pytest summary line into your PR description. A green
gate is a green gate — paste it, don't summarize it.

If you change a world pack, `norns validate` after every edit.
The tool always checks; never trust a hand edit.

## What needs an issue first

- Changing the pack contract (`src/vefr/world.py` REQUIRED keys,
  `VALID_SURFACES`, the loader's canonical shape, or the
  acts/flat on-disk layouts).
- Adding a tracked world pack beyond `sample-world`.
- A new public API route in `main.py`.
- Any git history rewrite.

## What you should never do

These are decisions that already cost time once:

- Don't commit story content from a private story-pack repo
  (any non-shipped pack under `worlds/` is gitignored).
- Don't name any specific game in engine code, prompts, API
  titles, tests, or docs. The engine is story-agnostic on purpose.
- Don't commit runtime state (`data/sessions/`, `data/vault-*.json`,
  `data/journal-*.json`, `data/weave.jsonl`,
  `worlds/*/world-tree.md`, `worlds/*/handbok.md` — all
  gitignored).
- Don't hand-edit `uv.lock`.
- Don't add `"think": true` (or drop `strict: true`) on any
  schema-constrained generation call.
- Don't bypass the public-surface guard with `// I know what I'm
  doing`. If a leak has to land, the right move is to update the
  guard's allowlist with a deliberate comment, in the same PR,
  with discussion.

## Touching the Storyteller WIP

`AGENTS.md` lists the protected WIP files. The summary: there is
a Storyteller capability in flight (homelab issue
rylee/vefr#50) that touches:

- `src/vefr/cli.py`, `src/vefr/generator.py`,
  `src/vefr/storyteller_test.py`
- `docs/guides/storyteller-packs.md`
- `deploy/vefr.container`
- `tests/fixtures/storyteller/*.json` (private-pack fixtures,
  including `rosa-after-close.json`)
- `storyteller_packs/*/`
- `src/vefr/npc_action.py`, `npc_action_scenarios.py`,
  `storyteller_benchmark.py`
- `tests/test_npc_action.py`, `test_storyteller_benchmark.py`

These stay on their WIP branch until the story-team design
lands. Public-release PRs do not stage them. If a refinement
pass needs to touch any of them, surface the conflict first.

## Commit and PR style

- One coherent PR per change. Atomic-per-PR is the rhythm: ship
  in one motion, mix concerns in the commit log if it gets the
  PR in faster.
- Commit message: short imperative summary; body explains the
  why.
- PR description: paste the pytest summary line. Paste any
  counters you claim ("16 passed", "5 deleted", etc.) next to the
  exact command that produced them.

## How decisions get made

VEFR resolves to Play-Nice for behavioral authority and to
the engine's own contracts for everything else. If a decision
question doesn't have an obvious home, open an issue and ask.

## Code of conduct

This project follows the Contributor Covenant. See
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions are licensed
under the same MPL-2.0 terms as the project for source/tooling
(see [`LICENSE`](LICENSE)). Contributions to world packs follow
that pack's license (CC0 1.0 for `sample-world`, CC BY-SA 4.0 for
the lore mood-boards). See each pack's `LICENSE` or `LICENSE.md`.
