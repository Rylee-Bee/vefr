# Packet equip-ui-a3: the Bag "You" section

Goal: draw the worn gear in the pause-menu Bag panel, with working Equip and Take off
buttons, a swap into a full slot, a polite live line, and the state saved and reloaded
honestly. Spec: `design/equipment.md` ("What the player sees and does" and "The rules"),
#217 track A slice A3.

The pure engine is **built and merged** (#247): `window.VEFR_EQUIP_ENGINE` with `statsFor`,
`equip`, `unequip`, `clean` and `clampHealth`. **You call it. Do not re-implement any of it**
and do not change it — if you think it is wrong, report that instead.

Read first, in this order:
1. `docs/packets/equip-engine-a2.md` — the engine's contract, function by function.
2. `web/packaged.html` around the Bag panel, and around `heroMax()` / `heroAtk()` (~line 1484)
   and `loadHeroHp()` (~1500). The engine is at ~2640.
3. `tests/test_declutter.py` and `tests/test_quiet_ui.py` — the two suites that already pin
   this panel's layout. Your change must not break either.
4. `docs/guides/accessibility-contract.md` — the seven rules. This is a UI change, so it applies
   in full.

## Files you may touch (nothing else)

- `web/packaged.html` — the player: the Bag panel, the hero stat reads, the storage.
- `tests/fixtures/equip_ui_harness.mjs` — **new**, the harness (below).
- `tests/test_equipment_ui.py` — **new**, the pins (below).

`web/packaged.html` also holds the woven player for **every** pack, so this is the highest-risk
file in the repo. Change as little as you can: the Bag panel, the storage helpers, the two
stat functions, and nothing else. If a change would ripple further, stop and report it.

## Files you may NOT touch

`src/**` (the engine, the validator, the bake), `web/*.css`, `docs/**`, `design/**`, and any
existing test. The A2 tests, the A1 validator tests, the declutter and quiet-UI suites are all
frozen: your change must not alter a single assertion in them.

## The contract, exactly

**Storage.** `localStorage['vefr-equipped-' + worldName]` holding `{slot: itemId}`, written with
the bag, exactly as `design/equipment.md` says. Follow the house pattern already in the file
(`BAG_KEY` at ~963, `heroHpKey()` at ~1495): every read and write is wrapped in `try {} catch {}`,
because a sandboxed iframe can make `localStorage` throw (#224). A stored value that is not a
usable object is treated as nothing worn — never a crash. On load, run the engine's `clean`
against the real catalog and save nothing else: a saved id the catalog no longer has is dropped.

**The panel.** The Bag panel gets a **"You"** section *above* the bag list: five slots, in the
order `hand`, `body`, `head`, `feet`, `charm`. Each row is the slot's word, the item's sprite
when something is worn, and a plain drawn outline when it is empty. The row's accessible name is
the sentence the design gives: **"Hand: a short bow"** / **"Hand: empty"** — one string, so a
screen reader reads the same thing the eye sees. Empty-slot outlines are drawn in code (an inline
SVG or a CSS box), not new art files.

**Buttons.** A bag row for an equippable item gets an **Equip** button. A worn slot gets **Take
off**. Equipping into a full slot swaps: the outgoing item goes back to the bag. Buttons are real
`<button>` elements with a visible label or an `aria-label`, and **the whole row is not the
target** — the button is. Touch targets are **44px minimum** (rule 1); the existing small icon
buttons in this panel are the pattern to copy, not to exceed.

**The live line.** One plain sentence per action, through the narrator line the panel already
uses, naming the change in words — the design's own example is **"You put on a green hooded cloak.
Health up by 2."** Colour is never the only signal (rule 2). On a swap, say what came off. On a
refusal, say the plain reason the engine returned (`no-slot`, `wrong-slot`, `not-an-item`,
`bad-slot`) in words, not as the code. A worn item is **not** in the bag list, so it cannot be
traded or dropped while worn; if anything can still reach it, the line says "Take it off first."

**The stats.** `heroMax()` and `heroAtk()` add the engine's `statsFor(...)` to what they already
return, the same way they already add `growthStats()`. **On the `costume` surface health never
drops to zero** — that promise is in the design and must survive this change. When something is
taken off and current health is above the new max, call `clampHealth` and store the result through
the existing hero-health save. **Check the item's `use`/`heal` and `light` fields too:** a
slotted item cannot carry them (A1 refuses it), so nothing here should try to drink a cloak.

**Keyboard.** `B` opens the Bag as it does today. Within the panel, `Tab` reaches the buttons in
DOM order and `Enter`/`Space` activate them — the same keys the rest of the panel already answers
(PR #224/#240 territory). Arrow-key movement is already in the panel; do not remove it.

**No model call, no randomness, no clock.** Equipping is deterministic. `design/equipment.md` says
so and so must the code.

## Tests you must write (they are part of your packet)

Two new files, following the existing house pattern exactly — read
`tests/fixtures/lock_play_harness.mjs` and `tests/test_locked_stairs.py` first and match them.

**`tests/fixtures/equip_ui_harness.mjs`** — a jsdom harness that loads a **woven** file
(`cli.weave_html` of a pack built by `tests/fixtures/make_equip_pack.py`, which already exists and
already has a cloak, a bow, a ring and a potion), drives the real panel, and prints one JSON
object. Use the `beforeParse` canvas/matchMedia stubbing the other harnesses use, and
`w.close()` at the end. Drive it through the **DOM and the keyboard**, not by calling internal
functions: this slice is about what a player can actually do.

**`tests/test_equipment_ui.py`** — weave once in a module-scoped fixture, run the harness, assert
the JSON. At minimum, pin:
1. the five slots appear, in order, each with its accessible name sentence, and empty ones read
   "empty";
2. a bag row for a slotted item has an Equip control; a worn item is **not** in the bag list;
3. equipping shows the live line, and the slot now names the item;
4. **attack and max health change by the worn mods** — the real numbers, read from the live
   `heroAtk()` / `heroMax()`;
5. equipping into a full slot swaps and the outgoing item is back in the bag, with a line naming
   what came off;
6. Take off restores the numbers, and clamps health when the new max is lower;
7. a **potion cannot be equipped** (no-slot) and the line says so in words;
8. state survives a **reload**: re-weave or re-read, and the same slots are still worn;
9. a saved id the catalog no longer have is dropped on load, with no crash;
10. the panel still passes the frozen declutter and quiet-UI suites (do not edit them; just do not
    break them).

**These are new tests, not xfails.** They must pass in the same PR as the code. Do not add
`xfail` markers — there is no later slice to flip them; you are writing both halves.

## Constraints

- ES5-style only (`var`, `function`), matching `web/packaged.html`. No arrow functions, no
  `const`/`let`, no template literals, no optional chaining.
- One file, no build step, no new dependency. It must run from `file://`.
- Every `localStorage` access inside `try {} catch {}`.
- 44px minimum targets. Keyboard reachable. Every control has an accessible name. No
  colour-only signal. Motion: none added.
- No story text, no monster names, no pack-specific vocabulary. Neutral engine-test canon only.
- Do not change `VEFR_EQUIP_ENGINE`. Do not change `heroHpKey`, `BAG_KEY`, the bag read/write, or
  the growth engine.

## Your latitude

Function and variable names, DOM structure, the exact wording of the live lines beyond the
examples, the SVG for an empty outline, and the test shape. Make those decisions yourself without
asking. Stop and report instead of guessing only if the brief is materially ambiguous, or a change
would touch scope, canon, security or architecture, or you would have to modify a frozen test to
make your code pass. **Say which decisions you made in the report.**

## Acceptance

```bash
bash tests/run.sh tests/test_equipment_ui.py
```
Expected: all passed, no xfails.

```bash
bash tests/run.sh tests/test_equipment_engine.py tests/test_equipment_validator.py \
  tests/test_declutter.py tests/test_quiet_ui.py tests/test_locked_stairs.py
```
Expected: every one of those suites passes, unchanged. If you need to edit one of them to make
your code pass, **stop and report that instead** — that is a signal the design is wrong, not that
the test is.

```bash
python3 scripts/check_public_surface.py
```
Expected: `public-surface: clean`.

**Take a screenshot of the panel before and after** (`scripts/capture-screenshots.py` has the
recipe) and look at them yourself. A pass that reads well and looks broken is a fail.

## Report

End with: the files you changed, the diff summary, each acceptance command and its **verbatim**
output, and what the screenshots showed. Do not claim tests pass in prose; the orchestrator runs
them again. List any place where you had to choose between two readings of the brief.
