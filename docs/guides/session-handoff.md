# Session handoff - the next agent

Where the vefr session stands as of 2026-08-31, what the next
agent can skip verifying, what's still open, and the seams the
next agent will need to touch.

## What's verified now (don't re-prove)

Every line below was checked within the hour. Re-run any time the
next agent wants fresh evidence, but don't assume it's drifted.

| Check                                         | Command                                                                                | Result                                                                |
| --------------------------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Repo + working tree                           | `git status && git log --oneline -5`                                                  | clean, HEAD `2e94822`                                                |
| All pushed                                    | `git log --oneline origin/main -5`                                                     | matches local                                                         |
| Full test suite                               | `uv run --group test pytest -q`                                                        | **155 passed** in ~7.2s                                               |
| DOM harness (route-aware)                     | `uv run --group test pytest tests/test_web_dom.py -q`                                 | green (route table from `app.routes` via `VEFR_ROUTES_JSON`)          |
| Live bazzite health                           | `curl -s http://192.168.2.76:8820/api/health \| jq -c .`                              | `{"ok":true,"service":"vefr","purpose":"..."}`                        |
| Live world payload                            | `curl -s http://192.168.2.76:8820/api/world \| jq '.hero_start'`                      | non-null string                                                       |
| Live journal intact                           | `curl -s http://192.168.2.76:8820/api/journal \| jq 'length'`                         | **18 entries**                                                        |
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

Three things the next agent should know haven't been proven:

1. **No real-model pool weave has run end-to-end yet.** The pool
   generation path is unit-tested; the cross-box llama.cpp seam is
   reachable. But a full `ratatoskr weave --pool N` (~14 combos ×
   N samples × ~30s per generation) needs a warm model. From the
   dev box, single chat completions stalled past 60s — looks cold
   or queued. **Recommendation:** run the first real weave from
   bazzite itself (localhost llama.cpp, warm model, ~3-5 min for
   N=1) so the pool ships into a real `dist/<world>-<date>.html`.

2. **`preferences_add` MCP timed out twice** in the prior session.
   The langgraph journal wrote the decisions fine; the mem0
   preferences layer did not. **Next agent:** retry
   `preferences_get_profile` early in the session per the standing
   rule; if mem0 is still down, note it in the first response so
   the preference layer's degraded status is visible, not silent.

3. **The pool-draw runtime in `web/packaged.html` is not covered by
   the DOM harness.** The harness runs `web/index.html`, not
   `dist/<world>.html`. The route guard checks `/api/...` literals
   in the web layer (which the packaged file shares), but the
   pool-draw fallback (no endpoint → `window.VEFR_POOL` →
   `localStorage.vefr-pool-used`) is only end-to-end-tested by
   shipping a real woven file. **Follow-up:** a packaged-file
   harness, or a unit test that loads `dist/*.html` in jsdom and
   asserts the pool-draw path. Skip until a real woven file exists
   to test against.

## What to do next (pick one and start)

The path in the prior session was: **Harden → Redeploy → Pool**.
That landed. The next sensible moves, in rough order:

| # | Move                                                                | Why                                                                                       |
| - | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 1 | Run the first real `weave --pool 1 --pack sample-world` on bazzite  | Closes gap #1; produces a shippable `dist/sample-world-<date>.html` for a friend to test |
| 2 | Add a packaged-file harness                                         | Closes gap #3; makes the pool-draw path subject to the route-truth guard                  |
| 3 | USPTO + common-law name-collision search for `vefr` AND `Old Name`     | Pre-release gate; both names live on `rylee/vefr` description                              |
| 4 | Clean up the pre-rename `old-name-*.bundle` NAS backups                 | Rotation now covers both prefixes; old `old-name-*` bundles keep accumulating unless pruned  |
| 5 | Move Gitea to a public-reachable host before any public release    | `http://192.168.2.216:3000` is LAN-only                                                   |

The next agent should pick (1) first — it's the one piece of
in-progress work that the prior session couldn't close due to model
latency, and it's a clean 10-15 min job on bazzite. (2) through (5)
are queue items from the ROADMAP, in priority order, none blocking.

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
| `src/vefr/stefna.py`                    | `stefna_voice_key()` config-driven, defaults `"mother"`. `Letter` model + `generate_letter()`. |
| `src/vefr/export.py`                    | `_preface()` reads `logbok.md` + `lore-notes.md`; `refresh_living_tree(world, sid)`. Headings `## The Fen Walked`, `## The Whispers Heard`, `## Relics`, `## The Stefna`, `## The Voices Heard`, `## The Journal`. Includes a `fork` kind renderer. |
| `src/vefr/cli.py`                       | `ratatoskr` + `norns` entry points. `cmd_weave` has `--pool N`. `cmd_scaffold` (`ferry scaffold`) copies a pack as standalone repo. `cmd_backup` rotation prunes both `vefr-*.bundle` AND `old-name-*.bundle` — leave that as-is until #4 above. |
| `web/index.html` + `web/state.js`       | `window.VEFR_SESSION = { id, wrap, mint }`. Tab labels are Norse (Sagnir/Safn/Annall/Fræði/Spor/Old Name/Town). `data-view` keys kept stable — DOM harness depends on this. |
| `web/packaged.html`                     | Inlines `window.VEFR_WORLD/VEFR_LOGBOK/VEFR_LEDGER/VEFR_VOICES/VEFR_POOL`. Pool fallback: unused-from-this-combo → unused-from-any-combo → honest silence. `localStorage.vefr-pool-used` tracks spent. |
| `tests/fixtures/dom_harness.mjs`        | Reads `VEFR_ROUTES_JSON` (a file path) and validates every fetched URL against the real route table before answering. Falls back to bare stubs if env absent (so plain `node harness` still works). |
| `tests/test_web_routes.py`              | Scans `web/*.js` + `web/index.html` for `/api/...` literals; asserts each is in `app.routes`. The guard that would have caught the Stefna-tab incident. |
| `docs/guides/one-source-of-routes.md`   | The incident + the rule + the guard. Read before touching any web layer. |
| `worlds/lore/<name>/`                   | Five files: `textures.md`, `names.md`, `questions.md`, `prompt.md`, `LICENSE.md` (CC BY-SA 4.0). Not gitignored — they're shareable. |
| `worlds/<private-name>/` (gitignored)   | Rylee's private game (`private-canon` today). Lives on disk + `the private story repo` Gitea repo + bazzite `~/vefr-worlds/`. Don't commit into `rylee/vefr`. |

## Things the next agent must not do

These are decisions that already cost time once. Don't relitigate
without a real reason:

- **Don't re-point `git origin`** at the DuckDNS hostname. Default
  is `http://192.168.2.216:3000/rylee/vefr.git` (LAN-direct Gitea).
- **Don't rename the engine again.** `vefr` is the public name;
  `Old Name` is the private game that runs on the engine. Both repos
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

1. `git status && git log --oneline -5` — confirm clean, confirm HEAD.
2. `uv run --group test pytest -q` — confirm 155 green (if not,
   check for a half-finished edit before touching anything).
3. `curl -s http://192.168.2.76:8820/api/health | jq -c .` — confirm live.
4. `preferences_get_profile` — confirm mem0 reachable; if not, say
   so once and continue from `rylee.md`.
5. Read `docs/guides/one-source-of-routes.md` if touching the web
   layer; read `docs/guides/one-source-of-routes.md` if adding a
   new route anywhere; the rule is the same.
6. Pick from the "What to do next" table. (1) is the unfinished
   business from the prior session.
