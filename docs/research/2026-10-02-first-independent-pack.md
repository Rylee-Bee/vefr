# Findings from the first independent pack (2026-10-02)

Lanternwake was built as an independent consumer of VEFR - one
substantial game, written with a hard rule: never patch the engine,
only record what hurts. This file is the verification pass: every
claim it made checked against `main` at `ecbb1ea` (2026-10-02), then
classified and acted on.

Classification: **BUG** (the engine violates its own intended
contract) / **DOC** (implementation right, docs stale) / **GAP**
(missing general primitive) / **GAME** (that pack's design need) /
**UNKNOWN** (insufficient evidence).

Scope rule for everything below: no Lanternwake-specific feature
enters the engine. Each fix must be a primitive another unrelated
game could use, and finished games stay self-contained - no server,
no account, no network, no model.

## Findings matrix

| # | Claim (source: the pack's design/LIMITATIONS.md) | Verified evidence (2026-10-02, main) | Class | Action | Status |
|---|---|---|---|---|---|
| 1 | Pack inventory: 15 regions, 27 people, 50 books, 40 rules | counted from the pack: 15 / 27 / 50 / 40 ✓ | — | none | verified |
| 2 | "33 enemies" | **counted 44** (26 hand regions + 18 deep floors); the pack's README undercounts | GAME | fix in the pack (follow-up) | verified (claim false) |
| 3 | `opens` exists in rule vocabulary and has a runtime call site, but Interact's chest path never fires it (L4) | `grep`: `fireRule('opens')` only inside `useHere()` (packaged.html:3704); `useHere` has **zero callers**; `doInteract` chest branch opens with no event | BUG | fire `opens` through the canonical Interact path; delete the orphan; regression test on the interaction path | **implemented** |
| 4 | Docs say doors transition when stepped on; the player requires Interact (L18) | `rulesets.md:192` "A door is stepped on"; `world.py:53` same phrase; `move()` has no `transitionAt` call; only `doInteract` crosses (packaged.html:3650) | DOC | Interact is canonical (the one-button design is intentional and tested); correct docs + docstring wording | **implemented** |
| 5 | Runtime POI events carry display labels and distance 0; the validator requires declared thing ids and distance 1..9 (L5) | live probe reproduces 4 errors (labels unknown as things; distance 0 rejected); runtime sends exactly those shapes (packaged.html:972, :3773) | BUG | canonical identity model: **a POI's label is its id** (declared in the region contract) and `comes-near` distance is 0..9 (0 = on the tile). Validator, schema, runtime, docs, tests agree | **implemented** |
| 6 | `picks-up` fires for floor drops but not chest contents (L16) | `bagAdd` at 5 sites; `fireRule('picks-up')` only in `takeHere` (packaged.html:2240); chest (:3431), trade (:1187), rule `give` (:1910) silent | BUG | semantic contract: `picks-up` = the player acquired it by acting (floor, chest, trade). Rule `give` stays silent (the no-chains law). Tests per path | **implemented** |
| 7 | `handbok --pack X` consumed another pack's journal and printed that game's title/data (L21) | `cmd_handbok` reads global `data/trace.jsonl` + `list_entries()` unfiltered and titles with `load_world()` (the *active* world, not `--pack`) | BUG | scope by pack identity; fail closed on no data; cross-pack isolation test | **implemented** |
| 8 | Quest tools impossible: Use exists only for heal/light items and consumes them (L17) | `renderBagPanel` shows Use only for `heal`/`light` (packaged.html:1086); `useLightItem`/heal paths spend the copy | GAP | separate **usable** from **consumable**: a bare `use` verb grants the button and never spends; new `keep: true` makes any use free. Small, additive | **implemented** |
| 9 | Items can be given by rules but never removed (L7) | rule vocabulary has `give` only; `bagRemoveOne` exists but no rule reaches it | GAP | new rule action `takes` (remove one copy). Delivery/turn-in becomes expressible: `comes-near` + `has` + `takes` + `say` | **implemented** |
| 10 | Rules engine starved for observable events (P1 brief) | vocabulary is 6 events; player already performs defeats, buys, sells, reads, phase changes with no way for the world to notice | GAP | add `defeats`, `buys`, `sells`, `reads`, `phase-changes` - facts the engine already has. Deterministic, validated | **implemented** |
| 11 | Rule causality (`VEFR_WHY`) is recorded but invisible (L9 side) | `rulesWhyRecord` keeps 20 `{id, why}` in storage; no player surface | GAP | **Why did that happen?** panel from existing evidence only; plain words; accessible; nonintrusive | **implemented** |
| 12 | Players get lost: `point-to` hints are ephemeral (playtest's top complaint) | `VEFR_RULES_POINT_TO` prints one `combatSay` line and forgets it | GAP | **Where next?** panel: `point-to` results persist as inspectable intentions. Authored by rules; offline; no inference | **implemented** |
| 13 | 40-rule ceiling hit exactly (P2 brief) | `RULE_LIMIT = 40`; Lanternwake ships exactly 40 | GAP | do not raise blindly: propose scoping (region-local rules) in an ADR; keep 40 global until evidence | proposal (ADR) |
| 14 | Dialogue cannot react to flags except one-shot `say` (P2 brief) | seeds are keyed by phase only (`speakers[].seeds[phase]`) | GAP | smallest primitive: flag-conditioned seed selection. Pack-contract change → ADR | proposal (ADR) |
| 15 | Only `acts[0]` playable; one play surface per game (L1, L2) | `cli.weave_html` bakes `acts[0]`; `startPlaySurface` picks one screen | GAP | architecture work: verify + document intended progression; proposal only | proposal (ADR) |
| 16 | Combat verbs beyond `attack` are words (L6) | `applyVerb` damages only on `attack` | GAME | intentional costume model (documented); that pack's design problem, not an engine defect | no action |
| 17 | Tide flooding is cosmetic (L10) | `draw()` overlays flood tiles; walkability unchanged | GAME | consistent with the no-timers law; leave | no action |
| 18 | One shop per region; no stock (L8) | reward ruleset v1, documented | GAME | leave | no action |
| 19 | Creator reinvented: content/generate split, acceptance checks, art contact sheets | pack tooling (`tools/build_pack.py`, `check_*.py`, `art/tools/`) | GAP | evaluate small studio tooling: pack scaffold, `validate --play`, art contact sheets (trust boundary required) | proposal (ADR) |
| 20 | jsdom harness needs real origin + a tick + canvas stub (L19) | reproduced while building `tools/rules_test.mjs` | DOC | note in the testing docs; covered by the new fixtures' shared helpers where cheap | noted |
| 21 | *(found while implementing 5/6/9)* the same contract is mirrored in **four** places - `maplab` (validator), `_rule_bakes` + `_action_bakes` (the bake), `validAction` (the woven engine) - and the bake/engine mirrors had silently drifted: `takes` rules were dropped and distance-0 rules refused, with no error anywhere | reproduced: a fixture rule with `takes` baked away (`_rule_bakes`) and, when forced through, the engine skipped it whole (`validAction`); both mirrors pinned by new tests | BUG | bring every mirror in lockstep and pin the agreement in tests at both ends | **implemented** |
| 22 | *(found while implementing 7)* `refresh_living_tree` promised "failures must never break the mutation" but caught only `OSError` - a missing pack (a fresh world's first journal write) raised `PackError` through `journal.log` | reproduced: `journal.log` for a world with no pack throws | BUG | honor the documented contract (catch and return None) | **implemented** |

## What the matrix says in one line

The engine's contracts are honest but three seams let **call-site
accidents define game semantics** (events that cannot fire, one
acquisition path silent, ids the validator won't accept although the
runtime sends them) and one command lost pack scoping. Every fix
below widens a contract that already existed; none adds a hidden
mechanism.

## Deferred proposals

See `docs/adr/0004-scoped-rules.md`, `docs/adr/0005-dialogue-state.md`,
and `docs/adr/0006-acts-and-surfaces.md`. Creator tooling (pack
scaffold, play validation, art import) is evaluated in
`docs/adr/0007-creator-tooling.md`.

## Studio lesson (one)

**An independent pack finds contract bugs that feature design cannot,
because it hits the seams between three honest things** - the
validator, the runtime, and the docs - which were each written
against a slightly different moment of the same design. The fix is
never "add a feature"; it is "make the three agree, and add the test
that keeps them agreeing". The second lesson, smaller but real:
the player's question is rarely "how do I do more?" - it was "where
was I going?" - and the cheapest answer reused machinery the engine
already had.
