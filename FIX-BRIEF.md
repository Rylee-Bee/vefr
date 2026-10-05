# E3 fix pass

You are the single build worker for one slice of the VEFR game engine, working alone in
a throwaway clone: you read, write, edit, run shell commands and commit here. Do not try
to launch `offload` or any other agent; it does not exist here.

Your sandbox has no `uv`, no `node`, no `pytest` and no `ruff`. That is expected: the
coordinator runs every check. Do not weaken, skip, resize or delete a test to make
something pass - you cannot run them anyway. Change the code until the parity is right by
reading both sides line by line, then say in UNRESOLVED which checks you could not run.

## Where things stand

`web/player/parts/395-engine-delve-v3.js` is a line-by-line JavaScript twin of the Python
spec `src/vefr/delve_v3.py`, landed in the previous pass with a frozen per-stage parity
harness. It is committed on this branch. Read PLAN.md section 2 in
`docs/plans/endless-dungeon/` first: the parity constraint and the determinism rule.

## What the coordinator measured, outside your sandbox

    bash tests/run.sh -q tests/test_floor_v3_parity.py

All three tests fail:

1. `test_every_stage_matches` - 20 stage mismatches.
2. `test_every_floor_matches_end_to_end` - 20 end-to-end mismatches.
3. `test_the_twin_honours_the_determinism_rule` - the twin reports its stream labels as the
   literal placeholder string `seed/section/kind` instead of the real floor key:

       twin:   plan stream 'v3|seed/section/kind|plan'
       spec:   plan stream 'v3|sweep-0/cellar-normal/normal|plan'

   The real key is run_seed / section.id / kind. `tests/floor_v3_parity_cases.py:115`
   (`floor_key`) already builds it correctly on the Python side.

Good news: the plan and layout stages match on every seed. Every reported mismatch is in
the populate stage (`pop`) and in the end-to-end floor that contains it. Fix `pop` first.

## The mismatches, verbatim from the harness

Each line names the seed, size, kind, stage, and the character where the two canonical JSON
strings first differ. `python` is the spec, `twin` is the JavaScript.

    seed=sweep-0 size=48x32 kind=normal stage=pop: at character 801:
      python ... family rat id m13, then at [18,10] family rat id m14 ...
      twin   ... family moth id m12, then the spawns array ends

    seed=sweep-1 stage=pop: at character 44:
      python chests c0 table t1 at [27,4], c1 table t1 at [10,4], c2 ...
      twin   chests c0 table t2 at [27,4], c1 table t2 at [10,4], c2 ...

    seed=sweep-2 stage=pop: at character 45:
      python chests c0 table t2 at [34,18], c1 table t1 at [39,18]
      twin   chests c0 table t1 at [34,18], c1 table t2 at [39,18]

    seed=sweep-3 stage=pop: at character 772:
      python ... family beetle id m11, then at [3,2] family rat id m12, then m13 ...
      twin   ... family beetle id m11, then the spawns array ends

    seed=sweep-4 stage=pop: at character 117:
      python ... c1 table t2 at [22,4], c2 table t1 at [22,4], then spawns ...
      twin   ... c1 table t2, c2 table t2 at [22,4], c3 table t2 at [27,2], then spawns ...

    seed=sweep-5 stage=pop: at character 83: chest tables and chest count differ
    seed=sweep-7 stage=pop: at character 44: python has c0, c1, c2; twin has c0, c1 only
    seed=sweep-8 and sweep-9: the same shape

Read those as three symptoms:

- the chest table draw (t1 against t2) diverges from the first chest onwards, so the table
  choice is not coming off the stream the spec uses;
- the number of chests diverges - the twin stops early, or places a different number;
- the number of spawns diverges - the twin's spawns list ends where the spec's continues.

Likely causes, in this order. Check each against the spec's populate stage rather than
guessing:

- a stream name that is not byte-identical to the spec's: a prefix, a suffix, a
  chest-id separator, or a different id order;
- a draw count that differs - the spec may derive the number of chests or mobs from an area
  budget and then run a rejection loop, and the twin must reject identically;
- an id counter that starts at a different place;
- a filter (reachable, at least 7 tiles from the stairs, inside the budget) applied with a
  different comparison, strict against non-strict;
- a sorted-by-id iteration where the twin iterates in insertion order. PLAN.md forbids
  iterating a map's keys where draws are consumed; use arrays sorted by id.

Compare the two functions line by line, in order, counting the draws on each side as you
go. Do not fix one symptom and stop: fix the stage, then read it once more against the spec.

## Also open from the first pass

- `395-engine-delve-v3.js` is 117,552 bytes and grows the woven player by about 118 KB,
  against PLAN.md section 3's budget of 30 KB of engine-code growth in packaged.html. About
  47 percent of the file is the spec's numbered draw-order comments, which the parity
  contract wants in both languages. Do not delete the comments - the reviewer decides that
  trade. Report the byte split again after your change.
- The stamped half of the sweep runs only at the two smallest sizes. Say whether that is
  still true and why.

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

- Stay inside this clone. No network access and no privileged commands are available.

## Report

End your final message with the same RESULT / CHANGED / CHECKS / EVIDENCE / UNRESOLVED / NEXT block SLICE-PLAN.md asks for.
