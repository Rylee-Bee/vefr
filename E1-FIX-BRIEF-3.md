# E1 round 3 — the generated floor is not the same floor twice

You are the single build worker for one slice of the VEFR game engine, working alone in a
throwaway clone: you read, write, edit, run shell commands and commit here. Do not try to
launch `offload` or any other agent; it does not exist here.

Ten round-2 findings are fixed and in the tree you are given. **Two of this round's tests
fail when the coordinator runs them**, and one of those failures is a real defect that
invalidates the premise of round-2 finding 1. Fix both.

## Decisions in force (quote these; do not paraphrase them)

- 2026-10-04 Rylee, recorded in PLAN.md: floor identity is `(gen version, section content
  hash, floor_key)`, and `floor_key = run_seed/section.id/cycle/k`, with every stream named
  `prng("v3|" + floor_key + "|…")`. Same key, same floor, always.
- 2026-10-05 Rylee: "I want to have a fun project running alongside the infrastructure work."
  This lane is that project.
- 2026-10-05 Rylee: nothing goes live without her yes after a gallery preview.
- PLAN.md §2's forbidden list, in the player's parts as much as in Python: no `Math.random`,
  no clock, no globals; no floats other than `floor(rng() * n)`; never iterate a map's keys
  where draws are consumed; sorts must break ties by index.
- `src/vefr/delve.py` is the spec. If the Python plan is right and the JS player is wrong,
  fix the player. Never change the spec to match.

## Failure 1 — the same floor key draws two different floors (the important one)

`tests/test_descent_review_fixes_2.py::test_a_monster_killed_on_a_generated_floor_stays_killed_after_a_reload`
fails. It is not a bad test. The coordinator reproduced the cause directly, and the cause is
worse than the round-2 finding it was written for.

**Two sessions, one save, the same floor key, a different floor:**

```
SESSION 1 (begin, walk into the descent, fight the mob)
  region       cellar-0-1
  enemies      [{'id': 'm0', 'at': [15, 15], 'hp': 0, ..., 'alive': False}]
  doc run/seed 0 run-a
  floor k      run-a/cellar/0/1

SESSION 2 (same save handed back in, walk into the descent again)
  region       cellar-0-1
  enemies      [{'id': 'm0', 'at': [13, 15], 'hp': 1, ..., 'alive': True}]
  doc run/seed 0 run-a
  floor k      run-a/cellar/0/1
```

The run seed is the same, the floor key is the same, the id is the same — and the monster is
on a **different tile** ([15,15] against [13,15]) with full health. So the save's kill list is
not wrong; it is recording the death of a monster that the next session does not put there.

Ruled out by the coordinator, so you do not have to:

- it is **not** the `ONE_MOB_PATCH` fixture — the probe reproduces identically with no patch
  at all;
- it is **not** the `begin` step — adding `begin` to the second session changes nothing.

So: same key, different floor. That is PLAN.md §2's identity rule broken, and it is the
property the whole slice exists to guarantee.

**Why the existing tests do not catch it.** `tests/browser/test_descent_reload.py` compares
the *grid rows* after a reload and descends three floors inside one session; it never reads
the enemies snapshot, so a floor that redraws its monsters still passes it.

**What to do.** Find the draw that differs between the two sessions. Start from the
descent's own generation path in `web/player/parts/395-the-descent.js` — where the floor is
drawn at the stair, what it is seeded from, and what it is keyed on — and compare it against
`src/vefr/delve.py`'s plan for the same `floor_key`. Candidate causes worth checking, in this
order, and each is a guess to test rather than a conclusion:

- the stream name carries something that is not in the floor key (a counter, an attempt
  number, a timestamp, a length, an index that depends on what has already been drawn);
- a draw is consumed in one session and not the other, so every later draw is one out;
- the record's existing state (a kill list, an explored bitset, a depth) changes a filter or
  a bound, so the same key lays out differently once the floor has history on it;
- an id counter or a region-name index is seeded off mutable state;
- a clock or `Math.random` somewhere in the path, which PLAN.md §2 forbids outright.

**A test that would have caught it, and must exist afterwards:** two sessions, one save, and
assert the enemies snapshot is identical — same ids, same tiles — plus the round-2 assertion
that a killed monster is still dead. Put it in a new file; the frozen files may not be edited
to make this pass.

## Failure 2 — a round-2 test's expectation no longer describes the design

`tests/test_descent_review_fixes.py::test_a_save_over_the_byte_budget_is_never_stored_over_it`
fails at `assert got["storedFloors"] == delve.FLOOR_CAP` → `31 == 40`.

Round 2 enforced `FLOOR_BYTES` per floor record on write, so 40 records of 1.5 KB is 60 KB,
inside `SAVE_BYTES`, and the whole-save trim now sheds floors on its own to fit: 31 are kept,
not 40. That is the new design working. The round-2 worker already rewrote this test's first
assertion to the per-floor bound and left this one behind.

Required: make the test assert what the design now promises — the save that lands is inside
`SAVE_BYTES`, every record in it is inside `FLOOR_BYTES`, and nothing was refused — and drop
the "40 floors are kept" claim, saying in the file that the order of sacrifice is pinned by
the frozen `tests/test_descent_deltas.py`, which drives `trimDoc` directly. Do not weaken it to
whatever the code happens to print: say what the contract is.

## Rules for this pass

- **Write the test before the fix, in its own commit**, for Failure 1. For Failure 2 the test
  already exists and is simply wrong; correct it in its own commit with the reason.
- `src/vefr/delve.py` is the spec. If a finding turns out to be a defect in the spec rather
  than in the code that uses it, **stop and say so in UNRESOLVED**.
- **Never change a frozen test to make this pass.** The frozen E1 tests are
  `tests/test_descent_floors.py`, `tests/test_descent_deltas.py`,
  `tests/test_descent_parity.py`, `tests/test_descent_gen_card.py`,
  `tests/test_descent_bot.py`, `tests/test_descent_validator.py` and
  `tests/browser/test_descent_reload.py`. If one is genuinely wrong, fix it in its own commit
  and say why in that commit message.
- `web/packaged.html` is GENERATED: edit the part, and the coordinator rebuilds it with
  `scripts/build_player.py`. Never hand-edit it, and remember the harness weaves over the
  generated file — a correct part edit still measures as a failure until you rebuild.
- Your sandbox has no `uv`, no `node`, no `pytest` and no `ruff`, and no network. `python3`
  (the system one), `git`, `grep` and `sed` work. Do not claim a check you did not run — the
  coordinator has now been bitten twice by a fix that was argued rather than measured, so
  "NOT RUN" with a reason is worth more here than a confident summary.
- Every commit ends with exactly this trailer line:

      Co-Authored-By: MiniMax-M3.1-Flash-Preview <noreply@minimax.io>

- Stay inside this clone. No network access and no privileged commands are available.

## Report

End with the RESULT / CHANGED / CHECKS / EVIDENCE / UNRESOLVED / NEXT block. For Failure 1, the
EVIDENCE section must name the single site where the two sessions diverge and say which of the
candidate causes it was. If you cannot find it, say so and name where you got to — a
half-answer that names the next file to read is worth more than a guess.
