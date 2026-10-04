# V2 brief: `vefr check` follows the locks (foreman plan)

Objective: make `tests/test_lock_reachability.py` pass (read it first; it is the frozen contract, never edit it; if a test contradicts this brief STOP and report, do not work around it).

Task 1 (one worker, tier `code`): add `src/vefr/locks.py` with `findings(pack_dir) -> list[str]` and hook it into `vefr check` in `src/vefr/cli.py` with ONE small call (print each finding as a plain line, make `check` fail when any exist; a pack with no `requires` changes nothing in the output).

Facts to use (verify in the code): an acts-shape pack has `acts/<act>/world.json` with `regions` and `transitions` (`{from, at, to, to_at, requires?, locked_text?}`), region contracts at `acts/<act>/<region>/contract.json` (`hero_start`, `enemies[].drops`), library books `library/*.md` with front matter `drops:` and `at:`, speakers with `shop` and stock, world.json `items` (item `value` makes it sellable), `rules[].then[]` with `{"give": item}`. Reuse `maplab.load_pack` / existing helpers; do not duplicate parsing. Regions are reached from the world's start region (`player.wake.region`, else the first region). Transitions are one-way as declared (a way back is its own transition). A transition with `requires: {"item": X}` opens when X is obtainable in an already-reached region (enemy drops, chest-book drops whose book sits in that region, a shop in that region, or a rule give anywhere). Iterate to a fixpoint. Findings: a lock whose key is obtainable nowhere ("... unreachable"), a key obtainable only in regions behind that same lock ("... behind its own lock"), a key item that has a `value` ("... can be sold"). Flag locks are ignored. Keep each finding one plain sentence naming the item and the transition.

Constraints: stdlib only; no game-specific names (VEFR is public and neutral); do not touch web/packaged.html; do not change any existing test; `git add` only `src/vefr/locks.py`, `src/vefr/cli.py` and a one-line mention in `docs/guides/rulesets.md` (the lock checklist item) and `docs/features.json` (add the test file to the `gates` entry); never commit PLAN.md or this brief.

Acceptance (exit 0 only when right): `bash tests/run.sh tests/test_lock_reachability.py tests/test_locked_stairs.py tests/test_features.py --runxfail`

Final report: one JSON line `{"done": bool, "files": [...], "escalations": [...]}`.
Run every worker as a normal foreground Bash call with a long timeout; never background, nohup or a monitor.
