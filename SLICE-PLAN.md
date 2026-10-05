# Slice E1 — play-time floors (VEFR)

You are the foreman for one slice of the VEFR game engine. Read
`~/.agents/skills/offload/FOREMAN.md` first: it is the template and the rules.
Workers are `offload agent` runs in this clone. You have Bash/Read/Glob/Grep only:
all code comes from workers.

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

- Out of scope for this slice: E5b, E6, E8, E9, E10, anything under `worlds/` other than
  `worlds/sample-world` staying valid, art, deploys, any network push, sudo.
- One squash PR at the end. Do not merge anything. Do not push.

## What this slice is

The endless dungeon (PLAN.md §5, row **E1**, in `docs/plans/endless-dungeon/PLAN.md`). Read
before you plan: `docs/plans/endless-dungeon/PLAN.md` — §1 (the model), §2 (generator
architecture, the determinism rule, the save-deltas rule), §3 (sizes and budgets), §4 (fun at
scale). Read §2 in full; it is the contract.

**The idea.** A floor is sized by *minutes to play it* (6 to 10 minutes; a Section is one
evening), not by tiles. Floors are generated when the hero reaches the stair, from a run seed,
so an endless descent can go as deep as the player likes without the world pack carrying a map
for every floor. What the save keeps is a small set of deltas per visited floor, never a grid.

Already landed and yours to build on: K2 (`web/player/parts/065-store.js`, one `store()` helper
plus a lint that refuses `localStorage` anywhere else), E2 (`src/vefr/delve_v3.py` and its property
sweep), E5a (stamps in the v3 generator), E7 (elites, groups, leash), F1 (fog as a bitset),
S1 (`src/vefr/shapes.py`, the schema table), B1/B2 (Blueprint format 2 and 3).

## Scope (PLAN.md §5, row E1)

- the pack `descent` block (run seed, the New-descent control),
- `locate(depth, pack)` — pure, returns `(cycle, section, k)`, derived only from the pack's
  Section list; the story is cycle 0,
- a v2 floor generated at stair time (the shipped `generate_floor_v2`, not v3 — v3's JS twin is
  another slice running in parallel),
- a **virtual region**: the player's region tables gain the generated region on demand, so a
  floor that was not baked at weave time loads and plays. This is the biggest structural unknown
  in the plan (§7), so prove it first, before anything else in this slice,
- deltas through `store()` only — never a raw `localStorage` call anywhere,
- the `gen_version` card: a one-time "Start over" card keyed on `gen_version`, because a Release 1
  save cannot carry the new floors (§1 item 8).

Files likely touched: `src/vefr/delve.py`, `src/vefr/shapes.py`, `src/vefr/cli.py` (the bake),
the delve JS part (`web/player/parts/390-engine-delve-v2.js`) and the region-load part of the
player, `web/player/parts/065-store.js`.

## The rules that must hold (PLAN.md §2)

Determinism:

- `depth` is a global integer. `floor_key = run_seed/section.id/cycle/k`.
- Each stream is `prng("v3|" + floor_key + "|layout")` and likewise for `|plan`, `|pop`,
  `|loot|<mob id>`, `|chest|<chest id>`. Separate streams mean that changing an affix table never
  moves a wall.
- Floor identity is `(gen version, section content hash, floor_key)`.
- Forbidden, and a test must say so: `Math.random`, the clock and globals; floats other than
  `floor(rng() * n)` with `0 <= n < 2^31`; iterating a map/dict/object's keys where draws are
  consumed (use arrays sorted by id); sorts whose comparator can tie (break ties by index).

Save deltas — the save never stores a grid:

- per floor: the identity triple, killed mob ids, taken chest ids, items the hero dropped with
  their tile, secrets found, and an explored bitset (1 bit per tile, base64),
- permanent and story-level, kept in rule state: warden killed, vault read, landings reached,
  act flags,
- returning to town clears kills and chests for that Section (Stardew's mines reset); the
  explored bitset and the secrets found are kept,
- an identity mismatch on a visited floor regenerates the floor and drops its deltas; story flags
  are untouched, so progress is never lost,
- cap: deltas for at most 40 floors; evict the oldest bitsets first.

## Acceptance (PLAN.md §5, row E1) — all four, each as a test

1. Same seed gives the same floor after a reload in Chromium.
2. Deltas are inside the budget of §3: **≤ 1.5 KB per visited floor**, **≤ 250 KB for a whole
   save at 40 floors**. A test asserts the byte counts.
3. A Release 1 save (the pre-`gen_version` shape) shows the card once, and the game is playable
   after it.
4. The bot (`cottage-of-the-breeze/tests/playthrough/`, the player-level proof) plays three
   generated floors. If that harness cannot run from this clone because it needs the private pack,
   write the equivalent engine-side proof — three generated floors played end to end through the
   real player in the node-vm/jsdom harness — and say in UNRESOLVED that the Cottage bot still
   owes that run.

The whole repo gate must be green, which is what `--accept` runs:

    bash tests/run.sh && uv run --group test ruff check src tests scripts && uv run --group test norns validate --pack worlds/sample-world && python3 scripts/check_public_surface.py

## How to run this slice

1. A worker reads the plan sections above and answers, in writing, **where the virtual region
   hook goes**: the exact file and function in the player that loads a region, and the exact place
   the generated region must be inserted. If it cannot answer that from the code, stop and report
   the blocker's file:line rather than guessing.
2. A worker writes the FROZEN tests for acceptance 1 to 4 above and commits them alone.
3. Workers implement, smallest piece first, committing as they go. `store()` only.
4. A worker runs the gate and fixes what it broke.
5. Update `ROADMAP.md` with exactly one entry for this landed change (`AGENTS.md`: one ROADMAP
   entry per landed change). Update `.project/CURRENT.md` only if the phase changed.
6. Rebuild `web/packaged.html` with `uv run python scripts/build_player.py` and prove it with
   `uv run python scripts/weave_digest.py`.

## Report (this exact shape, at the end)

    RESULT: <one sentence: is this slice done, and what is left>
    CHANGED: <files, with the commit sha of each logical step>
    CHECKS: <each command you ran and its result, verbatim output lines>
    EVIDENCE: <file:line for each of the four acceptance items>
    UNRESOLVED: <anything a reviewer must decide, or NONE>
    NEXT: <the one action the coordinator takes next>

Be honest. A slice that is not done is not a failure to report as done.
