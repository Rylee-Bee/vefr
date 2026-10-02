# Growth: levels, or learning by doing

Status: **built** (Rylee asked for this on 2026-10-02: "wire in classic xp and growth and learn-by-doing into the engine, but I think that cottage should be standard. just don't lose the learn by doing.. that's important for another game I'm working on"). Both modes are in the engine and off by default; Cottage turns on classic levels later.

## What exists today

Checked 2026-10-02: the hero has fixed `hp` and `atk` (`"player": {"hp": 6, "atk": 2}`, defaults 6 and 2). Nothing in `src/`, `web/` or the docs mentions experience or levels. A killed enemy can drop items; it grants nothing else. Equipment is also only a proposal (`design/equipment.md`).

## The idea

Two ways for the hero to get stronger, one shape for both. A pack picks **one mode**:

- **`levels`** (classic). Defeating enemies earns XP. Enough XP is a new level. A level adds a little health and attack.
- **`practice`** (learn by doing). Each thing the hero does a lot makes her better at it: strike often and her attack grows, take hits and her health grows. No levels, no XP bar. Growth is a quiet consequence of play.

Neither is on by default. A pack with no `growth` key behaves byte for byte as today. Cottage chooses `levels`; `practice` stays in the engine for other games.

## The pack fields (additive; absent means today's behaviour)

```json
"growth": {
  "mode": "levels",
  "levels": {"xp": [0, 10, 25, 50, 90, 150], "gain": {"hp": 2, "atk": 1}}
}
```

```json
"growth": {
  "mode": "practice",
  "practice": {
    "atk": {"by": "strikes",  "every": 12, "gain": 1, "cap": 4},
    "hp":  {"by": "hits-taken", "every": 8, "gain": 1, "cap": 6}
  }
}
```

and on an enemy (levels mode only; absent means 0):

```json
{"id": "rat", "hp": 4, "atk": 1, "sprite": "rat", "xp": 3}
```

- `levels.xp` is a strictly rising list of whole numbers starting at 0; entry N is the XP that reaches level N+1. At most 20 entries. The hero starts at level 1.
- `levels.gain` and `practice.<stat>.gain` use only `hp` and `atk`, whole numbers 0 to 9 (the same two stats equipment may change).
- `practice.<stat>.by` is one of `strikes` (hits the hero lands), `hits-taken` (hits that reach her), `consoles` and `hurls` (those combat verbs used). `every` is whole 1 to 99, `cap` is the most the stat can grow in total.
- Anything else is a validation error that names the field and says what is allowed.

## What the player sees

- **Levels:** a short line when XP is earned ("The rat is beaten. 3 experience."), a plain line at a level-up ("You are stronger. Level 2: health up by 2, attack up by 1."), and the Bag/status area shows "Level 2 · 14 of 25 experience". The numbers are text; nothing depends on colour or a bar.
- **Practice:** one plain line when a stat grows ("All that striking is paying off. Attack up by 1."). A "You" line shows the totals. No counters are shown while it ticks; the surprise is the point.
- On the default **costume** surface the hero still never drops to zero, so growth changes the displayed numbers and how quickly fights end. It bites on `story` and `stakes`.

## The rules (deterministic: no randomness, no model call, no clock)

- Hero attack = base `atk` + growth gain + worn equipment `mods.atk` (when equipment exists). Same for max health.
- A level-up (or a practice growth) raises max health and also heals by the same amount, never beyond the new max.
- State is saved at `localStorage['vefr-growth-<world>']` as `{xp, counts}`, beside the bag. Level and the gained stats are **derived from it every time**, never stored, so a changed table in a re-woven game cannot leave a stale level. A saved key the pack no longer has is dropped, never crashes.
- Start over clears it, like the bag.

## Rule-engine tie-in

Growth can matter to the story ("when the hero is level 3, the keeper says…"). One new event is proposed, **not** in the first slice:

| `when` | Means | Fires from |
|---|---|---|
| `{"grows": {"to": N}}` | the hero reaches level N (levels mode) | the XP award that crosses the line |

It would be a twelfth event, a fact the player already performs, so it follows the "no chains" law. Until it exists, a pack cannot react to growth. Decide after the first slice is played.

## What this does not do

No classes, no skill trees, no spells-per-level (the DESIGN checklist's "learn one per level" is a later ruleset that would build on `levels`), no stat points to spend, no XP from anything but defeating enemies in the first slice, no mixing the two modes in one pack. All of these can come later without breaking this shape.

## Checks and tests the build must carry

1. **Validator** (`maplab.validate`): the `growth` shape above, enemy `xp` only in levels mode, plain-sentence errors. A pack with no `growth` is unchanged.
2. **Logic harness** (node, like `tests/fixtures/combat_harness.mjs`): pure functions for XP to level, the stat sums, practice thresholds and caps, the heal on growth, persistence, a missing id or changed table recovered.
3. **Played in the real woven file** (like `tests/test_events_play.py`): defeat enemies, see the lines and the numbers change; a practice pack grows after N strikes.
4. **Compatibility:** a pack without `growth` behaves as before and bakes `window.VEFR_GROWTH = null;`; it is no longer byte for byte. The `axe-core` gate passes with the new status text.

## Build order

1. Validator and the pack fields (small, safe, testable alone).
2. The pure growth maths with the node harness (both modes).
3. Wire into the woven player: award on defeat, the lines, the status text, persistence, Start over.
4. Docs: glossary (**experience**, **level**, **practice**), `rulesets.md`, the player guide.
5. A demo pack for `practice` (a tiny test world, not Cottage) so the mode stays alive and tested. Satisfied by the test fixture `tests/fixtures/make_growth_pack.py`.
6. Cottage turns on `levels` and sets enemy `xp` by playing.

## Decided and still open

**Decided (Rylee, 2026-10-02):** both modes live in the engine; Cottage uses classic levels; learn-by-doing must not be lost.

**Open for Rylee (feel, tune by playing):**
- Cottage's numbers: how many levels, how fast. The sample table above (6 levels, 10 to 150 XP) is a first guess.
- Whether the level-up should be a small moment (a line, a jingle later) or a quiet one.
- Whether Cottage's `grows` event is wanted for story beats.
- For `practice`: which verbs and caps the other game wants. The sample is only to prove the shape.
