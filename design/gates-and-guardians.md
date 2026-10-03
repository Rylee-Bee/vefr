# Gates and guardians: a key worth fighting for

Status: **build step 1 (locked transitions) is built** (Rylee, 2026-10-02: "is it more rewarding to have one tougher mob with the key that you have to find? I do want the levels and mobs to be generated"). The validator, the player and the docs landed; `tests/test_locked_stairs.py` passes. Steps 2-4 (guardians, depth tables, the Cottage stair) stay proposed and wait for a build.

## The word for it

Making a player earn power before going deeper is **progression gating**. A *soft gate* is a power curve: nothing blocks you, but the monsters are tuned so you cannot win without the level and gear (a "gear check"). A *hard gate* is lock and key. Walking around a gate is *sequence breaking*. A **key guardian** is a tougher monster that carries the key: it is a gear check and a lock in one.

## What exists today (checked 2026-10-02)

- Enemies can carry `drops` (items), and an item can be a kept tool (`keep: true`). So "a monster that drops a key you keep" works now.
- Rules can notice the kill (`defeats`) and the pick-up (`picks-up`), set a flag and say a line.
- **A stair or door cannot be locked.** A transition is always usable. This is the one missing piece.
- `bosses` in the act contract is reserved and inert. A guardian is just an enemy with big numbers for now.
- Cozy surface ("costume") means the hero cannot lose, so gear does not matter yet. Stakes are a later switch (`design/growth.md`, `docs/GAME-PLAN.md` step 4).
- `norns delve` generates floors at author time from a fixed seed; per-run generation is `design/random-floors.md` (proposed).

## The design

**1. A lock on a transition (neutral engine feature).** A transition may carry `requires`: `{"item": "<id>"}` or `{"flag": "<name>"}`, plus `locked_text`, one plain sentence shown when the hero tries it without ("The stair is shut. Something below keeps the key."). Interact on the stair with the item (or the flag set) opens it; with `keep: true` the key stays in the bag. Absent means today's behaviour, so every pack loads unchanged. The validator names a `requires` that points at an unknown item or flag.

**2. A ladder of guardians, one per floor, and a king at the bottom (Rylee, 2026-10-02: "act 1 is the cellar, the main boss of the cellar is the cellar king, and we can have 5-6 levels that are randomly generated, each with a ... [duke] to progress").** Act 1 is the cellar: five or six generated floors. Every floor has one guardian, a tougher mob that carries the key to the stair down. The last floor's guardian is the Cellar King, the act's boss; beating him ends act 1. The pack declares them as a ladder:

```json
"guardians": [
  {"floor": 1, "enemy": "first-guardian", "carries": "key-1"},
  {"floor": 2, "enemy": "second-guardian", "carries": "key-2"},
  {"floor": "last", "enemy": "cellar-king", "boss": true, "carries": "the-cellar-seal"}
]
```

Each guardian is stronger than the last, tuned to the power curve of the levels. The generator places each one in the room farthest from that floor's arrival stair with its key in `drops`. Like the ending room, it is placed by the generator and never left to chance, so every seed can be finished. The `requires` lock from section 1 is on each floor's stair down. The names and looks of the guardians are Rylee's to choose; a rank scheme from a king's court (seneschal, chamberlain, marshal, warden, bailiff) is one option.

**3. Mobs come from tables, scaled by depth.** Each table row gets `depth` bands and a weight; `hp`/`atk` scale by floor; `xp` follows `design/growth.md`. The guardian is a row with `guardian: true`, never rolled as filler.

**4. Cozy-safe.** On the `costume` surface the guardian simply takes a while; on `story`/`stakes` it can send the hero back to the temple. Either way the key is only taken by winning.

## Slice 1 contract: locked transitions (set 2026-10-02, tests in `tests/test_locked_stairs.py`)

This is build step 1 only; guardians, depth tables and the Cottage placement stay open below. Decisions made while writing the tests (Rylee: veto any of them):

- `requires` is an object with **exactly one** key: `{"item": "<item id>"}` or `{"flag": "<declared flag>"}`. An unknown item id or undeclared flag is a validator error naming it; any other shape is one plain sentence naming `requires`. No level-based lock yet.
- `locked_text` is **optional**, one plain sentence of 1 to 200 characters. When absent the line is "It will not open yet."
- A locked door or stair, used with Interact, says the line in the narrator line (the combat log) and the hero stays put. With the item in the bag (or the flag set) it opens exactly as before.
- **Keys are never consumed in this slice**, whether or not the item has `keep: true`. A consumed key would need a remembered "opened" state, which the design does not yet specify.
- A flag lock only survives a reload when the pack uses `saves.rules: persist` (ADR 0009); otherwise the rule that sets the flag runs again on the next load, as before.
- A transition without `requires` behaves exactly as before.

## What this does not do

No timed locks, no lockpicking, no key ring UI, one lock per floor in the first slice (the ladder), no second kind of key, no level-based lock (a `requires` on level can follow once growth lands).

## Checks the build must carry

1. Validator: `requires` shape and references; `locked_text` plain; guardian `carries` must be a declared item.
2. A woven-file play test: try the stair (shut, the line shown), defeat the guardian, take the key, the stair opens, the key stays.
3. Generator test: a guardian and its key exist on every seed in a fixed sweep; the stairs stay connected.
4. Compatibility: a pack with no `requires` and no `guardians` plays exactly as before.

## Build order

1. `requires` on transitions: validator, player, test. (Small; unlocks hand-authored gates today, e.g. Cottage's stair into floors 4 to 6.)
2. Cottage uses it: the floor 6 guardian carries the key; the stair down from floor 3 is the lock. Placed by hand first.
3. Guardians and depth tables in `random-floors`, when per-run generation is built.

## Open for Rylee

- ~~The guardians' creatures~~ **Decided (Rylee, 2026-10-02):** variants of the monsters we already have, with names based on their art and abilities. Still hers: approving the names.
- ~~Where the last room sits.~~ **Decided (Rylee, 2026-10-02):** "his seal opens like a treasure room with a lore note and a 'back to town' before you start the next set of dungeons". So the Cellar King's drop is a seal; using it on the last floor's sealed door opens a room with a treasure, a lore note, and a way back to town; act 2 starts after that. In the design: a guardian row may name `"opens": {"room": "king-room"}`, and the generator joins that authored room to the last floor on every seed (the "ending reachable on every seed" rule of `design/random-floors.md`). Still hers: what the treasure is and the lore note's words; nothing is canon until she writes or picks them.
- ~~Which stair is the first lock?~~ **Decided (Rylee, 2026-10-02):** the stair from floor 3 to floor 4.
- ~~Does the guardian's key look like a key?~~ **Decided (Rylee, 2026-10-02):** an actual key.
