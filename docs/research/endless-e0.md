# E0a: benching the floor generator at four sizes

Measured 2026-10-04 on `ba79c72`, measurement only — no product code touched.
Answers items 1–5 of `docs/plans/endless-dungeon/PLAN.md` §3 for the **v2**
generator. The E0b answers (items 6–7) are in `docs/research/endless-e0b.md`.

## TL;DR

- **Generation is free.** Python p95 ≤ 0.79 ms, JS p95 ≤ 0.10 ms (0.43 ms
  throttled 4×) at every size — the ≤ 40 ms / ≤ 150 ms budget has ~50–400×
  headroom. The `MIN_STAIR_DISTANCE` fallback never fired (0/200 seeds at
  every size), and every walkable tile was reachable on every seed.
- **The monster turn is the binding constraint.** The real AI (parts 410/420/430)
  blows the ≤ 8 ms desktop budget beyond 48×32: 45 monsters cost 10.8 ms at
  64×48, 19.9 ms at 96×64, 33.3 ms at 128×96. Under a 4× throttle only 48×32
  stays inside ≤ 30 ms (27.8 ms at 45 monsters).
- **Fog storage fails the ≤ 1.5 KB save budget at every size** — 10.6 KB to
  77.6 KB of `"x,y"` strings for one fully explored floor. The plan already
  prescribes a bitset (§3 "Fog and auto-map"); this quantifies it.
- **Frames and autoexplore are fine.** Desktop frame work ~2.0–2.3 ms/task per
  frame (≤ 4 ms budget); clearing a floor takes 233–1419 explore turns.

## Method and its edges

Two commands produce every number below:

| Command | Produces |
|---|---|
| `uv run python scripts/bench_floors.py --seeds 200 --json bench/runs/endless-e0-py.json` | §1 Python times, §2 counts, walkable tiles, stair→stair turns |
| `VEFR_BENCH=1 uv run pytest -q tests/browser/bench_floor_play.py -s` | §1 JS times, §3 monster turns, §4 frames, §5 fog bytes, §6 explore turns |

(plus `uv run --group test pytest -q tests/test_bench_floors.py`, which proves
the counts repeat — see [Determinism](#determinism).)

Sizes are w×h×rooms: 48×32×16, 64×48×18, 96×64×24, 128×96×32. Seeds are
`bench-0` … `bench-199` (200 per size). Percentiles are nearest-rank,
`sorted[floor(p·(n−1))]`, identical in both languages.

Edges that shaped the numbers:

- **The generator is called directly**, not through `norns delve`: the
  "width and height 20 to 64" limits in `design/random-floors.md` are a
  *proposed* validator — nothing in `src/vefr/` enforces them on this commit,
  and 96×64 / 128×96 exceed them anyway. `generate_floor_v2`'s own contract
  (width/height ≥ 5, rooms ≥ 1) is all that is relied on.
- **JS timing is a mean of 10 generations per seed** — Chromium's
  `performance.now()` resolves ~0.1 ms, too coarse for one sub-millisecond
  floor. An FNV-1a checksum per seed is compared against Python's
  (`python_js_checksum_mismatches: 0` for all 4 × 200 seeds), so the times
  provably come from the twin, not a stub.
- **The monster turn runs the shipped AI verbatim** (parts 410, 420, 430
  inlined) inside a bench closure; `draw`, `combatSay`, `soundCue` and the
  growth/bag/gold helpers are no-op stubs. So §3 is AI + pathing **without**
  rendering — a lower bound on the in-game turn. Rendering cost shows up in
  §4 as `task_ms_per_turn`.
- **Play measurements use one seed (`bench-0`)** per size — a real woven
  player per size (sample pack copy + generated `bench` region; nothing
  tracked edited), autoexplore driving the camera. Counts (turns, fog bytes)
  are deterministic; times are not.
- Fog keys include non-walkable tiles: `litNow()` marks every tile in the
  radius-6 disc with no wall filter (`450-fog-of-war.js` L36–48). The bytes
  below are what the shipped code actually writes.

## 1. Generation time (Python and JS)

Python (`scripts/bench_floors.py`, 200 seeds, direct call):

| Size | p50 (ms) | p95 (ms) | max (ms) |
|---|---|---|---|
| 48×32×16 | 0.362 | 0.594 | 0.852 |
| 64×48×18 | 0.267 | 0.333 | 0.380 |
| 96×64×24 | 0.381 | 0.418 | 0.478 |
| 128×96×32 | 0.603 | 0.789 | 1.018 |

JS in Chromium (`generateFloorV2` verbatim; mean-of-10 per seed, 200 seeds):

| Size | p50 (ms) | p95 (ms) | p50 4× (ms) | p95 4× (ms) | checksum mismatches |
|---|---|---|---|---|---|
| 48×32×16 | 0.02 | 0.03 | 0.07 | 0.11 | 0/200 |
| 64×48×18 | 0.03 | 0.03 | 0.10 | 0.14 | 0/200 |
| 96×64×24 | 0.05 | 0.06 | 0.19 | 0.24 | 0/200 |
| 128×96×32 | 0.09 | 0.10 | 0.36 | 0.43 | 0/200 |

Every cell: budget ≤ 40 ms desktop / ≤ 150 ms phone → **PASS** everywhere
(worst cell 0.79 ms Python, 0.43 ms JS throttled).

## 2. Stair distance and reachability (200 seeds each)

| Size | stairs ≥ 10 apart | fallback below 10 | every walkable tile reachable | disconnected |
|---|---|---|---|---|
| 48×32×16 | 200/200 | 0 | 200/200 | 0 |
| 64×48×18 | 200/200 | 0 | 200/200 | 0 |
| 96×64×24 | 200/200 | 0 | 200/200 | 0 |
| 128×96×32 | 200/200 | 0 | 200/200 | 0 |

The v2 fallback rule (`MIN_STAIR_DISTANCE = 10`, `src/vefr/delve.py`) never
fired — the fallback rate the v3 plan caps at 0.5% is **0%** for v2 at every
size tested. "Reachable" is a flood fill from the up-stair over all non-wall
tiles compared against the full walkable set (so every room, and the
down-stair, is in one component).

Context — floor size and the shortest stair→stair path (both from the same
200 seeds):

| Size | walkable min / p50 / max | u→d turns p50 / p95 / max |
|---|---|---|
| 48×32×16 | 478 / 596 / 703 | 28 / 51 / 74 |
| 64×48×18 | 638 / 853 / 998 | 37 / 69 / 113 |
| 96×64×24 | 1131 / 1434 / 1870 | 49 / 86 / 121 |
| 128×96×32 | 1932 / 2466 / 2913 | 64 / 132 / 189 |

## 3. Monster turn (real AI, rendering stubbed)

One player turn, N awake monsters on a real `bench-0` floor, monsters reset
to spawn tiles before every sample; p50/p95 over the sampled turns.
`flood` = one `distMap` flood alone (the "once per turn, shared" number).

| Size | N | turn p50 (ms) | turn p95 (ms) | flood p50 (ms) | 4× p50 (ms) |
|---|---|---|---|---|---|
| 48×32×16 | 10 | 1.3 | 1.6 | 0.1 | 5.6 |
| 48×32×16 | 25 | 3.6 | 4.2 | 0.1 | 15.2 |
| 48×32×16 | 45 | 6.6 | 6.9 | 0.2 | 27.8 |
| 64×48×18 | 10 | 2.2 | 2.3 | 0.2 | 9.4 |
| 64×48×18 | 25 | 5.7 | 7.9 | 0.2 | 23.6 |
| 64×48×18 | 45 | 10.8 | 11.2 | 0.2 | 44.3 |
| 96×64×24 | 10 | 4.3 | 4.7 | 0.4 | 18.0 |
| 96×64×24 | 25 | 11.0 | 12.1 | 0.4 | 44.3 |
| 96×64×24 | 45 | 19.9 | 20.2 | 0.4 | 81.8 |
| 128×96×32 | 10 | 7.3 | 7.4 | 0.7 | 29.7 |
| 128×96×32 | 25 | 18.3 | 18.7 | 0.8 | 73.6 |
| 128×96×32 | 45 | 33.3 | 34.0 | 0.8 | 133.8 |

Budget ≤ 8 ms desktop / ≤ 30 ms phone (4× throttle):

| Size | 10 monsters | 25 monsters | 45 monsters |
|---|---|---|---|
| 48×32×16 | PASS / PASS | PASS / PASS | PASS / PASS (27.8 ms) |
| 64×48×18 | PASS / PASS | PASS / PASS | **FAIL** (10.8) / **FAIL** (44.3) |
| 96×64×24 | PASS / PASS | **FAIL** (11.0) / **FAIL** (44.3) | **FAIL** (19.9) / **FAIL** (81.8) |
| 128×96×32 | PASS / PASS (29.7 ms) | **FAIL** (18.3) / **FAIL** (73.6) | **FAIL** (33.3) / **FAIL** (133.8) |

Desktop cell / phone cell. Cost scales roughly linearly in N × floor area:
each monster's decision path-floods the floor, and one flood alone is cheap
(≤ 1.0 ms even at 128×96) — the sum over monsters is what breaks the budget.
This is the headline constraint on size.

## 4. Frame time while scrolling (autoexplore drives the camera)

6-second windows, 359 frames each (vsync-locked); `task_ms_per_frame` =
CDP `Performance.getMetrics` `TaskDuration` delta ÷ frames;
`task_ms_per_turn` = same delta ÷ turns executed in the window.

| Size | interval p50/p95 desktop (ms) | task ms/frame desktop | interval p50/p95 4× (ms) | task ms/frame 4× | task ms/turn desktop | task ms/turn 4× |
|---|---|---|---|---|---|---|
| 48×32×16 | 16.7 / 16.8 | 2.16 | 16.7 / 16.8 | 14.05 | 10.62 | 70.43 |
| 64×48×18 | 16.7 / 16.7 | 2.30 | 16.7 / 16.7 | 11.62 | 11.30 | 59.62 |
| 96×64×24 | 16.7 / 16.7 | 2.15 | 16.7 / 16.8 | 7.91 | 10.58 | 40.59 |
| 128×96×32 | 16.7 / 16.7 | 2.00 | 16.7 / 16.7 | 8.96 | 9.81 | 47.30 |

- **Desktop**: 2.00–2.30 ms average task per frame → budget ≤ 4 ms
  **PASS** at every size. (Frame *interval* is vsync 16.7 ms everywhere.)
- **Phone proxy**: 7.91–14.05 ms → ≤ 12 ms: PASS at 96×64 and 128×96,
  PASS at 64×48 (11.62), **FAIL at 48×32 (14.05)** — the 48×32 window was
  the first measured after load, so warm-up is a plausible contributor, but
  as measured it misses. The size ordering is non-monotonic for the same
  reason; treat the throttle column as ±one measurement window.
- **p95 per-frame work time: UNKNOWN.** CDP gives window-average task
  duration, not a per-frame distribution; a per-frame p95 needs tracing that
  the bench does not do. The interval p95 (16.8 ms) is the *pacing*, not the
  work, and is not a substitute.
- `task_ms_per_turn` (whole turn incl. rendering, during active explore)
  is 9.8–11.3 ms desktop — i.e. an exploring turn already exceeds the 8 ms
  monster-turn budget once render is added on top of §3's AI-only numbers.

## 5. Fog bytes at 100% explored (and floor-loot storage)

After autoexplore reports "Nothing left to explore here." with every
walkable tile visited (`walkable_tiles_explored == walkable_tiles` for all
four sizes — the 100% claim is proven, not assumed):

| Size | walkable (bench-0) | explored walkable | fog tiles (incl. walls) | `vefr-fog-*` bytes | `vefr-floor-*` bytes |
|---|---|---|---|---|---|
| 48×32×16 | 559 | 559/559 | 1399 (91.1% of map) | 10 587 | 0 |
| 64×48×18 | 868 | 868/868 | 2517 (81.9%) | 19 611 | 0 |
| 96×64×24 | 1437 | 1437/1437 | 5146 (83.8%) | 40 358 | 0 |
| 128×96×32 | 2431 | 2431/2431 | 9607 (78.2%) | 77 649 | 0 |

- Format confirmed: a JSON array of `"x,y"` strings, ~6–8 bytes per tile,
  written whole on every change (`450-fog-of-war.js` L33–35) — the E0b
  prediction measured exactly: a 96×64 floor costs ~40 KB, not ~1.5 KB.
- **Save-per-floor budget ≤ 1.5 KB: FAIL at every size** (7× to 52× over)
  *if fog counts as the floor's save*. Whether `vefr-fog-*` (localStorage)
  counts against the "save" budget is an interpretation call for E0c; if it
  does, no size passes today and the planned bitset is a prerequisite
  (a bitset over the map is `w·h/8` bytes: 1.5 KB at 48×32…12 KB at
  128×96, before encoding overhead — arithmetic, not measured).
- **Whole save at 40 floors ≤ 250 KB**: 40 × the fog column is 423 KB /
  784 KB / 1614 KB / 3106 KB → FAIL at every size under the same reading.
- `vefr-floor-<world>` (loot dropped on the floor, `430-loot-on-the-floor.js`)
  is 0 bytes on a clean explore — no combat, no drops. It is one list per
  *world*, not per floor, so its floor-scaling cost is UNKNOWN (needs a
  combat playthrough; out of E0a scope).

## 6. Autoexplore: turns to clear a floor

| Size | turns to clear (bench-0) | restarts after `EXPLORE_CAP` (400) | final status |
|---|---|---|---|
| 48×32×16 | 233 | 0 | Nothing left to explore here. |
| 64×48×18 | 369 | 0 | Nothing left to explore here. |
| 96×64×24 | 806 | 2 | Nothing left to explore here. |
| 128×96×32 | 1419 | 3 | Nothing left to explore here. |

The cap is `EXPLORE_CAP = 400` turns per click (`490-autoexplore.js`): floors
above ~400 turns need the player to press explore again (the bench does this
automatically; the count includes the extra turns). With §4's ~11 ms/turn
during explore, a full clear is ~2.6 s / 4.1 s / 8.9 s / 15.7 s of active
exploring — plus the stair→stair p50s from §2 (28–64 turns) as the
"minutes per floor" proxy.

## Budget verdicts (PLAN §3, current code)

| Budget | Desktop | Phone 4× | Verdict |
|---|---|---|---|
| Generate + validate p95 ≤ 40 / 150 ms | ≤ 0.79 ms (Python) | ≤ 0.43 ms (JS) | **PASS** all sizes |
| Monster turn ≤ 8 / 30 ms | 45 monsters: 6.6 / 10.8 / 19.9 / 33.3 ms | 45 monsters: 27.8 / 44.3 / 81.8 / 133.8 ms | **PASS 48×32 only** at 45 monsters; 96×64 and 128×96 fail from 25 monsters |
| Frame while scrolling ≤ 4 / 12 ms | 2.00–2.30 ms | 7.91–14.05 ms | **PASS** desktop all sizes; phone FAILs 48×32 as measured (14.05) |
| Save per visited floor ≤ 1.5 KB | 10.6–77.6 KB fog | — | **FAIL** all sizes if fog counts (else PASS: loot list = 0 B) |
| Whole save at 40 floors ≤ 250 KB | 423 KB – 3.1 MB fog | — | **FAIL** all sizes under the same reading |
| `packaged.html` growth ≤ 30 KB | 0 (E0a adds no engine code) | — | **PASS** by construction |
| JS heap for the floor ≤ 5 MB | — | — | **UNKNOWN** — not measured (needs CDP heap snapshot per size; not in E0a's six items) |

## Determinism

Counts repeat across runs; only timings vary:

- `uv run --group test pytest -q tests/test_bench_floors.py` → **2 passed**.
  It runs the Python bench twice and asserts `stair_distance`,
  `reachability`, `walkable_tiles`, `stair_to_stair_turns` and `seeds` are
  byte-identical between runs.
- The browser bench repeats autoexplore for 48×32 twice in one session:
  `[233 turns, 10587 fog bytes, 1399 fog tiles]` both times
  (`explore_repeatability.identical: true` in
  `bench/runs/endless-e0-play.json`).
- JS/Python parity: FNV-1a checksums equal for all 4 × 200 seeds
  (`python_js_checksum_mismatches: 0`).

## UNKNOWNs (marked, per the brief)

| Cell | Why |
|---|---|
| Per-frame work p95 (§4) | CDP gives window averages, not per-frame distribution; needs tracing |
| `vefr-floor-*` bytes under combat | 0 on a clean explore; needs a fight to populate (out of scope) |
| JS heap per floor (§3 budget) | Not among E0a's six items; needs a heap snapshot per size |
| Fog's status vs the "save" budgets | An E0c interpretation call — measured bytes are exact either way |

## Reproduce

```bash
uv run python scripts/bench_floors.py --seeds 200 --json bench/runs/endless-e0-py.json   # §1–2
VEFR_BENCH=1 uv run pytest -q tests/browser/bench_floor_play.py -s                        # §1, 3–6
uv run --group test pytest -q tests/test_bench_floors.py                                 # determinism proof
```

Raw JSON: `bench/runs/endless-e0-py.json`, `bench/runs/endless-e0-play.json`
(gitignored run output).
