# E0a: bench the floor generator at four sizes (measurement only)

Objective: measure, do not build. Add `scripts/bench_floors.py` and `tests/browser/bench_floor_play.py` (a browser bench, skipped unless `VEFR_BENCH=1`) and write the report `docs/research/endless-e0.md`.

Use the existing v2 generator (`src/vefr/delve.py` `generate_floor_v2`, and the JS twin `generateFloorV2` in `web/player/parts/390-engine-delve-v2.js`). Sizes (w x h x rooms): 48x32x16, 64x48x18, 96x64x24, 128x96x32. Seeds: 200 per size (`bench-0` to `bench-199`). The validator limits (20..64) may refuse large sizes: call the generator functions directly and note it.

Measure and report as a table (p50 and p95, or counts):
1. Generation time in Python and in JS (Chromium via Playwright), per size.
2. Fraction of seeds where up and down stairs are at least 10 apart (the `MIN_STAIR_DISTANCE` fallback rate) and where every room is reachable.
3. Monster turn cost: place 10, 25 and 45 awake monsters on a floor of each size and time one player turn (`web/player/parts/410-the-living-hazards.js` AI). If that is not callable in isolation, say so and time the flood fill alone.
4. Frame time while the camera scrolls across a floor, desktop and with `cdp.Emulation.setCPUThrottlingRate(4)`.
5. Bytes of `vefr-fog-*` after exploring 100% of a floor at each size (see `450-fog-of-war.js`).
6. Turns for autoexplore (`490-autoexplore.js`) to clear a floor, per size.

Rules: new files only; do not edit `src/` or `web/player/`. Deterministic counts must repeat across runs (only times vary). Each number cites the command that produced it. Mark anything you could not measure `UNKNOWN`.

Acceptance: `uv run --group test pytest -q tests/test_bench_floors.py` passes (write a tiny test that runs the bench with 5 seeds at 48x32 and checks the output shape), `ruff` clean, and the report has every cell filled or marked UNKNOWN.
