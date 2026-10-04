# S1 brief: the schema table core (saves and sound) (foreman plan)

Objective: make `tests/test_shapes.py` pass and keep `tests/test_validator_golden.py` green (read both first; frozen contracts, never edit them, nor `tests/golden/`; if a test contradicts this brief STOP and report). Read `docs/plans/tighten-shapes/PLAN.md` section 4 for the table design.

One worker (tier `code`), two seams:
1. New `src/vefr/shapes.py` (stdlib only): `Key`, `Block`, `Problem` (namedtuple `code pointer sentence`), `BLOCKS` with `saves` and `sound`, and `check(block, value)`. Default sentence templates per code, `Block.say` overrides per code, so every sentence stays byte-identical to today's (the golden is the proof; sound needs overrides, saves only for unknown-key).
2. `maplab.saves_errors` and `maplab.sound_errors` keep their signature and their `if 'saves' not in w: return []` guard, then return `[p.sentence for p in shapes.check(BLOCKS[name], w[name])]`. Delete the hand-written branches. Keep `SAVES_RULE_MODES` / `SAVES_LEGACY_MODES` if anything else reads them (grep first).

Constraints: no behaviour change; no other file edits except an import line; do not touch `skin`, tiles, sheets or rule actions.
Acceptance: `bash tests/run.sh tests/test_shapes.py tests/test_validator_golden.py tests/test_sound.py tests/test_rules_saves.py tests/test_rules_saves_pack.py --runxfail`, then the full suite.
