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
at: [7, 4]        # map: the tile it lies on (walkable), on a region drawn by hand
region: town      # map: the region it lies in (default town)
speaker: keeper   # resident: the act voice that hands it over
when: bell        # earned: bell | first-visit | act-complete | rumor-verified | book:<id>
kind: note        # book (default) | note | terminal
status: draft     # draft | approved (default: approved) - see Story status below
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

**Every map book names a region the pack has** (`vefr check` refuses one
that does not, with the regions it does have). A book can also lie on a
floor of the generated descent, named `<section>-<cycle>-<floor>`
(`cellar-0-3` is the third floor of the `cellar` Section, first cycle).
A generated floor is redrawn every run ("New descent") and whenever its
Section changes, so such a book names **where** on the floor to lie
instead of a tile:

```markdown
---
title: A Letter, Folded Small
found: map
region: cellar-0-1
place: near-up    # near-up | near-down (2 to 6 steps from that stair) | anywhere
chest: yes
---
```

The floor chooses the tile each run: reachable ground, off the stairs and
the monsters, one book per tile, from the floor's own `book|<id>` stream,
so a run always shows the book in the same place and a new run moves it
(`delve.place_books`, and `placeBooks` in the descent part, held equal by
`tests/test_pinned_books.py`). A fixed `at` on a generated floor is
refused, and `vefr check` proves every pinned book finds a tile in each
of 200 runs.

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

### delve --section (a whole Section)

`--section <id>` bakes a Section instead of N floors. Everything above it
still applies - the pack, the act, `--from-region`, `--from-at`,
`--seed`, `--force` - and the floors come out of the pack's
`sections/<id>.json` rather than out of `--width`/`--height`/`--rooms`:

```sh
uv run norns delve --pack worlds/<name> --seed <text> \
    --section cellar --from-region town --from-at 4,5
```

One region per floor, named `<section id>-<k>`, drawn by the v3 generator
(`src/vefr/delve_v3.py`) at the size and the floor kind the Section's own
pattern asks for. Each floor is drawn from the key
`run_seed/section.id/cycle/k`, which is what keeps two ordinary floors of
one Section from being the same map.

The wiring is the elevator rule. The `from-region`'s stair goes down
into floor 1; each floor's down-stair goes to the floor below; the last
floor is the bottom and keeps no down-stair. Every floor's up-stair
climbs back to the floor above it, except on a **landing** - a Section's
first floor and its fifth - where it goes straight back to `from-region`
instead.

Each written `contract.json` carries four keys a generated floor did not
have before, all additive: `section`, `k`, `floor_kind` and `landing`,
beside the `floor_key` the floor was drawn from. Otherwise it is the
shape `delve.contract` has always written.

A Section's own shape is checked by `vefr check` (`src/vefr/shapes.py`),
and every floor of every Section is swept over 200 seeds there too: one
component, and every anchor, point of interest, secret, monster and
chest reachable from the up-stair. Code: `src/vefr/sections.py`,
`src/vefr/locks.py` (`section_findings`), `src/vefr/cli.py`
(`_bake_section`); tests: `tests/test_sections_e4.py`.

A Section's `fog` is how far it sees: `{"radius": N}`, a whole number
from 2 to 32, and the lit area around the arrival tile is a disc `N`
tiles in radius. The ceiling is a quarter of the widest floor `size`
allows (`size.w` tops out at 128), so a Section says its sight as a
fraction of the floor it declares rather than against a fixed number -
read it at the table as `shapes.FOG_RADIUS_MAX`, which is `SIZE`'s
largest `w` over four. A Section that leaves `fog` out gets the engine's
default (5) and plays exactly as before; this range bounds what a pack
may ask for, and changes nothing a pack left out. The lit area is a
disc, which a floor of rooms is not: what else to draw, and whether
sight should grow with what the hero has seen, is #364's open question
rather than this table's.

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

`at` is the tile the door stands on in `from`; `to_at` is where the hero
lands in `to`. A door is **used, not walked through**: the hero stands
on or faces the door tile and presses Interact (the button says "Go
through the door"), and passing a doorway never yanks the hero to
another map. Interact is the one canonical interaction path - the
same verb that opens a chest or a trade. A speaker
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

### Locked doors

A door or stair may be locked behind a key. A transition may carry an
optional `requires` (a key item, or a flag) and an optional one-sentence
`locked_text`:

```json
"transitions": [
  {"from": "town", "at": [4, 5], "to": "cottage", "to_at": [4, 3],
   "requires": {"item": "brass-ring"},
   "locked_text": "The door is shut. The ring turns it."}
]
```

`requires` holds **exactly one** of `item` (an id in the pack's `items`
catalog) or `flag` (a declared flag name). Interact on the locked door
without it says `locked_text`, or "It will not open yet." when absent, and
the hero stays put - no `opens`, no arrival. With the item in the bag, or
the flag set, the door opens as it always did. **A key is never consumed:**
it stays in the bag whether or not the item is a kept thing.

A flag lock only survives a reload when the pack uses `saves.rules:
persist` (ADR 0009); otherwise the rule that sets the flag runs again on
the next load, as before. A transition with no `requires` behaves exactly
as today. `maplab.validate` names a `requires` that is not an object with
exactly one `item`/`flag`, points at an unknown item or flag, or carries
an unknown key, and a `locked_text` that is not one plain sentence of 1
to 200 characters (design/gates-and-guardians.md).

`vefr check` now follows the locks from the start region and names a
key that cannot be obtained before its door.

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
followed by one turn for each living enemy of the region. A monster
walks the floor, not a straight line: at the start of the turn the
walkable tiles are flooded once, breadth-first, from the hero (and, for
a monster that cannot see the hero, from the monster it is drifting
toward), and each monster steps to the neighbour closest to - or
furthest from - that flood. Walls, corners and rooms are therefore
walked round rather than into.

- adjacent (Manhattan distance 1) -> it attacks: hero hp drops by its
  `atk`, clamped at zero.
- else within `sight`, and hurt to a third of the `hp` it walked into
  the region with -> it steps one tile *away*: the neighbour furthest
  from the hero down the map.
- else within `sight` -> it steps one tile toward the hero, the short
  way round.
- else (out of sight) -> if another monster is alive it steps toward
  the nearest one, so a pack stays a pack; alone, it holds still.

A step never lands on a solid tile, another living monster, or the
hero - a step that would land on the hero attacks instead. Ties go to
a fixed neighbour order (up, down, left, right), so the same floor
always plays out the same way. There is no randomness and no clock
anywhere in the movement.

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
no stock limits, no equipping (equipment came later: see Equipment), no weight - and still deterministic:
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
shop inventories beyond the catalog, no equipping (added later: see Equipment) or effects other than
healing, no dropping or giving, no currency other than gold, and selling
always pays exactly `value`. `maplab.validate` does not yet pin the
reward fields; the bake ignores a `value`/`heal` that is not a positive
int and a `use` that is blank.

## light (first slice: a torch and a one-shot reveal)

Some regions are dark (their `contract.json` declares `fog`). A pack can
give a carried thing a `light` so the player can widen that circle or
lay the whole map open. It is additive: an item without a `light` bakes
exactly as before, and a pack with no `light` anywhere plays as it always
did. Still deterministic - fixed numbers, no randomness, no model call.

An item's `light` takes one of two forms:

```json
"items": {
  "torch":       {"name": "a pitch torch",
                  "light": {"radius": 2, "turns": 6}},
  "chalked-map": {"name": "a chalked map",
                  "light": {"reveal": true}}
}
```

`radius` (an int 1..20) widens the lit circle by that many tiles for
`turns` (an int 1..999) hero turns; when the turns run out the region's
own base radius returns and the light gutters out (announced once).
`reveal: true` marks every tile of the current region explored in a
single use. A `light` must name at least one form.

**Use.** A `light` item gets a Use control in the Bag panel, like a
`heal`. Using a torch from the Bag widens the light, spends one copy, and
says so ("The torch catches: 2 wider for 6 turns."); using a reveal map
spends one copy and says "The whole place is laid out.". In a region with
no dark (or after the player turns the dark off with `V` / Display) it
says "There is no dark here to light." and **keeps the thing**. While a
light burns, the top-left HUD shows a small "Turns of light: N"; the
counter is for glancing, and the news rides the ordinary announcements.
Entering another region ends the light (a fresh region is a fresh dark).

Baked as the extra `light` field on each `VEFR_ITEMS` entry (only a
usable form is baked). Code: `src/vefr/cli.py` (`_player_items`) +
`src/vefr/maplab.py` (`item_light_errors`) + `web/packaged.html` (the
Bag use, the HUD, the turn); tests: `tests/test_light.py`. The sample
world carries a torch and a chalked map in a chest for a live look.

Known gaps (this slice): one burning light at a time (a second torch
replaces the first), no light on the floor (drops are not lamps), and no
colour or animation - the lit circle simply grows.

## growth (levels or learning by doing)

Growth is optional and additive. **Both ways are off by default:** a pack
with no `growth` key plays as before. A pack that declares one picks a
single `mode` and carries only that mode's block.

In `levels` mode a defeated enemy gives experience, and enough experience
is a new level. `levels.xp` is a strictly rising list of whole numbers
that starts at 0, with at most 20 entries; entry N is the experience that
reaches level N+1, and the hero starts at level 1. `levels.gain` gives the
health and attack added by each level (whole numbers 0 to 9):

```json
"growth": {
  "mode": "levels",
  "levels": {"xp": [0, 10, 25, 50], "gain": {"hp": 2, "atk": 1}}
}
```

An enemy carries its own `xp` (a whole number of at least 0; absent means
0), and only in `levels` mode:

```json
{"id": "rat", "hp": 4, "atk": 1, "sprite": "rat", "xp": 3}
```

In `practice` mode there are no levels and no experience. Each stat grows
as the hero keeps doing a thing. `practice` names only `hp` and `atk`;
each carries `by` (one of `strikes`, `hits-taken`, `consoles`, `hurls`),
`every` (a whole number 1 to 99), `gain` (a whole number 0 to 9) and `cap`
(the most that stat can grow in total, at least 1):

```json
"growth": {
  "mode": "practice",
  "practice": {
    "atk": {"by": "strikes", "every": 12, "gain": 1, "cap": 4},
    "hp":  {"by": "hits-taken", "every": 8, "gain": 1, "cap": 6}
  }
}
```

A level-up (or a practice growth) of health also heals the hero by the
same amount, never above the new max. The extra health and attack are
derived from the saved state every time, never stored, so a re-woven game
cannot leave a stale level. `maplab.validate` checks the shape above and
names a bad field in plain words. The status line ("Level 2 · 14 of 25
experience") shows in `levels` mode only. All of it is deterministic: no
randomness, no model call, no clock.

Code: `src/vefr/maplab.py` (validation) + `src/vefr/cli.py` (bake) +
`web/packaged.html` (the engine and its seams); tests:
`tests/test_growth_validator.py` + `tests/test_growth_engine.py` +
`tests/test_growth_play.py` + `tests/fixtures/make_growth_pack.py`.

## equipment (the pack fields and the engine; the wearing is a later slice)

Equipment is optional and additive: a pack whose items carry no `slot`
plays exactly as it did, and a pack with no `items` is untouched. **This
slice is the pack fields and the pure engine.** Nothing wears anything
yet: the Bag panel, the buttons and the live line are the next slice.

An item may carry `slot`, exactly one of `hand`, `body`, `head`, `feet` or
`charm`, and `mods`, which is only allowed beside a slot:

```json
"items": {
  "green-cloak": {"name": "a green hooded cloak", "sprite": "cloak",
                  "slot": "body", "mods": {"hp": 2}},
  "short-bow":   {"name": "a short bow", "sprite": "bow",
                  "slot": "hand", "mods": {"atk": 1}},
  "brass-ring":  {"name": "a plain brass ring", "sprite": "ring",
                  "slot": "charm"},
  "cloudy-potion": {"name": "a cloudy potion", "heal": 3, "use": "drink"}
}
```

- `mods` holds only `atk` and `hp` (max health), each a whole number from
  0 to 9; a bool is refused. No `mods` means a keepsake that only looks
  nice.
- A slotted item may still carry `value` and `keep`, but not `heal`,
  `light` or `use`: a worn thing is not drunk or lit.
- An item named by a door's `requires.item` may not have a slot. A key
  stays in the bag so it can open its door more than once.
- An item with no `slot` cannot be worn (a potion, a key) and behaves
  exactly as before.

`maplab.validate` checks the shape above and names a bad field in plain
words, once per item. The bake carries `slot`, and `mods` beside it, only
when the shape is valid, so a broken one is a silent no-op rather than
something the player cannot wear. This slice is the **pack fields and the
bake** only (`design/equipment.md`, build step 1 of 5): the equip state,
the stat sums, the Bag's "You" section and the buttons come with their
own slices. Deterministic throughout: no randomness, no model call, no
clock.

The engine (`window.VEFR_EQUIP_ENGINE`, pure, in the woven player) answers
the numbers and moves the worn state: `statsFor(base, items, equipped)`,
`equip`, `unequip`, `clean`, `clampHealth`. Attack is base `atk` plus the
worn `mods.atk`; max health is base `hp` plus worn `mods.hp`; taking off
something that lowered the max clamps current health down to it, never
below 1. `equip` refuses an item with no slot, a slot it does not fit, an
id the catalog lacks, and an id already worn, so a duplicate is
impossible, and equipping into a full slot returns the old wearer so the
bag can take it back. Nothing is written into the caller's state, because
that object is what gets saved. Deterministic like the rest: no
randomness, no model call, no clock.

Code: `src/vefr/maplab.py` (`SLOTS`, `MOD_STATS`,
`item_slot_and_mods`, `item_slot_errors`, `_door_key_items`) +
`src/vefr/cli.py` (the `_player_items` bake) + `web/packaged.html`
(`VEFR_EQUIP_ENGINE`); tests: `tests/test_equipment_validator.py` +
`tests/test_equipment_engine.py` + `tests/fixtures/make_equip_pack.py` +
`tests/fixtures/equip_engine_harness.mjs`.

## Album (stickers a world keeps)

A `world.json` may carry `album`, an optional list of stickers
`{id, name, kind, when, riddle?, shine?}`. `id` is unique and `name` is
1–60 characters; `kind` is `open`, `riddle` or `secret`; `shine` is
`paper` (default), `foil` or `holo`. `when` is exactly one rules event,
the same vocabulary and identity model a rule uses. An `open` sticker
shows its name from the start, a `riddle` shows only its riddle until
earned, and a `secret` appears only in a count. Rewards only add.
Code: `src/vefr/maplab.py` (`album_errors`) + `src/vefr/cli.py`
(`_player_album`) + `web/packaged.html`; tests: `tests/test_album.py`.

## Sound

A `world.json` may carry `sound`, an optional object: `{"theme": "soft"}`.
No audio files: every cue is synthesized in the browser; `soft` is the only theme.
The nine cues are `hit`, `hurt`, `defeat`, `pickup`, `door`, `locked`, `level`, `sticker` and `end`.
Each fires at one moment of play, never on a timer, and the live line already says it in words.
Menu > Display > Sound turns them off for this browser, on by default; a pack with no `sound` has no switch.
Code: `src/vefr/maplab.py` (`sound_errors`) + `src/vefr/cli.py` + `web/packaged.html`; tests: `tests/test_sound.py`.

## Skins (a picture pack for the interface)

A skin is a folder of pictures that repaints the player's interface. It is
optional and additive: a pack that names none bakes exactly as before.

A pack's `world.json` may carry a `skin` field naming a folder inside the
pack:

```json
"skin": "skins/parchment-and-wood"
```

The folder holds one `skin.json` and its pictures. `skin.json` has a
`name`, a `credit`, a `parts` object and an optional `ink` object, plus
two more optional keys — a `backdrop` and a `fonts` pair:

```json
{
  "name": "parchment-and-wood",
  "credit": "Rylee and Claude",
  "parts": {
    "panel":  {"file": "panel.webp", "slice": 32},
    "button": {"file": "button.webp", "slice": 20, "hover": "button-hover.webp",
               "pressed": "button-pressed.webp", "disabled": "button-disabled.webp"},
    "bar":    {"frame": "bar-frame.webp", "fill": "bar-fill.webp"},
    "cursor": {"file": "cursor.webp", "hand": "cursor-hand.webp", "hotspot": [4, 4]}
  },
  "ink": {"on_panel": "#2B2118", "on_panel_dim": "#5A4A38"},
  "backdrop": "table.webp",
  "fonts": {"display": "Cinzel", "body": "Crimson Pro"}
}
```

The known parts are `panel`, `button`, `tab`, `toggle`, `bar`, `slot`,
`speech`, `tooltip`, `gold-plate`, `divider`, `banner`, `corner` and
`cursor`; each names its pictures under the keys that part uses.

**The backdrop** is one seamless picture for the ground the drawn map
does not cover inside the window — the table the game sits on. It is
painted on the map canvas, not with CSS, and only where the map does not
reach: a map that fills the window shows none of it. A skin without a
`backdrop` gets today's flat dark ground, exactly as before.

**The fonts** choose the type: `display` for titles and buttons, `body`
for reading. The names come from the families the engine bundles and
ships inside the woven file — `Cinzel`, `Atkinson Hyperlegible Next` and
`Crimson Pro` — so there is no download at play time. Any other name is
refused by the validator rather than left to fall back. Choosing a
typeface does not change any colour, so the ink rules below still decide
whether the words are readable.

**The validator's rules.** `maplab.validate` (and so `norns validate`)
reads the folder and refuses a bad skin with one plain sentence. The
folder must stay inside the pack. `skin.json` must be a JSON object with
a non-empty `name` and `credit`, and only known parts; an unknown part is
a typo to fix, not something the player quietly ignores. Every named
picture must exist, be a `.png` or `.webp`, and be under 300 KB. A
`slice` must be a whole number of at least 1 and at most half the smaller
side of its picture. `ink` colours must be `#RRGGBB`. A `backdrop` is
checked like any other picture, and `fonts` may only name a bundled
family for `display` or `body`.

**How it is drawn.** The loader inlines every picture as a data URI, so
the woven file stays one offline file. Panels and buttons use CSS
`border-image` with the slice width (a nine-slice), so one small picture
stretches to any size. Bars are a frame picture with a clipped fill
picture. The cursor is a CSS `cursor: url(...)` with a hotspot, and a
hand for things you can use. The backdrop is tiled on the map canvas
under the whole stylesheet, and the fonts are the player's own `--display`
and `--read` variables, so every rule already written reaches them.

**Safety.** Text is never inside a picture: every word is real HTML, and
pictures are only backgrounds, borders and icons. Focus is never removed.
Targets stay at least 44 px. `prefers-contrast: more` and forced colours
fall back to the plain flat look, so a skin never wins over a person's
contrast setting — the backdrop goes with it, and the type returns to the
player's own. **No skin means no change**: a pack with no `skin`
field bakes byte-for-byte as before, and the baked value is `null`.

Code: `src/vefr/maplab.py` (`skin_errors`) + `src/vefr/cli.py`
(`_baked_skin`) + `web/player/parts/540-the-skin.js` (`applySkin`),
`440-the-camera.js`, `448-asset-loaders.js` (the ground's pictures) and
`480-town-input-and-turns.js` (the ground);
tests: `tests/test_skin_validator.py` + `tests/test_skin_apply.py`.

## Walk sheets (a character that walks)

A sprite may carry a walk cycle: three files side by side in `sprites/`.

    sprites/hero.png            the single picture (still the fallback)
    sprites/hero-sheet.png      the frames, left to right, top to bottom
    sprites/hero.sheet.json     which frame is which

```json
{
  "image": "hero-sheet.png",
  "frame": [32, 32],
  "fps": 8,
  "directions": {
    "down":  {"idle": [0],  "walk": [1, 2, 3, 4]},
    "right": {"idle": [10], "walk": [11, 12, 13, 14]},
    "up":    {"idle": [15], "walk": [16, 17, 18, 19]}
  }
}
```

Frames number left to right, top to bottom.
`frame` is one cell's size and `fps` its pace.
A direction may be missing: a missing `left` or `right` is the other
side mirrored, and a missing `up` falls back to `down`. `down` is
required. The player draws the `idle` frame standing, a `walk` frame
per step, and settles back to `idle`. The validator checks every
sheet: the image exists beside it, `frame` and `fps` are in range, the
directions are known, and every frame index is inside the sheet's grid.

## Story status (draft words and the release gate)

An agent may draft a whole story; nothing ships as canon until the
owner has read and edited it. So a pack may say which of its words are
still drafts, with an optional `status` key: **`draft`** or
**`approved`** (the default when the key is absent, so every pack that
predates it validates and reads exactly as before). A `status` written
as anything else is a validation error naming the file, like every
other typed key.

`status` is a **sibling key on the object that already owns the words** -
no wrapper object, no second format:

| words | where the key goes |
|---|---|
| a book | its front matter, beside `title`/`found`/`kind` (above) |
| a voice file | `world.json`'s `voices.<id>`, beside `file` and `strike` |
| a speaker's voice file | `world.json`'s `speakers.<id>`, beside `voice_file` and `seeds` |
| a `say` rule | the rule, beside `when`/`if`/`then` |
| an album sticker name | the sticker, beside `name`/`kind`/`when` (Album, above) |
| an item name | the item, beside `name` (`items.<id>`) |

A voice file is the one surface with no front matter of its own - the
whole `.md` is the prompt the weaver sends, so a `---` block would
become words - which is why its status rides on the record that names
the file. A rule's status is on the rule rather than on the `say`
action because an action names exactly one thing to do, and the woven
player's rule engine reads that object key by key.

`vefr check --release` lists every draft word with its file and line:

```console
$ uv run vefr check --pack worlds/<name> --release
6 draft word(s):
  acts/act-1/world.json:20  speaker 'keeper' - voices/keeper.md is a draft
  library/a-draft-book.md:3  book 'a-draft-book' - A Draft Book is a draft
  world.json:85  voice 'draft-keeper' - voices/keeper.md is a draft
  ...
```

It lists and exits 0. Add `--strict` to make the gate fail on a draft -
it prints the whole list **first**, so a human sees what is in the way
before the non-zero exit. A pack with no drafts prints one line
(`no drafts - every word in this pack is approved`) and exits 0 under
both spellings.

This is a release gate, not a mode: **a draft word plays exactly as an
approved one does.** Nothing in `web/` reads the key, and no surface
reads it outside the gate. Code: `src/vefr/story_status.py`
(`drafts`, `errors`, `report`) + `src/vefr/library.py` (the book's front
matter) + `src/vefr/maplab.py` (the unknown-value refusal) +
`src/vefr/cli.py` (`vefr check --release --strict`); tests:
`tests/test_story_status.py` + `tests/fixtures/make_story_status_pack.py`.

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
6. **Every overlay the ruleset adds (a panel, a note, a speech box) must be continued by the Interact keys** (E, F, Space, Enter) or deliberately be a choice that keeps its own controls, and a test must say which. A player that needs a click mid-loop breaks the loop (Rylee, 2026-10-02; `tests/test_overlay_interact.py`).
7. ROADMAP entry with pasted gates; dev-guards green; merge without
   `--admin`.

## What a ruleset must never do

- Call a model from a deterministic surface (`export.py`, `weave.py`,
  `maplab.py`, `journal.py`, `desk.py` — the export law).
- Introduce timers or pressure (the truck-arrives law).
- Punish: failure bends the story or waits; it never ends it.
- Name private canon in engine code or fixtures (the neutrality guard
  reads engine surfaces on every CI run).
