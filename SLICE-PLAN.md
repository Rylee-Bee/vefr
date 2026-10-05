# Slice S2 — one event table (VEFR)

You are the single build worker for one slice of the VEFR game engine, working alone
in a throwaway clone: you read, write, edit, run shell commands and commit here. There is
no foreman and no sub-workers — do every step yourself, in order, committing each finished
step. Do not try to launch `offload` or any other agent; it does not exist here.

Your sandbox may not have `uv` or `node` on PATH and has no network. If you cannot run the
test suite, say so plainly in UNRESOLVED and still write the code and the tests; the
coordinator runs the gate outside your sandbox and reports what it sees.

## Repo and rules (they are not optional)

- Repo: VEFR (`Rylee-Bee/vefr`), a game ENGINE, MPL-2.0, Python 3.11+ under `src/vefr/`,
  tests under `tests/`. Read `AGENTS.md` in the repo root first; it is short and it is the boundary.
- `validate()` still returns `list[str]` to every caller, so the error codes stay internal to
  the table and are pinned by `tests/test_shapes.py`. The public API does not change.
- The engine must never name a game. `tests/test_pack_neutrality.py` enforces it.
- No model calls in deterministic surfaces: `export.py`, `weave.py`, `maplab.py`, `journal.py`,
  `blueprint.py`, `generator.py`, `delve.py`.
- Tests first, frozen, and committed in their OWN commit before the implementation starts.
  A frozen test is not edited to make an implementation pass. If a frozen test is genuinely
  wrong, fix the test in a separate commit and say so in your report with the reason.
- Every commit ends with exactly this trailer line:

      Co-Authored-By: MiniMax-M3.1-Flash-Preview <noreply@minimax.io>

- Out of scope: S3 (the JS twin of the table — it needs K3, the camera split, which has not
  landed), A-series art slices, B-series Blueprint slices, anything under `worlds/` other than
  `worlds/sample-world` staying valid, deploys, any network push, sudo.
- One squash PR at the end. Do not merge anything. Do not push.

## What this slice is

PLAN.md §5 row **S2** in `docs/plans/tighten-shapes/PLAN.md` (the "tighten the shapes" plan).
Read §1 (the critical review), §4 (the schema table) and §7 (proof and rollback) before you
start. Epic: vefr #267.

**The idea.** Rylee's ask was "I want our code to be as tight as possible". The schema track
gives the validators one table of shapes instead of hand-written checks scattered across
`maplab.py`. S1 landed the table core (`src/vefr/shapes.py`, #281) with `saves` and `sound` on
it. **S2 puts the event vocabulary on it: one table.**

**The bug this slice exists to fix.** The event vocabulary is typed in **three** places and has
already drifted (vefr issue #269):

1. `maplab.py` `_rule_event_errors` (the rules validator),
2. `maplab.py` `_album_when_errors` (the album validator),
3. the JavaScript `EVENTS` table in `web/player/parts/440-the-camera.js` (the runtime).

`maplab.py` says "the six events are ..." in a sentence while `RULE_EVENTS` holds **eleven**.
S2 makes the Python side one table so 1 and 2 cannot drift again. It does **not** touch the JS
`EVENTS` table — that is S3, which needs the K3 camera split and is out of scope here — but S2
must leave a single obvious place for S3 to read.

Files to touch: `src/vefr/shapes.py` (the table) and `src/vefr/maplab.py` (the rules and album
`when` checks call into it instead of carrying their own list).

## Frozen tests

- The S0 validator golden already exists on `main`: `tests/golden/validator/cases.json`,
  `tests/golden/validator/gen.py`, `tests/test_validator_golden.py`. It is about 60 mutation
  cases built with `pack(base, patch)` merge patches, covering every sentence branch of the
  functions that migrate, and the expected `validate()` lists were captured on `main` before S1.
- **One sentence changes on purpose**: "the six events" becomes "the eleven events". Regenerate
  the golden for that case exactly once, and write the reason in the PR body: the sentence was
  wrong on `main`, not the validator.

## Acceptance (PLAN.md §5 row S2)

1. `tests/test_validator_golden.py` passes, with the one deliberate regeneration above.
2. `tests/test_rules_validator.py` passes.
3. `tests/test_album.py` passes.
4. The full gate green, which is what the coordinator runs:

       bash tests/run.sh && uv run --group test ruff check src tests scripts && python3 scripts/check_public_surface.py

5. Proof and rollback (PLAN.md §7): for explicit packs, `uv run python scripts/weave_digest.py`
   must be unchanged — this slice moves Python only and must not alter the woven player.

## How to build this slice (you do every step yourself)

1. Read `src/vefr/shapes.py` and learn the shape of the table S1 left. Then find every place the
   event vocabulary is spelled out on the Python side and list them with file:line.
2. Write the FROZEN tests and commit them alone.
3. Move the vocabulary onto the table; make `maplab.py`'s two validators read it. Delete the
   duplicated lists rather than leaving them as a second source.
4. Regenerate the golden for the "six events" sentence, in its own commit, with the reason in
   the message.
5. Run what checks you can; update `ROADMAP.md` with exactly one entry for this landed change.

## Report (this exact shape, at the end)

    RESULT: <one sentence: is this slice done, and what is left>
    CHANGED: <files, with the commit sha of each logical step>
    CHECKS: <each command you ran and its result, verbatim output lines>
    EVIDENCE: <file:line for the single table, and for each of the duplicated lists it replaced>
    UNRESOLVED: <anything a reviewer must decide, or NONE>
    NEXT: <the one action the coordinator takes next>

Be honest. A slice that is not done is not a failure to report as done. Never weaken the
golden to get green.
