# 0013 - Stamps: hand-painted rooms in generated floors

Date: 2026-10-04

## Status

Proposed. Becomes Accepted when slice E5 (`vefr stamp check` and placement in both languages) merges. Plan: `docs/plans/endless-dungeon/PLAN.md` sections 2 and 5. Rylee's call: the generator places painted rooms "anchored, rotated or not, with doors that must connect".

## Context

Delve v3 carves only from the `layout` stream (`delve_v3.py`). The plan sketches a stamp JSON (DCSS vaults without Lua) but leaves open what a legal socket is, how corridors reach it, what happens when a stamp does not fit, how the twin stays equal, and what the author is told.

## Decision

**File layout.** One stamp per file at `stamps/<id>.json`; the name equals `id` (`[a-z0-9-]+`); stamps load in sorted `id` order. Every stamp a Section can use is in that Section's content hash, so editing one regenerates visited floors.

```json
{"stamp":1,"id":"wine-alcove","role":"landmark","tags":["cellar"],"depth":[1,9],"weight":2,
 "max_per_floor":1,"rotate":true,"mirror":true,
 "rows":["##+##","#...#","+.A.#","#...#","#####"],
 "legend":{"A":{"anchor":"chest"}},"poi":"the wine alcove"}
```

**Closed keys.** The twelve shown. Required: `stamp` (must be `1`; reader `read_v1`), `id`, `role`, `rows`. Defaults: `tags []`, `depth [1,99]`, `weight 1`, `max_per_floor 1`, `rotate false`, `mirror false`. A legend entry has only `anchor`.

- `depth` is `k`, the floor's 1-based position in its Section (`locate()`), so stamps keep appearing in endless cycles.
- A stamp is eligible when its `tags` overlap the Section's `stamps`, `k` is inside `depth`, and its role is wanted on the floor.

**Glyphs (closed).**

| Glyph | Meaning |
|---|---|
| `#` | wall |
| `.` | floor |
| `+` | door socket |
| `?` | secret socket |
| space | outside the stamp; the generator decides |
| `A`–`Z` | named anchor, standing on floor |

Lowercase letters are reserved, because `u` and `d` are stairs. Any other character is rejected.

**Shape rules.**

- `rows` is a rectangle of at most 21x21. (This line was written at
  15x15; the owner's decision 1 below, "go bigger, 21x21" for the
  throne-room redraw, is the cap. `stamps.MAX_SIDE` and
  `tests/test_stamps_format.py` are the two places that hold it.)
- The floor, anchor and socket tiles form one 4-connected component.
- No space tile touches a floor or anchor tile orthogonally.
- A socket has exactly one orthogonal neighbour that is floor or anchor. The tile opposite that neighbour must lie outside the rectangle or be a space; that tile is the socket's **mouth**.
- Each legend letter appears exactly once in `rows`, and every letter in `rows` is in the legend.

**Anchors.** `up`, `down`, `warden`, `chest`, `note`, `home`, `poi`, `spawn`. Anchors are named by glyph, so rotating a stamp never loses one.

**Roles.**

| Role | Sockets | Required anchors |
|---|---|---|
| `landmark` | at least one `+` | a `poi` anchor or a stamp `poi` |
| `warden-hall` | at least one `+` | exactly one `warden` |
| `vault` | exactly one `+`, no `?` | `chest`, `note` and `home` (ADR 0015) |
| `secret` | no `+`, at least one `?` | no `warden` |
| `special`, `filler` | at least one `+` | none |

**Orientation.** An orientation is `o` in `0..7`.

1. If `o >= 4`, mirror first: `x' = w-1-x`.
2. Then turn clockwise `o % 4` times. One turn maps `(x,y)` in a `w x h` grid to `(h-1-y, x)` in an `h x w` grid.

The allowed orientations are `[0]`, plus `1..3` if `rotate` is set, plus `4` if only `mirror` is set or `4..7` if both are set. The draw is `allowed[floor(rng()*len)]`.

**Placement.** This happens in the layout stream, the same way in both languages.

1. **Order.** Place the warden-hall, then the vault, then the landmark. Then place `special`, `secret` and `filler` stamps up to the plan quotas. Pick within a role by weight, walking ids in sorted order. A stamp that reaches `max_per_floor` drops out.
2. **Attempts.** A stamp gets up to 24 attempts. Each attempt draws an orientation, then `x`, then `y`, and is accepted if it passes `_fits` (pad 1) **and** its whole rectangle is clear of carved tiles - a stamp never lands on a corridor, because overwriting one would strand whatever it served. A stamp too big for the floor at any orientation spends no attempt and gives its slot up at once. An accepted stamp becomes a room whose `shape` is its role, and its non-space tiles are **locked**.
3. **Connection.** Corridors start only at socket mouths and never carve locked tiles.
   - Sockets are tried nearest mouth first. Ties go to the socket that comes first in row-major order.
   - The corridor's far end is the nearest carved tile from that mouth, and then the next few nearest ones in the same order, until a bend lands: the ADR named where a corridor starts and not where it ends, and a room the stamp has not been placed next to yet is the only thing there is to end on. Four ends are tried, in a fixed order, with no draw.
   - For each end, try both of `_link`'s L-bends in order. The first route that crosses no locked tile, no other carved tile and no wall of the stamp itself wins.
   - A used `+` becomes floor, and a used `?` becomes a FloorPlan `secrets` entry. An unused socket becomes wall. A mouth that falls inside the room's own rectangle is the room's tile, not the corridor's, so the grid still reads as rooms plus corridors.
4. **Pinned try.** When a required stamp fails, the floor retries with `|try{n}`.
   - On the last try (`n = MAX_TRIES`), required stamps are pinned before any other room. The warden-hall goes at the far end of the spine, and the vault goes in the corner farthest from `up`. Each uses the first allowed orientation whose mouth faces the floor's centre. The landmark has no named position here and keeps its 24 attempts, because inventing one would be a rule the twin does not have.
   - A failure even then falls back to v2, and `vefr check` reports it as a defect: the v2 floor carries `stamp_defect: "stamp:<role>"`, and that is what the check reads.

**Validation.** `vefr stamp check --pack PACK [--seeds 200]` runs four kinds of check.

- **Static:** every rule above.
- **Fit:** a required-role stamp is at most one third of the smallest width and height of every Section that uses it.
- **Sweep:** run seeds `check-0..199` over every eligible Section and `k`. Each stamp must be placed on at least 95% of the floors where it is eligible, and required stamps on 100%.
- **Graph:** each placed stamp has at least one used socket. Every anchor is reachable from `up`. Secret sockets count as passable, except on the route to `warden` or to the vault door.

**Failure in plain words.** One sentence per problem: the stamp, what is wrong, the fix, a JSON pointer. Exit 1. For example:

- `stamp wine-alcove: no door socket (+) on its edge, so nothing can reach it; put a + in the outer wall. /rows`
- `stamp crypt-hall: placed on 171 of 200 cellar floors (85%); it needs 95%. It is 15 wide and cellar floors start at 64. /rows`

**Parity.** Parsing, the transform, eligibility, weighting and placement are twinned. The layout stage's numbered draw-order comment lists each attempt's draws: role pick, orientation, `x`, `y`. Rendering is not twinned.

## Consequences

- Hand-drawn rooms and vaults become data, with no code per room.
- The transform and placer are written twice, about 150 lines each.
- Pinned-try floors look more regular; acceptable below 0.5% of floors.
- No glyph can point a direction, because glyphs never rotate.

## Acceptance

- `tests/test_stamps_format.py`: every static rejection has a golden sentence, including "no connectable socket".
- `tests/test_stamps_orient.py`: all 8 orientations of every fixture stamp match the goldens, and anchors keep their letters.
- `tests/test_floor_v3_properties.py`, extended over 200 seeds x sizes x kinds: placement rates (95%, required 100%), unused sockets are walls, anchors reachable.
- `tests/test_floor_v3_parity.py`, extended: per-stage layout parity holds with stamps in all 8 orientations.
- `tests/test_cli_stamp_check.py`: the exit codes and both example sentences.

## Open questions for Rylee

1. **Decided: go bigger, 21x21** for the throne-room redraw. The stamp size cap and the placement cost budget must allow 21x21; confirm in the E5 tests.
2. **Decided: the throne room plus 5 hand-drawn rooms (six stamps to start).** **Only decorative stamps may rotate or mirror; story rooms never do.** **The five (owner, 2026-10-04): a random elite monster room; a room of 3 to 6 random chests where one is quite likely a monster in disguise; a shrine or small chapel; a treasure nook; and a sleeping den for a linked monster group.** The first two are generated variants that use the stamp mechanism with random contents.
3. May a landmark stamp leave out its point of interest and take a name from the Section list instead?
4. **Decided: required stamps always place; optional stamps may be rare on purpose.** The 95% bar applies to required stamps only.
