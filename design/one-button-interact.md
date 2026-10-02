# One-button Interact

Status: built. Decisions below were made by Rylee on 2026-10-01 (E with Space and Enter; facing first, then nearest;
a gentle nudge when nothing is in reach; combat folded into Interact; the label says what it will do).

## The problem

The woven player has three separate "use" paths, on three keys, with three different reach rules (`web/packaged.html`):

| Today | Key | What it reaches |
| --- | --- | --- |
| `tryNPC` | E, Space, Enter, the Talk button | the nearest speaker within 2 tiles (Manhattan) |
| `useHere` | F, the Interact button | doors, chests and notes on the hero's OWN tile, plus a trader nearby |
| `heroAttack` | arrow keys | an enemy on the tile you walk into (bump to attack) |

A new player has to learn which key does which, and E and F answer different questions. One verb is easier to learn,
to teach, to put on a touch screen, and to say aloud for a screen reader.

## The design

**One verb, `interact()`**, on E, Space, Enter and one on-screen button. F stays as an alias so nothing existing breaks.

**1. Find what is in reach.** Build a list of candidates, each with a kind and a tile:
resident (talk), trader (trade), chest (open), door or stairs (go through), place of interest (look), enemy (fight).
Reach is one tile for things you touch (chest, door, enemy, place) and two tiles for people (the current talk reach).
A door or chest on your own tile counts as distance zero.

**2. Pick one.** In order:
1. the thing on the tile the hero is **facing** (`heroFacing`, already kept by hero motion);
2. else a thing on the hero's own tile;
3. else the **nearest** in reach.
Ties break by kind: door or stairs, chest, trader, resident, place, enemy. The pick never changes mid-press.

**3. Do it.** Each kind calls the code that exists today: `enterRegion`, `foundBook` plus `giveChestDrops`, `openTrade`,
the speech path from `tryNPC`, `showSpeech` for places. Nothing about what those do changes.

**4. The label says what it will do.** The button and the `#use-hint` line update as the hero moves or turns:
"Open the chest", "Talk to <name>", "Trade with <name>", "Go through the door", "Look at <place>", "Face the <enemy>".
The text is the same for screen readers (`aria-live="polite"`, already on `#use-hint`). The target tile gets a thin ring
drawn on the canvas, so the picture and the words agree.

**5. A gentle nudge, never an error.** With nothing in reach, Interact says one friendly line ("Nothing to use here.
Walk up to something and try again.") in `#near`, spends no turn, and costs nothing.

**6. Combat folds in, bump-attack stays.** Walking into an enemy still strikes, exactly as today (Rylee, 2026-10-01).
Interact on a faced or nearest enemy is the second way to fight: it opens a small verb menu built from the surface's
verbs (today `Strike` and `Console` on the default costume; the list already comes from `web/packaged.html` near the
`['attack', 'Strike']` pairs). A surface with one verb acts at once. Enemies take their turn after a verb resolves, as
after a bump. This keeps fights familiar and gives non-attack verbs (Console) a home.

**7. Interact continues whatever has the screen (Rylee, 2026-10-02).** While a note is open, E, F, Space and Enter turn the page,
and on the last page close it; while a speech box is up they close it instead of starting a second talk. A focused button keeps its
own Enter and Space, and a held key never carries on into the next thing. Trade, the menu and the Bag are choices, not reading, so
they keep their own controls. Pinned by `tests/test_overlay_interact.py`.

## What does not change

Movement (one tile per call), the camera, hero motion, doors needing a deliberate use (passing a doorway never yanks you
away), item pickup on walking, trade and reader dialogs, fog, light, and pack-authored text. The `VEFR_MOTION` hooks stay.

## Accessibility

Every verb is reachable by one key and by one tap. The label is text first. Nothing depends on colour. The nudge is
polite, not an alert. The button is never the only way: keys keep working with the button hidden.

## Risks and open questions

- Two ways to fight (bump and Interact). If that feels confusing in play, a pack flag `bump_attack: false` is the
  planned escape hatch (not built now). The foreman must grep `worlds/` and `tests/` for bump-attack reliance and report.
- Touch targets: one big button is enough on a phone; a long-press for the verb menu is NOT proposed.
- Talk reach stays 2 tiles; if a resident and a chest tie, the chest wins by the kind order above.

## Tests the build must carry

1. Pure-logic tests in the existing node harness style (`tests/fixtures/*_harness.mjs`): candidate list, facing-first,
   nearest fallback, tie order, nothing-in-reach nudge, and that no turn passes on a nudge.
2. Browser tests (`tests/browser/`): press E, Space, Enter and F next to a resident, a door, a chest and a trader;
   the hint text matches the action; the ring appears on the target tile.
3. Combat: moving into an enemy still strikes; Interact on an enemy opens the verbs; `Strike` hurts the enemy; one-verb
   surfaces act at once; enemies still take their turn.
4. A regression test that every previously reachable action is still reachable.

## Build order

1. `interactTargets()` and `interact()` as pure functions, with the logic tests (no UI change yet).
2. Wire E, Space, Enter, F and the button to `interact()`; label and hint; the ring.
3. Fold combat in; update the surface verbs menu.
4. Update `docs/guides/glossary.md` (verb **interact**) and the player guide; update the first-ten-minutes walk-through.
