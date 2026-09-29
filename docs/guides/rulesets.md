# Rulesets — how an act declares the game it plays

The engine is a host; an act's `ruleset` says which game happens inside
it. Rulesets are **pack data plus a screen in the player**; the engine
supplies the shared core (journal, vault, canon, prompts, weave) and
never gates the player on numbers unless the act's `floor` says so.

## The per-act law fields

| Field | Values | Meaning |
|---|---|---|
| `ruleset` | `ambient` (default) · `cooking` · `desk` · future | which screen + loop the act plays |
| `floor` | `costume` (default) · `story` · `stakes` | how hard numbers bite. `costume` = the classic vefr way: HP tracks, the player never drops to zero, the bar is a costume. `story`/`stakes` get their mechanics from future rulesets; until then they validate and wait |
| `tone` | `literal` · `warm` · `deadpan` · `ridiculous` · `absurd` | the act's position on the ridiculous-literal dial; rides in every generation prompt for the act |
| `verbs` | list of strings | the act's own action vocabulary; when declared it replaces the engine's costume verbs in the HUD and the `/api/combat/action` whitelist |
| `transitions` | list of doors | the act's doors between `regions` (below) |
| `cooking` | object | the cooking loop's content (below) |
| `desk` | object | the desk loop's content (below) |

All optional. Absent means the engine's defaults, so every existing pack
loads unchanged. `maplab.validate` shape-checks whatever is declared
(orders must reference real pantry ids; headlines must be at least two
non-empty strings; verbs/enemies/bosses must be lists of strings;
`transitions` is a list of doors and is checked against the regions'
maps - see below).

## cooking (Act 1's loop)

```json
"cooking": {
  "opening": "Day one after the quiet. The grill remembers heat.",
  "byline": "by the morning truck",
  "pantry": [{"id": "egg", "label": "fried egg"}],
  "tickets": [{
    "id": "t1", "customer": "the regular", "order": ["egg", "salsa"],
    "note": "The usual. Egg, and the red one that bites.",
    "thanks": "The regular eats standing up, already turning toward the day.",
    "kind_line": "The regular eats it anyway, nodding at something only they can see."
  }],
  "morning_length": 3,
  "headlines": ["FIRST TRUCK ON THE ROAD SERVES BREAKFAST AGAIN"]
}
```

The loop: tickets arrive as **spoken notes** (reading them is the game —
the order ids stay hidden); the player wraps from the pantry and serves;
resolution is deterministic set equality; a wrong order gets its
`kind_line` (a kind beat, never a slap); after `morning_length` tickets
the player picks a headline and page 1 of the paper prints (masthead,
headline, `byline`, an honest body from the journal, the pack creed,
"more mornings soon"). `sleep · wake again` resets the rail for volume 2.

## desk (Act 2's loop)

```json
"desk": {
  "opening": "The desk opens after the quiet.",
  "headlines": ["FIRST LIGHT OVER THE EMPTY MARKET",
                 "TRAVELERS REPORT SONG AT THE FLOODED CROSSING"]
}
```

The loop: whispers arrive carrying a hidden truth (the engine owns
truth; the model only proposes the whisper). The player judges each
whisper — trust it / doubt it — and the engine compares the verdict
against what it actually sent (`src/vefr/desk.py`, deterministic, no
model calls). Correct verdicts and printed headlines become **world
knowledge**, derived from the session journal on every read, and ride
into every later rumor and NPC line as `WHAT THE WORLD KNOWS NOW`.
Wrong verdicts are journal entries, never failure states. Live app
routes: `POST /api/desk/verify`, `POST /api/desk/print`,
`GET /api/desk/facts`; the single-file player runs the same loop
client-side against the baked pool's truth.

## library (books a world keeps)

Not an act loop: a pack-level shelf every ruleset can use. A pack may
carry `library/*.md`, one authored book per file:

```markdown
---
title: A Miner's Note
found: map        # shelf (default) | map | resident | earned
at: [7, 4]        # map: the tile it lies on (walkable, in the town)
speaker: keeper   # resident: the act voice that hands it over
when: bell        # earned: bell | first-visit | act-complete | rumor-verified | book:<id>
kind: note        # book (default) | note | terminal
---
The first page.

* * *

The second page.
```

A line holding only `* * *` starts a new page. The author writes every
word; no model call touches a book. `maplab.validate` (and so `norns
validate`) checks every book: a title, non-empty pages, a known `found`,
a walkable `at` for map books, a real speaker for given books, a known
`when` (or an existing `book:<id>`) for earned books, lowercase-dash
file names. The loader carries them as `world["library"]`;
`GET /api/library` serves the current world's books plus the studio's
own shelf (`web/library/`, the game-making handbook); the workshop's
Library room reads them a page at a time (`web/js/library.js`); the book
export adds a "The Library" chapter. Finding books in play has landed in
the woven player: a map book is picked up on its tile, a resident hands
one over when you talk, and earned books unlock on `first-visit` or after
reading the `book:<id>` they name (`bell`, `act-complete` and
`rumor-verified` wait for events the player can see). The pause menu's
Books panel reopens anything found. Code: `src/vefr/library.py` +
`src/vefr/cli.py` (bake) + `web/packaged.html` (reader); tests:
`tests/test_library.py` + `tests/test_builder_weave.py` +
`tests/fixtures/make_library_pack.py`.

## delve (generated floors)

Not an act loop yet: a build-time tool that generates dungeon floors the
engine owns. `norns delve` draws a floor from a seed - rules only, no
model call, deterministic - and writes it as a region of the act, wiring
the stairs as transitions.

A region - generated or authored - may also carry `fog` in its
`contract.json`: `true`, or `{"radius": N}`, draws it dark until explored
(a lit circle around the hero, walked ground remembered dimmed, the rest
black). The Cottage floors use `{"radius": 4}`; a town omits it.

```sh
uv run norns delve --pack worlds/<name> --seed <text> --floors N \
    --from-region town --from-at 4,5 \
    [--width W] [--height H] [--rooms R] \
    [--first-name floor-2] [--force]
```

`--from-region` is an existing region and `--from-at x,y` is the
walkable tile there that the author placed as the down-stair; the command
refuses (non-zero) if that tile is not walkable. Each generated floor is
a directory (`acts/<id>/floor-2/`, `floor-3/`, ...) carrying a `map.md`
and a `contract.json`. Numbering continues after the pack's existing
`floor-*` regions unless `--first-name` names the start. The last floor
generated is the bottom for now and keeps no down-stair; the output says
so. An existing generated region is refused unless `--force`; nothing
outside the pack is ever written.

The stairs wire as doors: the `from-region`'s stair goes down to the
first floor's `u`; each floor's `d` goes to the next floor's `u`; every
floor's `u` climbs back to the previous floor's `d` (or to
`from-region`/`from-at` for the first). The act's `regions` gains the new
names at the end - the first region stays first - and `start` and the
existing regions are untouched.

A generated map uses one shared legend (`src/vefr/delve.py`):

| char | meaning | tile |
|---|---|---|
| `#` | solid wall | `dungeon-wall` |
| `.` | floor | `dungeon-floor` |
| `u` | up-stair | `dungeon-stairs-up` |
| `d` | down-stair | `dungeon-stairs-down` |

`generate_floor(seed, width=30, height=20, rooms=8)` draws rectangular
rooms joined by L-corridors, keeps a solid border, and guarantees one
connected cave with the two stairs reachable from each other and far
apart (at least `MIN_STAIR_DISTANCE` Manhattan tiles when the layout
allows; it relaxes to the widest pair otherwise). `delve.contract(...)`
writes the region `contract.json`.

Known limits (this slice): floors are generated once, at build time,
from a seed and then baked into the pack - per-playthrough generation is
a later slice. Only the first region's full geometry is validated today;
the generated floors are checked by the door rules (see
"regions + transitions" below). Code: `src/vefr/delve.py` +
`src/vefr/cli.py` (`cmd_delve`); tests: `tests/test_delve.py`.

## regions + transitions (doors between maps)

An act may declare several `regions`, each its own directory under
`acts/<id>/`: a `map.md`, a `contract.json` (legend, pois, poi_text,
hero_start, sanctuary_tiles, watch, water_by_phase, flood_tiles, tile,
bg and the colours), and `voices/` + `sprites/`. The first region is
the act's home map.

A `transition` is a door from one region to another - an **entry
room** inside a building, or a floor below:

```json
"transitions": [
  {"from": "town", "at": [4, 5], "to": "cottage", "to_at": [4, 3]}
]
```

`at` is the tile you step on in `from`; `to_at` is where the hero
lands in `to`. A door is stepped on, not stood on: the step enters the
other region instead of placing the hero on the door tile. A speaker
may carry `"region": "<region name>"`; a speaker with no `region`
belongs to the act's first region. Each loaded region carries its own
`speakers` dict (the act's speakers filtered to that region); the
act's `speakers` keeps all of them.

The woven player honours both: `weave_html` bakes `window.VEFR_REGIONS`
(one entry per region, from its `map_text` + contract),
`window.VEFR_TRANSITIONS` (the act's doors, verbatim), and
`window.VEFR_SPEAKERS` (the act's speakers grouped by region), and
`web/packaged.html` reassigns the current map, people and hero when a
door is crossed. A single-region pack with no transitions bakes one
region and behaves exactly as before. `maplab.validate` checks every
door: `from`/`to` name declared regions, and `at`/`to_at` are inside
their maps and walkable in their legends.

Known gap (this slice): only the **first** region's full geometry is
validated today (rectangular map, reachable tiles, pois, sanctuary,
water). Other regions' maps are read only for the door checks; their
own geometry validation is a follow-on.

## combat (first slice: bump to fight)

The dungeon has floors, fog, doors and stairs; this is the first thing
in them that moves on its own. Combat is **deterministic** - fixed
numbers, no randomness, no clock, no model calls - and **Cozy**: going
down never ends a story.

A pack's `world.json` may give the hero its own numbers and a wake
point:

```json
"player": {"hp": 6, "atk": 2,
           "wake": {"region": "town", "at": [11, 11]}}
```

`hp`/`atk` default to 6/2. `wake` is where Cozy death wakes the hero;
it defaults to the act's first region at its `hero_start`. A `wake`
that names no real region is dropped, and one on a missing or solid
tile falls back to that region's `hero_start` - the baked point is
always real.

A region's `contract.json` may carry `enemies`, one named hazard each:

```json
"enemies": [{"id": "cellar-rat", "name": "a cellar rat",
             "at": [12, 9], "hp": 4, "atk": 1, "sprite": "rat"}]
```

`id` is unique within the region; `at` is a walkable tile; `hp`/`atk`
are positive ints; `sprite` is optional and names an entry in the
pack's `player.sprites` (the same map the hero and speakers use). No
`sprite` draws the same body-and-head figure a speaker gets, in a
hostile colour. `sight` is optional (default 6) and is Manhattan
distance.

**The turn.** Every *successful* move (a step, or a bump attack) is
followed by one turn for each living enemy of the region:

- adjacent (Manhattan distance 1) -> it attacks: hero hp drops by its
  `atk`, clamped at zero.
- else within `sight` -> it steps one tile toward the hero (the larger
  axis first, the other axis if that tile is blocked; never onto a
  solid tile, another enemy, or the hero - a step that would land on
  the hero attacks instead).
- else it holds still.

**Bump to attack.** Walking into a living enemy does not move the
hero; the hero strikes it instead for `hero.atk`. A killed enemy is
remembered per region, per world (`vefr-slain-<world>-<region>` in the
player's storage), so a cleared room stays cleared; a wounded one
resets when the page reloads.

**Cozy death.** At zero hp the hero is restored to `hp`, one plain
line is shown ("You wake in the temple. You lost nothing that
mattered."), and the hero wakes at `wake`. Nothing is lost.

The HUD's health line shows the hero's real `hp/max`; a small
`aria-live` line speaks each hit. Baked per region (`VEFR_ENEMIES`)
and once for the hero (`VEFR_HERO`).

Known gaps (this slice): no fleeing, no
rooms-and-corridors AI (enemies only step and hit), no randomness, and
only a move is a turn - a hero can stand still safely. Classic death
is a later slice. Loot - what a kill leaves and a bag holds - is the
next slice (see "loot" below).

`maplab.validate` checks the region `enemies` shape: a unique id, a
name, a walkable `at`, and positive int `hp`/`atk`; a broken one is
named in plain words. Code: `src/vefr/maplab.py` (validation) +
`src/vefr/cli.py` (bake) + `web/packaged.html` (the turn); tests:
`tests/test_combat_loop.py` + `tests/test_transitions.py` +
`tests/test_builder_weave.py` + `tests/fixtures/make_combat_pack.py`.

## loot (first slice: drops and a simple bag)

Killing something used to give survival and nothing else. Now a kill can
leave a thing behind, the hero can carry it, and a Bag panel shows what
is held. It is deliberately small: no weight, no grids, no identifying,
and no using or selling. Deterministic like the rest - fixed ids, no
randomness, no model call.

A pack's `world.json` may carry an `items` catalog (optional), keyed by
id:

```json
"items": {
  "cloudy-potion": {"name": "a cloudy potion", "sprite": "potion"},
  "brass-ring":    {"name": "a plain brass ring", "sprite": "ring"}
}
```

`name` is plain words, shown in the bag. `sprite` names an entry in the
pack's `player.sprites` (the same map the hero and speakers use) and is
optional; with none the marker falls back to a small neutral dot. An
entry with no name is dropped from what is baked, and a drop naming a
missing item is dropped too - the player never meets a thing the world
cannot describe.

A region's enemy may carry `drops`, a list of catalog ids:

```json
{"id": "cellar-rat", "name": "a cellar rat", "at": [2, 1],
 "hp": 4, "atk": 1, "sprite": "rat", "drops": ["cloudy-potion"]}
```

A chest book (`chest: yes` in its front matter) may also hold items:
`drops: cloudy-potion, brass-ring` - a comma-separated list of catalog
ids, read from `extra` like `chest` already is.

**The drop.** A killed enemy's drops are left on the tile it died on, as
a small item marker (the item's sprite, or a dot). Fog rules apply: a
drop is drawn only where the light reaches. **Walking onto a drop takes
it**: it leaves the floor, one plain line says so ("You pick up a cloudy
potion."), and a small sprite appears in the HUD where the health bar is.
The floor is remembered per world (`vefr-floor-<world>`), so leaving and
coming back is honest about what is still lying there. **The bag** is a
list of item ids at `localStorage['vefr-bag-<world>']`; a duplicate id is
still added - two potions are two potions. The pause menu's Bag panel
(next to Journal and Books) lists what is carried, one row per thing,
sprite and name; empty it says "Nothing yet.". Opening a chest still
gives its note, and also gives any items its `drops` names, with one
line.

Baked as `VEFR_ITEMS` (the catalog), a `drops` list on each enemy and
each book. Code: `src/vefr/cli.py` (`_player_items`, `_drop_ids`) +
`web/packaged.html` (floor, take, bag panel, HUD strip); tests:
`tests/test_builder_weave.py` + `tests/test_combat_loop.py` +
`tests/fixtures/combat_harness.mjs` + `tests/fixtures/make_combat_pack.py`.

Known gaps (this slice): no weight, no using, no dropping, no selling,
and no identifying - a carried thing is only a name and a picture for
now. `maplab.validate` does not yet pin the `items`/`drops` shape; the
bake drops an unknown id instead. The bag has no size limit.

## reward (first slice: gold, trade, and using a thing)

The loot slice left a thing carried but did nothing with it. This slice
adds the reward end: a purse of gold, a shopkeeper who buys and sells,
and using a carried thing. It is still deliberately small - no haggling,
no stock limits, no equipping, no weight - and still deterministic:
prices and heals are fixed pack numbers, no randomness, no model call,
no clock.

Three optional additions to the pack shape, all additive:

An item may carry `value` (a positive int: what a shop pays and asks),
`heal` (a positive int), and `use` (a verb such as `drink`):

```json
"items": {
  "cloudy-potion": {"name": "a cloudy potion", "sprite": "potion",
                    "value": 8, "heal": 3, "use": "drink"},
  "brass-ring":    {"name": "a plain brass ring", "sprite": "ring",
                    "value": 3}
}
```

A speaker may carry `"shop": "true"` (also `yes` or `1`). At most one
shopkeeper per region; the first one named wins. A speaker with no
`shop` is exactly the speaker it always was:

```json
"speakers": {
  "merchant": {"name": "a dusty merchant", "at": [2, 2],
               "near": "the stall", "shop": "true",
               "seeds": {"dusk": "...", "dawn": "..."}}
}
```

And `world.player` may carry `gold`, the starting purse (a non-negative
int, default 0):

```json
"player": {"hp": 3, "atk": 2, "gold": 5, "wake": {"region": "town", "at": [1, 1]}}
```

None of the three is required. A pack that names none of them bakes
exactly the player it had before, and its HUD does not move: the gold
line appears only when the world trades at all (a shopkeeper exists, or
some catalog item has a `value`).

**The purse.** Gold is one number at `localStorage['vefr-gold-<world>']`,
seeded from the baked `VEFR_HERO.gold`. It shows as a short line in the
top-left HUD ("5 gold") and as plain words in the Bag panel ("You carry
5 gold.").

**The trade.** A shopkeeper's Trade panel opens when the hero stands
within one tile of them (the same reach as a bump) and presses Interact
(or `F`), the same verb that opens a door or a chest. Sell lists each
carried thing with a `value` and its price, with a Sell button; Buy lists
every catalog entry with a `value` and its price, with a Buy button. A
Buy the purse cannot afford is disabled. Each trade updates both lists,
the purse, and an `aria-live` line ("You sell a cloudy potion for 8
gold."). The panel is a dialog: 44px targets, close with the Close button
or `Escape`, and focus returns to the Interact button. Talking (Talk /
`E`) still gives the shopkeeper's own line; trading is a separate verb.

**Using a thing.** The Bag panel gives a Use button to any carried thing
the pack gave a `heal`. Using it raises health by `heal`, never above the
max, spends one copy, and says so ("You drink a cloudy potion. You
recover 2 health."). At full health it says "You are already whole." and
keeps the thing - a potion is never spent on nothing.

Baked as `VEFR_HERO.gold`, `VEFR_SHOPS` (a `{region: speaker key}` map),
and the extra `value`/`heal`/`use` fields on each `VEFR_ITEMS` entry.
Code: `src/vefr/cli.py` (`_player_items`, the hero block, the shops map)
+ `web/packaged.html` (gold, bag, use, trade); tests:
`tests/test_builder_weave.py` + `tests/test_combat_loop.py` +
`tests/fixtures/combat_harness.mjs` + `tests/fixtures/make_combat_pack.py`.

Known gaps (this slice): no haggling or variable prices, no stock or
shop inventories beyond the catalog, no equipping or effects other than
healing, no dropping or giving, no currency other than gold, and selling
always pays exactly `value`. `maplab.validate` does not yet pin the
reward fields; the bake ignores a `value`/`heal` that is not a positive
int and a `use` that is blank.

## Adding a ruleset (the checklist later acts follow)

1. Loader passthrough in `src/vefr/world.py` (acts + flat shapes).
2. `maplab.validate` pins for the block's shape.
3. A screen branch in `startPlaySurface()` in `web/packaged.html`
   (and, when the live app needs it, routes in `src/vefr/main.py` —
   AGENTS.md lists new public routes as ask-first).
4. A neutral fixture builder in `tests/fixtures/make_<name>_pack.py`
   (engine-test canon only; real canon lives in pack repos).
5. A harness in `tests/fixtures/<name>_harness.mjs` (jsdom, dev-only)
   that PLAYS the loop, plus a `tests/test_<name>_loop.py` pinning
   journal order, feedback lines, and the click budget — the
   pleasant-loop protocol (VEFR-ACT1-SPEC §9): two playtest passes per
   increment, nine-point checklist, dud kill-switch.
6. ROADMAP entry with pasted gates; dev-guards green; merge without
   `--admin`.

## What a ruleset must never do

- Call a model from a deterministic surface (`export.py`, `weave.py`,
  `maplab.py`, `journal.py`, `desk.py` — the export law).
- Introduce timers or pressure (the truck-arrives law).
- Punish: failure bends the story or waits; it never ends it.
- Name private canon in engine code or fixtures (the neutrality guard
  reads engine surfaces on every CI run).
