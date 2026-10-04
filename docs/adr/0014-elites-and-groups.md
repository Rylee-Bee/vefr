# 0014 - Elites and linked groups

Date: 2026-10-04

## Status

Proposed. Becomes Accepted when slice E7 merges. Plan: `docs/plans/endless-dungeon/PLAN.md` sections 1.4, 2 and 5.

Rylee's calls:
- one or two elites per floor;
- linked groups, where waking one member wakes the rest;
- sleeping monsters (E0d);
- maps up to 128x96.

## Context

Blueprint format 1 closes the enemy fields at `name, sprite, hp, atk, xp, sight, drops` (`FIELD_KEYS`, `src/vefr/blueprint.py`). ADR 0008 makes any new field a format change.

The plan warns that a group waking together can strike in one turn. The AI floods "once per turn, shared". `delve_v3.py` budgets one monster per 30 floor tiles, clamped to 4–36. Spawn ids must be seed-derived so the slain list survives regeneration (E0b).

## Decision

### Blueprint stays at format 1

Affixes, groups and wardens are **Section pack data** checked by `shapes.py`, not Blueprint keys. A Section `families` entry names a Blueprint family id; its base record comes from a new additive function, `vefr.blueprint.resolve_family(source, family_id)`, with its own test (frozen contract tests unchanged). Generated monsters are never written into an `enemies` list, so the stale rule does not apply.

A future family key (`moves`, `wakes`) is format 2: a `read_v2` reader, fixtures, a normalizer bump and an ADR 0008 amendment, in that order. This ADR adds none.

### Closed shapes

**Affix.** Affixes live in one list in `affixes.json` at the pack root, shared by all Sections. Ids are unique.

```json
{"id":"big","label":"Big {name}","hp":1.5,"atk":1.0,"xp":1.5,"sight":0,"scale":1.3,"extra_drops":1}
```

- `id`, `label` required; `label` contains `{name}`.
- `hp`, `atk`, `xp` in [1.0, 2.0]; `scale` in [1.0, 1.5]; all whole hundredths.
- `sight` (added to base) and `extra_drops` (extra rolls on the mob's `loot` stream): whole numbers in [0, 2].
- "Quick" is `sight: 1` until the AI can grant an extra move (UNKNOWN; E7 reads the AI loop). `moves` is reserved and rejected today.

**Section `elites`.** `per_floor [lo,hi]` with `hi <= 2`, and `affixes`, a list of affix ids.

**Section `groups`:**

```json
{"per_floor":[1,2],"minions":[2,3],"leader":"elite","same_family":true,"wake":"all","leash":6}
```

`per_floor` `hi <= 3`; `minions` `lo >= 1`, `hi <= 3` (at most 4 members); `leader` is `elite` or `normal`; `same_family` boolean; `wake` only `all`; `leash` whole, in [3, 12].

**FloorPlan spawn keys (closed).** `id, family, at, elite, group, leader, warden`. Only the first three are always present. `leader` appears only as `true`.

### Stats, in whole numbers only

`pct(m) = round(m*100)`; curve pct for floor `k` of `n` is `lo + (hi-lo)*(k-1)//(n-1)`; cycle pct is `min(100+20c, 160)`. `hp = max(1, base_hp * curve_pct * affix_pct * cycle_pct // 1_000_000)`, and `atk` likewise. `mob_stats(base, affix, section, k, c)` is twinned, parity-tested, and used by the balance report.

### Pop stage

**Budget.** `budget = clamp(floor_tiles // 30, 4, 36)`. Elites and group members are reserved from it first, and randoms fill what is left. The warden is outside the budget (ADR 0015).

**Hard caps.** These are applied after omens, so the "Crowded" omen cannot break them.
- 36 monsters, plus the warden;
- 2 lone elites;
- 3 groups;
- 4 members per group;
- 1 elite-led group per 8 rooms, but at least 1 when the Section's `per_floor` range asks for one.

**Placement.** A leader stands on a reachable tile at least 7 (`STAIR_CLEAR`) from both stairs, never in a vault, hall or secret room. Minions stand within Chebyshev 2 of the leader, in the same room or corridor region.

**Draw order.** This is appended to the stage's numbered comment.
1. Elite count. Then, per elite: family, affix, tile.
2. Group count. Then, per group: minion count, leader family (and affix if the leader is elite), leader tile, then each minion's family (only when `same_family` is false) and tile.
3. Randoms.

Monster ids are `m<n>` in draw order, and groups are `g<n>`.

### Monster AI (JS only, not twinned)

**Sleeping (E0d).** Every generated monster spawns asleep. E0d's own wording is not in these files, so its trigger is UNKNOWN. Until E0d is checked:
- A sleeper does nothing.
- A sleeper wakes when one of these happens:
  - the hero ends a turn within its `sight` (Chebyshev distance);
  - it takes damage;
  - a member of its group wakes.
- The room-reveal fog shows sleepers but does not wake them.

**Wake grace.** A monster that wakes during a monster phase first acts in the *next* phase, so a group can wake together but not strike together.

**Wake-all.** All members of a group are marked awake in the same phase that any one of them wakes.

**Leash.**
- A group's home is its leader's spawn tile.
- On floor load, the game runs one BFS per group from home, limited to `leash + 1` steps. The result is cached, not saved.
- A member never steps onto a tile farther than `leash` from home. At that edge it attacks only an adjacent hero.
- When the hero is out of the member's `sight`, the member walks home until it is within 1 tile, then idles awake.
- Lone monsters and elites keep today's behaviour.

**Turn cost.** One shared flood from the hero, cut off at 24 steps; at most three cached home maps; one step per awake monster (37 at most). E0a's 45-monster measurement covers this.

**Saves.** Only killed ids are saved; on reload, survivors are back on their spawn tiles, asleep.

### Validator rejects

One sentence plus a JSON pointer each: an unknown key (or `moves`) in an affix, `elites` or `groups`; a duplicate or undefined affix id; a family not in the Blueprint, or one resolving without `hp`/`atk`; an out-of-range value or a multiplier not in whole hundredths; a `label` without `{name}`; an elite leader with no affixes; `wake` other than `all`; an exceeded cap.

## Consequences

- An affix is one pack record. Wake grace keeps Cozy mode survivable. Leash maps cost little, once, at load.
- Reloading resets sleepers, so a player can escape a chase; accepted for a cozy game.
- Status affixes (`inflicts`) need a later amendment.

## Acceptance

- `tests/test_section_shapes_elites.py`: a golden sentence for each rejection.
- `tests/test_mob_stats.py` and its parity case: the stats are the same whole numbers in both languages, for 200 seeds x curves x affixes x cycles 0–5.
- `tests/test_floor_v3_properties.py` (extended): the caps hold over 200 seeds x sizes, including 128x96 and with omens on. Minions stay within 2 tiles of their leader. Leaders stay at least 7 tiles from the stairs.
- `tests/browser/test_group_wake.py`: hitting one member wakes all of them within 1 turn, and none of them attacks on the turn it woke.
- `tests/browser/test_group_leash.py`: members never pass `leash`, and they return home once the hero is out of sight.
- `tests/browser/test_turn_budget.py`: with 37 awake monsters on a 128x96 floor, a turn takes at most 8 ms on desktop and at most 30 ms on the phone proxy.

## Owner decisions (2026-10-04) and open questions

1. **Decided: sight plus noise.** A monster wakes when the hero comes within its wake radius, or when fighting or other loud events happen within earshot. (E0d built sight only; noise is added in E7.) **Loud events (owner, 2026-10-04): fighting, opening doors and chests, breaking things, and using stairs.** **Noise radius (owner, 2026-10-04): fighting 12 tiles, doors and chests 6, stairs and breaking 8.**
2. **Decided: the warden is awake and hunts the hero once the hero enters its hall** (it does not sleep). The hall entrance is the trigger; the validator must prove every warden hall has one.
3. Is wake grace (a free turn when monsters wake) the feel you want?
4. What should the affixes and their labels be called?
5. **Decided: reloading resets sleepers to asleep.** No awake state is saved.
