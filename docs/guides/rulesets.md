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
