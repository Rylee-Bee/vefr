# Equipment: slots and icons first

Status: **steps 1-4 built** (the pack fields `slot` and `mods`, the validator, the bake, the pure `VEFR_EQUIP_ENGINE`, the Bag panel, the glossary and the guides). Rylee asked for this on 2026-10-01: "slots and icons first". Decided by Rylee on 2026-10-01: **five slots** (`hand`, `body`, `head`, `feet`, `charm`). Step 5, the pack demo, is not in this repo - see the table below.

## What exists today

From `docs/guides/rulesets.md` (loot and reward sections): a pack's `world.json` may carry an `items` catalog (`name`, `sprite`, `value`, `heal`, `use`).
Kills and chests can drop items. The hero carries them in a **bag**, a list of item ids at `localStorage['vefr-bag-<world>']`, shown in the pause menu's
Bag panel. A carried thing can be drunk (`use`) or traded. The player has `hp`, `atk` and `gold`. The reward section says plainly: **no equipping**.

## The idea

The hero can wear and hold things. Each item may fit **one slot**. Wearing it changes the hero's numbers a little, and the Bag panel shows what is worn
as a row of icons. Nothing changes how the hero is drawn: the walking frames are separate pictures, and a layered "paper doll" would need every
item drawn on every frame. That is later work.

## The pack fields (additive; absent means today's behaviour, so every existing pack loads unchanged)

```json
"items": {
  "green-cloak": {"name": "a green hooded cloak", "sprite": "cloak", "slot": "body", "mods": {"hp": 2}},
  "short-bow":   {"name": "a short bow",          "sprite": "bow",   "slot": "hand", "mods": {"atk": 1}},
  "brass-ring":  {"name": "a plain brass ring",   "sprite": "ring",  "slot": "charm"}
}
```

- `slot`: one of `hand`, `body`, `head`, `feet`, `charm`. Anything else is a validation error that names the item and the slot.
- `mods`: optional. Only `atk` and `hp` (max health), each a whole number from 0 to 9. Anything else is an error. No `mods` means a keepsake that only looks nice.
- An item with no `slot` cannot be equipped (a potion, a key). It behaves exactly as today.

## What the player sees and does

- **Bag panel** gets a "You" section above the bag: five slots, each an icon (the item's `sprite`, or a plain outline when empty) and a word ("Hand: a short bow" / "Hand: empty").
- A bag row for an equippable item has an **Equip** button. A worn slot has **Take off**. Equipping into a full slot swaps: the old item returns to the bag.
- A worn item leaves the bag list and sits in its slot, so it cannot be traded or dropped while worn (the Bag line says "Take it off first").
- One polite live line says what changed: "You put on a green hooded cloak. Health up by 2." The text always names the change; colour is never the only signal.
- Keyboard: B opens the Bag, arrows move, Enter equips or takes off. Touch: the same buttons, 44 px targets. Screen readers get the same sentence.

## The rules (deterministic: no randomness, no model call, no clock)

- **Attack** is base `atk` plus the sum of worn items' `mods.atk`. **Max health** is base `hp` plus worn `mods.hp`.
- Taking off an item that lowers max health clamps current health to the new max (never below 1).
- On the default **costume** surface, health still never drops to zero, so equipment mostly changes the displayed numbers and the look of fights, as the surface promises.
  On `story` and `stakes` surfaces it bites.
- State lives at `localStorage['vefr-equipped-<world>']` as `{slot: itemId}`, saved with the bag. A saved id that the catalog no longer has is dropped, never crashes.

## What this does not do

No weight, no durability, no set bonuses, no rarity by colour, no layered hero art, no selling a worn item, no two-handed rules. All of these can be added later without
breaking this shape.

## What is built (2026-10-03)

All five steps except the pack demo, which needs pack data in a private repo and is written up as
a companion change rather than an edit across the boundary
(`docs/guides/equipment-pack-companion.md`).

| Step | Where | Tests |
|---|---|---|
| 1. pack fields, validator, bake | `src/vefr/maplab.py` (`SLOTS`, `MOD_STATS`, `item_slot_and_mods`, `item_slot_errors`, `_door_key_items`), `src/vefr/cli.py` (`_player_items`) | `tests/test_equipment_validator.py` (39) |
| 2. the pure engine | `web/packaged.html` (`window.VEFR_EQUIP_ENGINE`) | `tests/test_equipment_engine.py` (18) + `tests/fixtures/equip_engine_harness.mjs` |
| 3. the Bag panel, equip/take off, storage, hero wiring | `web/packaged.html` | `tests/test_equipment_ui.py` (14) + `tests/fixtures/equip_ui_harness.mjs` |
| 4. glossary and guides | `docs/guides/glossary.md` (`slot`, `equip`/`take off`), `docs/guides/playing.md`, `docs/guides/rulesets.md` | `tests/test_pack_neutrality.py` |
| 5. the pack demo | **not in this repo** - needs a cloak and a bow, whose names are Rylee's | - |

The five empty-slot outlines the design asked for are drawn in code (inline SVG), not new art. The
1x1 sprites the tests use are engine-test canon and deliberately **not** the real icons.

## Art it needs

The round 8 items brief already covers the hero's kit as 128 px icons (bow, dagger, shield, boots, cloak, cap, ring, amulet, staff, spellbook, runes, potion, gem).
Five small **empty-slot outlines** (hand, body, head, feet, charm) are the only new pieces; they can be simple drawn shapes made in code.

## Checks and tests the build must carry

1. **Validator** (`maplab.validate`): item `slot` in the allowed set; `mods` keys only `atk`/`hp`, whole numbers 0..9; a clear plain-sentence error per problem. A pack with no `slot` anywhere is unchanged. **Done** (`tests/test_equipment_validator.py`).
2. **Logic harness** (node, like `tests/fixtures/combat_harness.mjs`): equip, unequip, swap, stat sums, health clamp, persistence, a missing id is dropped, a duplicate is impossible. **Done for the pure engine** (`window.VEFR_EQUIP_ENGINE`, `tests/test_equipment_engine.py` + `tests/fixtures/equip_engine_harness.mjs`): the sums, the refusals, the swap, the clamp and `clean` for a saved state the catalog no longer matches. *Persistence and storage are not part of it yet* - the engine is pure and the `localStorage` read/write belongs to the slice that draws the panel.
3. **Browser tests:** equip a cloak, see the slot icon and the sentence, take it off; the `axe-core` gate on woven players passes with the new panel.
4. **Compatibility:** the sample world bakes byte-for-byte as before (the existing compatibility test).
5. **Interact tie-in:** once one-button Interact lands, "Equip" is reachable from the Bag by the same keys; the Bag stays a pause-menu panel.

## Named edits tie-in (`design/named-edits.md`)

`add_item` gains optional `slot` and `mods`; its preview shows the item icon and what it changes ("short bow: Hand, attack +1"). Chat proposes; the player keeps.

## Build order

1. Validator and the pack fields (small, safe, testable alone). **Done** (#244).
2. Equip state and the stat maths as pure functions with the node harness. **Done** (the pure engine, #247; storage came with step 3).
3. The Bag "You" section, buttons, live line, keyboard. **Done** (#249).
4. Glossary (verbs **equip**, **take off**; noun **slot**), the rulesets guide, the player guide. **Done** (#251).
5. A demo: a private pack's cloak, bow and ring wired to real icons. **Not in this repo** - a companion change, and it needs a cloak and a bow that do not exist in the pack yet.
4. ~~Glossary (verbs **equip**, **take off**; noun **slot**), the rulesets guide, the player guide.~~ **Done.**
5. ~~A demo: a private pack's cloak, bow and ring wired to real icons.~~ **Not in this repo** - see the companion change.

## Decided and still open

**Decided (Rylee, 2026-10-01):** five slots from the start: `hand`, `body`, `head`, `feet`, `charm`.

**Still open:** whether an item that is also a key or a story item may be equipped. Recommendation: no, keep story items unequippable.
