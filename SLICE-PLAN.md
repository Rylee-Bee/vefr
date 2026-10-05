# Slice E3 — the delve v3 JS twin (VEFR)

You are the single build worker for one slice of the VEFR game engine, working alone
in a throwaway clone: you read, write, edit, run shell commands and commit here. There is
no foreman and no sub-workers — do every step yourself, in order, committing each finished
step. Do not try to launch `offload` or any other agent; it does not exist here.

Your sandbox may not have `uv` or `node` on PATH and has no network. If you cannot run the
test suite, say so plainly in UNRESOLVED and still write the code and the tests; the
coordinator runs the gate outside your sandbox and reports what it sees.

## Repo and rules (they are not optional)

- Repo: VEFR (`Rylee-Bee/vefr`), a game ENGINE, MPL-2.0, Python 3.11+ under `src/vefr/`,
  the woven player under `web/`, tests under `tests/`. Read `AGENTS.md` in the repo root
  before you start; it is short and it is the boundary.
- `web/packaged.html` is GENERATED. Edit the parts under `web/player/parts/`, then run
  `uv run python scripts/build_player.py`. Never hand-edit `packaged.html`. A conflict in it
  is rebuilt, never merged.
- The engine must never name a game. `tests/test_pack_neutrality.py` enforces it.
- No model calls in deterministic surfaces: `export.py`, `weave.py`, `maplab.py`, `journal.py`,
  `blueprint.py`, `generator.py`, `delve.py`.
- Tests first, frozen, and committed in their OWN commit before the implementation starts.
  A frozen test is not edited to make an implementation pass. If a frozen test is genuinely
  wrong, fix the test in a separate commit and say so in your report with the reason.
- Every commit ends with exactly this trailer line:

      Co-Authored-By: MiniMax-M3.1-Flash-Preview <noreply@minimax.io>

- Out of scope for this slice: E1 play-time floors (another lane is running it in parallel, in its
  own worktree — do not touch the `descent` block, `locate()` or the save deltas), E6, E8, E9,
  E10, art, deploys, any network push, sudo.
- One squash PR at the end. Do not merge anything. Do not push.

## What this slice is

PLAN.md §5, row **E3**, in `docs/plans/endless-dungeon/PLAN.md`. Read before you plan: that
plan's §2 (generator architecture, the determinism rule, the Python/JS parity constraint) and §3
(budgets). Read §2 in full; it is the contract.

**The idea.** The v3 floor generator exists in Python as `src/vefr/delve_v3.py` (landed as
PR #289, slice E2) and it is the **spec**: it serves `vefr check` and the property sweeps. The
game runs in a browser, so the same generator must exist in JavaScript — the **runtime** — in
the part that defines `window.VEFR_DELVE`. This slice writes the JS twin, line by line, and proves
the two agree.

Already landed: `src/vefr/delve_v3.py`, `tests/test_floor_v3_properties.py`,
`tests/golden/floors/v3/*.json`, and E5a (stamps placed in the v3 generator — check whether the
Python side and the JS side both have stamps; if only Python has them, the port must include
them or parity cannot pass, and that belongs in your UNRESOLVED as "E5b's JS half landed here").
Also landed: the v2 twin pair, which is the pattern to follow exactly
(`src/vefr/delve.py` and `web/player/parts/390-engine-delve-v2.js`).

## The contract (PLAN.md §2, "The Python/JS parity constraint")

- `src/vefr/delve_v3.py` is the spec. The JS twin is the runtime.
- Each stage carries a **numbered draw-order comment**, as `generate_floor_v2` does. Stage order
  is fixed: plan, layout, graph (no draws), populate, validate. Each stage draws from its own
  seeded stream.
- Parity is checked **per stage** (layout first, then the plan JSON), so a mismatch shows where
  it starts rather than only that the floor differs.
- `tests/test_floor_v3_parity.py` runs **200 seeds × every size × every floor kind** through the
  real player in Chromium and compares canonical FloorPlan JSON.
- v2 stays pinned by hash and stays the fallback.

The determinism rule (PLAN.md §2) — a test must say so, and the port must obey it:

- `floor_key = run_seed/section.id/cycle/k`; each stream is
  `prng("v3|" + floor_key + "|layout")` and likewise `|plan`, `|pop`, `|loot|<mob id>`,
  `|chest|<chest id>`.
- Floor identity is `(gen version, section content hash, floor_key)`.
- Forbidden: `Math.random`, the clock and globals; floats other than `floor(rng() * n)` with
  `0 <= n < 2^31`; iterating a map/dict/object's keys where draws are consumed (use arrays sorted
  by id); sorts whose comparator can tie (break ties by index).
- Retry with `|try{n}` on the seed, up to 8 times, then fall back to v2; the fallback rate must
  stay below 0.5%.

FloorPlan is the canonical shape (PLAN.md §2):

    {"gen":3,"w":80,"h":56,"rows":["####…"],"rooms":[[x,y,w,h,"shape"]],
     "anchors":{"up":[x,y],"down":[x,y],"warden":[x,y],"vault":[x,y]},
     "pois":[{"at":[x,y],"name":"…","stamp":"id"}],"secrets":[[x,y]],
     "spawns":[{"id":"m7","family":"moth","elite":"big","group":"g2","leader":true,"at":[x,y]}],
     "chests":[{"id":"c3","at":[x,y],"table":"t1"}],"waypoint":false}

Keys in a fixed order on both sides; the comparison is on canonical JSON, so the twin and the
spec must emit the same bytes after canonicalisation.

## Acceptance (PLAN.md §5, row E3)

1. **Per-stage parity over 200 seeds** × every size × every floor kind, through the real player in
   Chromium. `tests/test_floor_v3_parity.py`.
2. **Perf budget in Chromium** (PLAN.md §3): generate + validate p95 over 200 seeds ≤ 40 ms
   desktop, ≤ 150 ms on the phone proxy (Chromium, 4× CPU throttle).
3. The whole repo gate green, which is what `--accept` runs:

       bash tests/run.sh && uv run --group test ruff check src tests scripts && uv run --group test norns validate --pack worlds/sample-world && python3 scripts/check_public_surface.py

A parity or determinism failure you cannot explain is a BLOCKED report with **the seed and the
stage**, never a loosened harness. Never weaken the parity test, never reduce the seed count, and
never make it skip, to get green. If Chromium cannot run in this clone, say so in UNRESOLVED with
the exact error, and run the parity harness in the node-vm/jsdom path that `tests/run.sh` links,
over the same 200 seeds, so there is still real evidence.

## How to run this slice

1. A worker maps `src/vefr/delve_v3.py` stage by stage against
   `web/player/parts/390-engine-delve-v2.js` and the current JS delve part, and writes the
   function-by-function porting table: stage, function, JS target, already present or missing.
   That table is the plan you then execute.
2. Write the FROZEN `tests/test_floor_v3_parity.py` (per-stage, 200 seeds, canonical
   JSON, plus the perf budget case) and commits it alone.
3. Port stage by stage in the order plan → layout → graph → populate → validate, keeping
   the numbered draw-order comments identical in meaning on both sides. Commit per stage.
4. Run whatever checks you can and fixes what it broke.
5. Rebuild `web/packaged.html` with `uv run python scripts/build_player.py` and prove it with
   `uv run python scripts/weave_digest.py`.
6. Update `ROADMAP.md` with exactly one entry for this landed change.

## Report (this exact shape, at the end)

    RESULT: <one sentence: is this slice done, and what is left>
    CHANGED: <files, with the commit sha of each logical step>
    CHECKS: <each command you ran and its result, verbatim output lines>
    EVIDENCE: <file:line for parity over 200 seeds, and the measured p95 numbers>
    UNRESOLVED: <anything a reviewer must decide, or NONE>
    NEXT: <the one action the coordinator takes next>

Be honest. A slice that is not done is not a failure to report as done.
