# 0015 - Wardens, vaults and the town gate

Date: 2026-10-04

## Status

Proposed. Becomes Accepted when slice E8 merges. Plan: `docs/plans/endless-dungeon/PLAN.md` sections 1, 2, 4 and 5.

This ADR amends **ADR 0006**: "act advance" becomes **town states**. The edit to 0006 and the roadmap's NEXT entry land in E8's PR.

Rylee's calls:
- a key warden ends each Section;
- the vault note advances the act;
- acts change only the town;
- the next Section waits for a visit to town, and a paid shortcut can skip that visit;
- the King ends Act 3, and endless mode comes after him.

## Context

E0b found that `lockOpen` opens a transition when `requires.item` is in the bag *or* `requires.flag` is `true`, never consuming the key, and that generated regions can be inserted before `enterRegion`. ADR 0006 moved the hero to a new act region; here only the town changes. Returning to town clears a Section's kills and chests, which would revive wardens and vault chests unless they are story state.

## Decision

### Warden

```json
{"id":"ashwing","family":"moth","hp":3.0,"atk":1.6,"scale":1.4,"carries":"ashwing-key",
 "hall":"warden-hall-moth","placement":"farthest-off-path","endless":{"affixes":1}}
```

- Closed keys; `placement` has one value; `hp`, `atk` in [1.0, 4.0], whole hundredths, combined as in ADR 0014.
- It stands on its hall stamp's `warden` anchor. The hall has exactly one used socket, so it is a leaf off the up→down path (asserted).
- Spawn `{"id":"w","family":…,"warden":"ashwing","at":…}`, outside the monster budget.
- On death the key goes **straight into the bag** with a line, so it cannot be lost, and `warden:<id>:c<c>` is set.
- In cycles `c >= 1` it draws `endless.affixes` affixes on the `loot|w` stream; "Proud" adds one.

### Vault

```json
{"id":"vault-cellar","stamp":"vault-small","needs":"ashwing-key","note":"library/truth-one.md",
 "chest":["…"],"sets":"vault-1-read","home":"town"}
```

- **Where it is.** The vault stamp sits on the warden floor. Its single `+` is the **vault door**.
- **The door.** A transition with `requires: {"flag": "warden:<id>:c<c>"}`; its `locked_text` names the key. A flag, not the item, because keys are never consumed and a cycle-0 key would open every later vault. `needs` stays so `vefr check` can trace the key.
- **UNKNOWN: how the door opens.** Its `to` is the same region and `to_at` the tile just inside. Whether `enterRegion` into the current region keeps floor state is UNKNOWN; E8's first test checks it. If not, E8 adds a B2 `door` place that opens in place; nothing else changes.
- **The note.** The `note` anchor is a library book. Opening it fires the shipped `opens {what: <book id>}`, and a rule `opens → set <sets>` records that it was read.
- **The chest and the way home.** The `chest` anchor holds the loot. The `home` anchor is a stair to `home`.

### The town gate and the paid shortcut

- The warden floor's down stair and the town stair's entry for the next Section carry `requires: {"flag": "town-seen:<section>:c<c>"}`.
- A rule on `enters town`, guarded by the vault's `sets` flag, sets `town-seen`. The Section expansion emits it; packs never hand-write it.
- **Shortcut:** offered only when `c >= 1`, so a first pass never skips the story (plan challenge 7). Paying debits gold once and sets `town-seen:<s>:c<c>` and `shortcut-paid:<s>:c<c>`; a second press finds the flag set and charges nothing. The price is the Section's `shortcut` integer; its value is UNKNOWN (owner).

### Town states (ADR 0006 rescoped)

```json
"town_states": {"region":"town","states":[
  {"id":"act-2","when":"vault-1-read","use":"town-act-2"},
  {"id":"act-3","when":"vault-2-read","use":"town-act-3"},
  {"id":"after-king","when":"king-slain","use":"town-after-king"}]}
```

- Each `use` is an ordinary authored region, baked as usual: no patches, no new runtime language.
- Entering `region` loads the **last** state whose `when` is true, else `region`. Derived on each entry, never stored.
- The act is 1 plus the number of true story vault flags; `king-slain` opens the endless board. ADR 0006's `act-completes` event and per-act surfaces are withdrawn.
- All states share `region`'s save identity. A dropped item now on a wall moves to the nearest floor tile, scanning row-major.

### Save state

- **Permanent story flags.** These are never evicted or reset:
  - `warden:<id>:c<c>` and `vault-chest:<id>:c<c>`;
  - each vault's `sets` flag;
  - `town-seen:*` and `shortcut-paid:*`;
  - landings;
  - `king-slain`.
- A warden whose flag is set is not spawned; a vault chest whose flag is set opens empty. A town return cannot revive either.
- Floor deltas are the plan's: identity triple, killed ids (including `w`), taken chests, dropped items, found secrets, explored bitset.
- **The bitset encoding** belongs to slice F1; beyond "1 bit per tile, base64" it is UNKNOWN. At 128x96 the raw bitset is 1,536 bytes, about 2 KB in base64, over the 1.5 KB per-floor budget: F1 must run-length encode it, or the owner raises the budget.
- An identity mismatch drops deltas and keeps every flag. The 40-floor cap evicts only deltas.

### What `vefr check` must prove

These hold for every Section, for seeds `check-0..199`, in cycles 0 and 1:

1. The hall and the vault are placed (ADR 0013). The `warden` anchor and the vault door can be reached from `up` without using secret doors.
2. `note`, `chest` and `home` can be reached from the vault door.
3. `carries` names a declared item that is `keep` and has no value. That item is in no shop, in no chest table, and in no secret room.
4. Every `sets`, `when` and gate flag has a setter.
5. **Progress walk.** A flag-only simulation starts with no flags and repeats three steps over the Sections: kill the warden, read the note, enter town. It must open every Section and reach `king-slain`. In cycle 1 it must also succeed when it uses the shortcut, and the shortcut must never be offered in cycle 0.
6. Every `use` region exists and validates.

## Consequences

- One gate mechanism: `requires` flags through `lockOpen`; the Keybearer chain becomes flag locks.
- Each town state is one more baked region (ADR 0006's bake cost; town maps are small).
- About five flags per Section per cycle: negligible.

## Acceptance

- `tests/test_wardens_vaults.py`: the shapes, golden rejection sentences, and checks 1–4.
- `tests/test_progress_walk.py`: check 5, plus a fixture with a missing setter that fails with a sentence.
- `tests/test_town_states.py`: the last true state wins, no true flags gives the base region, and an item moves off a new wall.
- `tests/browser/test_vault_to_town.py`: the warden dies and the key is in the bag; the door opens; the note is read; the home stair leads to a changed town; the next stair is open.
- `tests/browser/test_shortcut.py`: there is no shortcut in cycle 0; in cycle 1 it charges once, and pressing again is free.
- `tests/test_story_flags_survive.py`: after a town return, an identity mismatch and an eviction, the warden stays dead and the chest stays empty.

## Owner decisions (2026-10-04) and open questions

1. **Decided: offered from the second cycle on, and paid with a one-use item found in a vault** (not gold). **Every section's vault drops one** (owner, 2026-10-04).
2. In endless mode, does a town visit still gate each Section when the town no longer changes?
3. Does "New descent" (a new seed) replay the story, or count as a later cycle?
4. Do vault notes read again in endless mode, or do those vaults hold only loot?
5. **Decided: its own region behind the final boss's door.** *(Per game since Amendment 1: a pack may end its story without a final boss.)*
6. What are the town lines, residents and shop stock for each state?

## Amendment 1 (proposed 2026-10-08; awaiting Rylee's approval)

Cottage of the Breeze, Rylee's decisions of 2026-10-08: **"No final boss"** (the story ends in a quiet room you reach and return from) and **"Different kinds of guardian encounters"** (a fight, a way past, an interaction). Her guidance: *"The engine should retain the ability to support final bosses in other games"* and *"I do not want a Cottage-specific workaround or three separate engine systems if an existing encounter contract can support these differences."* E8 is not built yet, so this amends design text only. Everything above stands except where this section says otherwise.

1. **The story end is a per-game flag.** A pack's `descent` names it: `"story_end": "<flag>"`, default `king-slain`. A final boss behind its own door, as decided above, stays fully supported. A pack may instead set the flag with any rule, for example on entering a final authored region reached through the last Section's vault door. Endless mode opens on `story_end`. Wherever this ADR says `king-slain` opens the endless board or ends the progress walk, read `story_end`.
2. **A warden's challenge.** A warden takes an optional `"challenge"`:
   - `"defeat"` (the default): exactly the current text. On death the key goes straight into the bag and `warden:<id>:c<c>` is set.
   - `"rule"`: a pack rule sets `warden:<id>:c<c>` (for example on `picks-up`, `uses-with` or `comes-near`). The moment the flag is set, the key goes into the bag with a line, the same as on death.

   The vault door, the town gate and the save rules see only the flag, so they do not change. Two optional presentation keys:
   - `"yields": true`: a defeated warden stays on its anchor, no longer hostile, instead of vanishing.
   - `"fightable": false`: only with `"rule"`. The warden cannot be attacked. It still sleeps, wakes and hunts by ADR 0014's sight and noise rules, so the hall stays dangerous and the Section's danger still rises.
3. **Town states for more than one region.** `town_states` may be a list of `{"region", "states"}` blocks, one per region (the town, an interior such as a tavern or a home). The single-block form above stays valid. Each region still loads its last true state, derived on entry and never stored.
4. **The checks.** Check 5's "kill the warden" becomes "complete the warden's challenge" (set its flag), and "reach `king-slain`" becomes "reach the pack's `story_end`". Check 4 (every flag has a setter) already requires a setter for a `"rule"` warden's flag, so a rule warden with no rule fails `vefr check` with a sentence.
5. **Acceptance additions** (in E8's tests):
   - a fixture whose warden has `"challenge": "rule"` passes the progress walk with a rule as its setter, and fails with a sentence without one;
   - a `"yields"` warden stays on its anchor after defeat;
   - a `"fightable": false` warden cannot be attacked;
   - a list-form `town_states` loads per region;
   - a pack whose `story_end` is set by entering a region opens endless mode with no boss.

**Order.** A `"rule"` warden needs rules that can name things on a generated floor. That comes from VEFR's pinned-placement work (books, chests and named things at a depth), which E8's vault notes also use. E8 may therefore ship `"defeat"` first and add `"rule"` once that work lands. Nothing here changes ADR 0010, 0013, 0014 or 0016.
