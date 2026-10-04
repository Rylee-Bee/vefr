# AGENTS.md

vefr - a rumor engine for playable worlds (MPL-2.0). Rylee's personal
profile comes from the global agent config — do not add personal files
to this repo.

## Quick navigation

| Want to... | Open this |
|---|---|
| Run the engine / build a world | `GETTING_STARTED.md` |
| See the whole path of making a game here (stops, lessons, rules for agents) | `docs/guides/journey.md` |
| Understand the bones/flesh split | `README.md` |
| Understand the brain/provider seam | `docs/guides/brain-socket.md` |
| Run the resident Spark service | `docs/guides/spark.md` |
| See what's landed / what's next | `ROADMAP.md` |
| Change what a world pack can hold | `src/vefr/world.py` docstring |
| Validate a pack | `uv run norns validate --pack worlds/<name>` |
| See every `vefr` verb (the one front door) | `docs/guides/vefr-command.md` |
| Find current truth / decisions | `.project/CURRENT.md` / `.project/DECISIONS.md` |
| Agent decision kernel & DoD | `AGENT_POLICY.md` |
| See Play-Nice behavioral authority | `.project/contracts/adoption.yaml` |
| Deploy the bundled brain | `docs/guides/bundled-brain.md` |

<!-- NOTE: the vefr row sits after "Validate a pack" because it is the
     CLI map of the table; the two old-CLI mentions were rewritten in
     place (repo-is bullet + CLI references block) rather than deleted,
     since both names still work as aliases. -->

## What this repo is

- **The engine only** ("the bones"): FastAPI + any OpenAI-compatible LLM backend. MPL-2.0-licensed.
- One front door: `vefr` (its verbs in journey order, `--help` is canonical). The two old CLIs, `ratatoskr` (ops: skipa, test, weave, ferry, volumes, spark) and `norns` (craft: chat, validate, migrate, build-map, delve, verify, handbok, doctor, storyteller-test, storyteller-benchmark), keep working as aliases.
- `worlds/sample-world/` (Emberfield) ships with the engine — the demo pack.
- `worlds/lore/<flavor>/` packs are data-only mood-boards (CC BY-SA 4.0).

## What this repo isn't

- **The game.** The engine is the bones; the author's story is the flesh, kept in a separate private pack repo. Any non-shipped pack under `worlds/` is gitignored. The engine must never re-learn a game's name.
- Multi-backend tied: llama.cpp preferred, Ollama fallback. Structured output only.
- **A mirror of its sibling engine repo.** Related, not synced: a separate private repo shares this codebase's rewritten-history origin (named in `.project/DECISIONS.md`, 2026-09-25; the engine tree must not name it — `tests/test_pack_neutrality.py`). That repo is now retiring its engine and folding its packs into VEFR; they still evolve independently — never merge, rebase, or cherry-pick between them without an explicit owner decision (port content by hand).

## Directory map

| Path | Purpose |
|---|---|
| `src/vefr/` | The engine. `world.py` is the only seam between engine + story |
| `web/` | The studio workshop (`app.html`, `studio.css`, `app.js`; `state.js` is the one client state), the woven player (`packaged.html`, GENERATED from `web/player/parts/`: edit a part, run `uv run python scripts/build_player.py`; a test fails if they disagree), art (`web/art/`), the studio shelf (`web/library/`) |
| `worlds/sample-world/` | Playable demo pack, acts shape, validates green |
| `worlds/lore/` | Three lore packs (norse, historical-event, norse-runes) |
| `tests/` | pytest suite, incl. node-vm harnesses for shipped JS |
| `.project/` | Current state, durable decisions, Play-Nice adoption pin, benchmark reports |
| `docs/guides/` | Operational guides (install, volumes, handoff, deploy, bundled-brain) |
| `scripts/` | CI helpers (public-surface guard, screenshot capture) |
| `deploy/` | Quadlet templates + startup script |
| `docs/screenshots/` | Committed screenshot gallery. CI (`screenshots.yml`) only uploads an artifact; refresh locally per `scripts/capture-screenshots.py` docstring |
| `bench/` | Model benchmarks (`bench/cli.py`); commit summaries to `bench/results/`, raw `bench/runs/*` output is gitignored. Rarely needed for engine work |
| `storyteller_packs/`, `templates/` | Tracked Storyteller packs and prompt templates (`docs/guides/storyteller-packs.md`) |
| `design/` | Design mockups, tokens, owner art (23 MB). Open for UI/art work, not for engine logic |
| `experiments/` | Scratch experiments; not shipped, excluded from the image |
| `data/` | Runtime state dir. A few tracked snapshot files predate the ignore rules (see Boundaries) — never add more |
| `.kilo/kilo.jsonc`, `.gitea/workflows/` | Kilo agent config (loads this file) and the legacy Gitea CI mirror |

## Commands

```bash
# The gate — run before claiming anything is done (mirrors ci.yml)
uv sync --group test
npm ci                    # jsdom for the node-vm harnesses; without it pytest errors
uv run --group test ruff check src tests scripts
uv run --group test pytest -q
bash tests/run.sh tests/test_x.py   # same, built for a throwaway clone (offload worker/foreman): links node_modules, offline, no foreign venv
uv run --group test norns validate --pack worlds/sample-world
python3 scripts/check_public_surface.py   # public-surface guard: catches private data in tracked files

# PR-only extras (dev-guards.yml): browser tests need Playwright chromium
uv run playwright install chromium   # once
VEFR_BROWSER_REQUIRED=1 uv run pytest -q tests/browser

# Static guards, same job (config lives in pyproject.toml)
uv tool run vulture        # dead code
uv tool run deptry .       # dependency hygiene
# CI-only too: lychee (offline link check) and Vale (prose, advisory)

# Session-start health
uv run --group test norns doctor

# CLI references (--help prints the live, complete command list)
uv run vefr --help        # the front door: every verb, journey order
uv run ratatoskr --help   # the old ops CLI, still an alias
uv run norns --help       # the old craft CLI, still an alias

# The player: web/packaged.html is GENERATED. Edit a part in web/player/parts/, then rebuild
# (tests/test_player_build.py fails if it is stale); weave_digest.py proves byte-equality
uv run python scripts/build_player.py
uv run python scripts/weave_digest.py

# Validate a world pack
uv run norns validate --pack worlds/<name>

# Run the engine locally
uv run uvicorn vefr.main:app --app-dir src --port 8820

# Package a single shareable HTML file
uv run ratatoskr weave --pool 5
```

## Boundaries

| Severity | Rule |
|---|---|
| **Always** | The gate above green before claiming done (matches CI). Paste the exact command + output. |
| **Always** | Every UI change answers the accessibility matrix: ≥44px targets, luminance over hue, motion off, keyboard + SR accessible. |
| **Always** | `norns validate` after any world-pack write. Never trust a hand edit. |
| **Always** | No model calls in deterministic surfaces: `export.py`, `weave.py`, `maplab.py`, `journal.py`, `blueprint.py`. |
| **Always** | One ROADMAP.md entry per landed change. Keep README/GETTING_STARTED in sync. |
| **Ask first** | Changing the pack contract, adding a tracked world pack, or a new public API route. |
| **Ask first** | Deploys (`ratatoskr ferry`, `deploy/`, `docs/guides/deploy.md`) and anything under CODEOWNERS (`scripts/`, `.github/workflows/`, licensing, `.gitleaks.toml`). |
| **Never** | Commit story content from a private pack, or name any specific game in engine code. |
| **Never** | Commit runtime state (sessions, vaults, journals, weave logs). Tracked runtime files already exist: `data/interface.jsonl`, `data/storyteller.jsonl`, `data/lore/` (snapshot commit `50a9fad`, now gitignored) and `data/vault.json` (committed with `7c74190`, not ignored). Untracking them is an owner call; don't refresh or stage them. |
| **Never** | Hand-edit `uv.lock` or drop `strict: true` on schema-constrained calls. |

## Style

- Python 3.11+, hatchling, `src/` layout. Deps: fastapi, uvicorn, httpx, pydantic, sqlite-vec (the Lorekeeper's vector index) — keep it short.
- Markdown: one idea per line, prose lines short.
- JS in `web/`: no framework; `state.js` is a plain object + subscribers. Shipped JS tested via node-vm harnesses.
- Engine voice: Norse-named, story-agnostic. Game-specific names belong in packs, never here.
- Branch model: `main` ← PR ← `feat/*`. CI runs on every PR: lint+test+validate+public-surface guard (`ci.yml`), secret scan (`secret-scan.yml`), security advisory intake (`security.yml`). Image publish (`publish-image.yml`) and screenshot capture (`screenshots.yml`) run on push to `main`.

## Cross-repo boundaries

- **Pack contract** (`src/vefr/world.py`) is consumed by private pack repos. Changing it is "Ask first"; record the companion change for the pack instead of editing another repo.
- Rylee's personal profile and estate rules come from the global agent config (`~/.agents/AGENTS.md`); don't restate them here.

## References

| Doc | What it is |
|---|---|
| `AGENT_POLICY.md` | Agent decision kernel: preflight, DoD, evidence requirements |
| `docs/guides/world-creation.md` | World authoring: norns chat -> validate -> build-map -> weave |
| `docs/guides/grammars.md` | Author grammars: offline whispers, weather, names |
| `docs/guides/rules.md` | Author rules: the eleven events, ids, actions, kept items |
| `docs/guides/lore.md` | The Lorekeeper: facts, the derived index, `vefr-lore` |
| `docs/uat/` | UAT contracts: a journey + machine-checkable acceptance triples |
| `README.md` | Design philosophy + screenshots + quickstart |
| `CONTRIBUTING.md` | How to contribute (human + agent onboarding) |
| `docs/guides/brain-socket.md` | Architecture: VEFR owns reality; brains plug in |
| `docs/guides/bundled-brain.md` | Bundled model fleet, ports, swap guide |
| `docs/guides/spark.md` | Spark: the resident small brain |
| `ROADMAP.md` | Landed/Next ledger |
| `GETTING_STARTED.md` | Install + first-world walkthrough |
| `src/vefr/world.py` | The pack contract (docstring) |
