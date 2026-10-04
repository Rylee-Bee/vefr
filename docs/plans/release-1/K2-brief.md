# K2 brief: store() and its ban-lint (foreman plan)

Objective: make `tests/test_store_lint.py` and `tests/test_store_keys.py` pass (read both first; frozen; never edit them or `tests/fixtures/store_golden.json`; if one contradicts this brief STOP and report). No behaviour change: every saved key and value stays byte-identical.

One worker (tier `code`):
1. New `web/player/parts/065-store.js` (add to `web/player/manifest.json` right after `060-minimal-state.js`): `var store = { get(key), set(key, value), getJSON(key, fallback), setJSON(key, value) }`. Every method is a try/catch around `localStorage` and never throws; `get` returns null on failure, `getJSON` returns `fallback` on a parse or access failure, `set`/`setJSON` return nothing and swallow errors (JSON.stringify for setJSON; `set` stores `String(value)`).
2. Replace every direct `localStorage` call in the other parts with `store.*`. Keep each call's exact semantics (same keys, same encodings, same fallbacks; a part that wrapped the call in its own try/catch may keep the wrapper). Reword comments that mention `localStorage` so the lint passes. `200-pause-menu.js` line ~64 passes `localStorage` into `window.startoverKeys`: pass `store`-backed storage instead by giving 065 a `store.raw()` that returns `localStorage` inside 065 only (try/catch, null on failure), and keep `230-engine-startover.js` unchanged.
3. Rebuild `web/packaged.html` with the repo's own player build command (see `tests/test_player_build.py` for how); never edit it by hand.
Acceptance: `bash tests/run.sh tests/test_store_lint.py tests/test_store_keys.py tests/test_player_build.py tests/test_play_kit.py tests/test_album.py tests/test_complete_act.py tests/test_sound.py --runxfail`, then the full suite `bash tests/run.sh --runxfail` must pass with no test edited.
Constraints: stdlib only; neutral names; `git add` only files you changed; never commit PLAN.md or this brief. Run every worker in the foreground with a long timeout; never background, nohup or a monitor.
Final report: one JSON line `{"done": bool, "files": [...], "escalations": []}`.
