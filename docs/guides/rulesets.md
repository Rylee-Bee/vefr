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
| `transitions` | list of strings | the Road's seeds: where this act can lead (connective tissue, Phase 2) |
| `cooking` | object | the cooking loop's content (below) |
| `desk` | object | the desk loop's content (below) |

All optional. Absent means the engine's defaults, so every existing pack
loads unchanged. `maplab.validate` shape-checks whatever is declared
(orders must reference real pantry ids; headlines must be at least two
non-empty strings; verbs/enemies/bosses/transitions must be lists of
strings).

## cooking (Act 1's loop)

```json
"cooking": {
  "opening": "Day one after the quiet. The grill remembers heat.",
  "byline": "by Scoop - breakfast burrito truck, editor of one",
  "pantry": [{"id": "egg", "label": "fried egg"}],
  "tickets": [{
    "id": "t1", "customer": "Rosa", "order": ["egg", "salsa"],
    "note": "The usual, mija. Egg, and the red one that bites.",
    "thanks": "Rosa eats standing up, already turning toward the day.",
    "kind_line": "Rosa eats it anyway, nodding at something only she can see."
  }],
  "morning_length": 3,
  "headlines": ["FIRST TRUCK ON THE ROAD SERVES BREAKFAST AGAIN"]
}
```

The loop: tickets arrive as **spoken notes** (reading them is the game —
the order ids stay hidden); the player wraps from the pantry and serves;
resolution is deterministic set equality; a wrong burrito gets its
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
