# The album: a shelf of everything you have met and found

Status: **proposed** (Rylee, 2026-10-02: "how do you reward progression and completeness while still being cozy ... I want everything"; for the shelf she chose the sticker album first, then a bestiary, item list and map as separate logs later, and said VEFR itself needs all of them). No code yet. This is a pack-contract addition, so it waits for approval before a build.

## The one rule

**Rewards only add. Nothing is ever taken away, timed, or missable for good.** (The studio's sticker book says the same: "nothing to lose", `src/vefr/achievements.py`.) Everything below follows from it.

## What exists today (checked 2026-10-02)

- The studio has a sticker book for using VEFR itself (`src/vefr/achievements.py`, `web/achievements/`): open, riddle and secret stickers, shine levels (paper, foil, holo). It is **not** available to a game made in VEFR.
- A woven game already remembers: books found (`vefr-library-<world>`, the Books panel says "N still to find"), monsters slain (`saveSlain`), the bag, the fog (explored tiles), gold.
- Rules notice eleven events (`docs/guides/rules.md`: defeats, picks-up, reads, enters, opens, buys...).

## The design: one record, many views

**1. One record of "met".** The player keeps `localStorage['vefr-record-<world>']`: `{enemies: {id: times}, items: [ids], books: [ids], regions: [names], people: [keys]}`. It is written from facts the player already performs (the same seams that fire rule events), never from a model, never lost by Start over unless the player asks. A saved id the pack no longer has is dropped, never crashes. This record is what every view reads.

**2. The album is the first view.** A pack may declare stickers:

```json
"album": [
  {"id": "met-the-rat", "name": "Cellar rat", "kind": "open",   "when": {"defeats": {"what": "floor-1-rat"}}},
  {"id": "the-first-letter", "name": "A letter, folded small", "kind": "riddle", "riddle": "Someone kept a promise about cakes.", "when": {"reads": {"what": "a-letter-in-a-chest"}}},
  {"id": "the-lit-window", "name": "A light in the window", "kind": "secret", "shine": "holo", "when": {"phase-changes": {"to": "dawn"}}}
]
```

`when` uses **the same event vocabulary as rules** (one thing to learn). `kind`: `open` (shows its picture and name from the start, as a silhouette), `riddle` (shows only its riddle until earned), `secret` (shows only in a count: "3 secrets"). `shine`: `paper` (default), `foil`, `holo`. The picture is the thing's own sprite (as a silhouette until found); a pack may give `art` for a painted sticker. An `all` sticker may be earned by `{"earned": "half" | "all" | N}` stickers, the completionist reward, never required for the story.

**3. How it looks and sounds.** An Album button next to Bag and Books. A found sticker says "You found a sticker: Cellar rat" once, politely, with no sound or flash needed (motion off is respected). The album shows "12 of 30 found, 3 secrets" in plain text. No streaks, no percentages nagging, no clock.

**4. The logs come later and are views of the same record.** A **bestiary** (every enemy met, its picture, how many you have beaten), an **item list**, and a **map** of what you have explored. Each is a screen over `vefr-record-<world>` plus the pack's catalogs. Designing the record now is what makes them cheap later.

**5. Rules can react to the album, not the other way round.** A sticker earned could fire a `earns` event in a later slice (so the town can warm when the shelf fills). Not in the first slice; the no-chains law holds.

## What this does not do

No achievements that punish, no hidden counters you can fail, no daily anything, no online sharing, no spending stickers. No logs in the first slice. Cottage's art for stickers is a later art pass.

## Checks the build must carry

1. Validator: `album` shape, `kind`/`shine` sets, every `when` names a declared thing (the rules identity model), ids unique, `riddle` required for riddle stickers. A pack without `album` is unchanged.
2. Pure engine block (like `VEFR_RULES_ENGINE`): record update, sticker evaluation, "earned" counts; a node harness pins it.
3. A woven-file play test: defeat the rat, read the letter, see the stickers appear once, silhouettes before, riddle text for the riddle sticker, secret only as a count, persistence across a reload.
4. Axe-core: the Album panel passes the existing accessibility gate; every state is text, never colour alone.
5. Compatibility: a pack with no `album` plays as before.

## Build order

1. The record (pure, tested) and its writers at the existing seams.
2. The `album` block: validator, engine, panel, live line.
3. Cottage declares its first dozen stickers (the five monsters, the letters, the Keeper, each floor entered).
4. Logs: bestiary first, then items, then map, as views over the record.
5. The studio's own sticker book moves onto the same engine pieces where it is cheap.

## Open for Rylee

- Names and pictures for Cottage's stickers (hers to keep or change; nothing is canon until she says).
- Which of the three secrets Cottage should hide, and where.
