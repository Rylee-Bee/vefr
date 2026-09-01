# Session handoff - the next agent

Where the vefr session stands as of 2026-08-31, what the next
agent can skip verifying, what's still open, and the seams the
next agent will need to touch.

## What's verified now (don't re-prove)

Every line below was checked within the hour. Re-run any time the
next agent wants fresh evidence, but don't assume it's drifted.

| Check                                         | Command                                                                                | Result                                                                |
| --------------------------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Repo + working tree                           | `git status && git log --oneline -5`                                                  | clean, HEAD `8a88221`                                                |
| All pushed                                    | `git log --oneline origin/main -5`                                                     | matches local                                                         |
| Full test suite                               | `uv run --group test pytest -q`                                                        | **200 passed, 2 skipped**                                               |
| DOM harness (route-aware)                     | `uv run --group test pytest tests/test_web_dom.py -q`                                 | green (route table from `app.routes` via `VEFR_ROUTES_JSON`)          |
| Live bazzite health                           | `curl -s http://192.168.2.76:8820/api/health \| jq -c .`                              | `{"ok":true,"service":"vefr","purpose":"..."}`                        |
| Live world payload                            | `curl -s http://192.168.2.76:8820/api/world \| jq '.hero_start'`                      | non-null string                                                       |
| Live journal intact                           | `curl -s http://192.168.2.76:8820/api/journal \| jq 'length'`                         | **2 entries**                                                        |
| Deployed world validates                      | `uv run norns verify`                                                                  | passes                                                                |
| llama.cpp reachable from dev box              | `curl -s -o /dev/null -w "%{http_code}" http://192.168.2.76:8081/v1/models`           | 200 in ~10ms                                                          |

The live stack: podman quadlet `~/.config/containers/systemd/vefr.container`
on bazzite `.76`, image `localhost/vefr:latest`, data `~/vefr-data/`,
worlds bind-mounted at `~/vefr-worlds/`, `VEFR_*` env in the unit
file (not the old `NORN_*` names — fixed at the redeploy). Restart
with `systemctl --user restart vefr` (NOT `podman restart`).

The dev box runs the same repo; `VEFR_LLAMACPP_URL` defaults to
`http://127.0.0.1:8081` (localhost) but the dev box has no llama.cpp
locally — live generation from dev routes through bazzite at
`http://192.168.2.76:8081`.

## What's still open (honest gaps)

None known as of this revision. The previous revision listed three
gaps; all three closed the same day (2026-08-31):

| Was open                            | Closed by                                                            | Evidence                                                                    |
| ----------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| No real-model pool weave end-to-end | `ratatoskr weave --pool` landed; first real weave vs the warm 6900XT | ROADMAP's "offline/no-server" LANDED note (10 lines, 24KB, sample-world)    |
| `preferences_add` (mem0) timing out | Layer recovered                                                      | `preferences_get_profile` verified live 2026-08-31; same-day memories written |
| Pool-draw runtime untested          | `tests/test_web_packaged.py`                                         | node-vm harness: no repeats, cross-combo fallthrough, honest null when spent |

New gaps go back in this section the moment they appear.

## What to do next (pick one and start)

The old (1) first-real-weave and (2) packaged-file harness landed
2026-08-31 (see the gaps table above). The queue now, in rough order:

| # | Move                                                                | Why                                                                                       |
| - | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 1 | Continue surface UI for combat packs (ROADMAP Next)                 | PR #4 landed the first pass (HP bar, tinted cards, encounter prompt, combat verbs); rendering follow-ups remain |
| 2 | USPTO + common-law name-collision search for `vefr`     | Pre-release gate; the name lives on `rylee/vefr` description                              |
| 3 | Clean up the pre-rename `*-*.bundle` NAS backups                 | Rotation now covers both prefixes; old bundles keep accumulating unless pruned            |
| 4 | Move Gitea to a public-reachable host before any public release    | `http://192.168.2.216:3000` is LAN-only                                                   |

The next agent should pick (1) first — it's the ROADMAP's top Next
item. (2) through (4) are queue items, in priority order, none
blocking.

## Seams the next agent will touch

A short tour of the layout so a fresh agent doesn't have to map it
from scratch:

| Path                                    | What lives there                                                                                |
| --------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `src/vefr/main.py`                      | FastAPI app. **Every state-touching route takes `session: str = ""` query param.** `/api/forge` was renamed from `forge` (URL stable, function is `forge_roll`); `/api/bell` was renamed from `bell` (URL is now `/api/stefna`); `/api/wiki` and `/api/trace` are read-only and have no model calls. |
| `src/vefr/sessions.py`                  | Per-session state: `clean(sid)`, `is_default(sid)`, `new_id()`, `derive(base, sid)`, `sessions_dir()`. `DEFAULT = "default"`. `SID_OK = r"[A-Za-z0-9_-]{1,64}"`. |
| `src/vefr/journal.py`                   | `KINDS = ("rumor", "npc_line", "item_forged", "stefna_letter", "fork")`. Per-session `_LAST_REMOVED: dict[str, dict]` undo stash. `set_entries`, `rewind`, `rewind_undo`. |
| `src/vefr/forge.py`                     | Same per-session undo stash shape. `forge_roll()` is the route handler. |
| `src/vefr/trace.py`                     | In-memory ring + JSONL trace (2 MB rotation). `trace.span(route, **detail)` context manager wraps model calls in `main.py`. |
| `src/vefr/pool.py`                      | `build_pool(samples, specials, progress=None)`, `ensure_current_world(name)`. Visitor pattern: set `VEFR_WORLD` for the build, restore in `finally`. |
| `src/vefr/stefna.py`                    | `stefna_voice_key()` config-driven, falls back to the pack's first declared voice. `Letter` model + `generate_letter()`. |
| `src/vefr/export.py`                    | `_preface()` reads `logbok.md` + `lore-notes.md`; `refresh_living_tree(world, sid)`. Headings `## The Fen Walked`, `## The Whispers Heard`, `## Relics`, `## The Stefna`, `## The Voices Heard`, `## The Journal`. Includes a `fork` kind renderer. |
| `src/vefr/cli.py`                       | `ratatoskr` + `norns` entry points. `cmd_weave` has `--pool N`. `cmd_scaffold` (`ferry scaffold`) copies a pack as standalone repo. `cmd_backup` rotation prunes both bundle prefixes — leave that as-is until #4 above. |
| `web/index.html` + `web/state.js`       | `window.VEFR_SESSION = { id, wrap, mint }`. Tab labels are Norse (Sagnir/Safn/Annall/Fræði/Spor/Town). `data-view` keys kept stable — DOM harness depends on this. |
| `web/packaged.html`                     | Inlines `window.VEFR_WORLD/VEFR_LOGBOK/VEFR_LEDGER/VEFR_VOICES/VEFR_POOL`. Pool fallback: unused-from-this-combo → unused-from-any-combo → honest silence. `localStorage.vefr-pool-used` tracks spent. |
| `tests/fixtures/dom_harness.mjs`        | Reads `VEFR_ROUTES_JSON` (a file path) and validates every fetched URL against the real route table before answering. Falls back to bare stubs if env absent (so plain `node harness` still works). |
| `tests/test_web_routes.py`              | Scans `web/*.js` + `web/index.html` for `/api/...` literals; asserts each is in `app.routes`. The guard that would have caught the Stefna-tab incident. |
| `docs/guides/one-source-of-routes.md`   | The incident + the rule + the guard. Read before touching any web layer. |
| `worlds/lore/<name>/`                   | Five files: `textures.md`, `names.md`, `questions.md`, `prompt.md`, `LICENSE.md` (CC BY-SA 4.0). Not gitignored — they're shareable. |
| `worlds/<private-name>/` (gitignored)   | Rylee's private game. Lives on disk + a private Gitea repo + bazzite `~/vefr-worlds/`. Don't commit into `rylee/vefr`. |

## Things the next agent must not do

These are decisions that already cost time once. Don't relitigate
without a real reason:

- **Don't re-point `git origin`** at the DuckDNS hostname. Default
  is `http://192.168.2.216:3000/rylee/vefr.git` (LAN-direct Gitea).
- **Don't rename the engine again.** `vefr` is the public name;
  The private game runs on the engine. Both repos
  exist. If a real trademark issue surfaces, file an issue and
  pause — don't pick a new name on the spot.
- **Don't add `hostname`, `mac_address`, or `com.docker.compose.*`
  labels** to compose files. (Doesn't apply to vefr directly, but
  applies to anything in the homelab repo.)
- **Don't write to `/opt/` on the stack VM directly.** Deploy-only.
- **Don't claim a weave or migration "works" without an end-to-end
  live verify command and its output.** The pool especially — the
  unit tests prove the chain but not the warm-model latency.

## Quick checklist for "continue on"

1. `uv run --group test norns doctor` — git sync, working tree,
   the test gate, the current pack, and (set `VEFR_LIVE_URL` to
   the live stack first) its `/api/health` — in one pass.
2. `preferences_get_profile` — confirm mem0 reachable; if not, say
   so once and continue from `rylee.md`.
3. Read `docs/guides/one-source-of-routes.md` if touching the web
   layer or adding a new route anywhere — the rule is the same.
4. Pick from the "What to do next" table.
