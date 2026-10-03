# Packet equip-engine-a2: the pure equipment engine

Goal: add `window.VEFR_EQUIP_ENGINE` to the woven player — a pure module that answers the hero's
attack and max health from what is worn, and moves a `{slot: itemId}` state around. Spec:
`design/equipment.md` ("The rules" and "What the player sees and does"), #217 track A slice A2.

The contract is **frozen and merged**: `tests/test_equipment_engine.py` (17 tests) and
`tests/fixtures/equip_engine_harness.mjs`. Read both before you write anything. You do not edit tests.

## Files you may touch (nothing else)

- `web/packaged.html` — add the engine, nothing else in this file.

That is the ONLY file. Do not touch `src/`, `tests/`, `docs/`, `design/`, or any other file. If you
find something broken outside this list, report it, do not fix it.

## Where it goes

`web/packaged.html`, immediately after the `window.VEFR_GROWTH_ENGINE = (function () { ... })()`
IIFE that ends near line 2600. Use the identical shape: an IIFE that returns an object of functions,
assigned to `window.VEFR_EQUIP_ENGINE`. Plain ES5-style `var`/`function`, no arrow functions, no
`const`/`let` — match the file. The file is a single-file player that must run from `file://`.

Copy the house conventions from `VEFR_GROWTH_ENGINE` (read it first, lines 2470-2600ish):

```js
window.VEFR_GROWTH_ENGINE = (function () {
  function isObj(v) {
    return typeof v === 'object' && v !== null && !Array.isArray(v);
  }

  function isWhole(v) {
    return typeof v === 'number' && isFinite(v) && v % 1 === 0;
  }
  ...
  return { levelFor: levelFor, statsFor: statsFor, award: award, bump: bump };
})();
```

Return the object explicitly at the end. One short comment per function explaining what it decides
and why, in the same voice as the growth engine.

## The contract, exactly

```js
statsFor(base, items, equipped) -> {hp, atk}          // base plus every worn mod
equip(state, items, slot, itemId) -> {state, swapped, reason}
unequip(state, slot) -> {state, removed}
clean(state, items) -> state
clampHealth(hp, maxHp) -> number
```

`base` is `{hp, atk}`. `items` is the pack catalog `window.VEFR_ITEMS`: keyed by id, each entry may
carry `slot` (one of `hand`, `body`, `head`, `feet`, `charm`) and `mods` (`{atk?, hp?}`, whole numbers
0-9). `equipped`/`state` is a plain `{slot: itemId}` map.

**`statsFor`** — `{hp, atk}` where hp is base `hp` plus the sum of every worn item's `mods.hp`, and
atk is base `atk` plus the sum of every worn `mods.atk`. Every one of these reads as no change:
a base that is not an object; a missing or non-whole `hp`/`atk` (that stat starts at 0); a catalog
that is not an object; a worn id the catalog does not have; a worn value that is not a string; a
`mods` that is not an object; a mod value that is not a whole number. An item with no `mods` adds
nothing. **Return both keys always**, even at 0.

**`equip(state, items, slot, itemId)`** — returns `{state, swapped, reason}`.
- Success: `state` is a NEW object with `slot` set to `itemId`, `swapped` is the id that was in that
  slot before or `null`, `reason` is `'ok'`.
- Refusals return the state it was given, `swapped: null`, and a reason:
  - `'not-an-item'` — `itemId` is not a string, or the catalog lacks it, or there is no catalog.
  - `'no-slot'` — the catalog entry has no `slot` (a potion, a key).
  - `'bad-slot'` — `slot` is not one of the five.
  - `'wrong-slot'` — the entry's `slot` is not the `slot` asked for. This also covers re-equipping
    an id that is already worn in its own slot (nothing changes, reason `wrong-slot`).
- **Never write into the state you were given.** Build a copy. The caller's object is what gets
  saved; the harness freezes the input and checks it afterwards.
- A duplicate is impossible: an id already worn in some slot cannot be worn again. Because each
  item has exactly one `slot`, the `wrong-slot` rule already covers this — do not add a second check.
- Order of the checks matters: `bad-slot` before `not-an-item`? No — see the harness. The harness
  pins these: `equip({body:'cloak-1'}, ITEMS, 'charm', 'cloak-1')` is `wrong-slot` (it is worn and
  charm is not its slot), and `equip(NOTHING, ITEMS, 'belt', 'cloak-1')` is `bad-slot`. Check
  `not-an-item` first (an unknown id cannot be reasoned about further), then `bad-slot`, then
  `no-slot`, then `wrong-slot`.

**`unequip(state, slot)`** — returns `{state, removed}`. A NEW state with that slot gone, and the id
that was there, or `null` for an empty slot, a slot that is not one of the five, or a missing state
(`{state: {}, removed: null}`). Never write into the caller's state.

**`clean(state, items)`** — a NEW object keeping only the entries that are still real: the key is one
of the five slots, the value is a string, the catalog has that id, the entry still has a `slot`, and
that `slot` equals the key. Everything else is dropped. A missing state or catalog gives `{}`.

**`clampHealth(hp, maxHp)`** — a number. The smaller of the two, floored at 1. A value that is not a
finite number is treated as 0, so junk in gives 1 out and never a crash. A bigger `maxHp` must NOT
heal: `clampHealth(5, 12) === 5`.

## Constraints

- No new dependencies, no imports, no `require`. One file, no build step.
- Pure: no `localStorage`, no `Date`, no `Math.random`, no DOM, no network, no `console.log`, no
  model call. Deterministic — same inputs, same outputs, always.
- ES5-style only (`var`, `function`), matching the file. No arrow functions, no `const`/`let`,
  no template literals, no spread, no optional chaining.
- Do not wire this into anything yet. No Bag panel, no buttons, no `heroMax()`/`heroAtk()` change,
  no call sites. A3 wires it to the UI; this packet is the module and nothing else. `heroMax()` and
  `heroAtk()` (near line 1484) must read exactly as they do today.
- Do not change the existing `VEFR_GROWTH_ENGINE`, `VEFR_WHY`, `VEFR_DELVE` or anything else in the file.
- No story text, no names of monsters, no pack-specific vocabulary.
- Accessibility is not in scope here (no UI), but do not add anything that would later need a
  colour-only signal.

## Your latitude

Naming of internal helpers, structure, comment wording, and the exact shape of the shared
slot-validity helper. Make those decisions yourself without asking. Stop and report instead of
guessing only if the brief is materially ambiguous or a change would touch scope, canon, security or
architecture. Say which decisions you made in the report.

## Acceptance

```bash
cd <the clone this packet is running in> && PYTHONPYCACHEPREFIX=$(mktemp -d) .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_equipment_engine.py
```

Expected: `17 passed`. All 17 are currently `xfail(strict=True)`; they flip to passing when the engine
exists. Do NOT edit the test file to remove the markers — the orchestrator does that. If you are
unsure whether your change made them pass, run:

```bash
cd <clone> && PYTHONPYCACHEPREFIX=$(mktemp -d) .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_equipment_engine.py --runxfail
```

and read the failures: each one must fail only with `KeyError` on a missing output key (meaning the
engine is absent or the harness cannot see it), never with an assertion mismatch of real values.

Also run the two neighbours that must not regress:

```bash
cd <clone> && PYTHONPYCACHEPREFIX=$(mktemp -d) .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_equipment_validator.py tests/test_growth_engine.py tests/test_features.py
```

Expected: `39 passed` and the growth and features counts unchanged from the base commit.

If `node` is missing or `npm ci` has not been run in the clone, the harness test will error on the
subprocess, not on your code. Say so in the report rather than working around it.

## Report

End with: the files you changed, the diff summary, the acceptance commands and their **verbatim**
output. Do not claim tests pass in prose; the orchestrator runs them again. List the five functions
you exported and one line each on what a malformed input does.
