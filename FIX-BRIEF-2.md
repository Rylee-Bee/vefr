# E3 fix pass 2 — the chest stage still diverges

You are the single build worker for one slice of the VEFR game engine, working alone in a
throwaway clone: you read, write, edit, run shell commands and commit here. Do not try to
launch `offload` or any other agent; it does not exist here.

Your sandbox has no `uv`, no `node`, no `pytest` and no `ruff`. That is expected: the
coordinator runs every check. Do not weaken, skip, resize or delete a test to make
something pass - you cannot run them anyway. Change the code until the parity is right by
reading both sides line by line, then say in UNRESOLVED which checks you could not run.

**A previous pass claimed a fix and was wrong.** It reported "checked 4800 floors,
0 mismatches" from a Python transliteration of its own reading of the twin, and the real
suite then failed on 20 of 4800 cases. Do not repeat that: you cannot prove parity from a
transliteration of your own new code. Reason from the spec line by line, and be explicit in
UNRESOLVED about what you are assuming rather than measuring.

## What the coordinator measured, outside your sandbox

    cd /var/home/agent/worktrees/vefr-e3
    bash tests/run.sh -q tests/test_floor_v3_parity.py

Pass 1's two commits are **already applied and are correct - do not revert them**:

- `web/player/parts/395-engine-delve-v3.js` — the randoms loop's bound was re-read from
  mutable state each turn; it is now hoisted into `var randoms`. That was right.
- `tests/fixtures/floor_v3_parity_harness.mjs` — the determinism check asked the twin for
  the streams of the literal placeholder `seed/section/kind`; it now builds the key from the
  first case's seed, kind and pack `id`. That was right too, and
  `test_the_twin_honours_the_determinism_rule` now passes.

The run still fails, **20 stage mismatches and 20 end-to-end mismatches**, and every one of
them is at **`size=48x32 kind=normal`**. The plan and layout stages still match on every
seed of the sweep. The graph stage reaches 4083 of 4800 cases and matches where reached.

The end-to-end mismatches are all on the **stamped** half of the sweep.

## The mismatches, verbatim

`python` is the spec, `twin` is the JavaScript.

    seed=sweep-0 stage=pop: at character 801
      python ... {"at":[14,19],"family":"moth","id":"m12"},{"at":[18,10],"family":"rat","id":"m13"},{"at":[29,8],...
      twin   ... {"at":[14,19],"family":"moth","id":"m12"}]}          <- twin's spawns array ENDS

    seed=sweep-3 stage=pop: at character 772
      python ... {"at":[29,18],"family":"beetle","id":"m11"},{"at":[3,2],"family":"rat","id":"m12"},...
      twin   ... {"at":[29,18],"family":"beetle","id":"m11"}]}        <- twin's spawns array ENDS

    seed=sweep-1 stage=pop: at character 44     <- the FIRST chest already disagrees
      python {"chests":[{"at":[27,4],"id":"c0","table":"t1"},{"at":[10,4],"id":"c1","table":"t1"},{"at":[16,4],...
      twin   {"chests":[{"at":[27,4],"id":"c0","table":"t2"},{"at":[10,4],"id":"c1","table":"t2"},{"at":[16,4],...

    seed=sweep-2 stage=pop: at character 45     <- the two tables are SWAPPED, not flipped
      python {"at":[34,18],"id":"c0","table":"t2"},{"at":[39,18],"id":"c1","table":"t1"},{"at":[9,4],...
      twin   {"at":[34,18],"id":"c0","table":"t1"},{"at":[39,18],"id":"c1","table":"t2"},{"at":[9,4],...

    seed=sweep-9 stage=pop: at character 83     <- the SECOND table disagrees, the first agrees
      python ... c0 t2, c1 t2, c2 t1
      twin   ... c0 t2, c1 t1, c2 t2

    seed=sweep-5 stage=pop: at character 83     <- twin has FEWER chests (2 vs 3)
    seed=sweep-7 stage=pop: at character 44     <- twin has FEWER chests (2 vs 3)
    seed=sweep-8 stage=pop: at character 85     <- twin has MORE chests (3 vs 2)
    sweep-4, sweep-6, sweep-11..38: the same three shapes, 20 in all

## Read this before you hunt

The chest block is **already textually faithful**. Spec `src/vefr/delve_v3.py:2137-2152`:

    chests: list[dict] = []
    off_path = sorted(
        (room for room in range(graph.room_count) if room not in set(graph.main_rooms)),
        key=lambda room: (-graph.depth[room], room),
    )
    spots = [(_center(tuple(canvas.rooms[room][:4])), room) for room in off_path]
    spots = [spot for spot in spots if spot[0] not in occupied]
    for number in range(min(_rand(rng, 2, 2 + plan["quota"] // 8), len(spots))):
        tile, _room = spots[number]
        occupied.add(tile)
        chests.append({
            "id": f"c{number}",
            "at": [tile[0], tile[1]],
            "table": CHEST_TABLES[_pick(rng, len(CHEST_TABLES))],
        })

Twin `web/player/parts/395-engine-delve-v3.js:2234-2262`:

    var mainRooms = new Set(graph.mainRooms);
    var offPath = [];
    for (var room = 0; room < graph.roomCount; room++) {
      if (!mainRooms.has(room)) offPath.push(room);
    }
    offPath.sort(function (a, b) {
      if (graph.depth[a] !== graph.depth[b]) return graph.depth[b] - graph.depth[a];
      return a - b;
    });
    var spots = [];
    for (var s2 = 0; s2 < offPath.length; s2++) {
      spots.push([center(head(canvas.rooms[offPath[s2]])), offPath[s2]]);
    }
    var free = [];
    for (var f = 0; f < spots.length; f++) {
      if (!occupied.has(spots[f][0][1] * canvas.w + spots[f][0][0])) free.push(spots[f]);
    }
    var chests = [];
    var chestCount = Math.min(rand(rng, 2, 2 + Math.floor(plan.quota / 8)), free.length);
    for (var n = 0; n < chestCount; n++) {
      var chestTile = free[n][0];
      occupied.add(chestTile[1] * canvas.w + chestTile[0]);
      chests.push({
        id: 'c' + n,
        at: [chestTile[0], chestTile[1]],
        table: CHEST_TABLES[pick(rng, CHEST_TABLES.length)],
      });
    }

`_pick` (`delve_v3.py:159`) is `int(rng() * count)` and `pick` is `Math.floor(rng() * count)` -
the same. `_rand` (`delve_v3.py:149`) is `lo + int(rng() * (hi - lo + 1))` and `rand` is the
same. **So the chest block is not where the bug is, and neither helper is.** Do not start
by editing this block; you will not find anything there.

**The bug is that the pop stream is one or two draws out of position by the time the chests
are drawn.** Every symptom fits that and nothing else fits it:

- sweep-1 has the same chest count and the same positions as the spec and still disagrees on
  the very first `table`. A wrong count cannot explain that; a stream offset can.
- sweep-9's FIRST table agrees and the second does not - one draw of drift.
- sweep-2's two tables are swapped - the drift can land anywhere.
- sweep-0 and sweep-3 show the twin's `spawns` array ending early, which is either
  `take(clear)` returning null sooner than the spec's, or a draw consumed where the spec
  consumes none. Either way it is upstream of the chests.
- sweep-5/7/8 diverge in chest COUNT, which is the `min(_rand(...), len(spots))` draw being
  read at a different point in the stream.

So hunt upstream, in this order, counting draws on both sides as you go:

1. **Every `place()` call between the start of `_pop_stage` and the chest block.** The spec's
   own comments at `delve_v3.py:2100-2120` and `2124-2135` are emphatic that the ORDER of
   draws is the ADR's order and that a placement costs no draw while a family draw always
   costs one - including a family drawn for a spawn that is never placed. Count the draws the
   spec makes at each site and count the twin's at the same site. A site where the twin draws
   a family before it has a tile, or fails to draw a family at all when a placement fails,
   shifts everything after it. This is the single most likely cause: pass 1 found exactly
   this class of bug one loop earlier.
2. **`take()` and the three pools.** `delve_v3.py:1915` documents the cursor rule - the pool
   is walked in the seed's spread order and its cursor moves forward because a tile only ever
   leaves the list. Read the twin's `take` and check (a) the pool is really an ordered array
   with a cursor and not a `Set` being iterated, (b) the leader pool is `clear` minus the
   spoken-for rooms in the SAME order rather than rebuilt in a different one, (c) the minion
   box is walked row-major on both sides, (d) the cursor is not rewound or re-sorted after a
   tile is taken, and (e) `take` returns null at the same point on both sides. A twin that
   walks its `clear` in `Set` insertion order where the spec walks `_spread(...)` order
   exhausts early and drops the tail spawns - that is sweep-0 and sweep-3 exactly.
3. **`occupied`.** The spec holds a set of `(x, y)` tiles; the twin holds a set of
   `y * w + x` integers. That is a bijection ONLY IF no tile is aliased - check that the
   twin's `place` adds the same key the spec adds, that nothing adds a key twice, and that
   `w` is the same `w` at every use. A single aliased or unadded tile changes which spots
   survive the free-filter and therefore the chest count and the stream offset together.
4. **`plan.quota`.** `2 + plan["quota"] // 8` in Python is an integer floor division on
   whatever `quota` is. Confirm the twin's `plan.quota` is the same number - a `undefined`
   that becomes `0` through `toInt`'s fallback would draw a different count while looking
   perfectly correct.

Do not fix one symptom and stop. When you have a candidate, read the WHOLE of `_pop_stage`
and the whole of the twin's pop function once more against each other, in order, counting
draws, before you commit.

## Also still open

- `395-engine-delve-v3.js` was 118,103 bytes after pass 1, of which 55,708 (47.2 percent)
  are whole-line `//` comments, against PLAN.md section 3's budget of 30 KB of engine-code
  growth in `packaged.html`. Do not delete the comments - the parity contract wants them and
  the reviewer owns that trade. Report the byte split again after your change.
- The stamped half of the sweep runs only at the two smallest sizes, because
  `STAMP_SIZES = SIZES[:2]` in the frozen `tests/floor_v3_parity_cases.py` is frozen. Say
  whether that is still true and why.

## Rules

- The Python spec `src/vefr/delve_v3.py` is the truth. Never change it to match the twin.
- Never change a frozen test to make the twin pass. The frozen tests are
  `tests/test_floor_v3_parity.py`, `tests/floor_v3_parity_cases.py`,
  `tests/browser/test_floor_v3_parity.py`, `tests/fixtures/floor_v3_parity_harness.mjs` and
  `tests/fixtures/floor_plan_canon.mjs`. If one is genuinely wrong, fix it in its own commit
  and say why in that commit message.
- `web/packaged.html` is GENERATED: edit the part, and the coordinator rebuilds it with
  `uv run python scripts/build_player.py`. Never hand-edit `packaged.html`.
- Every commit ends with exactly this trailer line:

      Co-Authored-By: MiniMax-M3.1-Flash-Preview <noreply@minimax.io>

  The previous pass refused this trailer on the grounds that it was signing as a different
  model. That was over-cautious and it costs the PR its merge review: the trailer is how
  `pr-land` knows the PR is another family's work at all. Use the trailer exactly as written
  above, on every commit.
- Stay inside this clone. No network access and no privileged commands are available.

## Report

End your final message with a RESULT / CHANGED / CHECKS / EVIDENCE / UNRESOLVED / NEXT
block. In UNRESOLVED, name the single site you most suspect and why, so the coordinator can
check that one thing first if it is still wrong.
