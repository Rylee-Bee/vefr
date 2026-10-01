# Random floors: a new descent every run

Status: **proposed**. Asked for by Rylee on 2026-10-01 ("stuff the random dungeon floor generator idea into it"), for Cottage of the Breeze first. No code yet.
`docs/guides/rulesets.md` (the "delve" section) says it plainly: "per-playthrough generation is a later slice". This is that slice.

## What exists

`norns delve` draws a floor from a seed with `generate_floor(seed, width, height, rooms)` in `src/vefr/delve.py` (rectangular rooms, L-corridors, a solid border, one connected cave,
stairs far apart), writes it into the pack as a region and wires the stair doors. It runs once, at build time, and the floors are then baked into the game: every player gets the same cellar.
Its only randomness is Python's `random.Random(seed)`.

## The problem

A woven game is one static HTML file with no server. To give each run a new cellar the **player itself** must be able to draw a floor, and a browser cannot reproduce Python's random stream.
So there must be a second generator that Python and JavaScript both run, identically, from a small shared random function.

## The design

1. **A shared tiny PRNG.** One function, written twice (Python in `delve.py`, JavaScript in `web/packaged.html`): a string seed is hashed to a 32-bit number (xmur3), and numbers come from mulberry32. Integer maths only, so both sides agree exactly.
2. **`generate_floor_v2(seed, width, height, rooms)`**: the same shape as today's floors (rooms, L-corridors, border, connected, far stairs), written once in each language on the shared PRNG.
   **The old `generate_floor` is not touched**, so every floor baked by `norns delve` (Cottage's included) stays byte-identical and `norns delve` behaves exactly as today.
3. **Parity is proven, not hoped for.** A fixture of test vectors (about 50 seeds with several sizes, rows produced by the Python function and checked into `tests/fixtures/`) is replayed by a node harness that extracts the REAL JavaScript function from the page (the way `pickVariant` is tested). Any difference is a test failure.
4. **The pack declares what is generated.** A new optional block in `world.json`:

```json
"descent": {
  "from": {"region": "town", "at": [1, 1]},
  "floors": 3, "width": 40, "height": 28, "rooms": 9,
  "end": "last-room",
  "tables": {
    "enemies": [{"id": "rat", "sprite": "rat", "hp": 4, "atk": 1, "per_floor": [2, 3]}],
    "items":   [{"id": "cloudy-potion", "per_floor": [1, 2]}],
    "notes":   [{"book": "a-scrap-in-the-dust", "floor": 1}]
  }
}
```

   The authored rooms (the town, the tavern, the cottage, and the **last room**) stay authored and fixed. Only the cellar floors between them are generated.
5. **A run seed.** The first time a game is played a run seed is made and kept in `localStorage['vefr-run-<world>']`. Each floor is generated the first time it is entered, from `(run seed, floor number)`, and remembered. The seed is shown in the Journal (a short readable phrase, for example `amber-otter-41`) and can be typed in, so two people can walk the same cellar.
   A **New descent** button in the menu starts a fresh run (a new seed; floors, fog memory and floor loot are cleared; the bag and gold are kept, which is a choice for Rylee to confirm).
6. **What goes on a floor** is placed by seeded rules from the tables: enemies and items on reachable free floor tiles away from the stairs, and fixed notes on their stated floor. The generator **guarantees** that the stairs connect, that every placed thing is reachable, and that the last floor's down stair leads to the authored last room, so **the ending is reachable on every seed**.
7. **No seed, no change.** A pack with no `descent` block loads and plays exactly as it does today. Cottage keeps its baked floors as the default "authored tour"; whether the random descent is the default or an option beside it is for Rylee to choose.

## Checks

The validator checks the `descent` block's shape; that `from.at` is a walkable tile in `from.region`; that every id in the tables is a real enemy, item or book; that `end` names a real region; and that sizes and counts are within limits (width and height 20 to 64, rooms 3 to 16, floors 1 to 8).
A build-time **sweep** generates 200 seeds per size in Python and asserts every one is connected with reachable stairs and placements; the node harness replays the same seeds and asserts identical rows and placements.

## Risks and honest doubts

- **Fun is not guaranteed by correctness.** A floor can be connected and still be dull. Expect to tune room counts and table numbers by playing.
- **Maintaining two copies** of the generator (Python and JavaScript) is the price of one static file. The parity fixture is what keeps it honest.
- **Save compatibility:** a run in progress when a game is updated could meet a changed generator. The run stores its generator version; an older run keeps the older rules, or asks to start a new descent.
- **Hidden rooms and secret doors** want the rules surface (a door that appears when something happens); until then generated floors have none.

## Build order (one foreman at a time, after the rules work is merged because both touch `web/packaged.html`)

| # | Task | Tag |
| --- | --- | --- |
| 1 | Approve this note, and choose: random descent as default or as an option; keep the bag on a new descent | **keep** (Rylee) |
| 2 | The shared PRNG and `generate_floor_v2` in Python with the sweep test | offloadable |
| 3 | The JavaScript twin, the fixture of vectors, and the node parity harness | offloadable |
| 4 | The `descent` block: validator, bake, lazy floor generation in the player, run seed, Journal line, New descent | offloadable, then **keep** (review) |
| 5 | Table placement with reachability guarantees, and the last room joined on every seed | offloadable |
| 6 | A Cottage descent: tables, three generated floors, the authored last room (needs the story passes) | Claude and foreman |
